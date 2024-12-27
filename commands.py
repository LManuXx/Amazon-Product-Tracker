# commands.py
import matplotlib
matplotlib.use('Agg') 
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_valid_amazon_url
from price_tracker import get_price
from price_tracker import get_product_info
from database import add_user, add_product, get_products, remove_product, get_price_history
import matplotlib.pyplot as plt
import os
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from utils import user_states



# Función para el comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📖 *Comandos disponibles:*\n"
        "/start - Iniciar el bot\n"
        "/add <URL> - Añadir una URL de Amazon para monitorear precios\n"
        "/list - Mostrar la lista de productos monitoreados\n"
        "/checkprice <URL> - Consultar el precio actual de un producto\n"
        "/remove <número> - Eliminar un producto monitoreado por su número en /list\n"
        "/history <URL> - Ver el historial de precios de un producto\n"
        "/help - Mostrar este mensaje de ayuda\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# Función para el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('¡Hola, soy tu Price Tracker Bot! Usa /add <URL> para agregar una URL de Amazon y /list para ver tus productos.')

# Función para el comando /add
async def add_url(update, context):
    if not update.message or not context.args:
        await update.message.reply_text("Por favor, proporciona una URL válida de Amazon después del comando /add.")
        return

    url = context.args[0]
    if not is_valid_amazon_url(url):
        await update.message.reply_text("La URL proporcionada no es válida para Amazon.")
        return

    user_id = update.message.chat_id
    product_name, product_price = get_product_info(url)
    add_user(user_id)
    add_product(user_id, url, product_name, product_price)

    await update.message.reply_text(f"Producto añadido: {product_name} - {product_price}")

# Función para el comando /list
async def list_urls(update, context):
    user_id = (
        update.callback_query.message.chat_id if update.callback_query else update.message.chat_id
    )
    products = get_products(user_id)

    if not products:
        if update.callback_query:
            await update.callback_query.edit_message_text('No tienes productos en seguimiento. Usa /add <URL> para añadir uno.')
        else:
            await update.message.reply_text('No tienes productos en seguimiento. Usa /add <URL> para añadir uno.')
        return

    # Crear mensaje con productos
    message = "Productos en seguimiento:\n"
    for index, (url, name, price) in enumerate(products, start=1):
        message += f"{index}. [{name}]({url}) - {price}\n"

    if update.callback_query:
        await update.callback_query.edit_message_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")


async def check_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text('Por favor, proporciona una URL después del comando /checkprice.')
        return

    url = context.args[0]
    await update.message.reply_text('Extrayendo precio, por favor espera...')

    # Llamar a la función para obtener el precio
    price = get_price(url)
    await update.message.reply_text(f'El precio del producto es: {price}')


async def remove_url(update, context):
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text('Por favor, proporciona el número del producto que deseas eliminar. Usa /list para ver tus productos.')
        return

    user_id = update.message.chat_id
    try:
        # Obtener el número del producto desde el argumento
        product_index = int(context.args[0]) - 1  # Ajustar índice para que comience en 0
        products = get_products(user_id)

        if not products:
            await update.message.reply_text('No tienes productos en seguimiento. Usa /list para ver tus productos.')
            return

        # Verificar que el índice esté dentro del rango válido
        if product_index < 0 or product_index >= len(products):
            await update.message.reply_text('El número del producto no es válido. Usa /list para ver tus productos.')
            return

        # Obtener la URL del producto seleccionado
        url_to_remove = products[product_index][0]
        remove_product(user_id, url_to_remove)

        await update.message.reply_text(f'El producto "{products[product_index][1]}" ha sido eliminado del seguimiento.')  # Nombre del producto
    except ValueError:
        await update.message.reply_text('Por favor, proporciona un número válido.')

