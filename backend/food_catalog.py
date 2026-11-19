import requests

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"


def search_food_products(product_name: str):

    params = {
        "search_terms": product_name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5,
        "fields": "code,product_name,brands,image_front_small_url"
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers={
            "User-Agent": "NutriLensAI/0.1 (development)"
        },
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    return data.get("products", [])

def get_product_by_barcode(barcode: str):

    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

    response = requests.get(
        url,
        headers={
            "User-Agent": "NutriLensAI/0.1 (development)"
        },
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != 1:
        return None

    product = data.get("product", {})

    nutriments = product.get("nutriments", {})

    nutrition = {
        "energy_kcal": nutriments.get("energy-kcal_100g"),
        "protein_g": nutriments.get("proteins_100g"),
        "carbohydrates_g": nutriments.get("carbohydrates_100g"),
        "fat_g": nutriments.get("fat_100g"),
        "saturated_fat_g": nutriments.get("saturated-fat_100g"),
        "sugars_g": nutriments.get("sugars_100g"),
        "salt_g": nutriments.get("salt_100g"),
        "calcium_mg": (
            round(nutriments["calcium_100g"] * 1000, 2)
            if nutriments.get("calcium_100g") is not None
            else None
        )
    }

    return {
        "barcode": product.get("code"),
        "product_name": product.get("product_name"),
        "brands": product.get("brands"),
        "ingredients_text": product.get("ingredients_text"),
        "nutrition_per_100g": nutrition,
        "image_url": product.get("image_front_url")
    }