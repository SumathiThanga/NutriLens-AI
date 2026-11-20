
import os
import requests
from dotenv import load_dotenv

load_dotenv("backend/.env")

api_key = os.getenv("USDA_API_KEY")

if not api_key or api_key == "DEMO_KEY":
    raise ValueError("Valid USDA API key not configured")

url = "https://api.nal.usda.gov/fdc/v1/foods/search"

params = {
    "api_key": api_key,
    "query": "Nutella",
    "dataType": ["Branded"],
    "pageSize": 3,
}

response = requests.get(
    url,
    params=params,
    timeout=20,
)

print("HTTP Status:", response.status_code)

response.raise_for_status()

foods = response.json().get("foods", [])

print("Products returned:", len(foods))

for food in foods:
    print(
        "Product:", food.get("description"),
        "| Barcode:", food.get("gtinUpc")
    )

print("\nUSDA API KEY TEST PASSED")
