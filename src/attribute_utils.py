def clean_landuse_text(gdf, source_col="使用分區", target_col="使用分區_clean"):
    """
    Clean land-use zoning text by removing line breaks, tabs,
    and leading/trailing whitespace.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input GeoDataFrame.

    source_col : str
        Original land-use text column.

    target_col : str
        Name of cleaned output column.

    Returns
    -------
    GeoDataFrame
        Copy of input GeoDataFrame with cleaned text column.
    """

    cleaned = gdf.copy()

    cleaned[target_col] = (
        cleaned[source_col]
        .str.replace(r"[\n\t]+", "", regex=True)
        .str.strip()
    )

    return cleaned


def attribute_qa(gdf, column):
    """
    Return basic QA statistics for a text attribute column.
    """

    return {
        "feature_count": len(gdf),
        "null_count": int(gdf[column].isna().sum()),
        "unique_count": int(gdf[column].nunique(dropna=True))
    }

def join_landuse_mapping(
    gdf,
    mapping_df,
    cleaned_col="使用分區_clean",
    mapping_key="使用分區"
):
    """
    Join land-use classification mapping to the cleaned GeoDataFrame.
    """

    result = gdf.merge(
        mapping_df[
            [
                mapping_key,
                "main_category",
                "review_required",
                "classification_note"
            ]
        ],
        left_on=cleaned_col,
        right_on=mapping_key,
        how="left"
    )

    return result


def split_analytical_features(
    gdf,
    category_col="main_category"
):
    """
    Split processed land-use data into analytical features
    and excluded features based on classification availability.

    Parameters
    ----------
    gdf : GeoDataFrame
        Processed land-use GeoDataFrame.

    category_col : str
        Analytical category column.

    Returns
    -------
    analytical : GeoDataFrame
        Features with valid analytical category.

    excluded : GeoDataFrame
        Features without analytical category.
    """

    analytical = (
        gdf[
            gdf[category_col].notna()
        ]
        .copy()
    )

    excluded = (
        gdf[
            gdf[category_col].isna()
        ]
        .copy()
    )

    return analytical, excluded