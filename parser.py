"""Winslow Shopify parser — prefers /collections/{handle}/products.json."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Optional
from urllib.parse import urljoin

import requests

from config import cfg

logger = logging.getLogger(__name__)

BACK_KEYWORDS = ("back", "rear", "_b.", "_back", "-back", "backview", "back_view")


def _headers() -> dict[str, str]:
    return {"User-Agent": cfg.USER_AGENT, "Accept": "application/json,text/html,*/*"}


def _stable_id(product_url: str) -> str:
    digest = hashlib.sha256(f"{cfg.SOURCE}:{product_url}".encode()).hexdigest()[:24]
    return f"winslow_{digest}"


def _money(cents: Optional[int | float], currency: str = "USD") -> Optional[str]:
    if cents is None:
        return None
    try:
        amount = float(cents) / 100.0 if float(cents) >= 100 else float(cents)
    except (TypeError, ValueError):
        return None
    return f"{amount:.2f}{currency}"


def _detect_back_image(images: list[dict[str, Any]], front_src: str) -> Optional[str]:
    for img in images:
        src = img.get("src") or ""
        alt = (img.get("alt") or "").lower()
        blob = f"{src} {alt}".lower()
        if src and src != front_src and any(k in blob for k in BACK_KEYWORDS):
            return src
    return None


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return urljoin(cfg.LANDING_PAGE, url)
    return url


def _category_handle(category_url: str) -> str:
    return category_url.rstrip("/").split("/")[-1]


def fetch_collection_products(category_url: str) -> list[dict[str, Any]]:
    """Paginate Shopify products.json until an empty page."""
    handle = _category_handle(category_url)
    display = cfg.CATEGORY_DISPLAY.get(handle, handle.title())
    products: list[dict[str, Any]] = []
    page = 1

    while True:
        url = f"https://winslowla.com/collections/{handle}/products.json?limit=250&page={page}"
        time.sleep(cfg.RATE_LIMIT_DELAY)
        try:
            resp = requests.get(url, headers=_headers(), timeout=cfg.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("Failed products.json %s page=%s: %s", handle, page, e)
            break

        batch = data.get("products") or []
        if not batch:
            break

        for raw in batch:
            parsed = parse_shopify_product(raw, display)
            if parsed:
                products.append(parsed)

        if len(batch) < 250:
            break
        page += 1

    # Deduplicate by product_url
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for p in products:
        if p["product_url"] not in seen:
            seen.add(p["product_url"])
            unique.append(p)
    logger.info("Category %s: %d products", display, len(unique))
    return unique


def parse_shopify_product(raw: dict[str, Any], category: str) -> Optional[dict[str, Any]]:
    handle = raw.get("handle") or ""
    if not handle:
        return None
    product_url = f"https://winslowla.com/products/{handle}"
    title = (raw.get("title") or "").strip() or "Unknown"
    images = raw.get("images") or []
    front = ""
    if images:
        front = _normalize_url(images[0].get("src") or "")
    if not front and raw.get("image"):
        front = _normalize_url((raw.get("image") or {}).get("src") or "")
    if not front:
        logger.warning("Skip %s: no image", product_url)
        return None

    variants = raw.get("variants") or []
    prices = []
    compare_prices = []
    sizes: list[str] = []
    colors: list[str] = []
    available_any = False
    for v in variants:
        if v.get("available"):
            available_any = True
        if v.get("price") is not None:
            try:
                # products.json price is often a string dollars
                price_val = v["price"]
                if isinstance(price_val, str):
                    cents = int(round(float(price_val) * 100))
                else:
                    cents = int(price_val)
                prices.append(cents)
            except Exception:
                pass
        if v.get("compare_at_price"):
            try:
                cmp = v["compare_at_price"]
                if isinstance(cmp, str):
                    compare_prices.append(int(round(float(cmp) * 100)))
                else:
                    compare_prices.append(int(cmp))
            except Exception:
                pass
        opt1 = (v.get("option1") or "").strip()
        opt2 = (v.get("option2") or "").strip()
        if opt1 and opt1 not in sizes:
            sizes.append(opt1)
        if opt2 and opt2 not in colors:
            colors.append(opt2)

    # Prefer original (compare_at) as price when on sale
    sale_price = None
    price = None
    if compare_prices and prices and min(compare_prices) > min(prices):
        price = _money(min(compare_prices))
        sale_price = _money(min(prices))
    elif prices:
        price = _money(min(prices))

    body = raw.get("body_html") or ""
    description = re.sub(r"<[^>]+>", " ", body)
    description = re.sub(r"\s+", " ", description).strip() or None

    back_image_url = _detect_back_image(images, front)
    additional = []
    for img in images[1:]:
        src = _normalize_url(img.get("src") or "")
        if src and src != front:
            additional.append(src)
    if back_image_url and back_image_url not in additional:
        additional.append(back_image_url)
    additional_images = " , ".join(additional) if additional else None

    tags_raw = raw.get("tags") or []
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    else:
        tags = list(tags_raw)

    metadata = {
        "handle": handle,
        "vendor": raw.get("vendor"),
        "product_type": raw.get("product_type"),
        "sku": (variants[0].get("sku") if variants else None),
        "colors": colors,
        "sizes": sizes,
        "availability": available_any,
        "tags": tags,
        "scrape_source": "products.json",
    }

    return {
        "id": _stable_id(product_url),
        "source": cfg.SOURCE,
        "product_url": product_url,
        "affiliate_url": None,
        "image_url": front,
        "compressed_image_url": None,
        "back_image_url": back_image_url,
        "brand": cfg.BRAND_COLUMN,
        "title": title,
        "description": description,
        "category": category,
        "gender": None,
        "price": price,
        "sale": sale_price,
        "metadata": json.dumps(metadata, ensure_ascii=False),
        "size": ", ".join(sizes) if sizes else None,
        "second_hand": cfg.SECOND_HAND,
        "country": "US",
        "tags": tags or None,
        "additional_images": additional_images,
        "other": None,
    }


def scrape_all_categories() -> list[dict[str, Any]]:
    all_products: list[dict[str, Any]] = []
    seen: set[str] = set()
    for url in cfg.CATEGORY_URLS:
        for p in fetch_collection_products(url):
            if p["product_url"] in seen:
                # Merge categories if product appears in multiple collections
                existing = next(x for x in all_products if x["product_url"] == p["product_url"])
                cats = {c.strip() for c in (existing.get("category") or "").split(",") if c.strip()}
                cats.add(p["category"])
                existing["category"] = ", ".join(sorted(cats))
                continue
            seen.add(p["product_url"])
            all_products.append(p)
    logger.info("Total unique products: %d", len(all_products))
    return all_products
