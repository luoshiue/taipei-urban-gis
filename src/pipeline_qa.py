
def require_columns(df, required_columns, dataset_name="dataset"):
    """
    Ensure required columns exist.
    """

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset_name} missing required columns: {missing}"
        )


def require_crs(gdf, expected_epsg, dataset_name="dataset"):
    """
    Ensure GeoDataFrame has expected CRS.
    """

    if gdf.crs is None:
        raise ValueError(
            f"{dataset_name} has no CRS."
        )

    actual_epsg = gdf.crs.to_epsg()

    if actual_epsg != expected_epsg:
        raise ValueError(
            f"{dataset_name} CRS mismatch: "
            f"expected EPSG:{expected_epsg}, "
            f"got {gdf.crs}"
        )


def require_no_invalid_geometry(gdf, dataset_name="dataset"):
    """
    Ensure there are no invalid geometries.
    """

    invalid_count = int(
        (~gdf.geometry.is_valid).sum()
    )

    if invalid_count > 0:
        raise ValueError(
            f"{dataset_name} contains "
            f"{invalid_count} invalid geometries."
        )


def require_no_empty_geometry(gdf, dataset_name="dataset"):
    """
    Ensure there are no empty geometries.
    """

    empty_count = int(
        gdf.geometry.is_empty.sum()
    )

    if empty_count > 0:
        raise ValueError(
            f"{dataset_name} contains "
            f"{empty_count} empty geometries."
        )


def require_nonempty(df, dataset_name="dataset"):
    """
    Ensure dataset contains at least one row.
    """

    if len(df) == 0:
        raise ValueError(
            f"{dataset_name} contains no rows."
        )

