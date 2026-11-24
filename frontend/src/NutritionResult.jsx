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


// Reused for barcode-based GPT analysis and image-label analysis.
export function AnalysisSections({ analysis, unavailableMessage = "" }) {
  if (!analysis) {
    return unavailableMessage ? (
      <section className="nr-section" aria-live="polite">
        <h4>🤖 AI Nutrition Analysis</h4>
        <p className="nr-subtitle">{unavailableMessage}</p>
      </section>
    ) : null;
  }

  const sections = [
    { heading: "✨ Positive aspects", items: analysis.positive_aspects },
    { heading: "⚠️ Concerns", items: analysis.concerns },
    { heading: "💡 Recommendations", items: analysis.recommendations },
    { heading: "ℹ️ Limitations", items: analysis.limitations },
    // Legacy image-analysis response fields remain supported.
    { heading: "✨ Nutritional highlights", items: analysis.nutritional_highlights },
    { heading: "🌿 Ingredient insights", items: analysis.ingredients_analysis },
    { heading: "❤️ Things to consider", items: analysis.health_considerations },
  ];

  return (
    <section className="nr-section nutrition-ai-analysis" aria-label="AI nutrition analysis">
      <h4>🤖 AI Nutrition Analysis</h4>
      {typeof analysis.summary === "string" && analysis.summary && (
        <p className="nr-summary">{analysis.summary}</p>
      )}
      {sections.map(({ heading, items }) =>
        Array.isArray(items) && items.length > 0 ? (
          <div key={heading} className="nr-section">
            <h4>{heading}</h4>
            <ul className="nr-insight-list">
              {items.map((item, index) => <li key={index}>{item}</li>)}
            </ul>
          </div>
        ) : null
      )}
    </section>
  );
}

function NutritionResult({ product = {}, analysis, analysisStatus }) {
  const facts = product.nutrition_facts || "";
  const metrics = nutrientSpecs.map((spec) => ({ ...spec, value: getNutrient(facts, spec.patterns) })).filter((metric) => metric.value !== null);
  const servingMatch = facts.match(/\bper\s+(\d+(?:\.\d+)?\s*(?:gms?|grams?|ml)\b(?:\s+per\s+pcs)?)/i);
  const serving = servingMatch ? `Per ${servingMatch[1]}` : "As shown on label";
  const ingredients = (product.ingredients || "").split(/[,;&\n]+/).map((s) => s.trim()).filter(Boolean);

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

      <AnalysisSections analysis={analysis} />

      {analysisStatus === "failed" && <p className="nr-subtitle nr-section">AI nutrition analysis is unavailable right now. Extracted label information is shown above.</p>}
      {facts && <details className="nr-raw"><summary>View extracted nutrition label text</summary><pre>{facts}</pre></details>}
      <p className="nr-note">AI-extracted label values may contain errors. Verify serving size, nutrients and allergens against the original package. General information only, not medical advice.</p>
    </article>
  );
}

export default NutritionResult;


export function formatProductTitle(product = {}) {
  const brand = String(product.brand || "").trim().replace(/\s+/g, " ");
  const name = String(product.product_name || "").trim().replace(/\s+/g, " ");
  const lower = name.toLowerCase();
  const prefix = brand.toLowerCase();
  if (brand && (lower === prefix || (lower.startsWith(prefix) && /^[\s\-–—:]/.test(name.slice(brand.length))))) return name;
  return [brand, name].filter(Boolean).join(" ") || "Food product";
}

