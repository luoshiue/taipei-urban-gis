-- =========================================================
-- 02_district_landuse_intersection.sql
-- Purpose:
-- Calculate land-use area by Taipei administrative district
-- using polygon intersection.
-- =========================================================

SELECT
    d."TNAME" AS district_name,
    l.main_category,

    ROUND(
        (
            SUM(
                ST_Area(
                    ST_Intersection(
                        l.geometry,
                        d.geometry
                    )
                )
            ) / 1000000.0
        )::numeric,
        3
    ) AS area_km2

FROM taipei_landuse.landuse_dissolved AS l

JOIN taipei_landuse.district AS d
    ON ST_Intersects(
        l.geometry,
        d.geometry
    )

GROUP BY
    d."TNAME",
    l.main_category

ORDER BY
    d."TNAME",
    area_km2 DESC;