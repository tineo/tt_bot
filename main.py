import asyncio
import logging
import argparse
import requests
from TikTokLive import TikTokLiveClient
from TikTokLive.client.logger import LogLevel
from TikTokLive.events import ConnectEvent, CommentEvent, GiftEvent, JoinEvent
from TikTokLive.client.errors import UserOfflineError
from datetime import datetime
import sys

# Variables globales
unique_id = None  # Declaramos la variable global
user_id = None  # Declaramos la variable global
topic_id = None  # Declaramos la variable global


def send_ntfy(message):
    topic = topic_id
    mensaje = message

    requests.post(
        f"https://ntfy.sh/{topic}",
        data=mensaje.encode("utf-8"),
        headers={"Title": "Tiktok Alert"}
    )


# Función para obtener la fecha y hora actual en formato legible
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Función para redirigir los prints a los logs
def log_print(message):
    logging.info(message)


# Configuración de logging
def setup_logging(unique_id):
    log_filename = f"{unique_id}_log.txt"  # Nombre de archivo basado en unique_id
    logging.basicConfig(
        level=logging.INFO,  # Nivel de log, INFO para capturar todos los logs
        format='%(asctime)s - %(message)s',  # Formato de los logs, incluye fecha y hora
        handlers=[
            logging.FileHandler(log_filename, mode='a'),  # Guardar los logs en archivo
            logging.StreamHandler()  # Imprimir también en la consola
        ]
    )


# Función para intentar la conexión
async def try_connect(client):
    while True:
        try:
            # Intentar conectar
            await client.connect()
            break  # Si la conexión es exitosa, salimos del bucle
        except UserOfflineError:
            # Si el usuario está fuera de línea, esperamos y reintentamos
            log_print(f"El usuario @{client.unique_id} está fuera de línea. Reintentando...(5min en reintentar)")
            await asyncio.sleep(300)  # Esperar 5 minutos antes de reintentar


# Escuchar al evento de conexión
async def on_connect(event: ConnectEvent):
    log_print(f"Conectado a @{event.unique_id} (Room ID: {event.room_id})")


# Escuchar al evento de comentario
async def on_comment(event: CommentEvent) -> None:
    log_print(f"{event.user.unique_id} -> {event.comment}")
    if event.user.unique_id == user_id:
        send_ntfy(f"(chat) {event.user.unique_id} : {event.comment}")


async def on_disconnect(event):
    log_print(f"{event.user.unique_id} se desconectó. Reintentando conexión...")
    await try_connect(client)  # Llama a la función de reconexión


# Escuchar al evento de regalo
async def on_gift(event: GiftEvent):
    if event.gift.streakable and not event.streaking:
        log_print(f"🎁 {event.user.unique_id} envió {event.repeat_count} \"{event.gift.name}\" ({event.gift_id})")
    elif not event.gift.streakable:
        log_print(f"🎁🎁 {event.user.unique_id} envió \"{event.gift.name}\" ({event.gift_id})")


# Escuchar un user uniendose al live
async def on_join(event: JoinEvent):
    global user_id  # Usamos la variable global
    log_print(f"🟢 {event.user.unique_id} Conectado")

    # Verificar si el user_id es el esperado
    if event.user.unique_id == user_id:
        send_ntfy(f"{event.user.unique_id} conectado en {unique_id}")


def setup_parser():
    parser = argparse.ArgumentParser(
        description="Ejecutar el script de TikTok Live para un usuario específico. "
                    "Asegúrate de proporcionar los siguientes parámetros: unique_id, user_id, y topic_id."
    )

    # Definir los argumentos con valores predeterminados y descripciones más claras
    parser.add_argument(
        "unique_id",
        type=str,
        help="unique_id es el username del live a ver (ejm: _itsudatte).",
        default="_default_unique_id"  # Valor predeterminado si no se pasa un argumento
    )

    parser.add_argument(
        "user_id",
        type=str,
        help="user_id es el username a seguir (ejm: _itsudatte).",
        default="_default_user_id"  # Valor predeterminado si no se pasa un argumento
    )

    parser.add_argument(
        "topic_id",
        type=str,
        help="topic_id es el identificador del canal de notificación (ejm: _itsudatte_topic).",
        default="_default_topic_id"  # Valor predeterminado si no se pasa un argumento
    )

    return parser


if __name__ == '__main__':
    parser = setup_parser()
    try:
        args = parser.parse_args()

        # Asignar los valores de los argumentos a las variables globales
        unique_id = args.unique_id
        user_id = args.user_id
        topic_id = args.topic_id

        print(f"unique_id: {unique_id}")
        print(f"user_id: {user_id}")
        print(f"topic_id: {topic_id}")

    except SystemExit as e:

        # Capturamos SystemExit y mostramos un mensaje amigable
        print("\nError: Faltan los siguientes argumentos requeridos:")
        print("  - unique_id: El unique_id del usuario de TikTok.")
        print("  - user_id: El user_id que se desea filtrar.")
        print("  - topic_id: El topic_id para las notificaciones.")
        print("\nPor favor, proporciónalos al ejecutar el script.")
        print("\nUso correcto del script:")
        parser.print_help()
        sys.exit(1)

    # Crear el cliente con el unique_id proporcionado
    client = TikTokLiveClient(unique_id=unique_id)

    # Configurar los logs
    setup_logging(unique_id)

    # Registra los listeners en el cliente después de la creación
    client.on(ConnectEvent)(on_connect)
    client.add_listener(CommentEvent, on_comment)
    client.on(GiftEvent)(on_gift)
    client.on(JoinEvent)(on_join)

    # Ejecutar la función de intentar conexión
    asyncio.run(try_connect(client))

    # Ejecutar el cliente
    client.run()
