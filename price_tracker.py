# price_tracker.py

import requests
from bs4 import BeautifulSoup
import time
import random
from utils import simplify_amazon_url
from logger import config_logger
from proxies import PROXY_POOL  # Importa el iterador de proxies
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = config_logger()

HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",  # Do Not Track
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",  # Agrega un referer
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",  # Agrega el header Accept
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/113.0.5672.126 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/110.0.5481.77 Safari/537.36",
    # Agrega más User Agents si lo deseas
]

MAX_RETRIES = 5
RETRY_DELAY_RANGE = (5, 15)  # Tiempos de espera aleatorios entre 5 y 15 segundos

# Configurar la sesión con reintentos
session = requests.Session()
retry_strategy = Retry(
    total=MAX_RETRIES,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
    backoff_factor=1,  # Factor de espera exponencial
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

def fetch_with_retries(url: str, headers: dict) -> str:
    """Realiza una solicitud HTTP con reintentos en caso de error."""
    for attempt in range(1, MAX_RETRIES + 1):
        proxy_info = next(PROXY_POOL)
        proxy_type = proxy_info["type"].lower()  # Convertir a minúsculas para compatibilidad
        proxy_url = proxy_info["url"]
        
        # Configurar proxies según tipo
        if proxy_type in ["http", "https"]:
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
        elif proxy_type == "socks5":
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
        else:
            logger.warning(f"Tipo de proxy desconocido: {proxy_type}. Intentando sin proxy.")
            proxies = {}
        
        try:
            headers_with_agent = headers.copy()
            headers_with_agent["User-Agent"] = random.choice(USER_AGENTS)
            if proxies:
                logger.info(f"Intentando conectar a Amazon (Intento {attempt}) con proxy: {proxy_url} ({proxy_type.upper()})...")
            else:
                logger.info(f"Intentando conectar a Amazon (Intento {attempt}) sin proxy...")
            response = session.get(url, headers=headers_with_agent, proxies=proxies, timeout=10)
            response.raise_for_status()
            logger.info("Conexión exitosa.")
            return response.text
        except requests.exceptions.ProxyError as e:
            logger.warning(f"ProxyError con {proxy_url} ({proxy_type.upper()}) (Intento {attempt}): {e}")
        except requests.exceptions.ConnectTimeout as e:
            logger.warning(f"ConnectTimeout con {proxy_url} ({proxy_type.upper()}) (Intento {attempt}): {e}")
        except requests.exceptions.ReadTimeout as e:
            logger.warning(f"ReadTimeout con {proxy_url} ({proxy_type.upper()}) (Intento {attempt}): {e}")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTPError con {proxy_url} ({proxy_type.upper()}) (Intento {attempt}): {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"RequestException con {proxy_url} ({proxy_type.upper()}) (Intento {attempt}): {e}")

        if attempt < MAX_RETRIES:
            delay = random.uniform(*RETRY_DELAY_RANGE)
            logger.info(f"Reintentando en {delay:.2f} segundos con otro proxy...")
            time.sleep(delay)
        else:
            logger.error("Máximo número de intentos alcanzado con proxies. Intentando sin proxy...")
            try:
                headers_with_agent = headers.copy()
                headers_with_agent["User-Agent"] = random.choice(USER_AGENTS)
                logger.info(f"Intentando conectar a Amazon sin proxy (Intento final)...")
                response = session.get(url, headers=headers_with_agent, timeout=10)
                response.raise_for_status()
                logger.info("Conexión exitosa sin proxy.")
                return response.text
            except requests.exceptions.RequestException as e:
                logger.error(f"Error al conectar con Amazon sin proxy: {e}")
                raise e

def get_product_info(url: str) -> tuple:
    """
    Extrae el nombre y el precio de un producto de Amazon.

    Args:
        url (str): URL de la página del producto.

    Returns:
        tuple: (nombre del producto, precio del producto). Si no se encuentra, devuelve mensajes de error.
    """
    try:
        logger.info("Obteniendo información del producto...")
        html = fetch_with_retries(url, HEADERS)
        logger.info("HTML obtenido exitosamente. Procesando datos...")
        soup = BeautifulSoup(html, "lxml")

        # Extraer nombre del producto
        title_element = soup.find("span", id="productTitle")
        if not title_element:
            logger.warning("No se encontró el elemento del título del producto.")
            product_name = "Nombre no disponible"
        else:
            product_name = title_element.text.strip() 

        # Extraer precio del producto
        whole_price = soup.select_one("span.a-price-whole")
        fractional_price = soup.select_one("span.a-price-fraction")
        if whole_price and fractional_price:
            price = f"{whole_price.text.strip().replace(',', '')},{fractional_price.text.strip()} €"
        else:
            logger.warning("No se encontró el elemento del precio del producto.")
            price = "Precio no disponible"

        logger.info(f"Producto encontrado: {product_name}, Precio: {price}")
        return product_name, price
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con Amazon: {e}")
        return "Error al conectar con Amazon", str(e)
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return "Error inesperado", str(e)


def get_price(url: str) -> str:
    """
    Extrae el precio de un producto en Amazon a partir de su URL.

    Args:
        url (str): URL de la página del producto.

    Returns:
        str: El precio del producto como texto. Si no se encuentra, devuelve un mensaje de error.
    """
    try:
        url = simplify_amazon_url(url)
        logger.info(f"URL simplificada: {url}")
        logger.info("Obteniendo precio del producto...")
        html = fetch_with_retries(url, HEADERS)
        logger.info("HTML obtenido exitosamente. Procesando datos...")

        soup = BeautifulSoup(html, "lxml")
        
        # Extraer la parte entera y fraccionaria del precio
        whole_price = soup.select_one("span.a-price-whole")
        fractional_price = soup.select_one("span.a-price-fraction")
        
        if whole_price and fractional_price:
            price_whole = whole_price.text.strip().replace(",", "")
            price_fraction = fractional_price.text.strip()
            price = f"{price_whole},{price_fraction} €"
            logger.info(f"Precio encontrado: {price}")
            return price

        logger.warning("No se encontró el precio en la página.")
        return "No se pudo encontrar el precio en esta página."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con Amazon: {e}")
        return f"Error al conectar con Amazon: {e}"
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return f"Error inesperado: {e}"
