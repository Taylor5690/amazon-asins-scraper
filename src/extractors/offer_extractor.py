thonimport logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

def _parse_single_offer(offer_tag: Tag) -> Dict[str, Any]:
    price = None
    seller = None
    condition = None

    price_span = offer_tag.find("span", {"class": "a-color-price"})
    if price_span:
        price_text = price_span.get_text(strip=True)
        price = price_text

    seller_span = offer_tag.find("span", {"class": "a-size-small"})
    if seller_span:
        seller = seller_span.get_text(strip=True)

    condition_span = offer_tag.find("span", {"class": "offer-condition"})
    if condition_span:
        condition = condition_span.get_text(strip=True)

    offer: Dict[str, Any] = {
        "price_raw": price,
        "seller": seller,
        "condition": condition,
    }
    return offer

def parse_offers(html: str) -> List[Dict[str, Any]]:
    """
    Parse offers from a product or offers-listing HTML page.

    The function is liberal in what it accepts so that it works with both
    real Amazon pages and synthetic HTML used in unit tests.
    """
    soup = BeautifulSoup(html, "lxml")

    offers: List[Dict[str, Any]] = []

    # Common container for offers
    offer_divs: List[Tag] = []

    # Custom "offer" class used in tests or simplified pages
    offer_divs.extend(soup.find_all("div", {"class": "offer"}))

    # Amazon offers listing examples:
    offer_divs.extend(soup.find_all("div", {"class": "olpOffer"}))

    seen_ids = set()
    for tag in offer_divs:
        key = id(tag)
        if key in seen_ids:
            continue
        seen_ids.add(key)

        try:
            offer = _parse_single_offer(tag)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to parse offer: %s", exc)
            continue

        # Filter out empty offers (no price and seller)
        if any(offer.values()):
            offers.append(offer)

    logger.debug("Parsed %d offers", len(offers))
    return offers