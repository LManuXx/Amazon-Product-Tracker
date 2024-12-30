import matplotlib
matplotlib.use('Agg') 
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_valid_amazon_url, is_valid_index, escape_markdown_v2
from price_tracker import get_price
from price_tracker import get_product_info
from database import add_user, add_product, get_products, remove_product, get_price_history
import matplotlib.pyplot as plt
import os
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from utils import user_states
import logging
from telegram.error import TelegramError



# Función para el comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📖 *Comandos disponibles:*\n"
        "/start  Iniciar el bot\n"
        "/add <URL>  Añadir una URL de Amazon para monitorear precios\n"
        "/list  Mostrar la lista de productos monitoreados\n"
        "/checkprice <URL>  Consultar el precio actual de un producto\n"
        "/remove <número>  Eliminar un producto monitoreado por su número en /list\n"
        "/history <URL> Ver el historial de precios de un producto\n"
        "/help  Mostrar este mensaje de ayuda\n"
    )
    await update.message.reply_text(escape_markdown_v2(help_text), parse_mode="MarkdownV2")

# Función para el comando /add
async def add_url(update, context):
    if not update.message or not context.args:
        await update.message.reply_text(escape_markdown_v2("⚠️ Por favor, proporciona una URL válida de Amazon después del comando /add."), parse_mode="MarkdownV2")
        return

    url = context.args[0]
    if not is_valid_amazon_url(url):
        await update.message.reply_text(escape_markdown_v2("⚠️ La URL proporcionada no es válida para Amazon."), parse_mode="MarkdownV2")
        return

    user_id = update.message.chat_id
    product_name, product_price = get_product_info(url)
    add_user(user_id)
    add_product(user_id, url, product_name, product_price)

    message = f"✅ Producto añadido: {product_name}  {product_price}"
    await update.message.reply_text(escape_markdown_v2(message), parse_mode="MarkdownV2")

