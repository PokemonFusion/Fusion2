"""Utilities for scraping the Bulbapedia item list."""

import re

import requests
from bs4 import BeautifulSoup


def sanitize_name(name: str) -> str:
	"""Return a normalized item identifier."""
	return re.sub(r"\W+", "", name).lower()


def scrape_items():
	"""Scrape item data from Bulbapedia's item list."""
	url = "https://bulbapedia.bulbagarden.net/wiki/List_of_items_by_name"
	html = requests.get(url).text
	soup = BeautifulSoup(html, "lxml")
	items = {}
	for table in soup.select("table.roundy"):
		rows = table.find_all("tr")[1:]
		for row in rows:
			cells = row.find_all("td")
			if len(cells) < 4:
				continue
			name = cells[1].get_text(" ", strip=True)
			if not name:
				continue
			key = sanitize_name(name)
			generation = cells[2].get_text(" ", strip=True)
			description = cells[3].get_text(" ", strip=True)
			items[key] = {
				"name": name,
				"generation": generation,
				"description": description,
			}
	return items


if __name__ == "__main__":
	import json

	data = scrape_items()
	print("ITEM_LIST = " + json.dumps(data, indent=4, ensure_ascii=False))
