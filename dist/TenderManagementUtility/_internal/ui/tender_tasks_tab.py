"""
Tender Tasks Tab module - UI component for managing tender-related tasks.
This is a placeholder implementation to prevent errors.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import sys
from typing import TYPE_CHECKING, Dict, Any

# Fix imports by adding parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can use the absolute imports
from utils.constants import SPACING, FONTS, COLORS
from ui.common_widgets import create_labeled_frame, create_action_button, create_info_label

if TYPE_CHECKING:
    from ui.main_window import MainApplication

logger = logging.getLogger(__name__)

class TenderTasksTab(ttk.Frame):
    """
    Placeholder implementation for Tender Tasks Tab.
    Displays a message indicating this feature is not yet implemented.
    """
    def __init__(self, parent: ttk.Notebook, main_app: 'MainApplication'):
        super().__init__(parent)
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self._create_widgets()
        self.logger.info("TenderTasksTab initialized (placeholder)")
    
    def _create_widgets(self):
        """Create the UI components."""
        main_frame = ttk.Frame(self, padding=SPACING['medium'])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Feature not implemented message
        message_frame = create_labeled_frame(main_frame, "Tender Tasks")
        message_frame.pack(fill=tk.BOTH, expand=True, pady=SPACING['medium'])
        
        ttk.Label(
            message_frame, 
            text="This feature is not yet implemented.",
            font=FONTS.get('heading', ('TkDefaultFont', 14, 'bold')),
            anchor=tk.CENTER
        ).pack(pady=SPACING['large']*2)
        
        ttk.Label(
            message_frame,
            text="The Tender Tasks feature will allow you to create and manage tasks\n"
                 "related to specific tenders, track progress, and set reminders.",
            font=FONTS.get('body', ('TkDefaultFont', 11)),
            justify=tk.CENTER
        ).pack(pady=SPACING['medium'])
        
        # Coming soon message
        coming_soon_frame = ttk.Frame(message_frame)
        coming_soon_frame.pack(pady=SPACING['large'])
        
        ttk.Label(
            coming_soon_frame,
            text="Coming Soon",
            font=FONTS.get('subheading', ('TkDefaultFont', 12, 'italic')),
            foreground=COLORS.get('primary', 'blue')
        ).pack()
    
    def on_tab_selected(self):
        """Called when this tab is selected."""
        self.logger.info("TenderTasksTab selected (placeholder)")
