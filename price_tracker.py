import requests
from bs4 import BeautifulSoup
import time
import random
from utils import simplify_amazon_url
from logger import config_logger

logger = config_logger()

HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",  # Do Not Track
    "Upgrade-Insecure-Requests": "1",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/113.0.5672.126 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/110.0.5481.77 Safari/537.36",
]

MAX_RETRIES = 5
RETRY_DELAY_RANGE = (5, 15)  # Tiempos de espera aleatorios entre 5 y 15 segundos

def fetch_with_retries(url: str, headers: dict) -> str:
    """Realiza una solicitud HTTP con reintentos en caso de error."""
    for attempt in range(MAX_RETRIES):
        try:
            headers_with_agent = headers.copy()
            headers_with_agent["User-Agent"] = random.choice(USER_AGENTS)
            logger.info(f"Intentando conectar a Amazon (Intento {attempt + 1})...")
            response = requests.get(url, headers=headers_with_agent, timeout=10)
            response.raise_for_status()
            logger.info("Conexión exitosa.")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error al conectar (Intento {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                delay = random.uniform(*RETRY_DELAY_RANGE)
                logger.info(f"Reintentando en {delay:.2f} segundos...")
                time.sleep(delay)
            else:
                logger.error("Máximo número de intentos alcanzado. Fallo de conexión.")
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
        product_name = title_element.text.strip() if title_element else "Nombre no disponible"

        # Extraer precio del producto
        whole_price = soup.select_one("span.a-price-whole")
        fractional_price = soup.select_one("span.a-price-fraction")
        if whole_price and fractional_price:
            price = f"{whole_price.text.strip().replace(',', '')},{fractional_price.text.strip()} €"
        else:
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
