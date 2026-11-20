
def normalize_open_food_facts(source):
    """Normalize Open Food Facts values per 100 g."""

    nutrients = source.get("nutriments", {})

    return {
        "source": "open_food_facts",
        "barcode": source.get("barcode"),
        "product_name": source.get("product_name"),
        "brand": source.get("brand"),
        "nutrition_basis": "per_100g",
        "nutrition": {
            "energy_kcal": nutrients.get("energy-kcal_100g"),
            "protein_g": nutrients.get("proteins_100g"),
            "carbohydrates_g": nutrients.get("carbohydrates_100g"),
            "fat_g": nutrients.get("fat_100g"),
            "saturated_fat_g": nutrients.get(
                "saturated-fat_100g"
            ),
            "sugars_g": nutrients.get("sugars_100g"),
            "salt_g": nutrients.get("salt_100g"),
        },
    }


def normalize_nutrition_sources(results):
    normalized = []

    for source in results.get("sources", []):
        source_name = source.get("source")

        if source_name == "open_food_facts":
            normalized.append(
                normalize_open_food_facts(source)
            )

        elif source_name == "usda":
            normalized.append(
                normalize_usda(source)
            )

    return {
        "barcode": results.get("barcode"),
        "normalized_sources": normalized,
    }


def normalize_usda(source):
    """Normalize USDA branded-food nutrient values."""

    nutrient_mapping = {
        1008: ("energy_kcal", "KCAL"),
        2047: ("energy_kcal", "KCAL"),
        2048: ("energy_kcal", "KCAL"),
        1003: ("protein_g", "G"),
        1005: ("carbohydrates_g", "G"),
        1004: ("fat_g", "G"),
        1258: ("saturated_fat_g", "G"),
        2000: ("sugars_g", "G"),
        1093: ("sodium_mg", "MG"),
    }

    nutrition = {
        "energy_kcal": None,
        "protein_g": None,
        "carbohydrates_g": None,
        "fat_g": None,
        "saturated_fat_g": None,
        "sugars_g": None,
        "salt_g": None,
    }

    for nutrient in source.get("nutrients", []):
        nutrient_id = nutrient.get("nutrientId")
        mapping = nutrient_mapping.get(nutrient_id)

        if mapping is None:
            continue

        field, expected_unit = mapping

        if str(nutrient.get("unitName", "")).upper() != expected_unit:
            continue

        value = nutrient.get("value")

        if value is None:
            continue

        if field == "sodium_mg":
            # Convert sodium (mg) to salt equivalent (g).
            nutrition["salt_g"] = round(
                float(value) * 2.5 / 1000, 4
            )
        else:
            nutrition[field] = float(value)

    return {
        "source": "usda",
        "barcode": source.get("barcode"),
        "product_name": source.get("product_name"),
        "brand": source.get("brand"),
        "nutrition_basis": "per_100g",
        "nutrition": nutrition,
        "fdc_id": source.get("fdc_id"),
        "serving_size": source.get("serving_size"),
        "serving_size_unit": source.get("serving_size_unit"),
    }
