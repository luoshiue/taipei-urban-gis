def add_area_fields(
    gdf,
    area_m2_col="area_m2",
    area_km2_col="area_km2"
):
    """
    Add area fields in square metres and square kilometres.

    Assumes the GeoDataFrame uses a projected CRS
    whose linear unit is metres.
    """

    result = gdf.copy()

    result[area_m2_col] = result.geometry.area

    result[area_km2_col] = (
        result[area_m2_col] / 1_000_000
    )

    return result


def dissolve_by_category(
    gdf,
    category_col="main_category"
):
    """
    Dissolve geometries by analytical category.
    """

    dissolved = (
        gdf
        .dissolve(by=category_col)
        .reset_index()
    )

    return dissolved


def summarize_area(
    gdf,
    category_col="main_category",
    area_km2_col="area_km2"
):
    """
    Summarize total area and percentage by category.
    """

    summary = (
        gdf[
            [category_col, area_km2_col]
        ]
        .copy()
    )

    total_area = summary[area_km2_col].sum()

    summary["pct"] = (
        summary[area_km2_col]
        / total_area
        * 100
    )

    summary = (
        summary
        .sort_values(
            area_km2_col,
            ascending=False
        )
        .reset_index(drop=True)
    )

    return summary


def intersect_with_districts(
    landuse_gdf,
    district_gdf,
    district_name_col="TNAME",
    category_col="main_category"
):
    """
    Intersect land-use geometries with administrative districts
    and calculate area statistics by district and category.

    Parameters
    ----------
    landuse_gdf : GeoDataFrame
        Land-use GeoDataFrame.

    district_gdf : GeoDataFrame
        Administrative district polygons.

    district_name_col : str
        District name column in district_gdf.

    category_col : str
        Land-use analytical category column.

    Returns
    -------
    intersection_gdf : GeoDataFrame
        Intersected geometries.

    summary_df : DataFrame
        Area and percentage summary by district and category.
    """

    district_analysis = (
        district_gdf[
            [district_name_col, "geometry"]
        ]
        .rename(
            columns={
                district_name_col: "district_name"
            }
        )
        .copy()
    )

    intersection_gdf = landuse_gdf.overlay(
        district_analysis,
        how="intersection",
        keep_geom_type=True
    )

    intersection_gdf["area_m2"] = (
        intersection_gdf.geometry.area
    )

    intersection_gdf["area_km2"] = (
        intersection_gdf["area_m2"]
        / 1_000_000
    )

    summary_df = (
        intersection_gdf
        .groupby(
            ["district_name", category_col]
        )
        .agg(
            area_km2=("area_km2", "sum")
        )
        .reset_index()
    )

    summary_df["district_total_km2"] = (
        summary_df
        .groupby("district_name")["area_km2"]
        .transform("sum")
    )

    summary_df["district_pct"] = (
        summary_df["area_km2"]
        / summary_df["district_total_km2"]
        * 100
    )

    return intersection_gdf, summary_df


def build_mrt_coverage(
    mrt_gdf,
    city_boundary_gdf,
    name_col="MARKNAME1",
    entrance_keyword="出入口",
    buffer_distance=800
):
    """
    Build dissolved MRT entrance buffer coverage clipped to city boundary.

    Parameters
    ----------
    mrt_gdf : GeoDataFrame
        MRT station / entrance point dataset.

    city_boundary_gdf : GeoDataFrame
        City boundary polygon layer.

    name_col : str
        Column containing MRT point names.

    entrance_keyword : str
        Keyword used to identify entrance points.

    buffer_distance : float
        Buffer distance in CRS units.
        For EPSG:3826, unit is metres.

    Returns
    -------
    entrances : GeoDataFrame
        MRT entrance points within city boundary.

    buffer_dissolved : GeoDataFrame
        Dissolved MRT entrance buffers.

    coverage_clipped : GeoDataFrame
        Dissolved buffer clipped to city boundary.
    """

    # 1. Filter entrance points
    entrances = (
        mrt_gdf[
            mrt_gdf[name_col]
            .str.contains(
                entrance_keyword,
                na=False
            )
        ]
        .copy()
    )

    # 2. Keep entrances intersecting city boundary
    entrances = entrances.sjoin(
        city_boundary_gdf[["geometry"]],
        how="inner",
        predicate="intersects"
    )

    entrances = (
        entrances
        .drop(
            columns=["index_right"],
            errors="ignore"
        )
        .copy()
    )

    # 3. Create buffers
    buffers = entrances[
        [name_col, "geometry"]
    ].copy()

    buffers["geometry"] = (
        buffers.geometry
        .buffer(buffer_distance)
    )

    # 4. Dissolve overlapping buffers
    buffer_dissolved = (
        buffers[["geometry"]]
        .dissolve()
        .reset_index(drop=True)
    )

    # 5. Clip to city boundary
    coverage_clipped = (
        buffer_dissolved
        .overlay(
            city_boundary_gdf[["geometry"]],
            how="intersection"
        )
    )

    # 6. Add area fields
    buffer_dissolved = add_area_fields(
        buffer_dissolved
    )

    coverage_clipped = add_area_fields(
        coverage_clipped
    )

    return (
        entrances,
        buffer_dissolved,
        coverage_clipped
    )


