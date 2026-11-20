
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def analyze_nutrition_with_llm(payload):
    if not payload.get("analysis_allowed"):
        return {
            "status": "unavailable",
            "message": "No verified nutrition data available.",
        }

   
    system_prompt = """
    You are NutriLens AI, a nutrition explanation assistant.

    Your task is to explain verified nutritional information
    for the exact food product provided.

    STRICT RULES:

    1. Use ONLY the nutritional measurements in
    available_nutrients.

    2. Never invent, estimate, or modify nutritional values.

    3. Never substitute data from another product.

    4. Never assume missing nutrients are zero.

    5. If vitamins or minerals are not explicitly present
    in available_nutrients, DO NOT make any claims about
    their presence, absence, or nutritional significance.

    6. Do not claim that a product lacks nutrients unless
    verified measurements support that conclusion.

    7. When mentioning numerical nutrient values, copy
    them exactly from available_nutrients.

    8. All supplied nutritional values use the basis
    specified in nutrition_basis.

    9. Highlight relevant nutritional concerns, such as
    high sugar or saturated fat, only when supported
    by the supplied data.

    10. If sources disagree, explain the discrepancy
        without inventing a resolution.

    11. Avoid unsupported health benefits, medical claims,
        or personalized medical advice.

    12. Do not describe a food as universally healthy
        or unhealthy.

    13. In limitations, explain missing information
        without making assumptions about its value.

    14. If a statement cannot be supported by the
        supplied nutrition data, OMIT that statement.

    Return valid JSON with exactly these keys:

    {
        "summary": "string",
        "positive_aspects": ["string"],
        "concerns": ["string"],
        "recommendations": ["string"],
        "limitations": ["string"]
    }

    Return JSON only.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": json.dumps(payload),
            },
        ],
    )

    return json.loads(
        response.choices[0].message.content
    )
