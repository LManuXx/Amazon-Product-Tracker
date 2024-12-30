import logging

# Configuración de logging
def config_logger():
    logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    return logger