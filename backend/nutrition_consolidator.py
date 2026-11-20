
NUTRIENT_FIELDS = [
    "energy_kcal",
    "protein_g",
    "carbohydrates_g",
    "fat_g",
    "saturated_fat_g",
    "sugars_g",
    "salt_g",
]

SOURCE_PRIORITY = [
    "open_food_facts",
    "usda",
]


def consolidate_nutrition(verified_results):
    
    selected_barcode = str(
        verified_results.get("barcode") or ""
    ).strip()

    if not selected_barcode:
        raise ValueError("Selected product barcode is required")

    sources = []

    for source in verified_results.get("verified_sources", []):
        source_barcode = str(
            source.get("barcode") or ""
        ).strip()

        if source_barcode != selected_barcode:
            raise ValueError(
                f"Barcode mismatch in consolidation: "
                f"expected {selected_barcode}, "
                f"received {source_barcode}"
            )

        sources.append(source)


    sources = sorted(
        sources,
        key=lambda item: (
            SOURCE_PRIORITY.index(item["source"])
            if item["source"] in SOURCE_PRIORITY
            else len(SOURCE_PRIORITY)
        ),
    )

    consolidated = {}
    provenance = {}
    conflicts = []

    for nutrient in NUTRIENT_FIELDS:
        candidates = []

        for source in sources:
            if source.get("nutrition_basis") != "per_100g":
                continue

            value = source.get("nutrition", {}).get(nutrient)

            if value is None:
                continue

            candidates.append({
                "source": source["source"],
                "value": value,
            })

        if not candidates:
            consolidated[nutrient] = None
            provenance[nutrient] = None
            continue

        selected = candidates[0]

        consolidated[nutrient] = selected["value"]
        provenance[nutrient] = selected["source"]

        if any(
            abs(float(candidate["value"]) -
                float(selected["value"])) > 0.01
            for candidate in candidates[1:]
        ):
            conflicts.append({
                "nutrient": nutrient,
                "selected": selected,
                "alternatives": candidates[1:],
            })

    return {
        "barcode": verified_results.get("barcode"),
        "nutrition_basis": "per_100g",
        "nutrition": consolidated,
        "provenance": provenance,
        "conflicts": conflicts,
        "sources_used": [
            source["source"] for source in sources
        ],
    }
