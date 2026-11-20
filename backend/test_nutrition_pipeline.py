
import asyncio
import json

from nutrition_pipeline import run_nutrition_pipeline


async def main():
    barcode = input("Enter product barcode: ").strip()

    result = await run_nutrition_pipeline(barcode)

    print("\nCOMPLETE NUTRITION PIPELINE RESULT:")
    print(json.dumps(result, indent=2))

    assert result["status"] in [
        "success",
        "nutrition_unavailable",
    ]

    print("\nNUTRITION PIPELINE TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