async def show_history(update, context):
    # Verificar si hay argumentos (URL) en el contexto
    if not context.args or len(context.args) == 0:
        await update.message.reply_text("Por favor, proporciona la URL del producto. Ejemplo: /history <URL>")
        return

    url = context.args[0]
    user_id = update.message.chat_id

    # Obtener el historial de la base de datos
    history = get_price_history(user_id, url)
    if not history:
        await update.message.reply_text("No se encontró historial de precios para este producto.")
        return

    # Generar la gráfica
    timestamps, prices = zip(*history)
    prices = [float(price.replace(",", ".").replace(" €", "")) for price in prices]

    # Crear el gráfico
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, prices, marker="o")
    plt.title("Historial de precios")
    plt.xlabel("Fecha")
    plt.ylabel("Precio (€)")
    plt.grid()
    plt.xticks(rotation=45)

    # Guardar y enviar la imagen
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
                f"*Nombre:* {name}\n"
                f"*Precio actual:* {price}\n"
                f"*URL:* [Enlace]({url})",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("El producto seleccionado no es válido.")

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
        await update.message.reply_text("Selecciona una acción:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("Selecciona una acción:", reply_markup=reply_markup)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.message.chat_id
    await query.answer()

    # Procesar la acción seleccionada
    action = query.data

    if action == "add_product":
        user_states[user_id] = {"state": "waiting_for_url"}
        await query.edit_message_text("Por favor, envía la URL del producto que deseas añadir.")
    elif action == "list_products":
        await list_urls(update, context)  # Reutiliza la función existente
    elif action == "remove_product":
        user_states[user_id] = {"state": "waiting_for_remove"}
        await query.edit_message_text("Por favor, envía el número del producto que deseas eliminar.")
    elif action == "check_price":
        user_states[user_id] = {"state": "waiting_for_check"}
        await query.edit_message_text("Por favor, envía la URL del producto para consultar el precio.")
    elif action == "price_history":
        user_states[user_id] = {"state": "waiting_for_history"}
        await query.edit_message_text("Por favor, envía la URL del producto para ver el historial de precios.")
    elif action == "help":
        await query.edit_message_text(
            "📖 *Comandos disponibles:*\n"
            "/start - Iniciar el bot\n"
            "/add <URL> - Añadir una URL de Amazon para monitorear precios\n"
            "/list - Mostrar la lista de productos monitoreados\n"
            "/checkprice <URL> - Consultar el precio actual de un producto\n"
            "/remove <número> - Eliminar un producto monitoreado por su número en /list\n"
            "/history <URL> - Ver el historial de precios de un producto\n"
            "/help - Mostrar este mensaje de ayuda\n",
        parse_mode="Markdown"
    )
  # Reutiliza la función de ayuda
    else:
        await query.edit_message_text("Acción no reconocida.")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("¡Hola! Bienvenido al Price Tracker Bot.")
    await show_menu(update, context)

async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    user_input = update.message.text

    if user_id not in user_states or "state" not in user_states[user_id]:
        await update.message.reply_text("Por favor, utiliza el menú para seleccionar una acción.")
        return

    state = user_states[user_id]["state"]

    if state == "waiting_for_url":
        if is_valid_amazon_url(user_input):
            product_name, product_price = get_product_info(user_input)
            add_user(user_id)
            add_product(user_id, user_input, product_name, product_price)
            await update.message.reply_text(f"Producto añadido: {product_name} - {product_price}")
        else:
            await update.message.reply_text("La URL proporcionada no es válida. Inténtalo de nuevo.")
        user_states.pop(user_id)  # Limpia el estado del usuario

    elif state == "waiting_for_remove":
        try:
            product_index = int(user_input) - 1
            products = get_products(user_id)
            if 0 <= product_index < len(products):
                url_to_remove = products[product_index][0]
                remove_product(user_id, url_to_remove)
                await update.message.reply_text(f'El producto "{products[product_index][1]}" ha sido eliminado del seguimiento.')
            else:
                await update.message.reply_text("El número proporcionado no es válido.")
        except ValueError:
            await update.message.reply_text("Por favor, proporciona un número válido.")
        user_states.pop(user_id)  # Limpia el estado del usuario

    elif state == "waiting_for_check":
        if is_valid_amazon_url(user_input):
            price = get_price(user_input)
            await update.message.reply_text(f'El precio del producto es: {price}')
        else:
            await update.message.reply_text("La URL proporcionada no es válida. Inténtalo de nuevo.")
        user_states.pop(user_id)

    elif state == "waiting_for_history":
        if is_valid_amazon_url(user_input):
            await update.message.reply_text("Generando el historial de precios, por favor espera...")
            context.args = [user_input]
            await show_history(update, context)  # Reutiliza la función existente
        else:
            await update.message.reply_text("La URL proporcionada no es válida. Inténtalo de nuevo.")
        user_states.pop(user_id)  # Limpia el estado del usuario

    else:
        await update.message.reply_text("Acción no reconocida. Por favor, utiliza el menú para empezar.")
