import logging
import sys
from pathlib import Path
from loguru import logger as loguru_logger
from app.core.config import settings


class InterceptHandler(logging.Handler):
    """
    Intercepta logs estándar de Python y los redirige a loguru
    """
    def emit(self, record):
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    """
    Configura el sistema de logging
    """
    # Remover handlers por defecto
    loguru_logger.remove()
    
    # Configurar formato
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Agregar handler para stdout
    loguru_logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
    )
    
    # Agregar handler para archivo
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    
    loguru_logger.add(
        log_path / "iaops_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="INFO",
        rotation="00:00",
        retention="30 days",
        compression="zip",
    )
    
    # Interceptar logs de librerías estándar
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Configurar loggers de librerías externas
    for logger_name in ["uvicorn", "uvicorn.access", "sqlalchemy", "boto3", "azure"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
    
    return loguru_logger


logger = setup_logging()
