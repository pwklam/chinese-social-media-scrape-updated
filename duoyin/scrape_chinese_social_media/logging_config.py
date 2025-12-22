import logging
from logging.handlers import RotatingFileHandler
import sys

def get_logger():
    logger = logging.getLogger('app')
    
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    
    log_file_path = 'app.log'
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10485760,  # 10MB
        backupCount=2,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger