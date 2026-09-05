from shapely.validation import make_valid
from shapely.geometry import (
    Polygon,
    MultiPolygon,
    GeometryCollection
)


def repair_geometry(geom):
    """
    Repair invalid geometry and retain polygonal components only.

    Parameters
    ----------
    geom : shapely geometry
        Input geometry.

    Returns
    -------
    shapely geometry
        Repaired Polygon or MultiPolygon.
    """

    if geom is None:
        return None

    repaired = make_valid(geom)

    if isinstance(repaired, GeometryCollection):

        polygons = []

        for part in repaired.geoms:

            if isinstance(part, Polygon):
                polygons.append(part)

            elif isinstance(part, MultiPolygon):
                polygons.extend(list(part.geoms))

        if len(polygons) == 0:
            return None

        if len(polygons) == 1:
            return polygons[0]

        return MultiPolygon(polygons)

    return repaired


def geometry_qa(gdf):
    """
    Return basic geometry quality statistics.
    """

    return {
        "feature_count": len(gdf),
        "invalid_count": int(
            (~gdf.geometry.is_valid).sum()
        ),
        "empty_count": int(
            gdf.geometry.is_empty.sum()
        ),
        "null_geometry_count": int(
            gdf.geometry.isna().sum()
        ),
        "geometry_types": (
            gdf.geometry
            .geom_type
            .value_counts()
            .to_dict()
        ),
        "crs": str(gdf.crs)
    }



