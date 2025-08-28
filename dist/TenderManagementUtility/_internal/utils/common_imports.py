"""
Common imports used across the application
"""

# Standard library imports
import sys
import os
import json
import logging
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union, TYPE_CHECKING
from configparser import ConfigParser
import threading
import traceback
import shutil
import subprocess
import webbrowser
import re
import uuid
import time

# Tkinter imports
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    from tkinter.scrolledtext import ScrolledText
except ImportError as e:
    print(f"Failed to import tkinter: {e}")
    sys.exit(1)

# Third-party imports with fallbacks
try:
    from tkcalendar import Calendar, DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False
    Calendar = None
    DateEntry = None
    print("Warning: tkcalendar not available. Calendar features will be limited.")

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not available. Data processing will be limited.")

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None
    FigureCanvasTkAgg = None
    print("Warning: matplotlib not available. Data visualization will be limited.")

# Application constants
APP_NAME = "Tender Management System"
APP_VERSION = "3.0"
DATABASE_NAME = "tender_management.db"

# Import constants
try:
    from utils.constants import SPACING, FONTS, COLORS
except ImportError:
    # Fallback constants if utils.constants is not available
    SPACING = {'small': 5, 'medium': 10, 'large': 20, 'tiny': 2}
    FONTS = {'body': ('TkDefaultFont', 10), 'heading': ('TkDefaultFont', 12, 'bold')}
    COLORS = {'primary': '#007acc', 'secondary': '#6c757d'}

# Import common widgets
try:
    from ui.common_widgets import create_labeled_frame, create_action_button, create_info_label, create_input_entry
except ImportError:
    # Will be handled by individual modules
    pass

# Project-specific imports (with error handling)
try:
    from core.config_manager import GlobalConfig
except ImportError:
    GlobalConfig = None

# Logger setup with fallback
def setup_logger(name: str, level: str = 'INFO', log_file: Optional[str] = None) -> logging.Logger:
    """Setup a logger with the given name and configuration."""
    logger = logging.getLogger(name)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Set level
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create file handler for {log_file}: {e}")
    
    return logger

HAS_LOGGER_SETUP = True

# Default configuration
DEFAULT_CONFIG = {
    'database': {
        'name': DATABASE_NAME,
        'backup_enabled': 'true',
        'backup_interval': '24'
    },
    'ui': {
        'theme': 'default',
        'window_width': '1200',
        'window_height': '800'
    },
    'logging': {
        'level': 'INFO',
        'file_enabled': 'true',
        'console_enabled': 'true'
    }
}

# Utility functions
def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent
