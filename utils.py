import re

import requests

# Diccionario para almacenar el estado de cada usuario
user_states = {}


def is_valid_amazon_url(url: str) -> bool:
    if not re.match(r"^https?://(www\\.)?amazon\\.[a-z]{2,3}(/.*)?$", url):
        return False
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def is_valid_index(index: str, max_index: int) -> bool:
    """Valida que el índice sea un número dentro de los límites permitidos."""
    if not index.isdigit():
        return False
    index = int(index)
    return 0 <= index < max_index
