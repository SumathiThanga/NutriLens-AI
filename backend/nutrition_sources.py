
import asyncio
import httpx


async def fetch_open_food_facts(barcode: str):
    url = (
        "https://world.openfoodfacts.org"
        f"/api/v2/product/{barcode}.json"
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "NutriLensAI/1.0"
                },
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != 1:
                return None

            product = data.get("product", {})

            if str(product.get("code")) != str(barcode):
                return None

            return {
                "source": "open_food_facts",
                "barcode": barcode,
                "product_name": product.get("product_name"),
                "brand": product.get("brands"),
                "nutriments": product.get("nutriments", {}),
            }

    except (httpx.HTTPError, ValueError) as exc:
        print(f"Open Food Facts error: {exc}")
        return None


async def fetch_usda(barcode: str, api_key: str):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"

    params = {
        "api_key": api_key,
        "query": barcode,
        "dataType": ["Branded"],
        "pageSize": 10,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

            foods = response.json().get("foods", [])

            for food in foods:
                if str(food.get("gtinUpc", "")).strip() == str(barcode):
                    return {
                        "source": "usda",
                        "barcode": str(food.get("gtinUpc", "")),
                        "product_name": food.get("description"),
                        "brand": food.get("brandOwner"),
                        "fdc_id": food.get("fdcId"),
                        "serving_size": food.get("servingSize"),
                        "serving_size_unit": food.get("servingSizeUnit"),
                        "nutrients": food.get("foodNutrients", []),
                    }

            return None

    except (httpx.HTTPError, ValueError) as exc:
        print(f"USDA error: {exc}")
        return None


async def retrieve_nutrition_sources(
    barcode: str,
    usda_api_key: str,
):
    results = await asyncio.gather(
        fetch_open_food_facts(barcode),
        fetch_usda(barcode, usda_api_key),
        return_exceptions=True,
    )

    return {
        "barcode": barcode,
        "sources": [
            result
            for result in results
            if isinstance(result, dict)
        ],
    }