export function WebNutritionResult({ product = {}, analysis, analysisStatus, analysisError, analysisMode }) {
  const list = (value) => Array.isArray(value) ? value.filter(Boolean) : [];
  const rows = list(product.nutrition_per_100g);
  const groups = [
    { heading: "Ingredients", facts: list(product.ingredients), tone: "ingredient" },
    { heading: "Additives", facts: list(product.additives), tone: "additive" },
  ];
  const allergenGroups = [
    { heading: "Declared presence", facts: list(product.allergens), tone: "allergen" },
    { heading: "Possible presence", facts: list(product.possible_allergens), tone: "possible" },
    { heading: "Website free-from claims (unverified)", facts: list(product.allergen_absence_claims), tone: "absence" },
    { heading: "Uncertain claims", facts: list(product.uncertain_allergen_claims), tone: "absence" },
  ];
  const specs = [
    ["Calories", /^(energy|calories)$/i], ["Protein", /^protein$/i],
    ["Total fat", /^(total fat|fat)$/i], ["Sugars", /^(total sugars|sugars|sugar)$/i],
    ["Fibre", /^(dietary )?fib(re|er)$/i], ["Sodium", /^sodium$/i],
  ];
  const metrics = specs.map(([label, pattern]) => ({ label, row: rows.find(r => pattern.test(r.name)) })).filter(m => m.row);
  const source = (() => { try { const u = new URL(product.source_url); return u.protocol === "https:" ? u.href : undefined; } catch { return undefined; } })();
  const evidence = [...rows, ...groups.flatMap(g => g.facts), ...allergenGroups.flatMap(g => g.facts)].filter(f => f.evidence);
  return (
    <article className="nutrition-result web-result web-compact">
      <div className="nr-eyebrow">Website-reported • Not barcode verified</div>
      <h3>{formatProductTitle(product)}</h3>
      <p className="nr-subtitle">{product.package_size || product.package_size_hint || "Package size unavailable"}</p>
      <section className="nr-section">
        <h4>Nutrition snapshot {rows.length > 0 && <span className="nr-serving">Per 100 g</span>}</h4>
        {metrics.length > 0 && <div className="web-metrics">{metrics.map(({label,row}) => (
          <div className="web-metric" key={label}><span>{label}</span><strong>{row.value} <small>{row.unit}</small></strong></div>
        ))}</div>}
        {rows.length > 0 ? <details className="web-details" open={metrics.length === 0 ? true : undefined}>
          <summary>View complete nutrition table ({rows.length})</summary>
          <table className="nutrition-table"><tbody>{rows.map((r,i) => <tr key={i}><td>{r.name}</td><td>{r.value} {r.unit}</td></tr>)}</tbody></table>
        </details> : <p className="nr-subtitle">Numerical nutrition values are unavailable from this source.</p>}
      </section>
      {groups.map(({heading,facts,tone}) => <section className="nr-section" key={heading}>
        <h4>{heading}</h4>
        {tone === "ingredient" && <p className="nr-subtitle web-classification">{product.ingredient_list_status === "declared_list_present" ? "Website-declared ingredient list (not independently verified)." : "Partial or unknown ingredient list."}</p>}
        {facts.length ? <div className="web-chips">{facts.map((f,i) => <span key={i} className={`web-chip ${tone}`}>{f.name}{f.value && f.value !== f.name ? ` · ${f.value}` : ""}</span>)}</div> : <p className="nr-subtitle">{tone === "additive" ? "No supported additive declarations found; absence is not established." : "Ingredient information unavailable."}</p>}
      </section>)}
      <section className="nr-section">
        <h4>Allergen information</h4>
        <p className="nr-subtitle">{product.allergen_status === "unknown" || !product.allergen_status ? "Allergen status: Unknown" : "Website-reported allergen information (unverified)"}</p>
        {allergenGroups.filter(g => g.facts.length).map(({heading,facts,tone}) => <div className="web-allergen-group" key={heading}>
          <h5>{heading}</h5>
          <div className="web-chips">{facts.map((f,i) => <span key={i} className={`web-chip ${tone}`}>{f.name}</span>)}</div>
        </div>)}
        <p className="nr-subtitle web-classification">Missing declarations and free-from claims do not establish allergy safety. Check the original package.</p>
      </section>
      {evidence.length > 0 && <details className="web-details"><summary>View source evidence ({evidence.length} facts)</summary>
        <dl className="web-evidence-list">{evidence.map((f,i) => <React.Fragment key={i}><dt>{f.name}</dt><dd>{f.evidence}{f.basis_evidence && ` — ${f.basis_evidence}`}</dd></React.Fragment>)}</dl>
      </details>}
      {source && <p className="web-source-link"><a href={source} target="_blank" rel="noopener noreferrer">View original product source</a></p>}
      <div className="web-ai-report" aria-live="polite" aria-busy={analysisStatus === "loading"}>
        {analysisStatus === "loading" ? <section className="nr-section"><h4>🤖 AI Nutrition Analysis</h4><p className="web-analysis-loading"><span className="web-spinner" aria-hidden="true" /> Analyzing available website information…</p></section> : analysis ? <>
          <p className="nr-subtitle web-analysis-mode">{({ingredient_based: "Ingredient-based analysis", nutrition_based: "Nutrition-based analysis", combined: "Nutrition and ingredient analysis", limited: "Limited analysis"})[analysisMode] || "Website-based analysis"} · Unverified source</p>
          <AnalysisSections analysis={analysis} />
        </> : <AnalysisSections unavailableMessage={analysisError || "AI nutrition analysis unavailable. Source facts remain available."} />}
      </div>
      <p className="nr-note">Product identity confirmed by you; website data is not independently verified. Check the actual package, especially allergens. General information only, not medical advice.</p>
    </article>
  );
}
