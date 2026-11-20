
from nutrition_llm_validator import validate_nutrition_analysis

payload = {
    "analysis_allowed": True,
    "available_nutrients": {
        "protein_g": {
            "value": 6.3,
            "source": "open_food_facts",
        }
    },
}

result = {
    "summary": "Nutella contains 15 g of protein per 100 g.",
    "positive_aspects": [],
    "concerns": [],
    "recommendations": [],
    "limitations": [],
}

try:
    validate_nutrition_analysis(result, payload)

except ValueError as error:
    print("Incorrect nutrition value rejected.")
    print("Reason:", error)

else:
    raise AssertionError(
        "TEST FAILED: Incorrect protein value accepted."
    )

print("\nNUTRIENT NUMBER VALIDATION TEST PASSED")
