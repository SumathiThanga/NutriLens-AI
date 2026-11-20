
import { useState } from "react";

export default function NutritionAnalysis() {
  const [barcode, setBarcode] = useState("3017620422003");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function analyzeNutrition() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        `/api/nutrition/analyze/${encodeURIComponent(barcode.trim())}`
      );

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Nutrition analysis failed");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h2>NutriLens AI — Nutrition Analysis</h2>

      <input
        value={barcode}
        onChange={(e) => setBarcode(e.target.value)}
        placeholder="Enter product barcode"
      />

      <button onClick={analyzeNutrition} disabled={loading}>
        {loading ? "Analyzing..." : "Analyze Nutrition"}
      </button>

      {error && <p role="alert">{error}</p>}

      {result && (
        <div>
          <h3>{result.product_name}</h3>
          <p>Brand: {result.brand}</p>

          <h4>Nutrition per 100 g</h4>
          <ul>
            {Object.entries(result.nutrition.nutrition).map(
              ([nutrient, value]) => (
                <li key={nutrient}>
                  {nutrient}: {value ?? "Not available"}
                </li>
              )
            )}
          </ul>

          <h4>AI Analysis</h4>
          <p>{result.analysis.summary}</p>

          {[
            "positive_aspects",
            "concerns",
            "recommendations",
            "limitations",
          ].map((section) => (
            <div key={section}>
              <h4>{section.replaceAll("_", " ")}</h4>
              <ul>
                {result.analysis[section].map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
