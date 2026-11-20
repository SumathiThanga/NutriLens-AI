
from nutrition_llm_validator import validate_nutrition_analysis

payload = {
    "analysis_allowed": True,
    "available_nutrients": {
        "protein_g": {
            "value": 6.3,
            "source": "open_food_facts"
        }
    }
}

result = {
    "summary": "Nutella contains protein (6.3 g per 100 g).",
    "positive_aspects": [],
    "concerns": [],
    "recommendations": [],
    "limitations": []
}

validated = validate_nutrition_analysis(result, payload)

assert validated == result

print("PER 100G VALIDATION TEST PASSED")
