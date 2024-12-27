import asyncio
from price_tracker import get_product_info
from telegram import Bot
from dotenv import load_dotenv
import os
from database import record_price_change, get_product_id, get_last_price, get_all_products
from asyncio import Semaphore

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
        # Obtener todos los productos desde la base de datos
        products = get_all_products()

        for product in products:
            product_id, user_id, url, name = product

            product_name, current_price = get_product_info(url)
            last_price = get_last_price(product_id)

            if not last_price:
                last_price = "999,99 €"
                record_price_change(product_id, last_price)

            if current_price != last_price:
                record_price_change(product_id, current_price)

                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"El precio del producto ha cambiado:\n"
                        f"[{product_name}]({url})\n"
                        f"**Nuevo precio:** {current_price}\n"
                        f"**Precio anterior:** {last_price}"
                    ),
                    parse_mode="Markdown"
                )
