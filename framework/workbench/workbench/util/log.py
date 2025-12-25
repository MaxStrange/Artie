"""
Logging utilities for Workbench.
"""
import logging

LOGGER_NAME = 'artie_workbench'
"""The name of the logger used throughout the Workbench."""

def initialize_logger(level: int = logging.DEBUG, fpath: str = None) -> logging.Logger:
    """Initialize and return a logger with the specified name and level."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    
    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
   
    # Create formatter and add it to the handler
    formatter = logging.Formatter('[%(asctime)s:%(name)s:%(levelname)s]>%(message)s')
    ch.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(ch)

    # Create file handler
    if fpath:
        fh = logging.FileHandler(fpath)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    
    return logger

def debug(message: str):
    """Log a debug message."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.debug(message)

def info(message: str):
    """Log an info message."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.info(message)

def warning(message: str):
    """Log a warning message."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.warning(message)

def error(message: str):
    """Log an error message."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.error(message)

def critical(message: str):
    """Log a critical message."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.critical(message)
