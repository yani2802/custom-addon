import logging
import logging.handlers
from pathlib import Path
import sys
from datetime import datetime

def setup_logger(name: str, config=None) -> logging.Logger:
    """Setup logger with file and console handlers"""
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Default log level
    log_level = getattr(logging, (config.LOG_LEVEL if config else 'INFO').upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if config:
        log_dir = config.log_dir
    else:
        log_dir = Path.home() / '.hardware_agent' / 'logs'
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'hardware_agent.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'hardware_agent_errors.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    return logger

class DeviceLogger:
    """Specialized logger for device events"""
    
    def __init__(self, config=None):
        self.logger = setup_logger('device_events', config)
        
        if config:
            log_dir = config.log_dir
        else:
            log_dir = Path.home() / '.hardware_agent' / 'logs'
        
        # Device events file handler
        device_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'device_events.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        device_handler.setLevel(logging.INFO)
        device_handler.setFormatter(logging.Formatter(
            '%(asctime)s - DEVICE - %(message)s'
        ))
        self.logger.addHandler(device_handler)
    
    def device_connected(self, device_info):
        """Log device connection"""
        self.logger.info(f"CONNECTED: {device_info}")
    
    def device_disconnected(self, device_info):
        """Log device disconnection"""
        self.logger.info(f"DISCONNECTED: {device_info}")
    
    def device_error(self, device