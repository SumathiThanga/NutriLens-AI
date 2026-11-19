
import base64
import json

from vision_service import get_openai_client


def extract_product_information(
    image_bytes: bytes,
    content_type: str
):
    client = get_openai_client()

    encoded_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    image_url = (
        f"data:{content_type};base64,{encoded_image}"
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You extract information from images "
                    "of packaged food products. "
                    "Read only information visible in the image. "
                    "Do not guess missing information. "
                    "Return null for any field that is not visible. "
                    "Return ingredients and nutrition facts "
                    "as text exactly as observed, when readable."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Extract the visible product name, "
                            "brand, quantity, ingredients, "
                            "and nutrition facts."
                        )
                    },
                    {
                        "type": "input_image",
                        "image_url": image_url
                    }
                ]
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "food_product_extraction",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": ["string", "null"]
                        },
                        "brand": {
                            "type": ["string", "null"]
                        },
                        "quantity": {
                            "type": ["string", "null"]
                        },
                        "ingredients": {
                            "type": ["string", "null"]
                        },
                        "nutrition_facts": {
                            "type": ["string", "null"]
                        }
                    },
                    "required": [
                        "product_name",
                        "brand",
                        "quantity",
                        "ingredients",
                        "nutrition_facts"
                    ],
                    "additionalProperties": False
                }
            }
        }
    )

    return json.loads(response.output_text)
