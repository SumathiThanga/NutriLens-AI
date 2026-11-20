
import json

from nutrition_consolidator import consolidate_nutrition

test_data = {
    "barcode": "3017620422003",
    "verified_sources": [
        {
            "source": "open_food_facts",
            "barcode": "3017620422003",
            "nutrition_basis": "per_100g",
            "nutrition": {
                "energy_kcal": 539,
                "protein_g": 6.3,
                "carbohydrates_g": 57.5,
                "fat_g": 30.9,
                "saturated_fat_g": 10.6,
                "sugars_g": 56.3,
                "salt_g": 0.107,
            },
        },
        {
            "source": "usda",
            "barcode": "3017620422003",
            "nutrition_basis": "per_100g",
            "nutrition": {
                "energy_kcal": 545,
                "protein_g": 6.5,
                "carbohydrates_g": 57.5,
                "fat_g": 31.0,
                "saturated_fat_g": 10.6,
                "sugars_g": 56.0,
                "salt_g": 0.11,
            },
        },
    ],
}

result = consolidate_nutrition(test_data)

print(json.dumps(result, indent=2))

assert result["nutrition"]["energy_kcal"] == 539
assert result["provenance"]["energy_kcal"] == "open_food_facts"

conflicted_fields = {
    item["nutrient"] for item in result["conflicts"]
}

assert "energy_kcal" in conflicted_fields
assert "protein_g" in conflicted_fields
assert "fat_g" in conflicted_fields
assert "sugars_g" in conflicted_fields

assert "carbohydrates_g" not in conflicted_fields

print("\nNUTRITION CONFLICT TEST PASSED")
