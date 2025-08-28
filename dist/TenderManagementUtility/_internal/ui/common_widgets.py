# ui/common_widgets.py
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Union, Dict, Any, cast
from utils.constants import COLORS, FONTS, SPACING

def create_labeled_frame(parent, title: str, padding: int = 5) -> ttk.LabelFrame:
    """Create consistently styled labeled frame with configurable padding."""
    frame = ttk.LabelFrame(parent, text=f" {title} ", padding=padding)
    return frame

def _lighter_color(hex_color, factor=0.3):
    """
    Create a lighter version of a given hex color for hover effects.
    
    Args:
        hex_color: Color in hex format (e.g., '#1976d2')
        factor: Float between 0 and 1 indicating how much to lighten (default: 0.3)
        
    Returns:
        Lightened hex color string
    """
    if not hex_color.startswith('#') or len(hex_color) not in [4, 7]:
        return hex_color
        
    # Handle shorthand hex (#RGB)
    if len(hex_color) == 4:
        r = int(hex_color[1], 16) * 17
        g = int(hex_color[2], 16) * 17
        b = int(hex_color[3], 16) * 17
    else:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
    
    # Calculate darker RGB values
    r = max(0, int(r * (1 - factor/2)))
    g = max(0, int(g * (1 - factor/2)))
    b = max(0, int(b * (1 - factor/2)))
    
    # Convert back to hex
    return f'#{r:02x}{g:02x}{b:02x}'

def create_action_button(parent, text, command, button_type='primary', width=None):
    """
    Create a styled action button with proper coloring and hovering effects.
    
    Args:
        parent: Parent widget
        text: Button text
        command: Function to call when button is clicked
        button_type: Style of button (primary, secondary, success, etc.)
        width: Optional width of button
        
    Returns:
        ttk.Button: The created button widget
    """
    style_name = f"{button_type}.TButton"
    
    # Create unique style for this button if not already created
    style = ttk.Style()
    
    # Get color scheme based on button type
    bg_color = COLORS.get(button_type, COLORS.get('primary'))
    fg_color = COLORS.get('white', '#ffffff')
    
    # Special handling for outlined buttons
    if button_type.endswith('_outline'):
        pass
    
    # Configure the style with reduced padding for better space usage
    style.configure(
        style_name,
        background=bg_color,
        foreground=fg_color,
        font=FONTS.get('button', ('TkDefaultFont', 10)),
        padding=(3, 1)
    )
    
    # Add hover effect
    style.map(
        style_name,
        background=[('active', _lighter_color(bg_color))],
        relief=[('active', 'sunken')]
    )
    
    # Create the button with the style
    button_kwargs: Dict[str, Union[str, int]] = {'style': style_name}
    if width is not None:
        # Ensure width is an integer (required by ttk.Button)
        try:
            button_kwargs['width'] = int(width)
        except (ValueError, TypeError):
            # If conversion fails, use default width
            pass
        
    # Create the button with proper type handling
    style = cast(str, button_kwargs.pop('style'))  # Use cast to ensure it's treated as str
    width_val = button_kwargs.pop('width', None)
    
    if width_val is not None:
        # Ensure width_val is an integer for ttk.Button
        if isinstance(width_val, int):
            button = ttk.Button(parent, text=text, command=command, style=style, width=width_val)
        else:
            # Default to no width if not an integer
            button = ttk.Button(parent, text=text, command=command, style=style)
    else:
        button = ttk.Button(parent, text=text, command=command, style=style)
    return button

def create_info_label(parent, text: str, font_style=None, textvariable=None, **kwargs) -> ttk.Label:
    """
    Create a consistent style information label.
    
    Args:
        parent: Parent widget
        text: Text to display (ignored if textvariable is provided)
        font_style: Optional font style tuple
        textvariable: Optional StringVar to bind to the label
        **kwargs: Additional keyword arguments for ttk.Label
        
    Returns:
        ttk.Label: The created label widget
    """
    if font_style is None:
        font_style = FONTS.get('body', ('TkDefaultFont', 10))
        
    # Create proper kwargs dict and set font
    label_kwargs = {'font': font_style}
    
    # Add provided kwargs
    label_kwargs.update(kwargs)
    
    if textvariable is not None:
        label = ttk.Label(parent, textvariable=textvariable, **label_kwargs)
    else:
        label = ttk.Label(parent, text=text, **label_kwargs)
    
    return label

def create_input_entry(parent, textvariable, width: int = 30) -> ttk.Entry:
    """Create a consistent style input entry field."""
    entry = ttk.Entry(parent, textvariable=textvariable, width=width)
    return entry