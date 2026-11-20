
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
                "saturated_fat_g": None,
                "sugars_g": None,
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
                "saturated_fat_g": 10.8,
                "sugars_g": 56.0,
                "salt_g": 0.11,
            },
        },
    ],
}

result = consolidate_nutrition(test_data)

assert result["nutrition"]["energy_kcal"] == 539
assert result["nutrition"]["saturated_fat_g"] == 10.8
assert result["nutrition"]["sugars_g"] == 56.0

assert result["provenance"]["energy_kcal"] == "open_food_facts"
assert result["provenance"]["saturated_fat_g"] == "usda"
assert result["provenance"]["sugars_g"] == "usda"

print("NUTRITION MISSING VALUES TEST PASSED")

print("\nSelected nutrition:")
for nutrient, value in result["nutrition"].items():
    print(
        nutrient,
        "=",
        value,
        "| Source:",
        result["provenance"][nutrient]
    )
