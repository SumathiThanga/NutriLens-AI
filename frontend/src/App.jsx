
import { useEffect, useRef, useState } from "react";
import "./App.css";
import NutritionResult, { AnalysisSections } from "./NutritionResult";

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

  async function handleSend(event) {
    event.preventDefault();

    if (busyRef.current) return;

    const query = message.trim();

    if (!query && !image) return;

    setError("");

    // Handle image analysis or catalog search.
    
    if (image) {
      busyRef.current = true;
      setLoading(true);

      try {
        await uploadImage(image, query);
        setMessage("");
        removeImage();
      } catch (err) {
        setError(err.message);
      } finally {
        busyRef.current = false;
        setLoading(false);
      }

      return;
    }


    if (query.length < 2) {
      setError("Please enter a valid product name.");
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
      await searchCatalog(query);
    } catch (err) {
      addMessage(
        createMessage("assistant", "text", {
          content: "Sorry, I couldn't complete the product search.",
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
    if (products.length === 0) {
      addMessage(createMessage("assistant", "text", {
        content: "No catalog matches were found. Please try a more specific name, provide the brand, or upload a barcode photo. No nutrition data has been assumed.",
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
  }

  async function confirmImageIdentity(messageId) {
    if (busyRef.current) return;
    const item = messages.find((entry) => entry.id === messageId);
    if (!item || item.type !== "image_identity" || item.confirmed || item.rejected) return;
    const product = item.product || {};
    const query = [product.brand, product.product_name, product.variant]
      .filter((value) => typeof value === "string" && value.trim())
      .join(" ").trim();
    if (!query) {
      setError("No readable product name was found. Please upload a clearer photo.");
      return;
    }
    busyRef.current = true;
    setLoading(true);
    setError("");
    setMessages((previous) => previous.map((entry) =>
      entry.id === messageId ? { ...entry, confirmed: true } : entry
    ));
    addMessage(createMessage("user", "text", { content: `Search for: ${query}` }));
    try {
      await searchCatalog(query, "image");
    } catch (err) {
      addMessage(createMessage("assistant", "text", {
        content: "Product identification was confirmed, but catalog search failed. No product was matched automatically.",
      }));
      setError(err.message);
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



  async function uploadImage(file, caption) {
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

    // Display uploaded image inside chat
    addMessage(
      createMessage("user", "image", {
        content: caption,
        imageUrl: URL.createObjectURL(file),
        filename: file.name,
      })
    );

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
      const hasIdentity = Boolean(extracted.product_name || extracted.brand);
      if (hasIdentity) {
        addMessage(createMessage("assistant", "image_identity", {
          product: extracted,
          confirmed: false,
          rejected: false,
          multipleProducts: /multiple|several/i.test(classification?.reason || ""),
        }));
      } else {
        addMessage(createMessage("assistant", "text", {
          content: "The food package was detected, but its product name could not be read. Please upload a clearer image.",
        }));
      }
      // Label extraction can be displayed, but do not treat front-of-package
      // identification or the image LLM response as verified nutrition data.
      if (extracted.nutrition_facts || extracted.ingredients) {
        addMessage(createMessage("assistant", "nutrition_result", {
          product: extracted,
          analysis: null,
          analysisStatus: "unverified",
        }));
      }
      return;
    }

    addMessage(
      createMessage("assistant", "text", {
        content: "Food-related image detected, but I couldn't extract the product details. Please try a clearer package or label photo.",
      })
    );
  }


  function renderMessage(item) {
    if (item.type === "image_identity") {
      const product = item.product || {};
      const identity = [product.product_name, product.variant].filter(Boolean).join(" — ") || "Unidentified food product";
      return (
        <div className="chat-result confirmed-card">
          <h3>Is this the product you want to analyze?</h3>
          <p><strong>{identity}</strong></p>
          <p>Brand: {product.brand || "Unknown"}</p>
          <p>Barcode: {product.barcode || "Not visible"}</p>
          <p>Identification confidence: {product.identification_confidence || "Unknown"}</p>
          {item.multipleProducts && (
            <p role="note">This photo appears to contain multiple products. Confirm only if this is the intended one.</p>
          )}
          {item.confirmed ? (
            <p className="selection-complete">✓ Identification confirmed. Review catalog candidates below.</p>
          ) : item.rejected ? (
            <p>Identification rejected. Upload another photo or enter a product name.</p>
          ) : (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              <button type="button" className="confirm-button" disabled={loading}
                onClick={() => confirmImageIdentity(item.id)}>
                Yes, search for this product
              </button>
              <button type="button" disabled={loading}
                onClick={() => rejectImageIdentity(item.id)}>
                No, identify another product
              </button>
            </div>
          )}
          <p className="nr-note">Identification is not verification. Select an exact catalog match before using its nutrition data.</p>
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
                    <td>{value ?? "Not available"}</td>
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

          {loading && (
            <div className="chat-message assistant">
              <span className="assistant-avatar">🌿</span>
              <div className="message-bubble">
                Searching...
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
            placeholder="Ask about a packaged food..."
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
          Product data from Open Food Facts.
          AI-extracted information may contain errors. Check the original label.
        </p>
      </div>
    </div>
  );
}

export default App;
