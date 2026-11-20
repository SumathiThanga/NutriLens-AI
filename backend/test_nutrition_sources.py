
import asyncio
import os

from dotenv import load_dotenv
from nutrition_sources import retrieve_nutrition_sources


from nutrition_normalizer import normalize_nutrition_sources
from nutrition_verifier import verify_nutrition_sources
from nutrition_consolidator import consolidate_nutrition


load_dotenv()


import json


async def main():
    barcode = input("Enter product barcode: ").strip()

    if not barcode.isdigit():
        print("Please enter a valid numeric barcode.")
        return

    usda_api_key = os.getenv("USDA_API_KEY", "DEMO_KEY")

    print("\nRetrieving nutrition data in parallel...\n")

    results = await retrieve_nutrition_sources(
        barcode=barcode,
        usda_api_key=usda_api_key,
    )

    normalized = normalize_nutrition_sources(results)
    verified = verify_nutrition_sources(normalized)
    consolidated = consolidate_nutrition(verified)

    print("\nCONSOLIDATED NUTRITION:")
    print(json.dumps(consolidated, indent=2))
    print("\nPRODUCT VERIFICATION:")
    print("Verified sources:", len(verified["verified_sources"]))
    print("Rejected sources:", len(verified["rejected_sources"]))

    for source in verified["verified_sources"]:
        print(
            "Accepted:",
            source["source"],
            source["product_name"],
            source["barcode"],
        )

    print("\nNORMALIZED NUTRITION:")
    print(json.dumps(normalized, indent=2))

    print("Selected barcode:", results["barcode"])
    print("Matching sources:", len(results["sources"]))

    for source in results["sources"]:
        print("\n" + "=" * 50)
        print("Source:", source["source"])
        print("Product:", source.get("product_name"))
        print("Brand:", source.get("brand"))

        nutrients = (
            source.get("nutriments")
            or source.get("nutrients")
            or {}
        )

        if isinstance(nutrients, dict):
            print("Energy:", nutrients.get("energy-kcal_100g"))
            print("Protein:", nutrients.get("proteins_100g"))
            print("Fat:", nutrients.get("fat_100g"))
            print("Sugar:", nutrients.get("sugars_100g"))
        else:
            print("USDA nutrient entries:", len(nutrients))
            for nutrient in nutrients[:5]:
                print(
                    nutrient.get("nutrientName"),
                    nutrient.get("value"),
                    nutrient.get("unitName"),
                )

        

if __name__ == "__main__":
    asyncio.run(main())
