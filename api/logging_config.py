"""
Logging configuration for OAS Checker e-service
Configures structured JSON logging for Loki integration.
"""
import logging
import sys
from pythonjsonlogger import jsonlogger
import config

def setup_logging():
    """
    Setup structured JSON logging to stdout.
    This format is ideal for Loki/Grafana integration.
    """
    root_logger = logging.getLogger()
    
    # Set log level from config
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Configure JSON formatter
    # Fields to include in the JSON log
    format_str = '%(asctime)s %(levelname)s %(name)s %(message)s %(module)s %(funcName)s'
    formatter = jsonlogger.JsonFormatter(format_str)
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Silence some noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized in JSON format (Level: {config.LOG_LEVEL})")
