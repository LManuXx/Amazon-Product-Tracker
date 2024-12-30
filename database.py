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
    "dbname": parsed_url.path[1:],
    "user": parsed_url.username,
    "password": parsed_url.password,
    "host": parsed_url.hostname,
    "port": parsed_url.port,
}

def get_connection():
    """
    Obtiene una conexión a la base de datos PostgreSQL.

    Returns:
        psycopg2.connection: Conexión a PostgreSQL.
    """
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def init_db():
    """
    Inicializa las tablas necesarias en la base de datos.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY
                )
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(user_id),
                    url TEXT NOT NULL,
                    name TEXT,
                    price TEXT
                )
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    price TEXT
                )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_id ON price_history(product_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON products(user_id)")
                conn.commit()
    except psycopg2.Error as e:
        logger.error(f"Error al inicializar la base de datos: {e}")

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
def add_user(user_id):
    """
    Añade un usuario a la base de datos si no existe.

    Args:
        user_id (int): ID del usuario.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
            conn.commit()

@handle_db_errors
def add_product(user_id, url, name=None, price=None):
    """
    Añade un producto y su precio inicial a la base de datos.

    Args:
        user_id (int): ID del usuario propietario del producto.
        url (str): URL del producto.
        name (str): Nombre del producto.
        price (str): Precio del producto.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Insertar producto
            cursor.execute("""
            INSERT INTO products (user_id, url, name, price)
            VALUES (%s, %s, %s, %s) RETURNING id
            """, (user_id, url, name, price))
            product_id = cursor.fetchone()["id"]

            # Insertar precio inicial en price_history
            if price:
                cursor.execute("""
                INSERT INTO price_history (product_id, price)
                VALUES (%s, %s)
                """, (product_id, price))
            conn.commit()

@handle_db_errors
def get_products(user_id):
    """
    Obtiene los productos de un usuario.

    Args:
        user_id (int): ID del usuario.

    Returns:
        list: Lista de productos con sus datos (URL, nombre, precio).
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT url, name, price FROM products WHERE user_id = %s", (user_id,))
            return cursor.fetchall()

@handle_db_errors
def remove_product(user_id, url):
    """
    Elimina un producto de la base de datos.

    Args:
        user_id (int): ID del usuario.
        url (str): URL del producto.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM products WHERE user_id = %s AND url = %s", (user_id, url))
            conn.commit()

@handle_db_errors
def record_price_change(product_id, price):
    """
    Registra un cambio de precio en la tabla price_history.

    Args:
        product_id (int): ID del producto.
        price (str): Nuevo precio del producto.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO price_history (product_id, price) VALUES (%s, %s)", (product_id, price))
            conn.commit()

@handle_db_errors
def get_price_history(user_id, url):
    """
    Obtiene el historial de precios de un producto para un usuario.

    Args:
        user_id (int): ID del usuario.
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
            WHERE p.user_id = %s AND p.url = %s
            ORDER BY ph.timestamp ASC
            """, (user_id, url))
            return cursor.fetchall()

@handle_db_errors
def get_last_price(product_id):
    """
    Obtiene el último precio registrado de un producto.

    Args:
        product_id (int): ID del producto.

    Returns:
        str: Último precio registrado, o None si no hay datos.
    """
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
            return result["price"] if result else None

@handle_db_errors
def get_all_products():
    """
    Obtiene todos los productos de la base de datos.

    Returns:
        list: Lista de productos con ID, usuario, URL y nombre.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, user_id, url, name FROM products")
            return cursor.fetchall()
        
@handle_db_errors
def get_product_id(user_id, url):
    """
    Obtiene el ID de un producto basado en el usuario y la URL.

    Args:
        user_id (int): ID del usuario.
        url (str): URL del producto.

    Returns:
        int: ID del producto, o None si no existe.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT id FROM products WHERE user_id = %s AND url = %s
            """, (user_id, url))
            result = cursor.fetchone()
            return result["id"] if result else None