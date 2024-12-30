import re

import requests

# Diccionario para almacenar el estado de cada usuario
user_states = {}


def is_valid_amazon_url(url: str) -> bool:
    """
    Valida si la URL proporcionada pertenece a Amazon y tiene un formato válido.
    
    Args:
        url (str): La URL a validar.
    
    Returns:
        bool: True si la URL es válida, False de lo contrario.
    """
    amazon_regex = re.compile(
        r'^https?:\/\/(www\.)?(amazon\.[a-z]{2,3}(\.[a-z]{2,3})?\/)'
        r'.+\/(dp|gp\/product)\/[A-Z0-9]{10}'
    )
    return bool(amazon_regex.match(url))


def is_valid_index(index: str, max_index: int) -> bool:
    """Valida que el índice sea un número dentro de los límites permitidos."""
    if not index.isdigit():
        return False
    index = int(index)
    return 0 <= index < max_index

def escape_markdown_v2(text: str) -> str:
    """
    Escapa caracteres reservados en MarkdownV2.

    Args:
        text (str): Texto a escapar.

    Returns:
        str: Texto escapado.
    """
    escape_chars = r"_*[]()~`>#+-=|{}.!" 
    return ''.join(f"\\{char}" if char in escape_chars else char for char in text)

def simplify_amazon_url(url: str) -> str:
    ###if "/dp/" in url:
    ###    return url.split("/dp/")[0] + "/dp/" + url.split("/dp/")[1].split("/")[0]
    return url



