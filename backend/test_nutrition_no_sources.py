
from nutrition_consolidator import consolidate_nutrition

test_data = {
    "barcode": "9999999999999",
    "verified_sources": [],
    "rejected_sources": [],
}

result = consolidate_nutrition(test_data)

print("\nCONSOLIDATION RESULT:")
print(result)

assert result["barcode"] == "9999999999999"

assert all(
    
    value is None
    for value in result["nutrition"].values()
)

assert result["sources_used"] == []
assert result["conflicts"] == []

print("\nNO SOURCES TEST PASSED")
