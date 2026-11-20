"""Open Food Facts catalog access for NutriLens AI.

Search results are candidates, not verified product identities.
The caller must require exact-product confirmation before using nutrition data.
"""

import copy
import logging
import os
import random
import threading
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import requests

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"
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


def _get_json(url, params=None):
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
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            delay = _retry_delay(response, attempt)
            logger.warning("Open Food Facts connection issue: %s; retrying", exc)
            time.sleep(delay)


def _search_once(term):
    key = ("search", term.casefold())
    cached = _cached(key)
    if cached is not None:
        return cached

    params = {
        "search_terms": term,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5,
        "fields": "code,product_name,brands,image_front_small_url",
    }
    try:
        data = _get_json(BASE_URL, params=params)
    except (requests.RequestException, ValueError):
        stale = _cached(key, allow_stale=True)
        if stale is not None:
            logger.warning("Using previously cached catalog search for %r", term)
            return stale
        raise

    products = data.get("products", [])
    if not isinstance(products, list):
        raise ValueError("Unexpected Open Food Facts search response")
    products = [p for p in products if isinstance(p, dict) and p.get("code")]
    _remember(key, products, SEARCH_TTL_SECONDS)
    return products


def _fallback_term(term):
    """One conservative shorter search; never treats results as exact matches."""
    words = term.split()
    if len(words) < 3:
        return None
    if term.casefold().endswith(" indian mix"):
        return term[:-len(" indian mix")].strip() or None
    # Other multiword names: remove only the last descriptive word.
    return " ".join(words[:-1])


def search_food_products(product_name: str):
    term = " ".join((product_name or "").strip().split())
    if len(term) < 2:
        return []

    results = _search_once(term)
    if results:
        return results

    shorter = _fallback_term(term)
    if shorter and shorter.casefold() != term.casefold():
        logger.info("No results for %r; trying broader candidate search %r", term, shorter)
        return _search_once(shorter)
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
        data = _get_json(PRODUCT_URL.format(barcode=barcode))
    except (requests.RequestException, ValueError):
        stale = _cached(key, allow_stale=True)
        if stale is not None:
            logger.warning("Using previously cached product data for barcode %s", barcode)
            return stale
        raise

    if data.get("status") != 1:
        _remember(key, None, SEARCH_TTL_SECONDS)
        return None

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
