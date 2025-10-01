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

class FilterButton(tk.Button):
    """A custom button class that supports active/inactive states for filters."""
    
    def __init__(self, parent, text, command, button_type='primary', **kwargs):
        super().__init__(parent, text=text, command=command, **kwargs)
        
        # Store original properties
        self.original_text = text
        self.is_filter_active = False
        
        # Get button colors based on type
        colors = _get_button_colors(button_type)
        self.normal_bg = colors['bg']
        self.normal_fg = colors['fg']
        self.active_fg = "#FFFFFF"  # Keep white text for active state
        self.active_border = "#000000"  # Black border for active state
        
        # Configure initial appearance with reduced padding
        self.configure(
            bg=self.normal_bg,
            fg=self.normal_fg,
            activebackground=_lighter_color(self.normal_bg, 0.1),
            activeforeground=self.normal_fg,
            font=FONTS.get('button', ('TkDefaultFont', 9, 'bold')),  # Slightly smaller font
            relief='raised',
            bd=1,  # Thinner border for normal state
            padx=6,  # Reduced from 10
            pady=3,  # Reduced from 6
            cursor='hand2'
        )
    
    def set_active(self, active=True):
        """Set the active state of the filter button."""
        self.is_filter_active = active
        if active:
            # Active state: Dark green background + checkmark + underlined text
            self.configure(
                text=f"✓ {self.original_text}",
                fg="#FFFFFF",  # White text
                bg="#2E7D32",  # Dark green background
                activebackground="#1B5E20",  # Even darker green on hover
                activeforeground="#FFFFFF",
                relief='sunken',  # Pressed appearance
                bd=2,
                highlightbackground="#000000",
                highlightcolor="#000000", 
                highlightthickness=1,
                # Add underline to the font
                font=('TkDefaultFont', 9, 'bold underline')
            )
        else:
            # Normal state: restore original appearance
            self.configure(
                text=self.original_text,
                fg=self.normal_fg,
                bg=self.normal_bg,
                activebackground=_lighter_color(self.normal_bg, 0.1),
                activeforeground=self.normal_fg,
                relief='raised',
                bd=1,
                highlightthickness=0,
                # Remove underline from font
                font=('TkDefaultFont', 9, 'bold')
            )
    
    def toggle_active(self):
        """Toggle the active state."""
        self.set_active(not self.is_filter_active)
    
    def is_active(self):
        """Check if the filter is active."""
        return self.is_filter_active

def create_action_button(parent, text, command, button_type='primary', width=None, **kwargs):
    """
    Create a styled action button with support for active states.
    """
    # Check if this is a filter button
    is_filter = kwargs.pop('is_filter', False)
    
    if is_filter:
        # Create filter button with active state support
        button = FilterButton(parent, text, command, button_type, **kwargs)
        if width:
            button.configure(width=width)
        return button
    else:
        # For regular buttons, use tk.Button with reduced padding
        colors = _get_button_colors(button_type)
        
        button_kwargs = {
            'bg': colors['bg'],
            'fg': colors['fg'],
            'activebackground': _lighter_color(colors['bg'], 0.1),
            'activeforeground': colors['fg'],
            'font': FONTS.get('button', ('TkDefaultFont', 9, 'bold')),  # Slightly smaller font
            'relief': 'raised',
            'bd': 1,  # Thinner border
            'padx': 6,  # Reduced from 10
            'pady': 3,  # Reduced from 6
            'cursor': 'hand2'
        }
        
        # Add any additional kwargs
        button_kwargs.update(kwargs)
        
        button = tk.Button(parent, text=text, command=command, **button_kwargs)
        
        if width:
            button.configure(width=width)
        
        return button

def _get_button_colors(button_type):
    """Get background and foreground colors for different button types."""
    color_map = {
        'primary': {'bg': '#4169E1', 'fg': '#FFFFFF'},    # Royal Blue
        'secondary': {'bg': '#6c757d', 'fg': '#FFFFFF'},   # Gray
        'success': {'bg': '#28a745', 'fg': '#FFFFFF'},     # Green
        'warning': {'bg': '#ffc107', 'fg': '#000000'},     # Yellow
        'danger': {'bg': '#dc3545', 'fg': '#FFFFFF'},      # Red
        'info': {'bg': '#17a2b8', 'fg': '#FFFFFF'},        # Cyan
    }
    return color_map.get(button_type, color_map['primary'])

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