"""Open Food Facts catalog access for NutriLens AI.

Search results are candidates, not verified product identities.
The caller must require exact-product confirmation before using nutrition data.
"""

import copy
import logging
import os
import random
import re
import unicodedata
import threading
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import requests

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"
SEARCH_V2_URL = "https://world.openfoodfacts.org/api/v2/search"
PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

# Set OFF_CONTACT_EMAIL in your backend environment for a real contact address.
CONTACT_EMAIL = os.getenv("OFF_CONTACT_EMAIL", "").strip()
USER_AGENT = (
    f"NutriLensAI/0.1 ({CONTACT_EMAIL})"
    if CONTACT_EMAIL
    else "NutriLensAI/0.1 (local-development; contact-not-configured)"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}

SEARCH_TTL_SECONDS = 15 * 60
PRODUCT_TTL_SECONDS = 60 * 60
MAX_CACHE_ITEMS = 300
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3

logger = logging.getLogger(__name__)
_cache = {}
_cache_lock = threading.Lock()


def _cached(key, allow_stale=False):
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        expiry, value = entry
        if not allow_stale and time.monotonic() >= expiry:
            return None
        return copy.deepcopy(value)


def _remember(key, value, ttl):
    with _cache_lock:
        if len(_cache) >= MAX_CACHE_ITEMS:
            # Evict the oldest-expiring entry to bound memory use.
            oldest = min(_cache, key=lambda item: _cache[item][0])
            del _cache[oldest]
        _cache[key] = (time.monotonic() + ttl, copy.deepcopy(value))


def _retry_delay(response, attempt):
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 60.0)
        except ValueError:
            try:
                deadline = parsedate_to_datetime(retry_after)
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                return min(max((deadline - datetime.now(timezone.utc)).total_seconds(), 0), 60)
            except (TypeError, ValueError, OverflowError):
                pass
    return min(2 ** attempt + random.uniform(0, 0.4), 8.0)


def _get_json(url, params=None, allow_product_not_found=False):
    for attempt in range(MAX_ATTEMPTS):
        response = None
        try:
            response = requests.get(
                url, params=params, headers=HEADERS, timeout=(5, 15)
            )
            if response.status_code in RETRYABLE_STATUSES and attempt < MAX_ATTEMPTS - 1:
                delay = _retry_delay(response, attempt)
                logger.warning(
                    "Open Food Facts returned HTTP %s; retrying in %.1fs",
                    response.status_code, delay,
                )
                time.sleep(delay)
                continue
            if allow_product_not_found and response.status_code == 404:
                data = response.json()
                if isinstance(data, dict) and data.get("status") == 0:
                    return data
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            delay = _retry_delay(response, attempt)
            logger.warning("Open Food Facts connection issue: %s; retrying", exc)
            time.sleep(delay)


def _search_once(term):
    """Search OFF with endpoint failover; only cache successful responses."""
    key = ("search", term.casefold())
    cached = _cached(key)
    if cached is not None:
        return cached

    common_fields = "code,product_name,brands,image_front_small_url"
    endpoints = [
        (BASE_URL, {
            "search_terms": term,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
            "fields": common_fields,
        }),
        (SEARCH_V2_URL, {
            "search_terms": term,
            "page_size": 10,
            "fields": common_fields,
        }),
    ]
    last_error = None
    for url, params in endpoints:
        try:
            data = _get_json(url, params=params)
            products = data.get("products", [])
            if not isinstance(products, list):
                raise ValueError("Unexpected Open Food Facts search response")
            products = [p for p in products if isinstance(p, dict) and p.get("code")]
            _remember(key, products, SEARCH_TTL_SECONDS)
            return products
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logger.warning("Open Food Facts search endpoint failed for %r (%s): %s", term, url, exc)

    stale = _cached(key, allow_stale=True)
    if stale is not None:
        logger.warning("Using previously cached catalog search for %r", term)
        return stale
    if last_error is not None:
        raise last_error
    return []


def _fallback_terms(term):
    """Broaden search cautiously; results always require exact product confirmation."""
    words = term.split()
    candidates = []
    if term.casefold().endswith(" indian mix"):
        candidates.append(term[:-len(" indian mix")].strip())
    if len(words) >= 3:
        candidates.append(" ".join(words[:-1]))
    elif len(words) == 2:
        # A brand-only search may be less specific but can help when the
        # exact brand + product search is unavailable or yields no results.
        candidates.append(words[0])
        candidates.append(words[1])
    seen = {term.casefold()}
    result = []
    for candidate in candidates:
        candidate = candidate.strip()
        if len(candidate) >= 2 and candidate.casefold() not in seen:
            seen.add(candidate.casefold())
            result.append(candidate)
    return result


# Generic packaging descriptors are not enough to establish a match.
_GENERIC_WORDS = {
    "indian", "mix", "mixture", "food", "foods", "product", "products",
    "pack", "packet", "pouch", "fresh", "original", "classic", "new",
    "high", "protein", "low", "fat", "g", "gm", "grams", "kg", "ml", "l",
}


