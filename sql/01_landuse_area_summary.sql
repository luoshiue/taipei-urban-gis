SELECT
    main_category,

    ROUND(
        (
            SUM(
                ST_Area(geometry)
            ) / 1000000.0
        )::numeric,
        3
    ) AS area_km2

FROM taipei_landuse.landuse_dissolved

GROUP BY
    main_category

ORDER BY
    area_km2 DESC;