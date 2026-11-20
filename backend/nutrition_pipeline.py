
import asyncio
import os

from dotenv import load_dotenv

from nutrition_sources import retrieve_nutrition_sources
from nutrition_normalizer import normalize_nutrition_sources
from nutrition_verifier import verify_nutrition_sources
from nutrition_consolidator import consolidate_nutrition
from nutrition_llm_payload import prepare_nutrition_llm_payload
from nutrition_llm_analyzer import analyze_nutrition_with_llm
from nutrition_llm_validator import validate_nutrition_analysis

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


async def run_nutrition_pipeline(barcode):
    usda_api_key = os.getenv("USDA_API_KEY")

    if not usda_api_key:
        raise ValueError("USDA_API_KEY is missing")

    # 1. Retrieve nutrition from multiple APIs
    raw_results = await retrieve_nutrition_sources(
        barcode,
        usda_api_key,
    )

    # 2. Normalize the nutrition records
    normalized = normalize_nutrition_sources(raw_results)

    # 3. Verify exact product barcode
    verified = verify_nutrition_sources(normalized)

    # 4. Consolidate verified nutrition values
    consolidated = consolidate_nutrition(verified)

    # 5. Handle unavailable nutrition data
    if not verified["verified_sources"]:
        return {
            "status": "nutrition_unavailable",
            "barcode": barcode,
            "nutrition": consolidated,
            "analysis": None,
        }

    # 6. Get product details from verified source
    product = verified["verified_sources"][0]

    # 7. Prepare the LLM payload
    payload = prepare_nutrition_llm_payload(
        consolidated,
        product_name=product.get("product_name"),
        brand=product.get("brand"),
    )

    if not payload["analysis_allowed"]:
        return {
            "status": "nutrition_unavailable",
            "barcode": barcode,
            "nutrition": consolidated,
            "analysis": None,
        }

    # 8. Run synchronous OpenAI call in a worker thread
    analysis = await asyncio.to_thread(
        analyze_nutrition_with_llm,
        payload,
    )

    # 9. Validate GPT output
    validated_analysis = validate_nutrition_analysis(
        analysis,
        payload,
    )

    return {
        "status": "success",
        "barcode": barcode,
        "product_name": product.get("product_name"),
        "brand": product.get("brand"),
        "nutrition": consolidated,
        "analysis": validated_analysis,
    }
