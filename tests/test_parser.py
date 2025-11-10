thonfrom pathlib import Path
import sys

import pytest

# Ensure src is on sys.path so imports work when running tests from repo root
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from extractors.amazon_parser import parse_product_page  # noqa: E402
from extractors.offer_extractor import parse_offers      # noqa: E402

SAMPLE_HTML = """
<html>
  <head>
    <title>Sample Product Page</title>
  </head>
  <body>
    <span id="productTitle">Amazing Widget 3000</span>
    <a id="bylineInfo">Widget Corp</a>

    <div id="imgTagWrapperId">
      <img id="landingImage" src="https://example.com/image.jpg" />
    </div>

    <span id="priceblock_ourprice">$19.99</span>

    <div id="feature-bullets">
      <ul>
        <li><span class="a-list-item">Fast and reliable</span></li>
        <li><span class="a-list-item">Two-year warranty</span></li>
      </ul>
    </div>

    <div id="averageCustomerReviews">
      <span id="acrPopover">
        <span>4.5 out of 5 stars</span>
      </span>
      <span id="acrCustomerReviewText">1,234 ratings</span>
    </div>

    <div id="wayfinding-breadcrumbs_feature_div">
      <ul>
        <li><a>Category A</a></li>
        <li><a>Subcategory B</a></li>
      </ul>
    </div>

    <div class="offer">
      <span class="a-color-price">$18.99</span>
      <span class="a-size-small">Third-Party Seller</span>
      <span class="offer-condition">Used - Like New</span>
    </div>
  </body>
</html>
"""

def test_parse_product_page_basic_fields():
    asin = "TESTASIN123"
    url = "https://www.amazon.com/dp/TESTASIN123"

    product = parse_product_page(SAMPLE_HTML, asin=asin, url=url)

    assert product["asin"] == asin
    assert product["url"] == url
    assert product["title"] == "Amazing Widget 3000"
    assert product["brand"] == "Widget Corp"
    assert product["thumbnailImage"] == "https://example.com/image.jpg"
    assert product["price.value"] == pytest.approx(19.99)
    assert product["price_currency"] == "$"
    assert "Fast and reliable" in (product["description"] or "")
    assert product["stars"] == pytest.approx(4.5)
    assert product["reviewsCount"] == 1234
    assert product["breadCrumbs"] == "Category A > Subcategory B"

def test_parse_offers_from_html():
    offers = parse_offers(SAMPLE_HTML)
    assert len(offers) == 1
    offer = offers[0]
    assert offer["price_raw"] == "$18.99"
    assert offer["seller"] == "Third-Party Seller"
    assert "Used" in (offer["condition"] or "")