-- =========================================================
-- 05_spatial_index_qa.sql
-- Purpose:
-- Inspect PostGIS GiST spatial indexes and query execution
-- plans for the land-use × district spatial join.
-- =========================================================


-- ---------------------------------------------------------
-- Part A: Check spatial indexes
-- ---------------------------------------------------------

SELECT
    schemaname,
    tablename,
    indexname,
    indexdef

FROM pg_indexes

WHERE schemaname = 'taipei_landuse'

ORDER BY
    tablename,
    indexname;


-- ---------------------------------------------------------
-- Part B: Refresh PostgreSQL statistics
-- ---------------------------------------------------------

ANALYZE taipei_landuse.landuse_analytical;
ANALYZE taipei_landuse.landuse_dissolved;
ANALYZE taipei_landuse.district;
ANALYZE taipei_landuse.mrt_entrances_taipei;
ANALYZE taipei_landuse.mrt_800m_coverage;


-- ---------------------------------------------------------
-- Part C: Inspect spatial join execution plan
-- ---------------------------------------------------------

EXPLAIN ANALYZE

SELECT
    l."編號",
    d."TNAME"

FROM taipei_landuse.landuse_analytical AS l

JOIN taipei_landuse.district AS d
    ON ST_Intersects(
        l.geometry,
        d.geometry
    );