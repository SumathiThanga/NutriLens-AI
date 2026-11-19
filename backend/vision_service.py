import os

from dotenv import load_dotenv
from openai import OpenAI

import base64
import json

load_dotenv()

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    return OpenAI(api_key=api_key)


def classify_food_image(image_bytes: bytes, content_type: str):
    client = get_openai_client()

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:{content_type};base64,{encoded_image}"

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You classify images for a packaged-food analysis app. "
                    "Choose exactly one category: food_package, "
                    "ingredients_label, nutrition_label, unrelated, uncertain. "
                    "Food packages include packaged food products. "
                    "Ingredients labels and nutrition labels can appear "
                    "without the product name. "
                    "If the image is blurry or ambiguous, choose uncertain. "
                    "Do not invent product names or ingredients. "
                    "Return only a JSON object with keys "
                    "category, is_relevant, and reason. "
                    "is_relevant must be true only for the first three categories."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Classify this image.",
                    },
                    {
                        "type": "input_image",
                        "image_url": image_data_url,
                    },
                ],
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "food_image_classification",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "food_package",
                                "ingredients_label",
                                "nutrition_label",
                                "unrelated",
                                "uncertain",
                            ],
                        },
                        "is_relevant": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                    "required": [
                        "category",
                        "is_relevant",
                        "reason",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    result = json.loads(response.output_text)

    result["is_relevant"] = result["category"] in {
        "food_package",
        "ingredients_label",
        "nutrition_label",
    }

    return result