def analyze_mrt_landuse_coverage(
    landuse_dissolved_gdf,
    mrt_coverage_gdf,
    category_col="main_category"
):
    """
    Intersect dissolved land-use categories with MRT coverage
    and calculate land-use composition and coverage rates.

    Parameters
    ----------
    landuse_dissolved_gdf : GeoDataFrame
        Dissolved land-use layer with one geometry per category.

    mrt_coverage_gdf : GeoDataFrame
        Dissolved and city-clipped MRT buffer coverage.

    category_col : str
        Land-use analytical category column.

    Returns
    -------
    intersection_gdf : GeoDataFrame
        Land-use geometries intersected with MRT coverage.

    composition_df : DataFrame
        Land-use composition within MRT coverage.

    coverage_df : DataFrame
        Percentage of each land-use category located within MRT coverage.
    """

    # 1. Intersect land use with MRT coverage
    intersection_gdf = (
        landuse_dissolved_gdf[
            [category_col, "geometry"]
        ]
        .overlay(
            mrt_coverage_gdf[["geometry"]],
            how="intersection",
            keep_geom_type=True
        )
    )

    # 2. Calculate intersected area
    intersection_gdf = add_area_fields(
        intersection_gdf
    )

    # 3. MRT area by land-use category
    composition_df = (
        intersection_gdf
        .groupby(category_col)
        .agg(
            mrt_area_km2=("area_km2", "sum")
        )
        .reset_index()
    )

    total_mrt_landuse_area = (
        composition_df["mrt_area_km2"].sum()
    )

    composition_df["mrt_composition_pct"] = (
        composition_df["mrt_area_km2"]
        / total_mrt_landuse_area
        * 100
    )

    composition_df = (
        composition_df
        .sort_values(
            "mrt_area_km2",
            ascending=False
        )
        .reset_index(drop=True)
    )

    # 4. Calculate total city area by category
    city_area_df = (
        landuse_dissolved_gdf[
            [category_col, "geometry"]
        ]
        .copy()
    )

    city_area_df = add_area_fields(
        city_area_df
    )

    city_area_df = city_area_df[
        [category_col, "area_km2"]
    ].rename(
        columns={
            "area_km2": "city_area_km2"
        }
    )

    # 5. Join MRT area and calculate coverage rate
    coverage_df = (
        city_area_df
        .merge(
            composition_df[
                [category_col, "mrt_area_km2"]
            ],
            on=category_col,
            how="left"
        )
    )

    coverage_df["mrt_area_km2"] = (
        coverage_df["mrt_area_km2"]
        .fillna(0)
    )

    coverage_df["mrt_coverage_pct"] = (
        coverage_df["mrt_area_km2"]
        / coverage_df["city_area_km2"]
        * 100
    )

    coverage_df = (
        coverage_df
        .sort_values(
            "mrt_coverage_pct",
            ascending=False
        )
        .reset_index(drop=True)
    )

    return (
        intersection_gdf,
        composition_df,
        coverage_df
    )