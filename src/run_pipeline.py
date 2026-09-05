from database_utils import (
    create_postgis_engine,
    export_to_postgis,
    get_table_count
)

import logging
from datetime import datetime

from pipeline_qa import (
    require_columns,
    require_crs,
    require_no_invalid_geometry,
    require_no_empty_geometry,
    require_nonempty
)

from pathlib import Path

import geopandas as gpd
import pandas as pd

from geometry_utils import (
    repair_geometry,
    geometry_qa
)

from attribute_utils import (
    clean_landuse_text,
    join_landuse_mapping,
    split_analytical_features
)

from spatial_analysis import (
    add_area_fields,
    dissolve_by_category,
    summarize_area,
    intersect_with_districts,
    build_mrt_coverage,
    analyze_mrt_landuse_coverage
)


# =========================================================
# Project paths
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_TABLES = PROJECT_ROOT / "outputs" / "tables"
LOG_DIR = PROJECT_ROOT / "logs"
ENV_PATH = PROJECT_ROOT / ".env"

# =========================================================
# Pipeline configuration
# =========================================================

EXPECTED_EPSG = 3826
EXPECTED_CATEGORY_COUNT = 14
MRT_BUFFER_DISTANCE = 800
EXPORT_TO_POSTGIS = True
POSTGIS_SCHEMA = "taipei_landuse"

# =========================================================
# Create output folders
# =========================================================

DATA_PROCESSED.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_TABLES.mkdir(
    parents=True,
    exist_ok=True
)


LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# =========================================================
# Logging
# =========================================================

LOG_FILE = (
    LOG_DIR
    / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
)


logging.basicConfig(
    level=logging.INFO,

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),

    datefmt="%Y-%m-%d %H:%M:%S",

    handlers=[
        logging.FileHandler(
            LOG_FILE,
            encoding="utf-8"
        ),

        logging.StreamHandler()
    ]
)


logger = logging.getLogger(__name__)

# =========================================================
# Main pipeline
# =========================================================

