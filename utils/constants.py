# utils/constants.py
"""
Defines consistent styling constants for the application.
"""

import os

# Application paths
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(APP_ROOT, "config", "app_config.json")

# Spacing constants in pixels
SPACING = {
    'tiny': 2,
    'small': 5,
    'medium': 10,
    'large': 15,
    'xlarge': 20
}

# Font definitions
FONTS = {
    'heading': ('Arial', 16, 'bold'),
    'subheading': ('Arial', 12, 'bold'),
    'body': ('Arial', 10),
    'small': ('Arial', 8),
    'tiny': ('Arial', 6),
    'button': ('Arial', 10),  # Standard button font
}

# Color scheme
COLORS = {
    'primary': '#2196F3',           # Vibrant blue
    'primary_light': '#64B5F6',     # Lighter blue
    'primary_dark': '#1565C0',      # Darker blue
    'primary_highlight': '#90CAF9',
    
    'secondary': '#9C27B0',         # Vibrant purple
    'secondary_light': '#BA68C8',   # Lighter purple
    
    'success': '#00C853',           # Vibrant green
    'success_light': '#69F0AE',     # Lighter green
    
    'warning': '#FFA000',           # Vibrant amber
    'warning_light': '#FFD54F',     # Lighter amber
    
    'danger': '#F44336',            # Vibrant red
    'danger_light': '#EF9A9A',      # Lighter red
    
    'info': '#00B0FF',              # Vibrant light blue
    'info_dark': '#0277BD',         # Darker light blue
    'info_light': '#81D4FA',        # Lighter light blue
    
    'white': '#FFFFFF',
    'black': '#000000',
    'background': '#FFFFFF',
    'background_light': '#F5F5F5',
    'text': '#333333'
}

# Default button types for create_action_button
BUTTON_TYPES = {
    'primary': {'bg': COLORS['primary'], 'fg': COLORS['white']},
    'secondary': {'bg': COLORS['secondary'], 'fg': COLORS['white']},
    'success': {'bg': COLORS['success'], 'fg': COLORS['white']},
    'info': {'bg': COLORS['info'], 'fg': COLORS['white']},
    'warning': {'bg': COLORS['warning'], 'fg': COLORS['black']},
    'danger': {'bg': COLORS['danger'], 'fg': COLORS['white']},
    'primary_outline': {'bg': COLORS['white'], 'fg': COLORS['primary'], 'bd': COLORS['primary']},
    'secondary_outline': {'bg': COLORS['white'], 'fg': COLORS['secondary'], 'bd': COLORS['secondary']},
    'info_outline': {'bg': COLORS['white'], 'fg': COLORS['info'], 'bd': COLORS['info']},
    'danger_outline': {'bg': COLORS['white'], 'fg': COLORS['danger'], 'bd': COLORS['danger']}
}

# Create default directories if they don't exist
os.makedirs(os.path.join(APP_ROOT, "config"), exist_ok=True)
os.makedirs(os.path.join(APP_ROOT, "data", "input_excel_files"), exist_ok=True)
os.makedirs(os.path.join(APP_ROOT, "data", "merged_files"), exist_ok=True)