# proxies.py

import itertools

# Lista de proxies con su tipo y dirección
PROXIES = [
    {"type": "HTTP", "url": "http://47.251.122.81:8888"},
    {"type": "HTTPS", "url": "https://103.86.116.46:8080"},
    {"type": "HTTP", "url": "http://78.80.228.150:80"},
    {"type": "HTTPS", "url": "https://103.186.90.116:8989"},
    {"type": "SOCKS5", "url": "socks5://98.175.31.195:4145"},
    {"type": "SOCKS5", "url": "socks5://164.68.127.147:41610"},
    {"type": "HTTPS", "url": "https://103.242.107.226:8098"},
    # Añade más proxies según disponibilidad
]

# Crear un iterador cíclico de proxies
PROXY_POOL = itertools.cycle(PROXIES)
