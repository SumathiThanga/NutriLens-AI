
import json

from vision_service import get_openai_client


def analyze_nutrition(product_info: dict):
    client = get_openai_client()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You are a packaged-food nutrition information assistant. "
                    "Explain ingredients and nutrition facts in simple language. "
                    "Use only the supplied product information. "
                    "Do not invent missing nutrients, ingredients, or health benefits. "
                    "Identify allergens explicitly mentioned in the data. "
                    "Explain nutritional strengths and considerations without "
                    "labeling foods as universally healthy or unhealthy. "
                    "Do not provide medical diagnoses or personalized dietary advice. "
                    "If important information is missing, mention the limitation."
                )
            },
            {
                "role": "user",
                "content": (
                    "Analyze this packaged food product:\n"
                    + json.dumps(product_info, ensure_ascii=False)
                )
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "nutrition_analysis",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "nutritional_highlights": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "ingredients_analysis": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "allergen_information": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "health_considerations": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": [
                        "summary",
                        "nutritional_highlights",
                        "ingredients_analysis",
                        "allergen_information",
                        "health_considerations"
                    ],
                    "additionalProperties": False
                }
            }
        }
    )

    return json.loads(response.output_text)
