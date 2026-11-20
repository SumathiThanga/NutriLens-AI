
from nutrition_llm_validator import validate_nutrition_analysis

payload = {
    "barcode": "3017620422003",
    "analysis_allowed": True,
    "available_nutrients": {
        "energy_kcal": {
            "value": 539,
            "source": "open_food_facts"
        },
        "sugars_g": {
            "value": 56.3,
            "source": "open_food_facts"
        }
    },
    "missing_nutrients": [
        "vitamins",
        "minerals"
    ]
}

llm_result = {
    "summary": "Nutella contains 539 kcal per 100 g.",
    "positive_aspects": [],
    "concerns": [
        "Contains 56.3 g of sugar per 100 g."
    ],
    "recommendations": [
        "Consume in moderation."
    ],
    "limitations": [
        "Does not provide significant vitamins or minerals."
    ]
}

try:
    validate_nutrition_analysis(llm_result, payload)

except ValueError as error:
    print("Unsupported claim correctly rejected.")
    print("Reason:", error)

else:
    raise AssertionError(
        "TEST FAILED: Unsupported claim was accepted."
    )

print("\nNUTRITION VALIDATOR TEST PASSED")
