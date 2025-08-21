import re

import requests
from bs4 import BeautifulSoup


def scrape_pokeballs():
    url = 'https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9_Ball?action=edit'
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'lxml')
    textarea = soup.find('textarea')
    if not textarea:
        raise RuntimeError('Failed to load wiki text')
    text = textarea.text
    match = re.search(r"\{\| class=\"roundtable sortable\".*?\|\}", text, re.DOTALL)
    if not match:
        raise RuntimeError('Could not find Poké Ball table')
    table = match.group(0)
    result = {}
    rows = table.split('\n|-')[1:]
    for row in rows:
        if row.strip().startswith('|}'):  # end of table
            break
        if 'class="unsortable"' in row:
            continue
        cells = [c.strip() for c in row.strip().split('\n|')]
        if len(cells) < 7:
            continue
        name_cell = re.sub(r'\{\{i\|(.*?)}}', r'\1', cells[1])
        m = re.search(r'\[\[([^\]|]+)', name_cell)
        name = m.group(1) if m else name_cell
        key = name.lower().replace(' ', '_')
        gen_m = re.search(r"'''([^']+)'''", cells[2])
        generation = f"Gen {gen_m.group(1)}" if gen_m else cells[2]
        catch_rate = BeautifulSoup(cells[5], 'lxml').get_text(' ', strip=True)
        notes = BeautifulSoup(cells[6], 'lxml').get_text(' ', strip=True)
        result[key] = {
            'name': name,
            'introduced_in': generation,
            'catch_rate_modifier': catch_rate,
            'description': catch_rate,
            'notes': notes,
        }
    return result

if __name__ == '__main__':
    import json
    data = scrape_pokeballs()
    print('POKE_BALLS = ' + json.dumps(data, indent=4, ensure_ascii=False))
