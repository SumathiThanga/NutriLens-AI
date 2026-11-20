
from nutrition_llm_validator import validate_nutrition_analysis

payload = {
    "analysis_allowed": True,
    "available_nutrients": {
        "energy_kcal": {
            "value": 539,
            "source": "open_food_facts",
        },
        "sugars_g": {
            "value": 56.3,
            "source": "open_food_facts",
        },
    },
    "missing_nutrients": ["protein_g"],
}

result = {
    "summary": "This product contains 12 g of protein per 100 g.",
    "positive_aspects": [],
    "concerns": [],
    "recommendations": [],
    "limitations": [],
}

try:
    validate_nutrition_analysis(result, payload)

except ValueError as error:
    print("Missing nutrient hallucination rejected.")
    print("Reason:", error)

else:
    raise AssertionError(
        "TEST FAILED: Missing nutrient value was accepted."
    )

print("\nMISSING NUTRIENT HALLUCINATION TEST PASSED")
