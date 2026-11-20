# NutriLens AI 🥗

**NutriLens AI** is a React + FastAPI application for identifying packaged foods, retrieving product-specific nutrition facts, and generating AI-assisted nutrition insights. Users can search by product name or upload a food-package image. The application prioritizes **verified product identity and source-grounded nutrition data** over guesses based on similar foods.

> **Development status:** Active prototype. The barcode-based Open Food Facts + USDA retrieval, normalization, consolidation, and GPT nutrition-analysis pipeline has been implemented and locally tested. Image-based product identification and confirmation are integrated. **Open Food Facts search failures (including HTTP 502/503) remain under investigation.** This is not a production release.

## Features

- **Catalog search:** Search Open Food Facts for packaged-food products and review candidates.
- **Product confirmation:** Select a specific catalog product before requesting its nutrition analysis.
- **Image upload:** Classify an uploaded package image and extract visible product information using an OpenAI vision-capable model.
- **Identity-first image workflow:** Display the extracted product name, brand, variant, barcode (when visible), and identification confidence. Require user confirmation before searching for catalog candidates.
- **Exact-barcode nutrition retrieval:** Query Open Food Facts and USDA FoodData Central concurrently; do not treat a similar product as an exact match.
- **Normalization and provenance:** Normalize supported nutrients to a per-100 g basis where source data permits; retain nutrient sources and identify conflicts.
- **Grounded AI analysis:** Generate structured nutrition commentary from available verified nutrients, then validate the generated output.
- **Chat-style interface:** React UI for search, upload, product selection, and nutrition results.
- **Resilient catalog client:** The updated catalog module includes bounded retries, short-name fallback searches, and in-memory caching. These measures cannot guarantee service availability.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI |
| Product catalog | Open Food Facts |
| Additional nutrition source | USDA FoodData Central |
| Image extraction | OpenAI API (`gpt-4.1-mini` used in the image-extraction workflow) |
| Grounded nutrition analysis | OpenAI API (`gpt-4o-mini` used in the verified-nutrition workflow) |
| Networking | REST/JSON, multipart uploads, `requests` and `httpx` |
| Nutrition processing | Python normalization, barcode verification, consolidation, and output validation |

## Repository structure

```text
NutriLens-AI/
├── backend/
│   ├── main.py                      # FastAPI routes
│   ├── food_catalog.py              # Catalog search and barcode details
│   ├── vision_service.py            # Image relevance classification
│   ├── product_extraction.py        # Visible package information extraction
│   ├── nutrition_analysis.py        # Image-label analysis workflow
│   ├── nutrition_sources.py         # Parallel OFF / USDA requests
│   ├── nutrition_normalizer.py      # Common nutrient representation
│   ├── nutrition_verifier.py        # Product/barcode verification
│   ├── nutrition_consolidator.py    # Source consolidation
│   ├── nutrition_llm_payload.py     # Grounded LLM input
│   ├── nutrition_llm_analyzer.py    # Structured GPT analysis
│   ├── nutrition_llm_validator.py   # Output validation
│   ├── nutrition_pipeline.py        # End-to-end nutrition workflow
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Chat, search, image confirmation
│   │   ├── NutritionResult.jsx      # Nutrition and analysis display
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   └── package.json
├── .gitignore
└── README.md
```

The tree illustrates the relevant modules; local development files and temporary test scripts are omitted.

## Getting started

### Prerequisites

- Python 3.10+ (subject to your pinned dependency versions)
- Node.js and npm compatible with `frontend/package.json`
- OpenAI API key
- USDA FoodData Central API key for USDA lookups
- Internet access for external APIs

### 1. Clone

```powershell
git clone https://github.com/SumathiThanga/NutriLens-AI.git
cd NutriLens-AI
```

### 2. Configure and start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env` with the variable names expected by your installed backend:

```dotenv
OPENAI_API_KEY=your_openai_api_key
USDA_API_KEY=your_usda_api_key
```

If your local code uses a different USDA environment-variable name, use that exact name instead. Ensure your application loads `.env` (for example, through `python-dotenv` or your shell environment).

For the updated catalog client, you can also configure an appropriate project contact address if supported:

```dotenv
OFF_CONTACT_EMAIL=your_project_contact@example.com
```

Start the API:

