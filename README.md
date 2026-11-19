# NutriLens AI 🥗

**NutriLens AI** is a web application for exploring packaged-food information. Search for a product in the Open Food Facts catalog, select a matching item to inspect its recorded nutrition data, or upload a food-package image to extract visible label information and receive AI-generated nutrition insights.

> **Baseline release:** This README describes the current React + FastAPI implementation. Parallel retrieval from multiple nutrition databases and LLM-based source consolidation are planned enhancements, **not implemented in this baseline**.

## Features

- **Product search:** Search the Open Food Facts catalog by product name and choose from matching products.
- **Product details:** Retrieve the selected product by barcode, including available ingredients and nutrition values.
- **Image upload:** Upload a JPEG, PNG, or WebP image of a food package or label (maximum 5 MB).
- **Image relevance check:** Classify uploaded images before attempting extraction.
- **AI-assisted label extraction:** Extract visible product name, brand, quantity, ingredients, and nutrition facts using an OpenAI vision-capable model.
- **Nutrition insights:** Generate a summary, nutritional highlights, ingredient analysis, allergen information, and health considerations from extracted information.
- **Conversational UI:** Search and upload within a chat-style React interface, with structured nutrition results.

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI |
| Product catalog | Open Food Facts API |
| Image understanding and nutrition analysis | OpenAI API (`gpt-4.1-mini` in the baseline implementation) |
| HTTP communication | REST / JSON; multipart upload for images |

## Repository structure

```text
NutriLens-AI/
├── backend/
│   ├── main.py                 # FastAPI routes and request handling
│   ├── food_catalog.py         # Open Food Facts integration
│   ├── vision_service.py       # Image classification
│   ├── product_extraction.py   # AI-assisted label extraction
│   ├── nutrition_analysis.py   # AI nutrition insights
│   ├── requirements.txt
│   ├── test_product_details.py
│   ├── testfood_catalog.py
│   └── .gitignore
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Chat interface and API calls
│   │   ├── App.css
│   │   ├── NutritionResult.jsx  # Structured image-analysis results
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── .gitignore
└── README.md
```

## Getting started

### Prerequisites

- Python 3.10+ (or a compatible Python version for the pinned dependencies)
- Node.js and npm (use a version compatible with `frontend/package.json`)
- An OpenAI API key for image analysis

### 1. Clone the repository

```bash
git clone https://github.com/SumathiThanga/NutriLens-AI.git
cd NutriLens-AI
```

### 2. Start the backend

On Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env`:

```dotenv
OPENAI_API_KEY=your_openai_api_key_here
```

Start FastAPI:

```powershell
uvicorn main:app --reload
```

Backend: **http://127.0.0.1:8000**  
Interactive API documentation: **http://127.0.0.1:8000/docs**

> Keep `.env` out of Git. Do not commit API keys or credentials.

### 3. Start the frontend

Open a **second terminal** from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** (or the URL printed by Vite).

The baseline frontend uses `http://127.0.0.1:8000` as its API base URL in `frontend/src/App.jsx`.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/products/search` | Search catalog products by name |
| `GET` | `/products/{barcode}` | Fetch a selected product and its available nutrition data |
| `POST` | `/images/upload` | Classify a food image, extract label details, and analyze nutrition |

### Search for a product

**Request**

```http
POST /products/search
Content-Type: application/json
```

```json
{
  "product_name": "Bru coffee"
}
```

A successful response contains the search query and a list of products, typically including product names, brands, barcodes, and available thumbnail URLs.

### Get product details

```http
GET /products/{barcode}
```

Replace `{barcode}` with the barcode returned by product search. Nutrition values depend on the selected product's Open Food Facts record; missing values should remain missing.

### Analyze a package image

Send a multipart request to `POST /images/upload` with an image file. The backend validates the upload, checks image relevance, extracts visible package information, and produces AI-generated nutrition insights when sufficient information is available.

The response can include `classification`, `product_info`, `nutrition_analysis`, and processing status fields.

## How it works

### Catalog search

```text
User enters product name
        ↓
FastAPI /products/search
        ↓
Open Food Facts search
        ↓
User selects a product
        ↓
FastAPI /products/{barcode}
        ↓
Display available product-specific details
```

### Image analysis

```text
User uploads package / label image
        ↓
Validate file type and size
        ↓
AI image relevance classification
        ↓
AI extraction of visible product / label details
        ↓
AI nutrition analysis
        ↓
Display structured results in React
```

## Data quality and limitations

- **Exact-product data matters.** A similar product or generic food is not a substitute for the selected branded item.
- **Catalog coverage varies.** Open Food Facts is a community-contributed database; records may be incomplete, outdated, or temporarily unavailable.
- **Missing nutrients are not zero.** If the source does not report a nutrient, the application should not invent it.
- **Image analysis can make mistakes.** Check extracted quantities, nutrient units, and serving basis against the original package label.
- **Serving basis matters.** Nutrition per serving, per 25 g, and per 100 g must not be treated as interchangeable.
- **Not medical advice.** AI-generated nutrition insights are informational and do not replace professional dietary or medical guidance.

## Planned improvements

- Query **Open Food Facts, USDA FoodData Central, Edamam, and Nutritionix** concurrently.
- Verify product identity across sources using barcode/GTIN and strict brand/variant checks.
- Normalize nutrient units and serving bases while retaining source attribution.
- Use an LLM to compare **verified** source records and explain discrepancies, with deterministic validation of displayed numbers.
- Improve API retries, graceful fallback, and unavailable-data messaging.

## License

No license is specified in this baseline. Add a `LICENSE` file if you intend to grant reuse permissions.
