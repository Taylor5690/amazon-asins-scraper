thonfrom pathlib import Path
import sys
import json

# Ensure src is on sys.path so imports work when running tests from repo root
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from outputs.exporters import export_products  # noqa: E402

def sample_products():
    return [
        {
            "asin": "TESTASIN1",
            "title": "Test Product 1",
            "brand": "Brand A",
            "price.value": 9.99,
            "price_currency": "$",
            "stars": 4.5,
            "reviewsCount": 100,
            "url": "https://example.com/TESTASIN1",
        },
        {
            "asin": "TESTASIN2",
            "title": "Test Product 2",
            "brand": "Brand B",
            "price.value": 19.99,
            "price_currency": "$",
            "stars": 4.0,
            "reviewsCount": 50,
            "url": "https://example.com/TESTASIN2",
        },
    ]

def test_export_products_creates_files(tmp_path: Path):
    products = sample_products()
    output_dir = tmp_path / "exports"

    export_products(
        products=products,
        output_dir=output_dir,
        formats=["json", "csv", "excel", "html"],
        base_filename="test_products",
    )

    json_file = output_dir / "test_products.json"
    csv_file = output_dir / "test_products.csv"
    excel_file = output_dir / "test_products.xlsx"
    html_file = output_dir / "test_products.html"

    assert json_file.is_file()
    assert csv_file.is_file()
    assert excel_file.is_file()
    assert html_file.is_file()

    # Basic sanity check on JSON content
    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["asin"] == "TESTASIN1"