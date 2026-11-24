
import { useEffect, useRef, useState } from "react";
import "./App.css";
import NutritionResult, { AnalysisSections, WebNutritionResult, formatProductTitle } from "./NutritionResult";

function safeWebUrl(value) { try { const url = new URL(value); return url.protocol === "https:" ? url.href : undefined; } catch { return undefined; } }

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fileInputRef = useRef(null);
  const bottomRef = useRef(null);
  const nextId = useRef(0);
  const busyRef = useRef(false);
  const selectedProductRef = useRef(null);

  function createMessage(role, type, data = {}) {
    nextId.current += 1;
    return {
      id: nextId.current,
      role,
      type,
      ...data,
    };
  }

  function addMessage(newMessage) {
    setMessages((previous) => [...previous, newMessage]);
  }

  // Automatically scroll to the latest conversation content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, loading]);

  function handleImageChange(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select an image file.");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("Image must be smaller than 5 MB.");
      return;
    }

    setError("");
    setImage(file);

    const reader = new FileReader();

    reader.onload = () => {
      setImagePreview(reader.result);
    };

    reader.readAsDataURL(file);
  }

  function removeImage() {
    setImage(null);
    setImagePreview("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  // Recent text turns are sent as bounded context; no server-side chat history is stored.
  function recentConversation() {
    return messages
      .filter((item) => item.type === "text" && typeof item.content === "string")
      .slice(-8)
      .map((item) => ({ role: item.role, content: item.content.slice(0, 600) }));
  }

  async function routeChatMessage(text, history) {
    const response = await fetch(`${API_URL}/chat/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        has_confirmed_product: Boolean(selectedProductRef.current),
        conversation_history: history,
      }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "Unable to classify this message.");
    }
    const data = await response.json();
    return data.intent;
  }

  async function askNutritionQuestion(question, history) {
    const response = await fetch(`${API_URL}/nutrition/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        product_context: selectedProductRef.current,
        conversation_history: history,
      }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(typeof body.detail === "string" ? body.detail : `Nutrition Q&A failed: HTTP ${response.status}`);
    }
    const data = await response.json();
    addMessage(createMessage("assistant", "text", {
      content: data.answer || "I couldn't generate an answer. Please try rephrasing your question.",
    }));
  }

  async function handleSend(event) {
    event.preventDefault();

    if (busyRef.current) return;

    const query = message.trim();

    if (!query && !image) return;

    setError("");

    // Handle image analysis or catalog search.
    
    if (image) {
      const submittedImage = image;
      const submittedCaption = query;
      const submittedImageUrl = URL.createObjectURL(submittedImage);

      // Move the attachment into the conversation immediately, before awaiting the API.
      addMessage(createMessage("user", "image", {
        content: submittedCaption,
        imageUrl: submittedImageUrl,
        filename: submittedImage.name,
      }));
      setMessage("");
      removeImage();
      busyRef.current = true;
      setLoading(true);

      try {
        await uploadImage(submittedImage);
      } catch (err) {
        addMessage(createMessage("assistant", "text", {
          content: "Image processing failed. Please try uploading the image again.",
        }));
        setError(err.message);
      } finally {
        busyRef.current = false;
        setLoading(false);
      }

      return;
    }


    if (query.length < 2) {
      setError("Please enter a valid product name or question.");
      return;
    }

    busyRef.current = true;
    setLoading(true);
    setMessage("");

    addMessage(
      createMessage("user", "text", {
        content: query,
      })
    );

    try {
      const history = recentConversation();
      const intent = await routeChatMessage(query, history);
      if (intent === "product_search") {
        await searchCatalog(query);
      } else if (intent === "nutrition_question") {
        await askNutritionQuestion(query, history);
      } else if (intent === "out_of_scope") {
        addMessage(createMessage("assistant", "text", {
          content: "I'm NutriLens AI, your food and nutrition assistant. I can help with ingredients, additives, nutrition values, allergens, and packaged-food products. Please ask a food-related question.",
        }));
      } else {
        throw new Error("Unexpected chat routing response.");
      }
    } catch (err) {
      addMessage(
        createMessage("assistant", "text", {
          content: "Sorry, I couldn't complete that request.",
        })
      );
      setError(err.message);
    } finally {
      busyRef.current = false;
      setLoading(false);
    }
  }

  async function searchCatalog(query, origin = "text") {
    const response = await fetch(`${API_URL}/products/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_name: query }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = typeof body.detail === "string" ? body.detail : "";
      throw new Error(response.status === 502 || response.status === 503
        ? "Product catalog is temporarily unavailable. Please try again later or provide a barcode."
        : detail || `Product search failed: HTTP ${response.status}`);
    }
    const data = await response.json();
    const products = Array.isArray(data.products) ? data.products : [];
    const web = data.web_discovery || {};
    const candidates = Array.isArray(web.candidates) ? web.candidates.filter(p => p?.match_status === "potential_match" && p.source_url) : [];
    if (!products.length && candidates.length) {
      addMessage(createMessage("assistant", "web_products", {
        content: data.catalog_status === "unavailable" ? "Catalog temporarily unavailable. Potential website matches found." : "No catalog match found. Potential website matches found.",
        products: candidates, selectedIndex: null, confirmed: false, rejected: false, query,
      }));
      return "web";
    }
    if (products.length === 0) {
      addMessage(createMessage("assistant", "text", {
        content: `${data.catalog_status === "unavailable" ? "Catalog temporarily unavailable." : "No catalog matches were found."} ${web.validation_status === "unavailable" || web.status === "unavailable" ? "Website lookup was unavailable." : "No usable website product match was found."} Try a more specific name, brand, or barcode photo. No nutrition data has been assumed.`,
      }));
    } else {
      addMessage(createMessage("assistant", "product_list", {
        content: `Found ${products.length} possible catalog matches. Check the brand and variant carefully, then select the exact product.`,
        products,
        selectedBarcode: "",
        confirmed: false,
        origin,
      }));
    }
    return products.length ? "catalog" : "none";
  }

  function chooseDetectedProduct(messageId, index) {
    setMessages((previous) => previous.map((entry) => {
      if (entry.id !== messageId || entry.type !== "detected_products" || entry.confirmed) return entry;
      return { ...entry, selectedIndex: index };
    }));
  }

  function continueWithDetectedProduct(messageId) {
    const item = messages.find((entry) => entry.id === messageId);
    if (!item || item.type !== "detected_products" || item.confirmed) return;
    const product = item.products?.[item.selectedIndex];
    if (!product) return;
    setMessages((previous) => previous.map((entry) =>
      entry.id === messageId ? { ...entry, confirmed: true } : entry
    ));
    addMessage(createMessage("assistant", "package_review", {
      product,
      confirmed: false,
      rejected: false,
      multipleProducts: false,
    }));
  }

  async function verifyExtractedProduct(messageId) {
    if (busyRef.current) return;
    const item = messages.find((entry) => entry.id === messageId);
    if (!item || item.type !== "package_review" || item.confirmed || item.rejected) return;
    const product = item.product || {};
    const barcode = String(product.barcode || "").trim();
    const query = [product.brand, product.product_name, product.variant]
      .filter((value) => typeof value === "string" && value.trim())
      .join(" ").trim();

    busyRef.current = true;
    setLoading(true);
    setError("");
    try {
    // Prefer exact-barcode lookup; do not treat an extracted barcode as verified.
    if (/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(barcode)) {
      try {
        const response = await fetch(`${API_URL}/products/${encodeURIComponent(barcode)}`);
        if (response.ok) {
          const data = await response.json();
          const catalogProduct = data.product || {};
          // Barcode found: show the catalog identity and require explicit user confirmation.
          addMessage(createMessage("assistant", "product_list", {
            content: `Barcode ${barcode} was found in the catalog. Check that the product name, brand, and variant match your package before confirming.`,
            products: [{
              code: barcode,
              product_name: catalogProduct.product_name || "Unknown product",
              brands: catalogProduct.brands || "Brand unavailable",
              image_front_small_url: catalogProduct.image_url || "",
            }],
            selectedBarcode: "",
            confirmed: false,
            origin: "image",
          }));
          setMessages((previous) => previous.map((entry) =>
            entry.id === messageId ? { ...entry, confirmed: true } : entry
          ));
          return;
        }
        if (response.status !== 404) {
          throw new Error(`Catalog barcode lookup failed (HTTP ${response.status})`);
        }
        if (query) addMessage(createMessage("assistant", "text", { content: "Barcode not found in the catalog. Searching by product name." }));
      } catch (err) {
        // A temporary service failure must not be presented as "barcode not found".
        if (!query) throw err;
        addMessage(createMessage("assistant", "text", {
          content: "Barcode verification is temporarily unavailable. Searching by product name instead.",
        }));
      }
    }

    if (!query) {
      setError("No readable product name was found. Please upload a clearer photo.");
      return;
    }
      const outcome = await searchCatalog(query, "image");
      setMessages((previous) => previous.map((entry) =>
        entry.id === messageId ? { ...entry, confirmed: true, searchOutcome: outcome } : entry
      ));
    } catch (err) {
      setError(err.message);
      addMessage(createMessage("assistant", "text", {
        content: "The catalog search failed. Your extracted label details remain unverified; please try again later.",
      }));
    } finally {
      busyRef.current = false;
      setLoading(false);
    }
  }

  function rejectImageIdentity(messageId) {
    setMessages((previous) => previous.map((entry) =>
      entry.id === messageId && !entry.confirmed ? { ...entry, rejected: true } : entry
    ));
    addMessage(createMessage("assistant", "text", {
      content: "Please upload a clearer photo showing one product, or enter the exact product name and brand in the chat.",
    }));
  }

  function selectProduct(messageId, barcode) {
    setMessages((previous) =>
      previous.map((item) =>
        item.id === messageId && !item.confirmed
          ? { ...item, selectedBarcode: barcode }
          : item
      )
    );
  }

  async function confirmProduct(messageId, barcode) {
    if (!barcode || busyRef.current) return;

    busyRef.current = true;
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/products/${encodeURIComponent(barcode)}`
      );

      if (!response.ok) {
        throw new Error(
          `Unable to retrieve product: HTTP ${response.status}`
        );
      }

      const data = await response.json();
      const product = data.product;

      // Run verified, barcode-specific GPT analysis after product lookup.
      // If the analysis service fails, still show the product information.
      let nutritionAnalysis = null;
      let analysisError = "";
      try {
        const analysisResponse = await fetch(
          `${API_URL}/nutrition/analyze/${encodeURIComponent(barcode)}`
        );
        if (!analysisResponse.ok) {
          const details = await analysisResponse.json().catch(() => ({}));
          throw new Error(
            typeof details.detail === "string"
              ? details.detail
              : `HTTP ${analysisResponse.status}`
          );
        }
        const analysisData = await analysisResponse.json();
        if (analysisData.status === "success" && analysisData.analysis) {
          nutritionAnalysis = analysisData.analysis;
        } else {
          analysisError = "Verified AI nutrition analysis is unavailable for this product.";
        }
      } catch (analysisException) {
        analysisError = `AI nutrition analysis unavailable: ${analysisException.message}`;
      }

      // Only confirmed catalog product data is passed as optional Q&A context.
      // A new product selection replaces the prior context.
      selectedProductRef.current = {
        product_name: product.product_name || null,
        brand: product.brands || null,
        barcode: product.barcode || barcode,
        ingredients_text: product.ingredients_text || null,
        nutrition_per_100g: product.nutrition_per_100g || null,
        verification_note: "Product details retrieved by barcode from the catalog; individual nutrition values may be incomplete or unverified.",
      };

      // Lock only this product selection.
      setMessages((previous) =>
        previous.map((item) =>
          item.id === messageId
            ? { ...item, confirmed: true }
            : item
        )
      );

      addMessage(
        createMessage("user", "product_confirmation", {
          content: `Confirmed: ${
            product.product_name || "Product"
          } — ${product.brands || "Unknown brand"}`,
        })
      );

      addMessage(
        createMessage("assistant", "product_details", {
          content: "Here are the available product details.",
          product,
          analysis: nutritionAnalysis,
          analysisError,
        })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      busyRef.current = false;
      setLoading(false);
    }
  }

  function formatNutritionValue(value) {
    if (value === null || value === undefined || value === "") return "Not available";
    const numeric = Number(value);
    return Number.isFinite(numeric) ? Number(numeric.toFixed(3)).toString() : "Not available";
  }

  function formatNutrient(key) {
    const names = {
      energy_kcal: "Energy (kcal)",
      protein_g: "Protein (g)",
      carbohydrates_g: "Carbohydrates (g)",
      fat_g: "Total fat (g)",
      saturated_fat_g: "Saturated fat (g)",
      sugars_g: "Sugars (g)",
      salt_g: "Salt (g)",
      calcium_mg: "Calcium (mg)",
    };

    return names[key] || key.replaceAll("_", " ");
  }



  async function uploadImage(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/images/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Image upload failed: HTTP ${response.status}`
      );
    }

    const data = await response.json();

    const classification = data.classification;

    if (!classification?.is_relevant) {
      const content = classification?.category === "uncertain"
        ? "⚠️ I couldn't clearly identify this image. Please upload a clearer food package or label."
        : "This image doesn't appear to show packaged food or a food label. Please upload a food-related image.";
      addMessage(createMessage("assistant", "text", { content }));
      return;
    }

    if (data.extraction_status === "success" && data.product_info) {
      const extracted = data.product_info;
      // The new extraction format returns a separate record for each visible product.
      // Never use a combined/empty top-level identity for a multi-product image.
      const detected = Array.isArray(extracted.products)
        ? extracted.products.filter((p) => p && (p.product_name || p.brand))
        : [];
      if (detected.length > 1 || extracted.multiple_products === true) {
        if (!detected.length) {
          addMessage(createMessage("assistant", "text", {
            content: "Multiple packages were detected, but their names could not be read. Please upload a clearer photo.",
          }));
          return;
        }
        addMessage(createMessage("assistant", "detected_products", {
          products: detected,
          selectedIndex: null,
          confirmed: false,
        }));
        return;
      }
      const product = detected.length === 1 ? detected[0] : extracted;
      if (!product.product_name && !product.brand) {
        addMessage(createMessage("assistant", "text", {
          content: "I couldn't read a product name. Please upload a clearer package photo.",
        }));
        return;
      }
      addMessage(createMessage("assistant", "package_review", {
        product,
        confirmed: false,
        rejected: false,
        multipleProducts: false,
      }));
      return;
    }

    addMessage(
      createMessage("assistant", "text", {
        content: "Food-related image detected, but I couldn't extract the product details. Please try a clearer package or label photo.",
      })
    );
  }


  function chooseWebProduct(id, index) {
    setMessages(prev => prev.map(m => m.id === id && !m.confirmed && !m.rejected ? {...m, selectedIndex: index} : m));
  }
  async function confirmWebProduct(id) {
    if (busyRef.current) return;
    const item = messages.find(m => m.id === id);
    const product = item?.products?.[item.selectedIndex];
    if (!product || item.confirmed || item.rejected) return;
    selectedProductRef.current = {product_name: product.product_name, brand: product.brand,
      source_url: product.source_url, verification_status: "unverified", user_confirmed_identity: true,
      verification_note: "Website-reported information, not barcode verified. Missing data does not establish absence.",
      nutrition_per_100g: product.nutrition_per_100g, ingredients: product.ingredients,
      allergens: product.allergens, additives: product.additives,
      possible_allergens: product.possible_allergens || [],
      allergen_absence_claims: product.allergen_absence_claims || [],
      uncertain_allergen_claims: product.uncertain_allergen_claims || [],
      allergen_status: product.allergen_status || "unknown",
      ingredient_list_status: product.ingredient_list_status || "partial_or_unknown",
      nutrition_data_status: product.nutrition_data_status || (product.nutrition_per_100g?.length ? "available" : "not_found"),
      variant: product.variant, package_size: product.package_size};
    // Keep the conversational context compact; full evidence remains in the report.
    for (const key of ["ingredients", "nutrition_per_100g", "additives"]) {
      const rows = selectedProductRef.current[key];
      if (Array.isArray(rows)) selectedProductRef.current[key] = rows.map(({name, value, unit}) => ({name, value, ...(unit ? {unit} : {})}));
    }
    setMessages(prev => prev.map(m => m.id === id ? {...m, confirmed: true} : m));
    addMessage(createMessage("user", "product_confirmation", {content: `Confirmed website match: ${formatProductTitle(product)}`}));
    const report = createMessage("assistant", "web_details", {product, analysisStatus: "loading"});
    addMessage(report);
    busyRef.current = true;
    setLoading(true);
    setError("");
    const updateReport = (patch) => setMessages(prev => prev.map(m => m.id === report.id ? {...m, ...patch} : m));
    try {
      if (!product.analysis_id) throw new Error("Search again to obtain a current website analysis ID.");
      const response = await fetch(`${API_URL}/nutrition/analyze-web`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({analysis_id: product.analysis_id, user_confirmed_identity: true}),
        signal: AbortSignal.timeout(100000),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(response.status === 404 ? "Website candidate expired or unavailable. Search again." : typeof data.detail === "string" ? data.detail : "AI analysis is temporarily unavailable.");
      if (data.status !== "success" || !data.analysis) {
        updateReport({analysisStatus: "unavailable", analysisError: "Insufficient information for AI analysis. Source facts remain available."});
      } else {
        updateReport({analysisStatus: "success", analysis: data.analysis, analysisMode: data.analysis_mode});
      }
    } catch (err) {
      updateReport({analysisStatus: "failed", analysisError: err.name === "TimeoutError" ? "AI analysis timed out. Search again to retry." : err.message || "AI analysis is temporarily unavailable."});
    } finally {
      busyRef.current = false;
      setLoading(false);
    }
  }
  function rejectWebProducts(id) {
    if (busyRef.current) return;
    const item = messages.find(m => m.id === id);
    if (!item || item.confirmed || item.rejected) return;
    setMessages(prev => prev.map(m => m.id === id ? {...m, rejected: true} : m));
    setMessage(item.query || "");
    addMessage(createMessage("assistant", "text", {content: "Please edit the product name or brand in the message box and search again."}));
  }
  function renderMessage(item) {
    if (item.type === "web_details") return <WebNutritionResult product={item.product} analysis={item.analysis} analysisStatus={item.analysisStatus} analysisError={item.analysisError} analysisMode={item.analysisMode} />;
    if (item.type === "web_products") return (
      <div className="chat-result web-candidates">
        <p>{item.content}</p>
        <div className="product-list">{item.products.map((p, index) => (
          <div className={`web-candidate ${item.selectedIndex === index ? "selected" : ""}`} key={`${item.id}-${index}`}>
            <label className="web-choice"><input type="radio" name={`web-${item.id}`} checked={item.selectedIndex === index} disabled={loading || item.confirmed || item.rejected} onChange={() => chooseWebProduct(item.id,index)} />
              <div className="product-info"><strong>{p.product_name || "Unknown product"}</strong><span>{p.brand || "Brand unavailable"}</span>{p.variant && <small>{p.variant}</small>}<small>{p.package_size || p.package_size_hint || "Package size unavailable"}</small></div>
            </label>
            <div className="web-meta">
              <span>Nutrition: {p.nutrition_per_100g?.length ? "available" : "not available"}</span>
              <span>Ingredients: {p.ingredients?.length ? (p.ingredient_list_status === "declared_list_present" ? "declared list" : "partial list") : "unknown"}</span>
              <span>Allergens: {p.allergens?.length ? "declared" : "unknown"}{p.possible_allergens?.length ? " · possible presence" : ""}{p.allergen_absence_claims?.length ? " · unverified free-from claim" : ""}{p.uncertain_allergen_claims?.length ? " · uncertain claims" : ""}</span>
              <span>Additives: {p.additives?.length ? "reported" : "not established"}</span>
            </div>
            <a href={safeWebUrl(p.source_url)} target="_blank" rel="noopener noreferrer">View original source</a>
          </div>))}</div>
        {item.confirmed ? <p className="selection-complete">Product identity confirmed by user.</p> : item.rejected ? <p>Website matches rejected.</p> : <div className="web-actions"><button type="button" className="confirm-button" disabled={loading || item.selectedIndex === null} onClick={() => confirmWebProduct(item.id)}>Confirm product</button><button type="button" className="confirm-button reject-button" disabled={loading} onClick={() => rejectWebProducts(item.id)}>Incorrect product</button></div>}
        <p className="nr-note">Website data is not barcode-verified. Compare with your actual package.</p>
      </div>
    );
    if (item.type === "detected_products") {
      return (
        <div className="chat-result confirmed-card">
          <h3 style={{ marginTop: 0 }}>📦 Multiple food products detected</h3>
          <p>Choose the package you want to analyze. Each product will be checked separately.</p>
          <div className="product-list">
            {item.products.map((product, index) => (
              <label
                key={`${item.id}-${index}`}
                className={`product-card ${item.selectedIndex === index ? "selected" : ""}`}
                style={{ cursor: item.confirmed ? "default" : "pointer" }}
              >
                <input
                  type="radio"
                  name={`detected-product-${item.id}`}
                  checked={item.selectedIndex === index}
                  disabled={item.confirmed || loading}
                  onChange={() => chooseDetectedProduct(item.id, index)}
                />
                <div className="product-info">
                  <strong>{product.product_name || "Name not readable"}</strong>
                  <span>{product.brand || "Brand not visible"}</span>
                  {product.variant && <small>Variant: {product.variant}</small>}
                  <small>Barcode: {product.barcode || "Not visible"}</small>
                  <small>Identification confidence: {product.identification_confidence || "Unknown"}</small>
                </div>
              </label>
            ))}
          </div>
          {item.confirmed ? (
            <p className="selection-complete">✓ Product selected. Review its extracted details below.</p>
          ) : (
            <button
              type="button"
              className="confirm-button"
              disabled={item.selectedIndex === null || loading}
              onClick={() => continueWithDetectedProduct(item.id)}
            >
              Continue with selected product
            </button>
          )}
          <p className="nr-note">These identities were extracted from the image and are not yet catalog-verified.</p>
        </div>
      );
    }

    if (item.type === "package_review") {
      const product = item.product || {};
      const identity = [product.brand, product.product_name, product.variant]
        .filter(Boolean).join(" — ") || "Unidentified food package";
      return (
        <div className="chat-result confirmed-card">
          <div style={{ marginBottom: 12 }}>
            <strong>📦 AI-extracted package details — not verified</strong>
            <p style={{ marginTop: 6 }}>{identity}</p>
            <p>Barcode read from image: {product.barcode || "Not visible"}</p>
            <p>Identification confidence: {product.identification_confidence || "Unknown"}</p>
          </div>
          <NutritionResult product={product} analysis={null} analysisStatus="unverified" />
          {item.multipleProducts && (
            <p role="note">Multiple products may be visible. Check that these details refer to the intended package.</p>
          )}
          {item.confirmed ? (
            <p className="selection-complete">{item.searchOutcome === "none" ? "Search completed. No matching product found." : item.searchOutcome === "web" ? "Website candidates displayed below. Confirm the matching product." : "Catalog candidates displayed below. Confirm the exact match."}</p>
          ) : item.rejected ? (
            <p>Please upload a clearer photo or enter the correct product name.</p>
          ) : (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
              <button type="button" className="confirm-button" disabled={loading}
                onClick={() => verifyExtractedProduct(item.id)}>
                Verify product &amp; analyze nutrition
              </button>
              <button
              type="button"
              className="confirm-button reject-button"
              disabled={loading}
              onClick={() => rejectImageIdentity(item.id)}
             >
              Incorrect product
              </button>
            </div>
          )}
          <p className="nr-note">Image-extracted values are not verified. Catalog lookup requires a matching product and explicit confirmation.</p>
        </div>
      );
    }
    if (item.type === "nutrition_result") {
      return (
        <NutritionResult
          product={item.product}
          analysis={item.analysis}
          analysisStatus={item.analysisStatus}
        />
      );
    }

    if (item.type === "image") {
    return (
      <div className="message-bubble image-message">
        {item.imageUrl && (
          <img
            src={item.imageUrl}
            alt={item.filename || "Uploaded food image"}
            className="chat-uploaded-image"
          />
        )}

        {item.content && <p>{item.content}</p>}
      </div>
    );
  }
    if (
      item.type === "text" ||
      item.type === "product_confirmation"
    ) {
      return (
        <div className="message-bubble">
          {item.content}
        </div>
      );
    }

    if (item.type === "product_list") {
      return (
        <div className="chat-result">
          <p>{item.content}</p>

          <div className="product-list">
            {item.products.map((product) => (
              <label
                key={product.code}
                className={`product-card ${
                  item.selectedBarcode === product.code
                    ? "selected"
                    : ""
                }`}
              >
                <input
                  type="radio"
                  name={`product-${item.id}`}
                  checked={item.selectedBarcode === product.code}
                  disabled={item.confirmed || loading}
                  onChange={() =>
                    selectProduct(item.id, product.code)
                  }
                />

                {product.image_front_small_url ? (
                  <img
                    src={product.image_front_small_url}
                    alt={product.product_name || "Packaged food"}
                    className="product-image"
                    onClick={(event) => {
                      event.preventDefault();
                      window.open(
                        product.image_front_small_url,
                        "_blank",
                        "noopener,noreferrer"
                      );
                    }}
                  />
                ) : (
                  <div className="product-placeholder">📦</div>
                )}

                <div className="product-info">
                  <strong>
                    {product.product_name || "Unknown product"}
                  </strong>
                  <span>
                    {product.brands || "Brand unavailable"}
                  </span>
                  <small>Barcode: {product.code}</small>
                </div>
              </label>
            ))}
          </div>

          {item.confirmed ? (
            <p className="selection-complete">
              ✓ Product selection confirmed
            </p>
          ) : (
            <button
              type="button"
              className="confirm-button"
              disabled={!item.selectedBarcode || loading}
              onClick={() =>
                confirmProduct(item.id, item.selectedBarcode)
              }
            >
              Confirm product
            </button>
          )}
        </div>
      );
    }

    if (item.type === "product_details") {
      const product = item.product;

      return (
        <div className="chat-result confirmed-card">
          <div className="confirmed-heading">
            ✓ Product details
          </div>

          <div className="confirmed-top">
            {product.image_url && (
              <img
                src={product.image_url}
                alt={product.product_name || "Product"}
              />
            )}

            <div>
              <h3>{product.product_name || "Unknown product"}</h3>
              <p>{product.brands || "Unknown brand"}</p>
              <small>Barcode: {product.barcode}</small>
            </div>
          </div>

          <h4>🌿 Ingredients</h4>
          <p>
            {product.ingredients_text ||
              "Ingredient information is unavailable."}
          </p>

          <h4>🍊 Nutrition per 100 g</h4>

          {product.nutrition_per_100g ? (
            <table className="nutrition-table">
              <tbody>
                {Object.entries(
                  product.nutrition_per_100g
                ).map(([key, value]) => (
                  <tr key={key}>
                    <td>{formatNutrient(key)}</td>
                    <td>{formatNutritionValue(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Nutrition information is unavailable.</p>
          )}

          <AnalysisSections
            analysis={item.analysis}
            unavailableMessage={item.analysisError}
          />
        </div>
      );
    }

    return null;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">🌿</div>
          <div>
            <h1>NutriLens AI</h1>
            <span>Know your food. Choose better.</span>
          </div>
        </div>

        <span className="header-tag">Food intelligence</span>
      </header>

      <div className="app-workspace">
        <aside className="info-sidebar" aria-label="About NutriLens AI">
          <div className="sidebar-hero">
            <div className="sidebar-eyebrow">🌿 YOUR SMART FOOD COMPANION</div>
            <h2>Know what’s inside your food.</h2>
            <p>Understand packaged foods with clearer ingredients, nutrition facts, and AI-powered insights.</p>
            <div className="sidebar-hero-decoration" aria-hidden="true">🥑 🍊 🥬</div>
          </div>

          <div className="sidebar-section-title">Discover what you can do</div>
          <div className="sidebar-feature-list">
            <div className="sidebar-feature">
              <span className="sidebar-feature-icon scan" aria-hidden="true">📷</span>
              <div><h3>Identify food packages</h3><p>Upload a package photo to read visible product information.</p></div>
            </div>
            <div className="sidebar-feature">
              <span className="sidebar-feature-icon nutrition" aria-hidden="true">📊</span>
              <div><h3>Explore nutrition</h3><p>Check available calories, protein, sugars, fats, and more.</p></div>
            </div>
            <div className="sidebar-feature">
              <span className="sidebar-feature-icon insights" aria-hidden="true">✨</span>
              <div><h3>Understand food better</h3><p>Ask about ingredients, additives, allergens, and nutrition values — no product required.</p></div>
            </div>
          </div>

          <div className="sidebar-howto">
            <h3>How to use NutriLens</h3>
            <ol>
              <li><span>Search a product, upload a photo, or ask a general nutrition question.</span></li>
              <li><span>Confirm the exact product from catalog or website matches.</span></li>
              <li><span>Explore nutrition facts and AI insights.</span></li>
            </ol>
          </div>

          <div className="sidebar-tip">
            <span aria-hidden="true">💡</span>
            <p>
              <strong>Incomplete food label? No problem!</strong>
              <br />
              NutriLens AI can help even when the barcode or nutrition
              values are not visible in your uploaded image.
              It suggests possible product matches for you to review
              and select, so you can explore available nutrition details.
            </p>
          </div>

          <p className="sidebar-disclaimer">🛡️ Nutrition information is educational and depends on source availability.</p>
        </aside>
        <div className="chat-column">
      <main className="chat-area">
        {messages.length === 0 && (
          <section className="welcome">
            <div className="welcome-icons">🥑 🥕 🍎</div>
            <h2>What's inside your food?</h2>
            <p>
              Explore packaged-food ingredients, nutrition,
              and make more informed choices.
            </p>

            <div className="feature-chips">
              <span>🌿 Ingredients</span>
              <span>🍊 Nutrition</span>
              <span>✨ Food insights</span>
            </div>
          </section>
        )}

        <div className="conversation">
          {messages.map((item) => (
            <div
              key={item.id}
              className={`chat-message ${item.role}`}
            >
              {item.role === "assistant" && (
                <span className="assistant-avatar">🌿</span>
              )}

              {renderMessage(item)}
            </div>
          ))}

          {loading && !messages.some(m => m.type === "web_details" && m.analysisStatus === "loading") && (
            <div className="chat-message assistant">
              <span className="assistant-avatar">🌿</span>
              <div className="message-bubble">
                Processing...
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      <div className="composer-wrapper">
        {error && (
          <p className="error-message">{error}</p>
        )}

        <form className="composer" onSubmit={handleSend}>
          {imagePreview && (
            <div className="image-preview">
              <img
                src={imagePreview}
                alt="Attachment preview"
              />
              <button
                type="button"
                onClick={removeImage}
                aria-label="Remove attachment"
              >
                ×
              </button>
            </div>
          )}

          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Search a product or ask about ingredients, additives, allergens, or nutrition..."
            rows={2}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />

          <div className="composer-actions">
            <div className="attachment-area">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                hidden
                onChange={handleImageChange}
              />

              <button
                type="button"
                className="attach-button"
                onClick={() =>
                  fileInputRef.current?.click()
                }
                aria-label="Attach image"
                title="Attach packaging or ingredient image"
              >
                +
              </button>

              <span>Attach image</span>
            </div>

            <button
              type="submit"
              className="send-button"
              disabled={loading || (!message.trim() && !image)}
              aria-label="Send message"
            >
              ↑
            </button>
          </div>
        </form>

        <p className="composer-note">
          Product data from catalogs and website sources.
          AI-extracted information may contain errors. Check the original label.
        </p>
      </div>
        </div>
      </div>
    </div>
  );
}

export default App;
