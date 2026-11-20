from fastapi import FastAPI
from fastapi import HTTPException
from food_catalog import search_food_products, get_product_by_barcode
import requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from vision_service import classify_food_image
from product_extraction import extract_product_information
from nutrition_analysis import analyze_nutrition
from fastapi import HTTPException
from nutrition_pipeline import run_nutrition_pipeline


app = FastAPI(
    title="NutriLens AI",
    description="AI-powered food product and ingredient analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
@app.post("/images/upload")
async def upload_image(file: UploadFile = File(...)):

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp"
    }

    max_size = 5 * 1024 * 1024

    # Step 1: Validate file type
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WebP images are allowed."
        )

    # Step 2: Validate file size
    contents = await file.read(max_size + 1)

    if len(contents) > max_size:
        raise HTTPException(
            status_code=413,
            detail="Image must be smaller than 5 MB."
        )

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty."
        )

    # Step 3: Classify image using OpenAI Vision
    try:
        classification = classify_food_image(
            image_bytes=contents,
            content_type=file.content_type
        )
    except Exception:
        # Log the detailed error on the backend only
        import logging
        logging.exception("Image classification failed")

        raise HTTPException(
            status_code=502,
            detail="Image analysis is temporarily unavailable."
        )


    # Step 4: Extract product information if relevant
    product_info = None
    extraction_status = "skipped"

    if classification["is_relevant"]:
        try:
            product_info = extract_product_information(
                image_bytes=contents,
                content_type=file.content_type
            )
            extraction_status = "success"

        except Exception:
            import logging
            logging.exception("Product extraction failed")
            extraction_status = "failed"

    # 
    # Step 5: Analyze nutrition if extraction succeeded
    nutrition_analysis = None
    analysis_status = "skipped"

    if extraction_status == "success" and product_info:
        try:
            nutrition_analysis = analyze_nutrition(product_info)
            analysis_status = "success"

        except Exception:
            import logging
            logging.exception("Nutrition analysis failed")
            analysis_status = "failed"

    # Step 6: Return all results
    return {
        "status": "success",
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(contents),
        "classification": classification,
        "extraction_status": extraction_status,
        "product_info": product_info,
        "analysis_status": analysis_status,
        "nutrition_analysis": nutrition_analysis
    }


@app.get("/")
def home():
    return {
        "message": "Welcome to NutriLens AI",
        "status": "running"
    }
from pydantic import BaseModel, Field


class ProductSearchRequest(BaseModel):
    product_name: str = Field(
        min_length=2,
        max_length=200,
        description="Name of the packaged food product"
    )

@app.post("/products/search")
def search_product(request: ProductSearchRequest):

    product_name = request.product_name.strip()

    if len(product_name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Please enter a valid food product name."
        )

    try:
        products = search_food_products(product_name)

    except requests.RequestException as e:
        print(f"Open Food Facts API Error: {type(e).__name__}: {e}")

        raise HTTPException(
            status_code=502,
            detail="Unable to connect to the food product database."
        ) from e

    return {
        "status": "success",
        "search_query": product_name,
        "total_results": len(products),
        "products": products
    }

@app.get("/products/{barcode}")
def get_product_details(barcode: str):

    if not barcode.isascii() or not barcode.isdigit():
        raise HTTPException(
            status_code=422,
            detail="Barcode must contain only digits."
        )

    try:
        product = get_product_by_barcode(barcode)

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve product details."
        )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    return {
        "status": "success",
        "product": product
    }


@app.get("/nutrition/analyze/{barcode}")
async def analyze_product_nutrition(barcode: str):
    barcode = barcode.strip()

    if not barcode.isdigit() or len(barcode) not in (8, 12, 13, 14):
        raise HTTPException(
            status_code=400,
            detail="Invalid product barcode"
        )

    try:
        result = await run_nutrition_pipeline(barcode)

        if result["status"] == "nutrition_unavailable":
            raise HTTPException(
                status_code=404,
                detail="Verified nutrition data unavailable for this barcode"
            )

        return result

    except HTTPException:
        raise

    except Exception:
        # Do not expose internal errors or API credentials.
        raise HTTPException(
            status_code=500,
            detail="Nutrition analysis failed"
        )
