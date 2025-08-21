import ast
import re
from pathlib import Path

from item_list_scraper import sanitize_name, scrape_items

ITEMDEX_PATH = Path(__file__).resolve().parents[1] / "pokemon" / "dex" / "items" / "itemsdex.py"


def load_itemdex_dict(path: Path):
	"""Load the raw `py_dict` from the itemsdex module without importing it."""
	text = path.read_text()
	# Strip any leading import lines
	lines = [line for line in text.splitlines() if not line.startswith("from")]
	text = "\n".join(lines)
	match = re.search(r"py_dict\s*=\s*(\{.*\})", text, re.S)
	if not match:
		raise ValueError("py_dict not found in itemsdex")
	return ast.literal_eval(match.group(1))


def get_missing_items():
	scraped = scrape_items()
	itemdex = load_itemdex_dict(ITEMDEX_PATH)
	existing = {sanitize_name(name) for name in itemdex}
	missing = [data for key, data in scraped.items() if sanitize_name(data["name"]) not in existing]
	return missing


if __name__ == "__main__":
	missing = get_missing_items()
	print(f"Missing {len(missing)} items from ITEMDEX:")
	for item in missing:
		print(f"- {item['name']}")
