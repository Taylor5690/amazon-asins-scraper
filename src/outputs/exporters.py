thonimport csv
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from openpyxl import Workbook

logger = logging.getLogger(__name__)

def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def _collect_fieldnames(products: Sequence[Dict]) -> List[str]:
    fieldnames: List[str] = []
    seen = set()
    for product in products:
        for key in product.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    return fieldnames

def export_json(products: Sequence[Dict], path: Path) -> None:
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        logger.info("Exported JSON to %s", path)
    except Exception as exc:
        logger.error("Failed to export JSON to %s: %s", path, exc)
        raise

def export_csv(products: Sequence[Dict], path: Path) -> None:
    fieldnames = _collect_fieldnames(products)
    try:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in products:
                writer.writerow(row)
        logger.info("Exported CSV to %s", path)
    except Exception as exc:
        logger.error("Failed to export CSV to %s: %s", path, exc)
        raise

def export_excel(products: Sequence[Dict], path: Path) -> None:
    fieldnames = _collect_fieldnames(products)
    wb = Workbook()
    ws = wb.active
    ws.title = "Products"

    ws.append(fieldnames)
    for product in products:
        ws.append([product.get(name) for name in fieldnames])

    try:
        wb.save(str(path))
        logger.info("Exported Excel to %s", path)
    except Exception as exc:
        logger.error("Failed to export Excel to %s: %s", path, exc)
        raise

def export_html(products: Sequence[Dict], path: Path) -> None:
    fieldnames = _collect_fieldnames(products)

    lines: List[str] = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '  <meta charset="utf-8" />',
        "  <title>Amazon Products Export</title>",
        "  <style>",
        "    table { border-collapse: collapse; width: 100%; }",
        "    th, td { border: 1px solid #ddd; padding: 8px; }",
        "    th { background-color: #f4f4f4; text-align: left; }",
        "    tr:nth-child(even) { background-color: #fafafa; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>Amazon Products Export</h1>",
        "  <table>",
        "    <thead>",
        "      <tr>",
    ]
    for name in fieldnames:
        lines.append(f"        <th>{name}</th>")
    lines.extend(
        [
            "      </tr>",
            "    </thead>",
            "    <tbody>",
        ]
    )
    for product in products:
        lines.append("      <tr>")
        for name in fieldnames:
            value = product.get(name, "")
            value_str = "" if value is None else str(value)
            lines.append(f"        <td>{value_str}</td>")
        lines.append("      </tr>")
    lines.extend(
        [
            "    </tbody>",
            "  </table>",
            "</body>",
            "</html>",
        ]
    )

    try:
        with path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("Exported HTML to %s", path)
    except Exception as exc:
        logger.error("Failed to export HTML to %s: %s", path, exc)
        raise

def export_products(
    products: Sequence[Dict],
    output_dir: Path,
    formats: Iterable[str],
    base_filename: str = "amazon_products",
) -> None:
    _ensure_output_dir(output_dir)
    format_set = {fmt.lower() for fmt in formats}

    if "json" in format_set:
        export_json(products, output_dir / f"{base_filename}.json")

    if "csv" in format_set:
        export_csv(products, output_dir / f"{base_filename}.csv")

    if "excel" in format_set:
        export_excel(products, output_dir / f"{base_filename}.xlsx")

    if "html" in format_set:
        export_html(products, output_dir / f"{base_filename}.html")