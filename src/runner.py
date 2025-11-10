thonimport argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Make the src directory the import root so we can import local packages
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not to sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from extractors.amazon_parser import parse_product_page  # noqa: E402
from extractors.offer_extractor import parse_offers      # noqa: E402
from outputs.exporters import export_products            # noqa: E402

DEFAULT_CONFIG: Dict[str, Any] = {
    "base_url": "https://www.amazon.com",
    "marketplace": "US",
    "concurrency": 5,
    "timeout_seconds": 20,
    "user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0 Safari/537.36"
    ),
    "output_formats": ["json", "csv"],
    "output_dir": "data",
    "input_file": "data/inputs.sample.txt",
}

def setup_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def load_settings(config_path: Optional[str]) -> Dict[str, Any]:
    settings = DEFAULT_CONFIG.copy()
    if config_path:
        cfg_file = Path(config_path)
    else:
        cfg_file = CURRENT_DIR / "config" / "settings.example.json"

    if cfg_file.is_file():
        try:
            with cfg_file.open("r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            if not isinstance(file_cfg, dict):
                logging.warning("Config file %s does not contain a JSON object", cfg_file)
            else:
                settings.update(file_cfg)
        except Exception as exc:  # pragma: no cover - defensive
            logging.error("Failed to read config file %s: %s", cfg_file, exc)

    return settings

def read_asins(input_path: Path) -> List[str]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    asins: List[str] = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            asin = line.strip()
            if asin and not asin.startswith("#"):
                asins.append(asin)
    if not asins:
        raise ValueError(f"No ASINs found in input file {input_path}")
    return asins

def build_product_url(base_url: str, asin: str) -> str:
    base_url = base_url.rstrip("/")
    return f"{base_url}/dp/{asin}"

def fetch_product_html(
    url: str,
    timeout: int,
    user_agent: str,
) -> str:
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9",
    }
    logging.debug("Requesting URL: %s", url)
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text

def process_single_asin(
    asin: str,
    settings: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    url = build_product_url(settings["base_url"], asin)
    try:
        html = fetch_product_html(
            url=url,
            timeout=int(settings.get("timeout_seconds", 20)),
            user_agent=str(settings.get("user_agent", DEFAULT_CONFIG["user_agent"])),
        )
    except Exception as exc:
        logging.error("Failed to fetch ASIN %s at URL %s: %s", asin, url, exc)
        return None

    try:
        product = parse_product_page(html, asin=asin, url=url)
    except Exception as exc:
        logging.error("Failed to parse product for ASIN %s: %s", asin, exc)
        return None

    try:
        offers = parse_offers(html)
    except Exception as exc:
        logging.warning("Failed to parse offers for ASIN %s: %s", asin, exc)
        offers = []

    product["offers"] = offers
    return product

def run(
    input_file: str,
    output_dir: str,
    formats: List[str],
    settings: Dict[str, Any],
) -> List[Dict[str, Any]]:
    input_path = Path(input_file)
    asins = read_asins(input_path)
    logging.info("Loaded %d ASINs from %s", len(asins), input_path)

    products: List[Dict[str, Any]] = []
    concurrency = int(settings.get("concurrency", 5))
    if concurrency < 1:
        concurrency = 1

    if concurrency == 1 or len(asins) == 1:
        for asin in asins:
            product = process_single_asin(asin, settings)
            if product:
                products.append(product)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_map = {
                executor.submit(process_single_asin, asin, settings): asin
                for asin in asins
            }
            for future in as_completed(future_map):
                asin = future_map[future]
                try:
                    product = future.result()
                    if product:
                        products.append(product)
                except Exception as exc:  # pragma: no cover - defensive
                    logging.error("Unhandled exception while processing %s: %s", asin, exc)

    if not products:
        logging.warning("No products successfully scraped; nothing to export.")
        return []

    export_dir = Path(output_dir)
    export_products(
        products=products,
        output_dir=export_dir,
        formats=formats,
        base_filename="amazon_products",
    )

    logging.info("Scraping completed: %d products exported to %s", len(products), export_dir)
    return products

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Amazon ASINs Scraper runner")
    parser.add_argument(
        "--config",
        "-c",
        help="Path to JSON config file (defaults to src/config/settings.example.json)",
    )
    parser.add_argument(
        "--input",
        "-i",
        help="Path to ASIN input file (one ASIN per line)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Directory to store exported files",
    )
    parser.add_argument(
        "--formats",
        "-f",
        help="Comma-separated list of output formats (json,csv,excel,html)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv)",
    )
    return parser.parse_args(argv)

def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    setup_logging(args.verbose)
    settings = load_settings(args.config)

    input_file = args.input or settings.get("input_file") or DEFAULT_CONFIG["input_file"]
    output_dir = args.output_dir or settings.get("output_dir") or DEFAULT_CONFIG["output_dir"]

    if args.formats:
        formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    else:
        formats = [f.lower() for f in settings.get("output_formats", [])] or [
            "json",
            "csv",
        ]

    valid_formats = {"json", "csv", "excel", "html"}
    for fmt in formats:
        if fmt not in valid_formats:
            raise ValueError(f"Unsupported export format '{fmt}'. Valid: {sorted(valid_formats)}")

    run(
        input_file=input_file,
        output_dir=output_dir,
        formats=formats,
        settings=settings,
    )

if __name__ == "__main__":  # pragma: no cover - manual execution
    main()