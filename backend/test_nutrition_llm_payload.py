
import json

from nutrition_llm_payload import prepare_nutrition_llm_payload

sample = {
    "barcode": "3017620422003",
    "nutrition_basis": "per_100g",
    "nutrition": {
        "energy_kcal": 539,
        "protein_g": 6.3,
        "sugars_g": 56.3,
        "salt_g": None,
    },
    "provenance": {
        "energy_kcal": "open_food_facts",
        "protein_g": "open_food_facts",
        "sugars_g": "open_food_facts",
        "salt_g": None,
    },
    "conflicts": [],
    "sources_used": ["open_food_facts"],
}

payload = prepare_nutrition_llm_payload(
    sample,
    product_name="Nutella",
    brand="Ferrero",
)

print(json.dumps(payload, indent=2))

assert payload["analysis_allowed"] is True
assert "salt_g" in payload["missing_nutrients"]
assert "salt_g" not in payload["available_nutrients"]

print("\nLLM PAYLOAD TEST PASSED")
