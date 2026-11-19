
import { useEffect, useRef, useState } from "react";
import "./App.css";
import NutritionResult from "./NutritionResult";

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
      const response = await fetch(`${API_URL}/products/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          product_name: query,
        }),
      });

      if (!response.ok) {
        throw new Error(`Product search failed: HTTP ${response.status}`);
      }

      const data = await response.json();
      const products = data.products || [];

      if (products.length === 0) {
        addMessage(
          createMessage("assistant", "text", {
            content:
              "I couldn't find matching products in the catalog. Try another product name.",
          })
        );
      } else {
        addMessage(
          createMessage("assistant", "product_list", {
            content: `I found ${products.length} matching products. Please select the correct one.`,
            products,
            selectedBarcode: "",
            confirmed: false,
          })
        );
      }
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
      addMessage(
        createMessage("assistant", "nutrition_result", {
          product: data.product_info,
          analysis: data.analysis_status === "success" ? data.nutrition_analysis : null,
          analysisStatus: data.analysis_status,
        })
      );
      return;
    }

    addMessage(
      createMessage("assistant", "text", {
        content: "Food-related image detected, but I couldn't extract the product details. Please try a clearer package or label photo.",
      })
    );
  }


  function renderMessage(item) {
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
