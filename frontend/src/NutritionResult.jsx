import React from "react";

// Extract only numbers explicitly present in the label text. Never infer a missing value.
function getNutrient(text, patterns) {
  if (!text) return null;
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return match[1];
  }
  return null;
}

const nutrientSpecs = [
  { label: "Calories", icon: "🔥", unit: "kcal", tone: "orange", patterns: [/\benergy\s*(?:\(?\s*kcal\s*\)?\s*)?[:\s]+([\d.]+)\s*kcal\b/i, /\benergy\s*\(?\s*kcal\s*\)?\s*[:\s]*([\d.]+)/i] },
  { label: "Protein", icon: "💪", unit: "g", tone: "green", patterns: [/\bprotein\s*(?:\(\s*g\s*\))?\s*[:\s]*([\d.]+)\s*g?\b/i] },
  { label: "Total fat", icon: "🥑", unit: "g", tone: "peach", patterns: [/\b(?:total\s+fat|fat)\s*(?:\(\s*g\s*\))?\s*[:\s]*([\d.]+)\s*g?\b/i] },
  { label: "Calcium", icon: "🦴", unit: "mg", tone: "blue", patterns: [/\bcalcium\s*(?:\(\s*mg\s*\))?\s*[:\s]*([\d.]+)\s*mg?\b/i] },
];

function NutritionResult({ product = {}, analysis, analysisStatus }) {
  const facts = product.nutrition_facts || "";
  const metrics = nutrientSpecs.map((spec) => ({ ...spec, value: getNutrient(facts, spec.patterns) })).filter((metric) => metric.value !== null);
  const servingMatch = facts.match(/\bper\s+(\d+(?:\.\d+)?\s*(?:gms?|grams?|ml)\b(?:\s+per\s+pcs)?)/i);
  const serving = servingMatch ? `Per ${servingMatch[1]}` : "As shown on label";
  const ingredients = (product.ingredients || "").split(/[,;&\n]+/).map((s) => s.trim()).filter(Boolean);
  const sections = [
    { heading: "✨ Nutritional highlights", items: analysis?.nutritional_highlights },
    { heading: "🌿 Ingredient insights", items: analysis?.ingredients_analysis },
    { heading: "❤️ Things to consider", items: analysis?.health_considerations },
  ];

  return (
    <article className="nutrition-result">
      <div className="nr-header">
        <div>
          <div className="nr-eyebrow">✓ Food package analyzed</div>
          <h3>{[product.brand, product.product_name].filter(Boolean).join(" ") || "Food product"}</h3>
          <p className="nr-subtitle">{product.quantity || "Quantity not visible"}</p>
        </div>
        <div className="nr-logo" aria-hidden="true">🌿</div>
      </div>

      {metrics.length > 0 && (
        <section className="nr-section">
          <h4>🍊 Nutrition snapshot <span className="nr-serving">{serving}</span></h4>
          <div className="nr-metrics">
            {metrics.map((metric) => (
              <div className={`nr-metric ${metric.tone}`} key={metric.label}>
                <div className="nr-metric-label">{metric.icon} {metric.label}</div>
                <div className="nr-metric-value">{metric.value}<span className="nr-metric-unit">{metric.unit}</span></div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="nr-section">
        <h4>🌿 Ingredients</h4>
        {ingredients.length > 0 ? (
          <div className="nr-ingredients">
            {ingredients.map((ingredient, i) => <span className="nr-chip" key={`${ingredient}-${i}`}>{ingredient}</span>)}
          </div>
        ) : <p className="nr-subtitle">Ingredients not visible in the image.</p>}
      </section>

      {Array.isArray(analysis?.allergen_information) && analysis.allergen_information.length > 0 && (
        <section className="nr-section nr-alert">
          <h4>⚠️ Allergen information</h4>
          <ul>{analysis.allergen_information.map((item, i) => <li key={i}>{item}</li>)}</ul>
        </section>
      )}

      {analysis?.summary && (
        <section className="nr-section">
          <h4>🤖 AI nutrition overview</h4>
          <div className="nr-summary">{analysis.summary}</div>
        </section>
      )}

      {sections.map((section) => Array.isArray(section.items) && section.items.length > 0 ? (
        <section className="nr-section" key={section.heading}>
          <h4>{section.heading}</h4>
          <ul className="nr-insight-list">{section.items.map((item, i) => <li key={i}>{item}</li>)}</ul>
        </section>
      ) : null)}

      {analysisStatus === "failed" && <p className="nr-subtitle nr-section">AI nutrition analysis is unavailable right now. Extracted label information is shown above.</p>}
      {facts && <details className="nr-raw"><summary>View extracted nutrition label text</summary><pre>{facts}</pre></details>}
      <p className="nr-note">AI-extracted label values may contain errors. Verify serving size, nutrients and allergens against the original package. General information only, not medical advice.</p>
    </article>
  );
}

export default NutritionResult;