def main():

    logger.info(
        "=== Taipei Urban GIS Pipeline ==="
    )


    # -----------------------------------------------------
    # 1. Load data
    # -----------------------------------------------------

    logger.info(
        "[1] Loading data..."
    )

    landuse = gpd.read_file(
        DATA_RAW
        / "landuse_main"
        / "landuse_main.shp",
        encoding="cp950"
    )

    # Raw land-use shapefile has no CRS metadata.
    # CRS assignment is based on verified source specification.
    if landuse.crs is None:

        logger.warning(
            "landuse CRS metadata missing. "
            "Assigning EPSG:%s based on "
            "verified source specification.",
            EXPECTED_EPSG
        )

        landuse = landuse.set_crs(
            epsg=EXPECTED_EPSG,
            allow_override=True
        )


    district = gpd.read_file(
        DATA_RAW
        / "Taipei_city_district"
        / "Taipei_city_district.shp"
    )


    MRT = gpd.read_file(
        DATA_RAW
        / "MRT_stations"
        / "MRT_stations.shp"
    )


    landuse_mapping = pd.read_csv(
        DATA_PROCESSED
        / "landuse_mapping.csv"
    )


    logger.info(
        "Data loaded successfully."
    )

    logger.info(
        "landuse rows: %s",
        len(landuse)
    )

    logger.info(
        "district rows: %s",
        len(district)
    )

    logger.info(
        "MRT rows: %s",
        len(MRT)
    )

    logger.info(
        "landuse_mapping rows: %s",
        len(landuse_mapping)
    )


    # -----------------------------------------------------
    # 2. Input QA
    # -----------------------------------------------------

    logger.info(
        "[QA] Validating input datasets..."
    )


    require_nonempty(
        landuse,
        "landuse"
    )

    require_columns(
        landuse,
        [
            "編號",
            "使用分區",
            "geometry"
        ],
        "landuse"
    )

    require_crs(
        landuse,
        EXPECTED_EPSG,
        "landuse"
    )


    require_nonempty(
        district,
        "district"
    )

    require_columns(
        district,
        [
            "TNAME",
            "geometry"
        ],
        "district"
    )

    require_crs(
        district,
        EXPECTED_EPSG,
        "district"
    )


    require_nonempty(
        MRT,
        "MRT"
    )

    require_columns(
        MRT,
        [
            "MARKNAME1",
            "geometry"
        ],
        "MRT"
    )

    require_crs(
        MRT,
        EXPECTED_EPSG,
        "MRT"
    )


    require_nonempty(
        landuse_mapping,
        "landuse_mapping"
    )

    require_columns(
        landuse_mapping,
        [
            "使用分區",
            "main_category",
            "review_required",
            "classification_note"
        ],
        "landuse_mapping"
    )


    logger.info(
        "Input QA passed."
    )


    # -----------------------------------------------------
    # 3. Geometry repair
    # -----------------------------------------------------

    logger.info(
        "[2] Repairing geometry..."
    )

    geometry_cleaned = landuse.copy()

    geometry_cleaned["geometry"] = (
        geometry_cleaned.geometry
        .apply(repair_geometry)
    )


    require_no_invalid_geometry(
        geometry_cleaned,
        "geometry_cleaned"
    )

    require_no_empty_geometry(
        geometry_cleaned,
        "geometry_cleaned"
    )


    geometry_stats = geometry_qa(
        geometry_cleaned
    )

    logger.info(
        "Geometry QA result: %s",
        geometry_stats
    )

    logger.info(
        "Geometry QA passed."
    )


    # -----------------------------------------------------
    # 4. Attribute cleaning
    # -----------------------------------------------------

    logger.info(
        "[3] Cleaning attributes..."
    )

    attribute_cleaned = (
        clean_landuse_text(
            geometry_cleaned
        )
    )

    logger.info(
        "Attribute cleaning completed."
    )


    # -----------------------------------------------------
    # 5. Join classification mapping
    # -----------------------------------------------------

    logger.info(
        "[4] Joining land-use mapping..."
    )

    landuse_processed = (
        join_landuse_mapping(
            attribute_cleaned,
            landuse_mapping
        )
    )


    if (
        len(landuse_processed)
        != len(attribute_cleaned)
    ):

        raise ValueError(
            "Mapping join changed row count: "
            f"{len(attribute_cleaned)} → "
            f"{len(landuse_processed)}"
        )


    logger.info(
        "Mapping join passed row-count QA."
    )


    # -----------------------------------------------------
    # 6. Split analytical / excluded
    # -----------------------------------------------------

    logger.info(
        "[5] Splitting analytical features..."
    )

    (
        landuse_analytical,
        excluded_features
    ) = split_analytical_features(
        landuse_processed
    )


    missing_category_count = (
        landuse_analytical[
            "main_category"
        ]
        .isna()
        .sum()
    )


    if missing_category_count != 0:

        raise ValueError(
            "Analytical dataset contains "
            f"{missing_category_count} "
            "missing categories."
        )


    logger.info(
        "Analytical features: %s",
        len(landuse_analytical)
    )

    logger.info(
        "Excluded features: %s",
        len(excluded_features)
    )


    # -----------------------------------------------------
    # 7. Add area fields
    # -----------------------------------------------------

    logger.info(
        "[6] Adding area fields..."
    )

    landuse_analytical = (
        add_area_fields(
            landuse_analytical
        )
    )


    # -----------------------------------------------------
    # 8. Dissolve
    # -----------------------------------------------------

    logger.info(
        "[7] Dissolving main categories..."
    )

    landuse_dissolved = (
        dissolve_by_category(
            landuse_analytical
        )
    )

    landuse_dissolved = (
        add_area_fields(
            landuse_dissolved
        )
    )


    if (
        len(landuse_dissolved)
        != EXPECTED_CATEGORY_COUNT
    ):

        raise ValueError(
            "Unexpected dissolved "
            "category count: "
            f"expected "
            f"{EXPECTED_CATEGORY_COUNT}, "
            f"got "
            f"{len(landuse_dissolved)}"
        )


    logger.info(
        "Dissolved category count: %s",
        len(landuse_dissolved)
    )


    # -----------------------------------------------------
    # 9. Area summary
    # -----------------------------------------------------

    logger.info(
        "[8] Creating area summary..."
    )

    final_area_summary = (
        summarize_area(
            landuse_dissolved
        )
    )


    # -----------------------------------------------------
    # 10. District analysis
    # -----------------------------------------------------

    logger.info(
        "[9] Running district analysis..."
    )

    (
        district_intersection,
        district_summary
    ) = intersect_with_districts(
        landuse_dissolved,
        district
    )


    logger.info(
        "District intersection features: %s",
        len(district_intersection)
    )


    # -----------------------------------------------------
    # 11. Taipei boundary
    # -----------------------------------------------------

    logger.info(
        "[10] Building Taipei boundary..."
    )

    taipei_boundary = (
        district[
            ["geometry"]
        ]
        .dissolve()
        .reset_index(
            drop=True
        )
    )


    # -----------------------------------------------------
    # 12. MRT 800m coverage
    # -----------------------------------------------------

    logger.info(
        "[11] Building MRT %sm coverage...",
        MRT_BUFFER_DISTANCE
    )

    (
        mrt_entrances,
        mrt_buffer_dissolved,
        mrt_coverage
    ) = build_mrt_coverage(
        MRT,
        taipei_boundary,
        buffer_distance=(
            MRT_BUFFER_DISTANCE
        )
    )


    require_nonempty(
        mrt_entrances,
        "mrt_entrances"
    )

    require_no_invalid_geometry(
        mrt_coverage,
        "mrt_coverage"
    )

    require_no_empty_geometry(
        mrt_coverage,
        "mrt_coverage"
    )


    if len(mrt_coverage) != 1:

        raise ValueError(
            "Expected one dissolved "
            "MRT coverage feature, "
            f"got {len(mrt_coverage)}"
        )


    logger.info(
        "Taipei MRT entrances: %s",
        len(mrt_entrances)
    )

    logger.info(
        "MRT coverage area km²: %.3f",
        mrt_coverage[
            "area_km2"
        ].sum()
    )


    # -----------------------------------------------------
    # 13. MRT land-use analysis
    # -----------------------------------------------------

    logger.info(
        "[12] Running MRT land-use analysis..."
    )

    (
        mrt_intersection,
        mrt_composition,
        mrt_coverage_summary
    ) = analyze_mrt_landuse_coverage(
        landuse_dissolved,
        mrt_coverage
    )


    logger.info(
        "MRT land-use intersection features: %s",
        len(mrt_intersection)
    )


    # -----------------------------------------------------
    # 14. Final QA
    # -----------------------------------------------------

    logger.info(
        "=== Final Pipeline QA ==="
    )

    logger.info(
        "Raw land-use features: %s",
        len(landuse)
    )

    logger.info(
        "Analytical features: %s",
        len(landuse_analytical)
    )

    logger.info(
        "Excluded features: %s",
        len(excluded_features)
    )

    logger.info(
        "Land-use categories: %s",
        len(landuse_dissolved)
    )

    logger.info(
        "MRT entrances in Taipei: %s",
        len(mrt_entrances)
    )

    logger.info(
        "MRT coverage area km²: %.3f",
        mrt_coverage[
            "area_km2"
        ].sum()
    )

    logger.info(
        "Total analytical area km²: %.3f",
        landuse_dissolved[
            "area_km2"
        ].sum()
    )


    # -----------------------------------------------------
    # 15. Export
    # -----------------------------------------------------

    logger.info(
        "[13] Exporting outputs..."
    )


    landuse_analytical.to_file(
        DATA_PROCESSED
        / "landuse_analytical.gpkg",
        layer="landuse_analytical",
        driver="GPKG"
    )


    landuse_dissolved.to_file(
        DATA_PROCESSED
        / "landuse_dissolved.gpkg",
        layer="landuse_dissolved",
        driver="GPKG"
    )


    excluded_features.to_file(
        DATA_PROCESSED
        / "excluded_features.gpkg",
        layer="excluded_features",
        driver="GPKG"
    )


    mrt_coverage.to_file(
        DATA_PROCESSED
        / "mrt_800m_coverage.gpkg",
        layer="mrt_800m_coverage",
        driver="GPKG"
    )


    final_area_summary.to_csv(
        OUTPUT_TABLES
        / "main_category_area_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )


    district_summary.to_csv(
        OUTPUT_TABLES
        / "district_landuse_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )


    mrt_composition.to_csv(
        OUTPUT_TABLES
        / "mrt_800m_landuse_composition.csv",
        index=False,
        encoding="utf-8-sig"
    )


    mrt_coverage_summary.to_csv(
        OUTPUT_TABLES
        / "mrt_800m_landuse_coverage.csv",
        index=False,
        encoding="utf-8-sig"
    )


    logger.info(
        "Outputs exported successfully."
    )

    logger.info(
        "=== Pipeline completed successfully ==="
    )

    logger.info(
        "Log file: %s",
        LOG_FILE
    )

    # -----------------------------------------------------
    #  16. Optional PostGIS export
    #  -----------------------------------------------------
    if EXPORT_TO_POSTGIS:
        logger.info(
            "[14] Exporting spatial layers to PostGIS..."
        )

        engine = create_postgis_engine(
            ENV_PATH
        )

        export_to_postgis(
            landuse_analytical,
            engine,
            "landuse_analytical",
            schema=POSTGIS_SCHEMA
        )

        export_to_postgis(
            landuse_dissolved,
            engine,
            "landuse_dissolved",
            schema=POSTGIS_SCHEMA
        )

        export_to_postgis(
            district,
            engine,
            "district",
            schema=POSTGIS_SCHEMA
        )

        export_to_postgis(
            mrt_entrances,
            engine,
            "mrt_entrances_taipei",
            schema=POSTGIS_SCHEMA
        )

        export_to_postgis(
            mrt_coverage,
            engine,
            "mrt_800m_coverage",
            schema=POSTGIS_SCHEMA
        )

        logger.info(
            "PostGIS export finished. Running QA..."
        )

        # -------------------------------------------------
        # PostGIS row-count QA
        # -------------------------------------------------
        postgis_checks = {
            "landuse_analytical": len(
                landuse_analytical
            ),

            "landuse_dissolved": len(
                landuse_dissolved
            ),

            "district": len(
                district
            ),

            "mrt_entrances_taipei": len(
                mrt_entrances
            ),

            "mrt_800m_coverage": len(
                mrt_coverage
            )
        }

        for (
            table_name,
            expected_count
        ) in postgis_checks.items():

            actual_count = get_table_count(
                engine,
                POSTGIS_SCHEMA,
                table_name
            )

            logger.info(
                "PostGIS QA - %s: "
                "expected=%s, actual=%s",
                table_name,
                expected_count,
                actual_count
            )

            if actual_count != expected_count:

                raise ValueError(
                    f"PostGIS row-count mismatch "
                    f"for {table_name}: "
                    f"expected {expected_count}, "
                    f"got {actual_count}"
                )


        logger.info(
            "PostGIS QA passed."
        )

        engine.dispose()

        logger.info(
            "PostGIS export completed successfully."
        )

    else:
        logger.info(
            "PostGIS export skipped."
        )


# -----------------------------------------------------
# Final success message
# -----------------------------------------------------

logger.info(
    "=== Pipeline completed successfully ==="
)

logger.info(
    "Log file: %s",
    LOG_FILE
)

if __name__ == "__main__":

    try:
        main()

    except Exception:

        logger.exception(
            "Pipeline failed."
        )

        raise