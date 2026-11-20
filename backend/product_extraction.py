import base64
import json

from vision_service import get_openai_client


def extract_product_information(image_bytes: bytes, content_type: str):
    """Extract visible packaged-food information without inferring missing facts."""
    client = get_openai_client()

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{content_type};base64,{encoded_image}"

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You extract information from images of packaged food products. "
                    "Read only information visible in the image. Do not guess missing "
                    "information. Return null for fields that are not visible or "
                    "cannot be read reliably. Transcribe ingredients and nutrition "
                    "facts exactly as observed, when readable. Identify the brand "
                    "separately from the product name. The variant is a visible "
                    "flavor, formulation, or product subtype, if stated. Only return "
                    "a barcode when its digits are clearly readable in the image; "
                    "never invent barcode digits. identification_confidence is "
                    "your confidence in the visible product identity (name and brand), "
                    "not a guarantee of a database match. Use low when identity is "
                    "uncertain, medium when partially readable, and high when clearly "
                    "readable. Return null if product identity cannot be established. "
                    "Do not infer nutrition or ingredients from product category."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Extract visible product name, brand, variant, barcode, "
                            "quantity, ingredients, and nutrition facts. Report "
                            "identification confidence based on image legibility."
                        ),
                    },
                    {"type": "input_image", "image_url": image_url},
                ],
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "food_product_extraction",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "product_name": {"type": ["string", "null"]},
                        "brand": {"type": ["string", "null"]},
                        "variant": {"type": ["string", "null"]},
                        "barcode": {"type": ["string", "null"]},
                        "identification_confidence": {
                            "type": ["string", "null"],
                            "enum": ["low", "medium", "high", None],
                        },
                        "quantity": {"type": ["string", "null"]},
                        "ingredients": {"type": ["string", "null"]},
                        "nutrition_facts": {"type": ["string", "null"]},
                    },
                    "required": [
                        "product_name",
                        "brand",
                        "variant",
                        "barcode",
                        "identification_confidence",
                        "quantity",
                        "ingredients",
                        "nutrition_facts",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    result = json.loads(response.output_text)

    # Reject malformed barcode strings even if the model emits one.
    barcode = result.get("barcode")
    if barcode is not None:
        barcode = barcode.strip().replace(" ", "")
        result["barcode"] = (
            barcode if barcode.isascii() and barcode.isdigit()
            and len(barcode) in (8, 12, 13, 14) else None
        )

    return result
