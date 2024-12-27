import sqlite3

# Nombre del archivo de la base de datos
DB_NAME = "tracker.db"

# Inicializar la base de datos
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT NOT NULL,
            name TEXT,
            price TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            price TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_id ON price_history(product_id)")
        conn.commit()

# Añadir un usuario
def add_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

# Añadir un producto
def add_product(user_id, url, name=None, price=None):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO products (user_id, url, name, price)
        VALUES (?, ?, ?, ?)
        """, (user_id, url, name, price))
        conn.commit()

# Obtener los productos de un usuario
def get_products(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT url, name, price FROM products WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchall()

# Eliminar un producto
def remove_product(user_id, url):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        DELETE FROM products WHERE user_id = ? AND url = ?
        """, (user_id, url))
        conn.commit()

def record_price_change(product_id, price):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO price_history (product_id, price)
        VALUES (?, ?)
        """, (product_id, price))
        conn.commit()


def get_price_history(user_id, url):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT ph.timestamp, ph.price
        FROM price_history ph
        JOIN products p ON ph.product_id = p.id
        WHERE p.user_id = ? AND p.url = ?
        ORDER BY ph.timestamp ASC
        """, (user_id, url))
        return cursor.fetchall()

def get_product_id(user_id, url):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id FROM products WHERE user_id = ? AND url = ?
        """, (user_id, url))
        result = cursor.fetchone()
        return result[0] if result else None

def get_last_price(product_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT price
        FROM price_history
        WHERE product_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """, (product_id,))
        result = cursor.fetchone()
        return result[0] if result else None


def get_all_products():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, user_id, url, name
        FROM products
        """)
        return cursor.fetchall()
