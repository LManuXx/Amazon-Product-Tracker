# utils.py
import re

# Validar si la URL es válida para Amazon
def is_valid_amazon_url(url: str) -> bool:
    return bool(re.match(r'https?://(www\.)?amazon\.\w{2,3}/', url))

user_states = {}
