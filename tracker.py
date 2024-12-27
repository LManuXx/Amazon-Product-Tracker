from telegram.ext import Application, CommandHandler
from commands import start, add_url, list_urls, check_price, remove_url, show_history, help_command, button_handler, menu_handler
from dotenv import load_dotenv
import os
import asyncio
from threading import Thread
from database import init_db
from price_checker import check_prices
from telegram.ext import CallbackQueryHandler
from commands import handle_user_input
from telegram.ext import MessageHandler, filters

# Cargar variables de entorno
load_dotenv()

# Leer el token del archivo .env
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("El token no está configurado en el archivo .env")

def run_scheduler():
    """
    Configura y ejecuta el scheduler para tareas periódicas en un hilo separado.
    """
    async def periodic_check(interval):
        while True:
            await asyncio.create_task(check_prices())
            await asyncio.sleep(interval)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(periodic_check(60))  # Ejecutar cada 60 segundos

def start_scheduler():
    """
    Inicia el scheduler en un hilo separado.
    """
    thread = Thread(target=run_scheduler, daemon=True)
    thread.start()

# Configuración del bot
def main():
    # Inicializar la base de datos
    init_db()

    # Crear la aplicación del bot
    application = Application.builder().token(TOKEN).build()

    # Registrar comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_url))
    application.add_handler(CommandHandler("list", list_urls))
    application.add_handler(CommandHandler("checkprice", check_price))
    application.add_handler(CommandHandler("remove", remove_url))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    


    # Iniciar el scheduler en un hilo separado
    start_scheduler()

    # Iniciar el bot
    application.run_polling()

if __name__ == "__main__":
    main()
