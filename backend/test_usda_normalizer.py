
import json
from nutrition_normalizer import normalize_usda

# Sample USDA-format record for testing.
# These are synthetic values, not actual product data.
sample_usda = {
    "source": "usda",
    "barcode": "123456789012",
    "product_name": "Test Food Product",
    "brand": "Test Brand",
    "fdc_id": 1234567,
    "serving_size": 52.0,
    "serving_size_unit": "g",
    "nutrients": [
        {
            "nutrientId": 1008,
            "nutrientName": "Energy",
            "value": 450,
            "unitName": "KCAL",
        },
        {
            "nutrientId": 1003,
            "nutrientName": "Protein",
            "value": 8.5,
            "unitName": "G",
        },
        {
            "nutrientId": 1005,
            "nutrientName": "Carbohydrate",
            "value": 55,
            "unitName": "G",
        },
        {
            "nutrientId": 1004,
            "nutrientName": "Total lipid (fat)",
            "value": 20,
            "unitName": "G",
        },
        {
            "nutrientId": 1258,
            "nutrientName": "Fatty acids, total saturated",
            "value": 7,
            "unitName": "G",
        },
        {
            "nutrientId": 2000,
            "nutrientName": "Sugars, total",
            "value": 30,
            "unitName": "G",
        },
        {
            "nutrientId": 1093,
            "nutrientName": "Sodium, Na",
            "value": 120,
            "unitName": "MG",
        },
    ],
}

result = normalize_usda(sample_usda)

print(json.dumps(result, indent=2))

assert result["nutrition"]["energy_kcal"] == 450
assert result["nutrition"]["protein_g"] == 8.5
assert result["nutrition"]["salt_g"] == 0.3
assert result["fdc_id"] == 1234567
assert result["serving_size"] == 52.0
assert result["serving_size_unit"] == "g"
print("\nUSDA normalization test PASSED")
