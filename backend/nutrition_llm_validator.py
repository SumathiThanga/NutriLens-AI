import re

REQUIRED_FIELDS = [
    "summary",
    "positive_aspects",
    "concerns",
    "recommendations",
    "limitations",
]
LIST_FIELDS = REQUIRED_FIELDS[1:]

UNSUPPORTED_CLAIMS = [
    "does not provide significant vitamins",
    "does not contain vitamins",
    "does not contain minerals",
    "contains no vitamins",
    "contains no minerals",
]


def validate_nutrient_numbers(result, payload):
    """Check explicit per-100-g nutrient measurements in common phrasings.

    This is a limited regex safeguard, not comprehensive fact checking.
    """
    nutrient_patterns = {
        "energy_kcal": r"(?:energy|calories|kcal)",
        "protein_g": r"protein",
        "carbohydrates_g": r"(?:carbohydrates|carbs)",
        "fat_g": r"(?<!saturated )\bfat\b",
        "saturated_fat_g": r"saturated\s+fat",
        "sugars_g": r"(?:sugar|sugars)",
        "salt_g": r"salt",
    }
    available = payload.get("available_nutrients", {})
    statements = [result["summary"]]
    for field in LIST_FIELDS:
        statements.extend(result[field])

    for statement in statements:
        text = statement.lower()
        # The '100 g' in 'per 100 g' is a basis, not a nutrient quantity.
        cleaned_text = re.sub(r"\bper\s+100\s*(?:g|grams?)\b", "", text)
        for nutrient, pattern in nutrient_patterns.items():
            # Nutrient first: 'protein (6.3 g)' or 'protein: 6.3 g'.
            after = re.finditer(
                rf"\b(?:{pattern})\b\s*(?:\(|:|is|of|contains|at|=|\s)*\s*"
                rf"(\d+(?:\.\d+)?)\s*(g|kcal)\b",
                cleaned_text,
            )
            # Quantity first: '6.3 g of protein' or '6.3 g protein'.
            before = re.finditer(
                rf"\b(\d+(?:\.\d+)?)\s*(g|kcal)\s*(?:of\s+)?(?:{pattern})\b",
                cleaned_text,
            )
            for match in list(after) + list(before):
                reported = float(match.group(1))
                unit = match.group(2)
                if nutrient == "energy_kcal" and unit != "kcal":
                    continue
                if nutrient != "energy_kcal" and unit != "g":
                    continue
                if nutrient not in available:
                    raise ValueError(f"Unsupported numeric claim for {nutrient}")
                expected = float(available[nutrient]["value"])
                if abs(reported - expected) > 0.01:
                    raise ValueError(
                        f"Incorrect {nutrient}: GPT reported {reported}, "
                        f"verified value is {expected}"
                    )


def validate_nutrition_analysis(result, payload):
    if not isinstance(result, dict):
        raise ValueError("LLM response must be a JSON object")
    for field in REQUIRED_FIELDS:
        if field not in result:
            raise ValueError(f"Missing field: {field}")
    if not isinstance(result["summary"], str):
        raise ValueError("Summary must be a string")
    for field in LIST_FIELDS:
        if not isinstance(result[field], list):
            raise ValueError(f"{field} must be a list")
        if not all(isinstance(item, str) for item in result[field]):
            raise ValueError(f"{field} must contain only strings")
    if not payload.get("analysis_allowed"):
        raise ValueError("Nutrition analysis is not permitted without data")
    statements = [result["summary"]]
    for field in LIST_FIELDS:
        statements.extend(result[field])
    for statement in statements:
        normalized = statement.lower()
        for claim in UNSUPPORTED_CLAIMS:
            if claim in normalized:
                raise ValueError(f"Unsupported nutrition claim: {statement}")
    validate_nutrient_numbers(result, payload)
    return result
