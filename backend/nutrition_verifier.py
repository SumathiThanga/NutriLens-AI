
def verify_nutrition_sources(normalized_results):
    """
    Accept only nutrition records matching the
    selected product's exact barcode.
    """

    selected_barcode = str(
        normalized_results.get("barcode") or ""
    ).strip()

    verified = []
    rejected = []

    for source in normalized_results.get(
        "normalized_sources", []
    ):
        source_barcode = str(
            source.get("barcode") or ""
        ).strip()

        has_nutrition = any(
            value is not None
            for value in source.get("nutrition", {}).values()
        )

        if (
            selected_barcode
            and source_barcode == selected_barcode
            and has_nutrition
        ):
            verified.append(source)
        else:
            rejected.append({
                "source": source.get("source"),
                "product_name": source.get("product_name"),
                "barcode": source_barcode,
                "reason": (
                    "Barcode mismatch or no nutrition data"
                ),
            })

    return {
        "barcode": selected_barcode,
        "verified_sources": verified,
        "rejected_sources": rejected,
    }
