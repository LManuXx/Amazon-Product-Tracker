import asyncio
from price_tracker import get_product_info
from telegram import Bot
from dotenv import load_dotenv
import os
from database import record_price_change, get_product_id, get_last_price, get_all_products
from asyncio import Semaphore
from utils import escape_markdown_v2

# Cargar variables de entorno
load_dotenv()

# Obtener el token desde .env
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("El token no está configurado en el archivo .env")

# Crear instancia del bot
bot = Bot(token=TOKEN)

semaphore = Semaphore(5)  # Límite de 5 tareas concurrentes

async def check_prices():
    async with semaphore:
        products = get_all_products()
        for product in products:
            try:
                product_id, user_id, url, name = product
                product_name, current_price = get_product_info(url)
                last_price = get_last_price(product_id)

                if last_price is None:
                    record_price_change(product_id, current_price)
                    continue

                # Comparar precios y notificar al usuario si hay un cambio
                if current_price != last_price:
                    record_price_change(product_id, current_price)

                    # Construir el mensaje y escaparlo
                    message = (
                        f"El precio del producto ha cambiado:\n"
                        f"{product_name}\n"
                        f"Nuevo precio: {current_price}\n"
                        f"Precio anterior: {last_price}"
                    )
                    await bot.send_message(
                        chat_id=user_id,
                        text=escape_markdown_v2(message),
                        parse_mode="MarkdownV2"
                    )
            except Exception as e:
                # Mejor manejo de errores con logging
                print(f"Error al procesar el producto '{name}' con ID {product_id}: {e}")
