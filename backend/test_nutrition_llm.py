
import json

from nutrition_llm_payload import prepare_nutrition_llm_payload
from nutrition_llm_analyzer import analyze_nutrition_with_llm
from nutrition_llm_validator import validate_nutrition_analysis
sample = {
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
    "provenance": {
        key: "open_food_facts"
        for key in [
            "energy_kcal",
            "protein_g",
            "carbohydrates_g",
            "fat_g",
            "saturated_fat_g",
            "sugars_g",
            "salt_g",
        ]
    },
    "conflicts": [],
    "sources_used": ["open_food_facts"],
}

payload = prepare_nutrition_llm_payload(
    sample,
    product_name="Nutella",
    brand="Ferrero",
)

result = analyze_nutrition_with_llm(payload)

validated_result = validate_nutrition_analysis(
    result,
    payload,
)

print("\nVALIDATED GPT ANALYSIS:")
print(json.dumps(validated_result, indent=2))


print("\nGPT NUTRITION ANALYSIS:")
print(json.dumps(result, indent=2))

assert result.get("summary")
assert isinstance(result.get("concerns"), list)
assert isinstance(result.get("recommendations"), list)

print("\nGPT NUTRITION ANALYSIS TEST PASSED")
