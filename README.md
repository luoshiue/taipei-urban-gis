Taipei Urban Land Use GIS Analysis
Overview

This project builds a reproducible GIS workflow for analyzing Taipei City land-use zoning using Python, GeoPandas, Shapely, PostgreSQL/PostGIS, and spatial SQL.

The workflow transforms raw government spatial data into a cleaned, classified, spatially validated, and database-ready analytical dataset.

Main goals:

validate and repair spatial data
reclassify 164 zoning types into analytical land-use categories
perform district-level spatial analysis
analyze MRT 800 m coverage
integrate processed layers into PostGIS
validate spatial SQL and spatial index performance
prepare the workflow for future automation
Tech Stack
Python
GeoPandas
Pandas
Shapely
Matplotlib
PostgreSQL
PostGIS
SQLAlchemy
GeoAlchemy2
psycopg2
pgAdmin
Git
Jupyter Notebook

CRS used for spatial analysis:

EPSG:3826 — TWD97 / TM2 zone 121
Project Workflow
Raw GIS Data
    ↓
Data Audit
    ↓
CRS Validation
    ↓
Geometry Validation & Repair
    ↓
Attribute Cleaning
    ↓
Land-Use Reclassification
    ↓
Topology / Overlap QA
    ↓
Dissolve by Main Category
    ↓
Area Analysis
    ↓
Administrative District Analysis
    ↓
MRT Entrance 800 m Buffer Analysis
    ↓
PostgreSQL / PostGIS
    ↓
Spatial SQL
    ↓
GiST Spatial Index Validation
Data Processing

The original land-use dataset contained:

3,840 features
164 unique land-use zoning labels
EPSG:3826

Initial geometry QA found:

136 invalid geometries
3.54% invalid rate

Main geometry issues included:

Hole lies outside shell
Nested shells
Self-intersection
Ring Self-intersection

Invalid geometries were repaired using Shapely make_valid().

Final geometry QA:

3,840 features
0 invalid geometries
0 empty geometries
Land-Use Reclassification

The original 164 zoning types were reclassified into 14 analytical categories:

住宅
商業服務
工業產業
文教
公共行政服務
公共事業設施
交通運輸
公園綠地遊憩
水域水利
農業
保護保育
文化宗教保存
殯葬
特殊專用

All 164 zoning labels were classified.

Ambiguous mixed-use categories were retained with manual-review flags rather than silently assigned.

Analytical Dataset

Eight non-analytical records were excluded after QA, including planning extents and unattributed geometries overlapping valid land-use polygons.

Final analytical layer:

3,832 features
0 invalid geometries
0 missing main_category

Same-category overlaps were removed using dissolve operations before final area calculations.

Land-Use Structure

Total dissolved analytical area:

254.179 km²

Largest categories:

Category	Area	Share
保護保育	119.951 km²	47.19%
住宅	45.962 km²	18.08%
水域水利	18.104 km²	7.12%
公園綠地遊憩	13.846 km²	5.45%
文教	11.406 km²	4.49%
商業服務	10.066 km²	3.96%
Administrative District Analysis

Taipei City's 12 administrative districts were spatially joined and intersected with the land-use layer.

Spatial join results:

3,832 land-use features
4,027 left-join rows
4 unmatched boundary features

The unmatched features were only 3–11 m from the nearest district boundary and were treated as source-boundary mismatches rather than force-assigned.

Examples of dominant district land-use categories:

District	Dominant Category	Share
士林區	保護保育	65.09%
北投區	保護保育	60.79%
南港區	保護保育	55.78%
內湖區	保護保育	52.85%
大安區	住宅	44.11%
松山區	交通運輸	30.98%
萬華區	水域水利	43.15%

A 100% stacked bar chart was generated to compare land-use structure across all districts.

MRT 800 m Coverage Analysis

The MRT dataset contained station-center and entrance points.

Entrance filtering produced:

587 MRT entrance points
284 located within Taipei City

Taipei City entrance breakdown:

Taipei Metro: 277
Taoyuan Airport MRT: 7

An 800 m Euclidean buffer was created around all Taipei City MRT entrances.

Workflow:

Entrance Points
    ↓
800 m Buffer
    ↓
Dissolve Overlaps
    ↓
Clip to Taipei City
    ↓
Intersect with Land Use

Coverage area after clipping:

91.523 km²

Land-use area inside MRT 800 m coverage:

80.798 km²

Overall land-use coverage:

31.79%
MRT Coverage by Land-Use Category

Highest MRT 800 m coverage rates:

Category	Coverage
商業服務	89.48%
特殊專用	86.51%
文化宗教保存	85.82%
文教	64.72%
住宅	63.73%
工業產業	54.48%

Lower coverage categories included:

保護保育: 5.33%
殯葬: 4.13%

The analysis uses straight-line Euclidean buffers and does not represent pedestrian-network travel distance.

PostgreSQL / PostGIS

Processed GIS layers were loaded into:

Database: taipei_gis
Schema: taipei_landuse

Main spatial tables:

landuse_analytical
landuse_dissolved
district
mrt_entrances_taipei
mrt_800m_coverage

PostGIS upload QA confirmed:

3,825 POLYGON
7 MULTIPOLYGON
Total: 3,832
SRID: 3826

The database outputs matched the GeoPandas analytical results.

Spatial SQL

PostGIS functions used include:

ST_Area()
ST_Intersects()
ST_Intersection()

Spatial SQL was used to reproduce:

land-use area summaries
district × land-use intersection
MRT 800 m land-use coverage
category-specific MRT coverage rates

Results were cross-validated against the GeoPandas workflow.

Spatial Indexing

All core PostGIS geometry columns use GiST indexes.

Example:

USING GIST (geometry)

EXPLAIN ANALYZE confirmed that the district spatial join used:

Index Scan using idx_landuse_analytical_geometry
Index Cond: geometry && d.geometry
Filter: ST_Intersects(...)

Execution time:

213.672 ms

PostGIS returned:

4,023 matched spatial pairs

which matched the GeoPandas result:

4,023 matched
+ 4 unmatched
= 4,027 left-join rows
Engineering Decisions

Key workflow decisions include:

repairing invalid geometry before analysis
not deleting duplicate geometry without attribute inspection
preserving excluded records for QA traceability
dissolving same-category overlaps before area summaries
recalculating area after geometry-changing operations
dissolving overlapping MRT buffers before intersection
avoiding forced nearest-district assignment
separating database credentials using .env
cross-validating GeoPandas and PostGIS outputs
validating spatial index usage with EXPLAIN ANALYZE
Repository Structure
taipei_urban_gis/
├─ data/
│  ├─ raw/
│  └─ processed/
├─ outputs/
│  ├─ maps/
│  └─ tables/
├─ src/
├─ sql/
├─ docs/
├─ .gitignore
└─ README.md

## Spatial SQL

PostGIS SQL scripts are stored in the `sql/` directory.

Main queries include:

- `01_landuse_area_summary.sql`
- `02_district_landuse_intersection.sql`
- `03_mrt_800m_landuse.sql`
- `04_mrt_coverage_rate.sql`
- `05_spatial_index_qa.sql`

The SQL workflow reproduces key GeoPandas analyses and validates
spatial query performance using GiST indexes and `EXPLAIN ANALYZE`.