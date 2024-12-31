import psycopg2
from psycopg2.extras import RealDictCursor
from logger import config_logger
import os
from urllib.parse import urlparse

logger = config_logger()

# Configuración de la base de datos desde la variable de entorno DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("La variable de entorno DATABASE_URL no está configurada.")

parsed_url = urlparse(DATABASE_URL)
DB_CONFIG = {
    "dbname": parsed_url.path[1:],       # Remueve la barra inicial
    "user": parsed_url.username,
    "password": parsed_url.password,
    "host": parsed_url.hostname,
    "port": parsed_url.port or 5432,      # Asigna el puerto por defecto de PostgreSQL si no está especificado
}

def get_connection():
    """
    Obtiene una conexión a la base de datos PostgreSQL.

    Returns:
        psycopg2.connection: Conexión a PostgreSQL.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        raise e

def init_db():
    """
    Inicializa las tablas necesarias en la base de datos.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Crear tabla de usuarios con chat_id como PRIMARY KEY
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id BIGINT PRIMARY KEY
                )
                """)
                
                # Crear tabla de productos referenciando chat_id en lugar de user_id
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT REFERENCES users(chat_id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    name TEXT,
                    price TEXT
                )
                """)
                
                # Crear tabla de historial de precios
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    price TEXT
                )
                """)
                
                # Crear índices para optimizar las consultas
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_id ON price_history(product_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_id ON products(chat_id)")
                
                conn.commit()
                logger.info("Tablas de la base de datos inicializadas correctamente.")
    except psycopg2.Error as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        raise e

# Decorador para manejar errores de base de datos
def handle_db_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except psycopg2.Error as e:
            logger.error(f"Error en {func.__name__}: {e}")
            return None
    return wrapper

@handle_db_errors
def add_user(chat_id):
    """
    Añade un usuario a la base de datos si no existe.

    Args:
        chat_id (int): ID del chat de Telegram.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (chat_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (chat_id,)
            )
            conn.commit()
            logger.info(f"Usuario añadido o ya existente: {chat_id}")

@handle_db_errors
def is_valid_url(url):
    """
    Valida que la URL tenga un esquema y un dominio válido.

    Args:
        url (str): La URL a validar.

    Returns:
        bool: True si la URL es válida, False de lo contrario.
    """
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

@handle_db_errors
def add_product(chat_id, url, name=None, price=None):
    """
    Añade un producto a la base de datos para un usuario específico.

    Args:
        chat_id (int): ID del chat de Telegram.
        url (str): URL del producto en Amazon.
        name (str, optional): Nombre del producto. Por defecto es None.
        price (str, optional): Precio del producto. Por defecto es None.
    """
    if not is_valid_url(url):
        logger.error(f"URL inválida: {url}")
        return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            INSERT INTO products (chat_id, url, name, price)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """, (chat_id, url, name, price))
            product_id = cursor.fetchone()["id"]
            logger.info(f"Producto añadido: ID {product_id}, URL {url}")

            if price:
                cursor.execute("""
                INSERT INTO price_history (product_id, price)
                VALUES (%s, %s)
                """, (product_id, price))
            conn.commit()
            logger.info(f"Historial de precio registrado para producto ID {product_id}")

@handle_db_errors
def get_products(chat_id):
    """
    Obtiene los productos de un usuario.

    Args:
        chat_id (int): ID del chat de Telegram.

    Returns:
        list: Lista de productos con sus datos (URL, nombre, precio).
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT url, name, price FROM products WHERE chat_id = %s
            """, (chat_id,))
            products = cursor.fetchall()
            logger.info(f"Productos obtenidos para chat_id {chat_id}: {products}")
            return products

@handle_db_errors
def remove_product(chat_id, url):
    """
    Elimina un producto de la base de datos.

    Args:
        chat_id (int): ID del chat de Telegram.
        url (str): URL del producto.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            DELETE FROM products WHERE chat_id = %s AND url = %s
            """, (chat_id, url))
            deleted_rows = cursor.rowcount
            conn.commit()
            if deleted_rows > 0:
                logger.info(f"Producto eliminado: chat_id {chat_id}, URL {url}")
            else:
                logger.warning(f"No se encontró el producto para eliminar: chat_id {chat_id}, URL {url}")

@handle_db_errors
def record_price_change(product_id, price):
    """
    Registra un cambio de precio para un producto específico.

    Args:
        product_id (int): ID del producto.
        price (str): Nuevo precio del producto.
    """
    if not isinstance(product_id, int):
        logger.error(f"ID de producto inválido: {product_id}")
        return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            INSERT INTO price_history (product_id, price)
            VALUES (%s, %s)
            """, (product_id, price))
            conn.commit()
            logger.info(f"Historial de precio actualizado para producto ID {product_id}")

@handle_db_errors
def get_price_history(chat_id, url):
    """
    Obtiene el historial de precios de un producto para un usuario.

    Args:
        chat_id (int): ID del chat de Telegram.
        url (str): URL del producto.

    Returns:
        list: Lista de historial de precios con fecha y precio.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT ph.timestamp, ph.price
            FROM price_history ph
            JOIN products p ON ph.product_id = p.id
            WHERE p.chat_id = %s AND p.url = %s
            ORDER BY ph.timestamp ASC
            """, (chat_id, url))
            history = cursor.fetchall()
            logger.info(f"Historial de precios obtenido para chat_id {chat_id}, URL {url}: {history}")
            return history

@handle_db_errors
def get_last_price(product_id):
    """
    Obtiene el último precio registrado para un producto.

    Args:
        product_id (int): ID del producto.

    Returns:
        str: Último precio registrado, o None si no existe.
    """
    if not isinstance(product_id, int):
        logger.error(f"ID de producto inválido: {product_id}")
        return None

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT price
            FROM price_history
            WHERE product_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """, (product_id,))
            result = cursor.fetchone()
            if result:
                logger.info(f"Último precio para producto ID {product_id}: {result['price']}")
                return result["price"]
            else:
                logger.warning(f"No se encontró historial de precios para producto ID {product_id}")
                return None

@handle_db_errors
def get_all_products():
    """
    Obtiene todos los productos de la base de datos.

    Returns:
        list: Lista de productos con ID, chat_id, URL y nombre.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT id, chat_id, url, name FROM products
            """)
            products = cursor.fetchall()
            logger.info(f"Todos los productos obtenidos: {products}")
            return products

@handle_db_errors
def get_product_id(chat_id, url):
    """
    Obtiene el ID de un producto basado en el chat_id y la URL.

    Args:
        chat_id (int): ID del chat de Telegram.
        url (str): URL del producto.

    Returns:
        int: ID del producto, o None si no existe.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT id FROM products WHERE chat_id = %s AND url = %s
            """, (chat_id, url))
            result = cursor.fetchone()
            if result:
                logger.info(f"ID del producto obtenido para chat_id {chat_id}, URL {url}: {result['id']}")
                return result["id"]
            else:
                logger.warning(f"No se encontró el producto para chat_id {chat_id}, URL {url}")
                return None
