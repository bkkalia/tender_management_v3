# utils/constants.py
"""
Defines consistent styling constants for the application.
"""

import os

# Application paths
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(APP_ROOT, "config", "app_config.json")

# Enhanced color palette for improved UI
COLORS = {
    'primary': '#1976d2',
    'primary_light': '#bbdefb',
    'primary_dark': '#1a237e', 
    
    'secondary': '#9c27b0',
    'secondary_light': '#ba68c8', 
    
    'success': '#4caf50',
    'success_light': '#c8e6c9', 
    
    'warning': '#ff9800',
    'warning_light': '#ffe0b2', 
    
    'danger': '#f44336',
    'danger_light': '#ffcdd2', 
    
    'info': '#0288d1',
    'info_dark': '#01579b',
    'info_light': '#e1f5fe', 
    
    'light': '#f5f5f5',
    'dark': '#424242',
    'white': '#ffffff',
    'black': '#000000',  # Add missing black color
    'background': '#FFFFFF',
    'background_light': '#F5F5F5',
    'text': '#333333',
    
    # New UI enhancement colors
    'department_bg': '#E8F4FD',  # Light blue for department search
    'global_bg': '#E8F8E8',     # Light green for global search
    'border_primary': '#2196f3',
    'border_success': '#4caf50',
    'text_muted': '#757575'
}

# Enhanced spacing for better layout
SPACING = {
    'tiny': 2,
    'small': 5,
    'medium': 10,
    'large': 15,
    'xlarge': 20,
    'xxlarge': 30
}

# Font definitions
FONTS = {
    'heading': ('Segoe UI', 14, 'bold'),
    'subheading': ('Segoe UI', 12, 'bold'),
    'body': ('Segoe UI', 10),
    'small': ('Segoe UI', 9),
    'tiny': ('Segoe UI', 8),
    'code': ('Consolas', 9)
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
    'success_outline': {'bg': COLORS['white'], 'fg': COLORS['success'], 'bd': COLORS['success']},
    'info_outline': {'bg': COLORS['white'], 'fg': COLORS['info'], 'bd': COLORS['info']},
    'danger_outline': {'bg': COLORS['white'], 'fg': COLORS['danger'], 'bd': COLORS['danger']}
}

# Create default directories if they don't exist
os.makedirs(os.path.join(APP_ROOT, "config"), exist_ok=True)
os.makedirs(os.path.join(APP_ROOT, "data", "input_excel_files"), exist_ok=True)
os.makedirs(os.path.join(APP_ROOT, "data", "merged_files"), exist_ok=True)