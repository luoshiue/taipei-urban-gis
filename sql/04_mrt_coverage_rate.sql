-- =========================================================
-- 04_mrt_coverage_rate.sql
-- Purpose:
-- Calculate the percentage of each land-use category
-- located within the MRT entrance 800 m buffer.
-- =========================================================

WITH mrt_area AS (

    SELECT
        l.main_category,

        ST_Area(
            ST_Intersection(
                l.geometry,
                m.geometry
            )
        ) / 1000000.0 AS mrt_area_km2,

        ST_Area(
            l.geometry
        ) / 1000000.0 AS city_area_km2

    FROM taipei_landuse.landuse_dissolved AS l

    CROSS JOIN taipei_landuse.mrt_800m_coverage AS m

    WHERE ST_Intersects(
        l.geometry,
        m.geometry
    )
)

SELECT
    main_category,

    ROUND(
        city_area_km2::numeric,
        3
    ) AS city_area_km2,

    ROUND(
        mrt_area_km2::numeric,
        3
    ) AS mrt_area_km2,

    ROUND(
        (
            mrt_area_km2
            / city_area_km2
            * 100
        )::numeric,
        2
    ) AS mrt_coverage_pct

FROM mrt_area

ORDER BY
    mrt_coverage_pct DESC;