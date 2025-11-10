thonimport logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

Selector = Tuple[str, Dict[str, Any]]

def _first_text(soup: BeautifulSoup, selectors: Iterable[Selector]) -> Optional[str]:
    for name, attrs in selectors:
        el = soup.find(name, attrs=attrs)
        if el and isinstance(el, Tag):
            text = el.get_text(strip=True)
            if text:
                return text
    return None

def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    title = _first_text(
        soup,
        [
            ("span", {"id": "productTitle"}),
            ("span", {"id": "title"}),
            ("h1", {"id": "title"}),
        ],
    )
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    return title

def _extract_brand(soup: BeautifulSoup) -> Optional[str]:
    brand = _first_text(
        soup,
        [
            ("a", {"id": "bylineInfo"}),
            ("span", {"id": "bylineInfo"}),
            ("a", {"id": "brand"}),
            ("tr", {"id": "brandRow"}),
        ],
    )
    if not brand:
        # A more generic guess based on product details table
        cell = soup.find("th", string=re.compile(r"brand", re.I))
        if cell and isinstance(cell, Tag):
            sibling = cell.find_next("td")
            if sibling:
                brand = sibling.get_text(strip=True)
    return brand

def _parse_price_string(value: str) -> Tuple[Optional[float], Optional[str]]:
    if not value:
        return None, None
    value = value.strip()
    currency = None
    match = re.search(r"([€£$¥₹])\s*([\d,.]+)", value)
    if match:
        currency = match.group(1)
        value = match.group(2)
    value = value.replace(",", "")
    try:
        num = float(value)
    except ValueError:
        num = None
    return num, currency

def _extract_price(soup: BeautifulSoup) -> Dict[str, Any]:
    price_text = _first_text(
        soup,
        [
            ("span", {"id": "priceblock_ourprice"}),
            ("span", {"id": "priceblock_dealprice"}),
            ("span", {"id": "price_inside_buybox"}),
            ("span", {"class": "a-offscreen"}),
        ],
    )
    price_value, currency = _parse_price_string(price_text or "")

    return {
        "price_raw": price_text,
        "price.value": price_value,
        "price_currency": currency,
    }

def _extract_thumbnail(soup: BeautifulSoup) -> Optional[str]:
    img = soup.find("img", {"id": "landingImage"})
    if not img:
        # Fallback – first product image thumbnail
        img = soup.find("img", {"data-a-image-name": "landingImage"})
    if not img:
        img = soup.find("img", {"class": re.compile(r"image|img", re.I)})
    if img and isinstance(img, Tag):
        for key in ("src", "data-old-hires", "data-a-hires"):
            url = img.get(key)
            if url:
                return url
    return None

def _extract_description(soup: BeautifulSoup) -> Optional[str]:
    bullets_container = soup.find("div", {"id": "feature-bullets"})
    if bullets_container:
        bullets = [
            li.get_text(strip=True)
            for li in bullets_container.find_all("span", {"class": "a-list-item"})
            if li.get_text(strip=True)
        ]
        if bullets:
            return " • ".join(bullets)

    desc = soup.find("div", {"id": "productDescription"})
    if desc:
        text = desc.get_text(" ", strip=True)
        if text:
            return text

    return None

def _extract_rating(soup: BeautifulSoup) -> Dict[str, Any]:
    rating_text = _first_text(
        soup,
        [
            ("span", {"id": "acrPopover"}),
            ("span", {"data-hook": "rating-out-of-text"}),
        ],
    )
    stars = None
    if rating_text:
        match = re.search(r"([\d.]+)\s+out of", rating_text)
        if match:
            try:
                stars = float(match.group(1))
            except ValueError:
                stars = None

    reviews_text = _first_text(
        soup,
        [
            ("span", {"id": "acrCustomerReviewText"}),
            ("span", {"data-hook": "total-review-count"}),
        ],
    )
    reviews_count = None
    if reviews_text:
        digits = re.sub(r"[^\d]", "", reviews_text)
        if digits:
            try:
                reviews_count = int(digits)
            except ValueError:
                reviews_count = None

    return {"stars": stars, "reviewsCount": reviews_count}

def _extract_breadcrumbs(soup: BeautifulSoup) -> Optional[str]:
    crumb_container = soup.find("div", {"id": "wayfinding-breadcrumbs_feature_div"})
    if not crumb_container:
        crumb_container = soup.find("ul", {"class": re.compile(r"breadcrumbs", re.I)})

    if not crumb_container:
        return None

    parts: List[str] = []
    for a in crumb_container.find_all("a"):
        text = a.get_text(strip=True)
        if text:
            parts.append(text)
    return " > ".join(parts) if parts else None

def parse_product_page(
    html: str,
    asin: Optional[str] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse a single Amazon product HTML page into a structured dictionary.

    This function is intentionally flexible so it also works with simplified
    HTML snippets for unit tests.
    """
    soup = BeautifulSoup(html, "lxml")

    product: Dict[str, Any] = {}

    product["asin"] = asin
    product["url"] = url

    product["title"] = _extract_title(soup)
    product["brand"] = _extract_brand(soup)
    product["thumbnailImage"] = _extract_thumbnail(soup)

    price_info = _extract_price(soup)
    product.update(price_info)

    rating_info = _extract_rating(soup)
    product.update(rating_info)

    product["description"] = _extract_description(soup)
    product["breadCrumbs"] = _extract_breadcrumbs(soup)

    # Clean up: If some numeric fields are None but present as keys, that's fine.
    logger.debug("Parsed product: %s", product)
    return product