# Función para el comando /list
async def list_urls(update, context):
    user_id = (
        update.callback_query.message.chat_id if update.callback_query else update.message.chat_id
    )
    products = get_products(user_id)

    if not products:
        message = "No tienes productos en seguimiento. Usa /add <URL> para añadir uno."
        if update.callback_query:
            await update.callback_query.edit_message_text(escape_markdown_v2(message), parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(escape_markdown_v2(message), parse_mode="MarkdownV2")
        return

    # Crear mensaje con productos
    message = "Productos en seguimiento:\n"
    for index, (url, name, price) in enumerate(products, start=1):
        message += f"{index}\. \[{name}\]\({url}\) {price}\n"


    if update.callback_query:
        await update.callback_query.edit_message_text(escape_markdown_v2(message), parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(escape_markdown_v2(message), parse_mode="MarkdownV2")


async def check_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(escape_markdown_v2("⚠️ Por favor, proporciona una URL después del comando /checkprice."), parse_mode="MarkdownV2")
        return

    url = context.args[0]
    await update.message.reply_text(escape_markdown_v2("Extrayendo precio, por favor espera..."), parse_mode="MarkdownV2")

    price = get_price(url)
    message = f"El precio del producto es: {price}"
    await update.message.reply_text(escape_markdown_v2(message), parse_mode="MarkdownV2")


async def remove_url(update, context):
    if not update.message or not context.args:
        await update.message.reply_text(escape_markdown_v2("⚠️ Por favor, proporciona el número del producto que deseas eliminar."), parse_mode="MarkdownV2")
        return

    user_id = update.message.chat_id
    try:
        product_index = context.args[0]
        products = get_products(user_id)

        if not is_valid_index(product_index, len(products)):
            await update.message.reply_text(escape_markdown_v2("⚠️ El número proporcionado no es válido. Usa /list para ver tus productos."), parse_mode="MarkdownV2")
            return

        product_index = int(product_index)
        url_to_remove = products[product_index][0]
        remove_product(user_id, url_to_remove)

        message = f"✅ El producto '{products[product_index][1]}' ha sido eliminado del seguimiento."

        await update.message.reply_text(escape_markdown_v2(message), parse_mode="MarkdownV2")
    except Exception:
        await update.message.reply_text(escape_markdown_v2("⚠️ Ocurrió un error. Inténtalo de nuevo más tarde."), parse_mode="MarkdownV2")

async def show_history(update, context):
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(escape_markdown_v2("⚠️ Por favor, proporciona la URL del producto. Ejemplo: /history <URL>"), parse_mode="MarkdownV2")
        return

    url = context.args[0]
    user_id = update.message.chat_id

    history = get_price_history(user_id, url)
    if not history:
        await update.message.reply_text(escape_markdown_v2("⚠️ No se encontró historial de precios para este producto."), parse_mode="MarkdownV2")
        return

    timestamps, prices = zip(*history)
    prices = [float(price.replace(",", ".").replace(" €", "")) for price in prices]

    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, prices, marker="o")
    plt.title("Historial de precios")
    plt.xlabel("Fecha")
    plt.ylabel("Precio (€)")
    plt.grid()
    plt.xticks(rotation=45)

    file_path = f"history_{user_id}_{int(time.time())}.png"
    plt.tight_layout()
    plt.savefig(file_path)
    plt.close()

    await update.message.reply_photo(photo=open(file_path, "rb"))
    os.remove(file_path)


async def button_handler(update, context):
    query = update.callback_query
    await query.answer()  # Responder al callback para evitar errores en Telegram

    # Procesar el callback_data
    data = query.data
    if data.startswith("product_"):
        product_index = int(data.split("_")[1]) - 1
        user_id = query.message.chat_id
        products = get_products(user_id)

        if 0 <= product_index < len(products):
            url, name, price = products[product_index]
            await query.edit_message_text(
                f"Producto seleccionado:\n\n"
                f"\*Nombre:\* {name}\n"
                f"\*Precio actual:\* {price}\n"
                f"\*URL:\* \[Enlace\]\({url}\)",
                parse_mode="MarkdownV2"
            )
        else:
            await query.edit_message_text(escape_markdown_v2("El producto seleccionado no es válido."), parse_mode="MarkdownV2")

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("➕ Añadir Producto", callback_data="add_product")],
        [InlineKeyboardButton("📜 Ver Productos", callback_data="list_products")],
        [InlineKeyboardButton("🔎 Consultar Precio", callback_data="check_price")],
        [InlineKeyboardButton("🗑️ Eliminar Producto", callback_data="remove_product")],
        [InlineKeyboardButton("📈 Historial de Precios", callback_data="price_history")],
        [InlineKeyboardButton("ℹ️ Ayuda", callback_data="help")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(escape_markdown_v2("Selecciona una acción:"), reply_markup=reply_markup, parse_mode="MarkdownV2")
    elif update.callback_query:
        await update.callback_query.edit_message_text(escape_markdown_v2("Selecciona una acción:"), reply_markup=reply_markup, parse_mode="MarkdownV2")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.message.chat_id
    await query.answer()

    # Procesar la acción seleccionada
    action = query.data

    if action == "add_product":
        user_states[user_id] = {"state": "waiting_for_url"}
        await query.edit_message_text(escape_markdown_v2("Por favor, envía la URL del producto que deseas añadir."), parse_mode="MarkdownV2")
    elif action == "list_products":
        await list_urls(update, context)  # Reutiliza la función existente
    elif action == "remove_product":
        user_states[user_id] = {"state": "waiting_for_remove"}
        await query.edit_message_text(escape_markdown_v2("Por favor, envía el número del producto que deseas eliminar."), parse_mode="MarkdownV2")
    elif action == "check_price":
        user_states[user_id] = {"state": "waiting_for_check"}
        await query.edit_message_text(escape_markdown_v2("Por favor, envía la URL del producto para consultar el precio."), parse_mode="MarkdownV2")
    elif action == "price_history":
        user_states[user_id] = {"state": "waiting_for_history"}
        await query.edit_message_text(escape_markdown_v2("Por favor, envía la URL del producto para ver el historial de precios."), parse_mode="MarkdownV2")
    elif action == "help":
        await query.edit_message_text(
            escape_markdown_v2(
                "📖 *Comandos disponibles:*\n"
                "/start  Iniciar el bot\n"
                "/add <URL>  Añadir una URL de Amazon para monitorear precios\n"
                "/list  Mostrar la lista de productos monitoreados\n"
                "/checkprice <URL>  Consultar el precio actual de un producto\n"
                "/remove <número>  Eliminar un producto monitoreado por su número en /list\n"
                "/history <URL>  Ver el historial de precios de un producto\n"
                "/help  Mostrar este mensaje de ayuda\n"
            ),
            parse_mode="MarkdownV2"
        )
    else:
        await query.edit_message_text(escape_markdown_v2("Acción no reconocida."), parse_mode="MarkdownV2")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(escape_markdown_v2("¡Hola! Bienvenido al Price Tracker Bot."), parse_mode="MarkdownV2")
    await show_menu(update, context)

async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    user_input = update.message.text

    if user_id not in user_states or "state" not in user_states[user_id]:
        await update.message.reply_text(escape_markdown_v2("Por favor, utiliza el menú para seleccionar una acción."), parse_mode="MarkdownV2")
        return

    state = user_states[user_id]["state"]

    if state == "waiting_for_url":
        if is_valid_amazon_url(user_input):
            product_name, product_price = get_product_info(user_input)
            add_user(user_id)
            add_product(user_id, user_input, product_name, product_price)
            await update.message.reply_text(escape_markdown_v2(f"Producto añadido: {product_name}  {product_price}"), parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(escape_markdown_v2("La URL proporcionada no es válida. Inténtalo de nuevo."), parse_mode="MarkdownV2")
        user_states.pop(user_id)  # Limpia el estado del usuario

    elif state == "waiting_for_remove":
        try:
            product_index = int(user_input) - 1
            products = get_products(user_id)
            if 0 <= product_index < len(products):
                url_to_remove = products[product_index][0]
                remove_product(user_id, url_to_remove)
                await update.message.reply_text(escape_markdown_v2(f'El producto "{products[product_index][1]}" ha sido eliminado del seguimiento.'), parse_mode="MarkdownV2")
            else:
                await update.message.reply_text(escape_markdown_v2("El número proporcionado no es válido."), parse_mode="MarkdownV2")
        except ValueError:
            await update.message.reply_text(escape_markdown_v2("Por favor, proporciona un número válido."), parse_mode="MarkdownV2")
        user_states.pop(user_id)  # Limpia el estado del usuario

    elif state == "waiting_for_check":
        if is_valid_amazon_url(user_input):
            price = get_price(user_input)
            await update.message.reply_text(escape_markdown_v2(f'El precio del producto es: {price}'), parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(escape_markdown_v2("La URL proporcionada no es válida. Inténtalo de nuevo."), parse_mode="MarkdownV2")
        user_states.pop(user_id)

    elif state == "waiting_for_history":
        if is_valid_amazon_url(user_input):
            await update.message.reply_text(escape_markdown_v2("Generando el historial de precios, por favor espera..."), parse_mode="MarkdownV2")
            context.args = [user_input]
            await show_history(update, context)  # Reutiliza la función existente
        else:
            await update.message.reply_text(escape_markdown_v2("La URL proporcionada no es válida. Inténtalo de nuevo."), parse_mode="MarkdownV2")
        user_states.pop(user_id)  # Limpia el estado del usuario

    else:
        await update.message.reply_text(escape_markdown_v2("Acción no reconocida. Por favor, utiliza el menú para empezar."), parse_mode="MarkdownV2")

# Configurar logs para capturar errores
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Captura errores inesperados."""
    logger.error(msg="Ocurrió un error con la actualización:", exc_info=context.error)
    try:
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text(escape_markdown_v2("⚠️ Ocurrió un error. Por favor, inténtalo de nuevo más tarde."))
        elif update and hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(escape_markdown_v2("⚠️ Ocurrió un error. Por favor, inténtalo de nuevo más tarde."))
    except TelegramError as e:
        logger.error(f"Error al enviar mensaje de error: {e}")
