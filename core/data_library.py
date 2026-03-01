import json
import os
from settings import BASE_DIR

DATA_DIR = os.path.join(BASE_DIR, "data")

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

CARD_LIBRARY = load_json('cards.json')
MONSTER_LIBRARY = load_json('monsters.json')
STORE_ITEMS_DATA = load_json('store_items.json')

STORE_CONFIG = STORE_ITEMS_DATA.get('config', {})
STORE_LIBRARY = {item['id']: item for item in STORE_ITEMS_DATA.get('items', [])}
