
import os
import json
import requests

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")

url = "https://api.nal.usda.gov/fdc/v1/foods/search"

params = {
    "api_key": API_KEY,
    "query": "Nutella",
    "dataType": ["Branded"],
    "pageSize": 3,
}

response = requests.get(
    url,
    params=params,
    timeout=20,
)

response.raise_for_status()

foods = response.json().get("foods", [])

print("USDA products returned:", len(foods))

if foods:
    product = foods[0]

    print("\nPRODUCT INFORMATION")
    print("Description:", product.get("description"))
    print("Brand:", product.get("brandOwner"))
    print("Barcode:", product.get("gtinUpc"))
    print("Serving size:", product.get("servingSize"))
    print("Serving unit:", product.get("servingSizeUnit"))

    print("\nFIRST 10 NUTRIENTS")
    print(
        json.dumps(
            product.get("foodNutrients", [])[:10],
            indent=2,
        )
    )