```powershell
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs

### 3. Start the frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (typically http://localhost:5173). The current local React integration uses `http://127.0.0.1:8000` as its API base URL.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/products/search` | Search catalog candidates by product name |
| `GET` | `/products/{barcode}` | Retrieve catalog details for a selected barcode |
| `GET` | `/nutrition/analyze/{barcode}` | Run exact-barcode retrieval, consolidation, and grounded AI analysis |
| `POST` | `/images/upload` | Classify an image and extract visible label information |

### Search for a product

```http
POST /products/search
Content-Type: application/json
```

```json
{
  "product_name": "Khatta Meetha Indian Mix"
}
```

Successful responses provide candidate products, typically with a barcode, name, brand, and thumbnail where available. **A search candidate is not a verified match.** Users must confirm the correct product.

### Retrieve a product by barcode

```http
GET /products/3017620422003
```

The response includes catalog details and available nutrition fields. Missing values should remain missing.

### Analyze verified nutrition

```http
GET /nutrition/analyze/3017620422003
```

The backend retrieves available exact-barcode records, verifies identity, normalizes nutrients, consolidates values with source information, builds a grounded LLM payload, and validates the structured AI response.

The structured analysis includes:

- `summary`
- `positive_aspects`
- `concerns`
- `recommendations`
- `limitations`

### Analyze a package image

Submit a JPEG, PNG, or WebP image to `POST /images/upload` as multipart form data (the existing upload flow has a 5 MB limit). The response may include `classification`, `product_info`, `nutrition_analysis`, and processing statuses.

Visible product details can include `product_name`, `brand`, `variant`, `barcode`, `identification_confidence`, `quantity`, `ingredients`, and `nutrition_facts`. A generated explanation based on incomplete image data **does not constitute verified nutrition analysis**.

## Processing workflows

### Product name / barcode

```text
User searches for packaged food
    ↓
Open Food Facts catalog candidates
    ↓
User selects the exact product
    ↓
Barcode-based Open Food Facts + USDA lookup (parallel)
    ↓
Identity verification
    ↓
Nutrient normalization and consolidation
    ↓
Grounded GPT analysis + output validation
    ↓
Nutrition facts, provenance, and insights displayed in React
```

### Package image

```text
User uploads package image
    ↓
File validation + image relevance classification
    ↓
Vision model extracts visible product identity
    ↓
React displays identity and confidence for confirmation
    ↓
Catalog candidate search
    ↓
User selects exact matching product (if available)
    ↓
Verified barcode nutrition pipeline
```

When the brand or barcode cannot be read, the application must not assume a matching product or invent nutrients. The image endpoint can also produce preliminary label-based commentary, which should be distinguished from barcode-verified results.

## Data quality, safety, and limitations

- **Exact identity first:** Similar product names, variants, or brands do not prove a match.
- **Incomplete catalogs:** Open Food Facts and USDA may not contain the requested exact barcode.
- **External API failures:** Open Food Facts can return HTTP 429/502/503 or time out. The UI must distinguish an unavailable service from a genuine no-results search.
- **Retries are bounded:** Fallback searches and caching improve usability but cannot fix a sustained upstream outage.
- **Per-100 g vs per-serving:** Do not compare or substitute nutrient values across serving bases without a valid conversion.
- **Unknown is not zero:** Missing nutrients must not be invented.
- **AI uncertainty:** Vision extraction and language-model analysis can be inaccurate; compare against the actual packaging when possible.
- **Not medical advice:** The app provides informational insights, not individualized dietary or medical recommendations.

## Development tests and Git hygiene

Temporary local scripts named `test*.py` are intended to remain internal. Add this rule to the repository's `.gitignore`:

```gitignore
# Local-only development test scripts
test*.py
```

`.gitignore` does not untrack files that have already been committed. For any previously tracked matching files, remove them from Git's index with `git rm --cached` while keeping the local copies. The rule also excludes automated test files matching this pattern; consider tracking a dedicated `tests/` suite later for reproducible CI.

Do not commit `.env`, API keys, virtual environments, generated credentials, or other secrets.

## Current development priorities

1. Diagnose and resolve intermittent catalog-search failures after image confirmation.
2. Improve explicit messaging for catalog unavailability versus zero matching products.
3. Expand test coverage and verify behavior across additional branded foods and barcodes.
4. Prepare secure, configurable deployment after the local workflow is stable.

## License

No license has been specified. Add a `LICENSE` file if you want to grant reuse permissions.
