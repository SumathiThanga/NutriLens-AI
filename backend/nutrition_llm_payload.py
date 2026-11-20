
def prepare_nutrition_llm_payload(
    consolidated,
    product_name=None,
    brand=None,
):
    nutrition = consolidated.get("nutrition", {})
    provenance = consolidated.get("provenance", {})

    available_nutrients = {}

    for nutrient, value in nutrition.items():
        if value is not None:
            available_nutrients[nutrient] = {
                "value": value,
                "source": provenance.get(nutrient),
            }

    missing_nutrients = [
        nutrient
        for nutrient, value in nutrition.items()
        if value is None
    ]

    return {
        "barcode": consolidated.get("barcode"),
        "product_name": product_name,
        "brand": brand,
        "nutrition_basis": consolidated.get(
            "nutrition_basis"
        ),
        "available_nutrients": available_nutrients,
        "missing_nutrients": missing_nutrients,
        "conflicts": consolidated.get("conflicts", []),
        "sources_used": consolidated.get("sources_used", []),
        "analysis_allowed": bool(available_nutrients),
    }
