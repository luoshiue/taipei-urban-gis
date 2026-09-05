-- =========================================================
-- 03_mrt_800m_landuse.sql
-- Purpose:
-- Calculate land-use area located within the dissolved
-- Taipei MRT entrance 800 m buffer.
-- =========================================================

SELECT
    l.main_category,

    ROUND(
        (
            ST_Area(
                ST_Intersection(
                    l.geometry,
                    m.geometry
                )
            ) / 1000000.0
        )::numeric,
        3
    ) AS mrt_area_km2

FROM taipei_landuse.landuse_dissolved AS l

CROSS JOIN taipei_landuse.mrt_800m_coverage AS m

WHERE ST_Intersects(
    l.geometry,
    m.geometry
)

ORDER BY
    mrt_area_km2 DESC;