def _name_tokens(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"([a-z])([A-Z])", r"\1 \2", normalized)
    return [token for token in re.findall(r"[a-z0-9]+", normalized.casefold())
            if len(token) > 1 and not token.isdigit()]


def _match_score(query, product):
    """Conservative lexical filter; never asserts that a candidate is verified."""
    requested = [t for t in _name_tokens(query) if t not in _GENERIC_WORDS]
    if not requested:
        return 0.0

    name = _name_tokens(product.get("product_name"))
    brand = _name_tokens(product.get("brands"))
    # Handle 'milkymist' vs 'milky mist', without accepting arbitrary substrings.
    joined_name = set(name + brand)
    joined_name.update(a + b for a, b in zip(name, name[1:]))
    joined_name.update(a + b for a, b in zip(brand, brand[1:]))
    matched = sum(1 for t in requested if t in joined_name)
    if not matched:
        return 0.0

    # A single generic-looking word must not qualify a multiword query.
    if len(requested) >= 2 and matched < 2:
        return 0.0
    if len(requested) >= 3 and matched / len(requested) < 0.60:
        return 0.0

    # Prefer exact product-name matches; brand-only hits cannot qualify.
    name_joined = set(name)
    name_joined.update(a + b for a, b in zip(name, name[1:]))
    name_matches = sum(t in name_joined for t in requested)
    if name_matches == 0:
        return 0.0

    return (matched / len(requested)) + 0.1 * (name_matches / len(requested))


def _relevant_candidates(query, products):
    ranked = []
    seen = set()
    for product in products:
        score = _match_score(query, product)
        barcode = str(product.get("code", ""))
        if score > 0 and barcode and barcode not in seen:
            ranked.append((score, product))
            seen.add(barcode)
    ranked.sort(key=lambda entry: entry[0], reverse=True)
    return [product for _, product in ranked]


def search_food_products(product_name: str):
    term = " ".join((product_name or "").strip().split())
    if len(term) < 2:
        return []

    had_successful_search = False
    last_error = None
    for candidate in [term, *_fallback_terms(term)]:
        try:
            products = _search_once(candidate)
            had_successful_search = True
            relevant = _relevant_candidates(term, products)
            if relevant:
                if candidate != term:
                    logger.info("Using filtered broader results for %r from %r", term, candidate)
                return relevant
            if products:
                logger.info("Discarded %d unrelated catalog candidates for %r", len(products), term)
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logger.warning("Catalog candidate search failed for %r: %s", candidate, exc)

    # Empty results from a working endpoint mean no matches; if all endpoints
    # failed, propagate the failure so the API can return 502 instead.
    if had_successful_search:
        return []
    if last_error is not None:
        if isinstance(last_error, requests.RequestException):
            raise last_error
        raise requests.RequestException("Open Food Facts returned invalid search data") from last_error
    return []


def get_product_by_barcode(barcode: str):
    barcode = str(barcode).strip()
    if not barcode.isdigit() or len(barcode) not in (8, 12, 13, 14):
        raise ValueError("Invalid product barcode")

    key = ("product", barcode)
    cached = _cached(key)
    if cached is not None:
        return cached

    try:
        data = _get_json(PRODUCT_URL.format(barcode=barcode), allow_product_not_found=True)
    except (requests.RequestException, ValueError):
        stale = _cached(key, allow_stale=True)
        if stale is not None:
            logger.warning("Using previously cached product data for barcode %s", barcode)
            return stale
        raise

    if isinstance(data, dict) and data.get("status") == 0:
        return None
    if not isinstance(data, dict) or data.get("status") != 1:
        raise requests.RequestException("Unexpected product lookup response")

    product = data.get("product") or {}
    # Do not silently accept a different barcode's data.
    if str(product.get("code", "")) != barcode:
        logger.warning("Barcode mismatch for requested product %s", barcode)
        return None

    nutriments = product.get("nutriments") or {}
    calcium = nutriments.get("calcium_100g")
    nutrition = {
        "energy_kcal": nutriments.get("energy-kcal_100g"),
        "protein_g": nutriments.get("proteins_100g"),
        "carbohydrates_g": nutriments.get("carbohydrates_100g"),
        "fat_g": nutriments.get("fat_100g"),
        "saturated_fat_g": nutriments.get("saturated-fat_100g"),
        "sugars_g": nutriments.get("sugars_100g"),
        "salt_g": nutriments.get("salt_100g"),
        "calcium_mg": round(calcium * 1000, 2) if isinstance(calcium, (int, float)) else None,
    }
    result = {
        "barcode": product.get("code"),
        "product_name": product.get("product_name"),
        "brands": product.get("brands"),
        "ingredients_text": product.get("ingredients_text"),
        "nutrition_per_100g": nutrition,
        "image_url": product.get("image_front_url"),
    }
    _remember(key, result, PRODUCT_TTL_SECONDS)
    return result
