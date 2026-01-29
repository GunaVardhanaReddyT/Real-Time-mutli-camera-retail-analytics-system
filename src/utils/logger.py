"""Logging configuration"""
import sys
from loguru import logger


def setup_logger():
    """Configure loguru logger"""
    logger.remove()
    
    # Console output
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True
    )
    
    # File output
    logger.add(
        "logs/retail_analytics_{time}.log",
        rotation="100 MB",
        retention="7 days",
        level="INFO"
    )
    
    return logger