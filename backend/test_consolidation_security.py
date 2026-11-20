
from nutrition_consolidator import consolidate_nutrition

test_data = {
    "barcode": "3017620422003",
    "verified_sources": [
        {
            "source": "usda",
            "barcode": "009800800124",
            "nutrition_basis": "per_100g",
            "nutrition": {
                "energy_kcal": 519,
                "protein_g": 7.69,
            },
        }
    ],
}

try:
    consolidate_nutrition(test_data)

except ValueError as error:
    print("Correctly rejected mismatched product")
    print("Reason:", error)

else:
    raise AssertionError(
        "SECURITY TEST FAILED: "
        "Mismatched product was accepted"
    )

print("\nCONSOLIDATION SECURITY TEST PASSED")
