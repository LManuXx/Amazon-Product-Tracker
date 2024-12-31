# proxies.py

import itertools

PROXIES = [
    "http://47.251.122.81:8888",
    "http://89.117.130.19:80",
    "http://47.90.211.55:10011",
    "http://147.135.128.218:80",
    "http://77.242.177.57:3128",
    "http://13.37.89.201:80",
    "http://13.38.176.104:3128",
    "http://3.126.147.182:80",
    "http://3.71.239.218:3128",
    "http://51.91.109.113:8118",
    "http://154.65.39.7:80",
    "http://162.214.165.203:80",
    "http://3.78.92.159:3128",
    "http://51.254.78.223:80",
    "http://47.251.43.115:33333",
    "http://37.187.25.85:80",
    "http://3.212.148.199:3128",
    "http://156.228.95.221:3128",
    "http://104.207.39.4:3128",
    "http://104.207.46.131:3128",
]

# Crear un iterador cíclico de proxies
PROXY_POOL = itertools.cycle(PROXIES)
