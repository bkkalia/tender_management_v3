# ui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import sys
from typing import Dict, Any, Optional

# Add parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import tabs
from ui.search_dashboard_tab import SearchDashboardTab
from ui.portal_merger_tab import PortalDataMergerTab
from ui.settings_tab import SettingsTab
from ui.logs_tab import LogsTab
from ui.calendar_tab import CalendarTab  # Import the CalendarTab class
# Note: TenderTasksTab is still placeholder
from ui.tender_tasks_tab import TenderTasksTab

from core.config_manager import GlobalConfig
from utils.constants import COLORS, FONTS

logger = logging.getLogger(__name__)

class MainApplication(tk.Tk):
    """Main application window and controller."""
    def __init__(self):
        super().__init__()
        
        # Initialize logger
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.title("Tender Search Utility V3")
        self.geometry("1200x800")
        self.minsize(800, 600)
        
        # Set app icon if available
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"Could not load application icon: {e}")
        
        # Initialize global configuration
        self.global_config = GlobalConfig()
        
        # Apply global styles for better button visibility
        self._configure_styles()
        
        # Dictionary to store references to tabs
        self.tabs = {}
        
        # Configure the root window grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header doesn't need to expand
        self.grid_rowconfigure(1, weight=1)  # Content area expands
        self.grid_rowconfigure(2, weight=0)  # Footer doesn't need to expand
        
        # Setup UI components
        self._create_header()
        self._create_notebook()
        self._create_footer()
        
        # Initialize tabs
        self._initialize_tabs()
        
        # Setup event handlers
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("Main application initialized")

    def _configure_styles(self):
        """Configure global styles for the application."""
        style = ttk.Style()
        
        # Set the theme
        try:
            style.theme_use('clam')  # More modern look that supports better styling
        except:
            logger.warning("Could not set theme to 'clam'. Using default theme.")
        
        # Configure default button style to use royal blue with WHITE TEXT
        style.configure('TButton', 
                       background=COLORS.get('primary', '#4169E1'),  # Royal blue
                       foreground=COLORS.get('white', '#FFFFFF'),    # WHITE text
                       padding=(5, 2),
                       relief='raised',
                       font=FONTS.get('button', ('TkDefaultFont', 10)))
        
        # Make sure hover/active state is also properly colored
        style.map('TButton',
                 background=[('active', COLORS.get('primary_dark', '#1A237E')),
                            ('disabled', COLORS.get('gray_light', '#E0E0E0'))],
                 foreground=[('active', COLORS.get('white', '#FFFFFF')),
                            ('disabled', COLORS.get('gray', '#9E9E9E'))],
                 relief=[('pressed', 'sunken')])
        
        # Configure other common elements for better visibility
        style.configure('TEntry', padding=(5, 2))
        style.configure('TCombobox', padding=(5, 2))
        
        # Specifically style dialog buttons to ensure they're visible
        style.configure('Dialog.TButton',
                       background=COLORS.get('primary', '#4169E1'),
                       foreground=COLORS.get('white', '#FFFFFF'),
                       padding=(10, 5),
                       font=FONTS.get('button', ('TkDefaultFont', 10, 'bold')))
                       
        logger.info("Global styles configured")

    def _create_header(self):
        """Create the header area with logo and title."""
        header_frame = tk.Frame(self, bg=COLORS.get('primary', '#2196f3'), height=50)
        header_frame.grid(row=0, column=0, sticky="ew")
        
        # Logo (placeholder - replace with actual logo path)
        # logo_img = tk.PhotoImage(file="path/to/logo.png")
        # logo_label = tk.Label(header_frame, image=logo_img, bg=header_frame['bg'])
        # logo_label.image = logo_img  # Keep a reference
        # logo_label.pack(side=tk.LEFT, padx=10)
        
        # App title
        title_label = tk.Label(
            header_frame, 
            text="🔍 Tender Management System", 
            font=FONTS.get('header', ('Helvetica', 16, 'bold')),
            bg=header_frame['bg'],
            fg='white'
        )
        title_label.pack(side=tk.LEFT, padx=10)

    def _create_notebook(self):
        """Create the main notebook to hold tabs."""
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _create_footer(self):
        """Create the footer area with status information."""
        footer_frame = tk.Frame(self, bg=COLORS.get('background_light', '#f5f5f5'), height=25)
        footer_frame.grid(row=2, column=0, sticky="ew")
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = tk.Label(
            footer_frame, 
            textvariable=self.status_var,
            font=FONTS.get('small', ('Helvetica', 9)),
            bg=footer_frame['bg']
        )
        status_label.pack(side=tk.LEFT, padx=10)
        
        # Version label
        version_label = tk.Label(
            footer_frame, 
            text="v3.0",
            font=FONTS.get('small', ('Helvetica', 9)),
            bg=footer_frame['bg']
        )
        version_label.pack(side=tk.RIGHT, padx=10)

    def _initialize_tabs(self):
        """Initialize and add all tabs to the notebook."""
        # Search & Dashboard Tab
        search_tab = SearchDashboardTab(self.notebook, self)
        self.notebook.add(search_tab, text="Search & Dashboard")
        self.tabs["Search & Dashboard"] = search_tab
        
        # Portal Data Merger Tab
        merger_tab = PortalDataMergerTab(self.notebook, self)
        self.notebook.add(merger_tab, text="Portal Merger")
        self.tabs["Portal Merger"] = merger_tab
        
        # Calendar Tab - Replace placeholder with actual implementation
        calendar_tab = CalendarTab(self.notebook, self)
        self.notebook.add(calendar_tab, text="Calendar")
        self.tabs["Calendar"] = calendar_tab
        
        # Tasks Tab
        tasks_tab = TenderTasksTab(self.notebook, self)
        self.notebook.add(tasks_tab, text="Tasks")
        self.tabs["Tasks"] = tasks_tab
        
        # Settings Tab
        settings_tab = SettingsTab(self.notebook, self)
        self.notebook.add(settings_tab, text="Settings")
        self.tabs["Settings"] = settings_tab
        
        # Logs Tab
        logs_tab = LogsTab(self.notebook, self)
        self.notebook.add(logs_tab, text="Logs")
        self.tabs["Logs"] = logs_tab
        
        # Select the default tab
        self.notebook.select(0)  # Select first tab

    def _on_tab_changed(self, event):
        """Handle tab change event."""
        current_tab = self.notebook.select()
        if current_tab:
            tab_text = self.notebook.tab(current_tab, "text")
            logger.debug(f"Switched to tab: {tab_text}")
            
            # Get the tab instance
            tab_instance = self.tabs.get(tab_text)
            
            # Call on_tab_selected if the tab has this method
            if tab_instance and hasattr(tab_instance, 'on_tab_selected'):
                tab_instance.on_tab_selected()

    def _on_close(self):
        """Handle application close event."""
        logger.info("Application closing")
        
        # Save any unsaved configuration
        self.global_config.save_config()
        
        # Call on_closing for each tab if it has this method
        for tab_name, tab_instance in self.tabs.items():
            if hasattr(tab_instance, '_on_closing'):
                try:
                    tab_instance._on_closing()
                except Exception as e:
                    logger.error(f"Error during {tab_name} tab cleanup: {e}")
        
        # Destroy the main window
        self.destroy()
        sys.exit(0)

    def propagate_config_changes(self):
        """
        Notify all tabs and components when configuration changes have been made.
        Called after settings are saved to update components that depend on configuration.
        """
        self.logger.info("Propagating configuration changes to all components")
        
        # Reinitialize components that depend on configuration
        # Loop through all tabs and notify them if they have an update_config method
        for tab_name, tab_instance in self.tabs.items():
            # Check if the tab has a method to handle config updates
            if hasattr(tab_instance, 'update_config') and callable(getattr(tab_instance, 'update_config')):
                self.logger.debug(f"Updating config for tab: {tab_name}")
                tab_instance.update_config(self.global_config)
            elif hasattr(tab_instance, 'data_processor') and hasattr(tab_instance.data_processor, 'update_config'):
                # If tab has a data processor with update_config method
                self.logger.debug(f"Updating data processor config for tab: {tab_name}")
                tab_instance.data_processor.update_config(self.global_config)
        
        # Update any global components that need configuration updates
        # For example, if there's a logging level change:
        log_level = self.global_config.get("log_level", "INFO")
        logging.getLogger().setLevel(log_level)
        
        self.logger.info("Configuration changes propagated successfully")

    def _create_widgets(self):
        """Create the main application widgets."""
        # Create a notebook to hold our tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Remove any excessive padding around notebook and tabs
        style = ttk.Style()
        style.configure('TNotebook', tabmargins=[0, 0, 0, 0])
        style.configure('TNotebook.Tab', padding=[10, 3])
        
        # Create a frame for the status bar
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.status_frame, textvariable=self.status_var, anchor=tk.W, padding=(5, 2))
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add version label on right side of status bar
        version_label = ttk.Label(self.status_frame, text=f"v{self.global_config.get('version', '2.0')}", padding=(5, 2))
        version_label.pack(side=tk.RIGHT)
        
        # Initialize the notebook tabs - will be populated in _initialize_tabs
        self.tabs = {}