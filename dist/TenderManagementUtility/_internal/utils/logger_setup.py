# utils/logger_setup.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
import queue
from typing import Optional

# Configure default logging
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_FILE_MAX_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_FILE_BACKUP_COUNT = 3

# Create logs directory if it doesn't exist
def setup_logging(log_dir: Optional[str] = None, log_level: Optional[int] = None):
    """
    Set up logging configuration for the application.
    
    Args:
        log_dir: Directory to store log files. If None, defaults to 'logs' in the application root.
        log_level: Logging level (e.g., logging.DEBUG, logging.INFO). If None, uses LOG_LEVEL constant.
    """
    if log_dir is None:
        # Get the application root directory (parent of the parent of this file)
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(app_root, 'logs')
    
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Determine log level
    level = log_level if log_level is not None else LOG_LEVEL
    
    # Configure the root logger
    log_file_path = os.path.join(log_dir, 'tender_management.log')
    
    # Create a rotating file handler
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=LOG_FILE_MAX_SIZE,
        backupCount=LOG_FILE_BACKUP_COUNT
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates when reconfiguring
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add the handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file_path}")
    return root_logger

# TextWidgetLogger class for the LogsTab
class TextWidgetLogger(logging.Handler):
    """
    Custom logging handler that writes log messages to a queue for display in a tkinter Text widget.
    """
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S'))
    
    def emit(self, record):
        """Process a log record and put it in the queue for the UI to display."""
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)

# Create a logger for use throughout the application
logger = logging.getLogger('tender_management')