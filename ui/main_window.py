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
        
        # Initialize logging first
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Initializing MainApplication...")

        # Store image references to prevent garbage collection
        self._image_references = {}

        # Initialize global configuration BEFORE setting up window
        try:
            self.global_config = GlobalConfig()
            self.logger.info("Global configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load global configuration: {e}")
            messagebox.showerror("Configuration Error", 
                               f"Failed to load application configuration:\n{str(e)}\n\nUsing default settings.")
            # Create a minimal config as fallback
            self.global_config = GlobalConfig()

        # Now setup window (which needs global_config)
        self._setup_window()
        
        # Initialize other components
        self.tabs = {}
        self._create_menu()
        self._create_notebook()
        self._create_status_bar()  # Fixed typo from _create_status_bfix
        
        # Load initial data after UI is ready
        self.after(100, self._load_initial_data)

        # Setup event handlers
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("Main application initialized")

    def _setup_window(self):
        """Configure the main window properties."""
        self.title(f"{self.global_config.get('app_title', 'Tender Management Utility')} - Version 3.0")
        
        # Set window icon if it exists
        icon_path = os.path.join("resources", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
                self.logger.info(f"Window icon set successfully: {icon_path}")
            except Exception as e:
                self.logger.warning(f"Could not set window icon: {e}")
        else:
            self.logger.warning(f"Icon file not found: {icon_path}")
        
        # Set minimum window size
        self.minsize(1000, 700)
        
        # Try to restore previous window size and position
        try:
            width = self.global_config.get("window_width", 1200)
            height = self.global_config.get("window_height", 800)
            
            # Center the window on screen
            self.update_idletasks()
            x = (self.winfo_screenwidth() - width) // 2
            y = (self.winfo_screenheight() - height) // 2
            self.geometry(f"{width}x{height}+{x}+{y}")
            
            self.logger.info(f"Window geometry set to {width}x{height}+{x}+{y}")
        except Exception as e:
            self.logger.warning(f"Could not set window geometry: {e}")
            # Fallback to default size and center it
            self.geometry("1200x800")
            self.update_idletasks()
            x = (self.winfo_screenwidth() - 1200) // 2
            y = (self.winfo_screenheight() - 800) // 2
            self.geometry(f"1200x800+{x}+{y}")

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

    def _create_menu(self):
        """Create the application menu bar."""
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        
        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self._on_close)
        
        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about_dialog)

    def _create_notebook(self):
        """Create the main notebook to hold tabs."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # Initialize all tabs
        self._initialize_tabs()

    def _create_status_bar(self):
        """Create the status bar at the bottom of the window."""
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.status_frame, textvariable=self.status_var, anchor=tk.W, padding=(5, 2))
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add version label on right side of status bar
        version_label = ttk.Label(self.status_frame, text="v3.0", padding=(5, 2))
        version_label.pack(side=tk.RIGHT)

    def _load_initial_data(self):
        """Load initial data after UI is ready."""
        try:
            # Call load_initial_data_if_any on Search tab if it exists
            search_tab = self.tabs.get("Search & Dashboard")
            if search_tab and hasattr(search_tab, 'load_initial_data_if_any'):
                search_tab.load_initial_data_if_any()
                self.logger.info("Initial data loaded for Search tab")
        except Exception as e:
            self.logger.error(f"Error loading initial data: {e}")

    def _show_about_dialog(self):
        """Show the about dialog with developer information."""
        # Create a custom dialog window - increased height to ensure all content is visible
        about_dialog = tk.Toplevel(self)
        about_dialog.title("About Tender Management Utility")
        about_dialog.geometry("500x700")  # Increased height from 600 to 700
        about_dialog.transient(self)
        about_dialog.grab_set()
        about_dialog.resizable(False, False)
        about_dialog.configure(bg="white")  # Set dialog background to white
        
        # Center the dialog
        about_dialog.update_idletasks()
        x = (about_dialog.winfo_screenwidth() - 500) // 2
        y = (about_dialog.winfo_screenheight() - 700) // 2  # Updated for new height
        about_dialog.geometry(f"500x700+{x}+{y}")
        
        # Main container with padding
        main_frame = tk.Frame(about_dialog, bg="white", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # App icon and title section
        header_frame = tk.Frame(main_frame, bg="white")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Try to load and display app icon
        try:
            icon_path = os.path.join("resources", "app_icon.ico")
            if os.path.exists(icon_path):
                app_icon = tk.PhotoImage(file=icon_path)
                icon_label = tk.Label(header_frame, image=app_icon, bg="white")
                # Store reference to prevent garbage collection
                self._image_references['app_icon'] = app_icon
                icon_label.pack(pady=(0, 10))
        except Exception as e:
            self.logger.warning(f"Could not load app icon in about dialog: {e}")
            # Fallback: show a text icon
            tk.Label(header_frame, text="🔍", font=("Arial", 48), bg="white").pack(pady=(0, 10))
        
        # App title and version
        tk.Label(header_frame, text="Tender Management Utility", 
                font=("Arial", 16, "bold"), bg="white", fg="#333333").pack()
        tk.Label(header_frame, text="Version 3.0", 
                font=("Arial", 12), bg="white", fg="#666666").pack(pady=(5, 0))
        
        # App description
        description_frame = tk.Frame(main_frame, bg="white")
        description_frame.pack(fill=tk.X, pady=(0, 20))
        
        description_text = """A comprehensive tool for managing tender data with search,
filtering, merging, and calendar features.

Features:
• Search and filter tender data
• Merge data from multiple portals  
• Calendar integration for deadlines
• Task management
• Export capabilities

Built with Python and Tkinter"""
        
        tk.Label(description_frame, text=description_text, 
                font=("Arial", 10), justify=tk.LEFT, wraplength=450, 
                bg="white", fg="#333333").pack()
        
        # Separator
        separator_frame = tk.Frame(main_frame, bg="white")
        separator_frame.pack(fill=tk.X, pady=20)
        tk.Frame(separator_frame, height=1, bg="#cccccc").pack(fill=tk.X)
        
        # Developer section with explicit white background
        developer_frame = tk.Frame(main_frame, bg="white")
        developer_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Try to load company logo
        try:
            logo_path = os.path.join("resources", "cloud84_logo.png")
            if os.path.exists(logo_path):
                company_logo = tk.PhotoImage(file=logo_path)
                logo_label = tk.Label(developer_frame, image=company_logo, bg="white")
                # Store reference to prevent garbage collection
                self._image_references['company_logo'] = company_logo
                logo_label.pack(pady=(0, 15))  # Space after logo
                self.logger.info(f"Cloud84 logo loaded successfully: {logo_path}")
            else:
                # Fallback: show company name as header
                tk.Label(developer_frame, text="CLOUD 84", 
                        font=("Arial", 14, "bold"), fg="#1976d2", bg="white").pack(pady=(0, 15))
                self.logger.warning(f"Cloud84 logo not found at: {logo_path}")
        except Exception as e:
            self.logger.warning(f"Could not load company logo: {e}")
            tk.Label(developer_frame, text="CLOUD 84", 
                    font=("Arial", 14, "bold"), fg="#1976d2", bg="white").pack(pady=(0, 15))
        
        # Developer address text - split into two parts for clickable URL
        developer_info_part1 = """Cloud 84
Galua Road, Una, HP
India - 174303"""
        
        # Create the address label (non-clickable part)
        address_label = tk.Label(developer_frame, text=developer_info_part1, 
                font=("Arial", 11), justify=tk.CENTER, 
                fg="#000000", bg="white")
        address_label.pack(pady=(0, 5))
        
        # Create clickable URL label
        url_label = tk.Label(developer_frame, text="www.cloud84.in", 
                font=("Arial", 11, "underline"), justify=tk.CENTER,
                fg="#1976d2", bg="white", cursor="hand2")
        url_label.pack(pady=(0, 15))
        url_label.bind("<Button-1>", lambda e: self._open_website("https://www.cloud84.in"))
        
        # Add hover effect for URL in address
        def on_url_enter(e):
            url_label.config(fg="#0d47a1")
        def on_url_leave(e):
            url_label.config(fg="#1976d2")
            
        url_label.bind("<Enter>", on_url_enter)
        url_label.bind("<Leave>", on_url_leave)
        
        # Website link (clickable) - separate from address
        website_label = tk.Label(developer_frame, text="🌐 Visit our website", 
                                font=("Arial", 12, "underline bold"), 
                                fg="#1976d2", bg="white", cursor="hand2")
        website_label.pack(pady=(0, 20))
        website_label.bind("<Button-1>", lambda e: self._open_website("https://www.cloud84.in"))
        
        # Add hover effect for website link
        def on_enter(e):
            website_label.config(fg="#0d47a1")
        def on_leave(e):
            website_label.config(fg="#1976d2")
            
        website_label.bind("<Enter>", on_enter)
        website_label.bind("<Leave>", on_leave)
        
        # Close button
        button_frame = tk.Frame(main_frame, bg="white")
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        close_btn = tk.Button(button_frame, text="Close", command=about_dialog.destroy,
                             font=("Arial", 11), bg="#1976d2", fg="white", 
                             padx=20, pady=5, relief="raised")
        close_btn.pack()

    def _open_website(self, url):
        """Open website in default browser."""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            self.logger.error(f"Could not open website: {e}")

    def _initialize_tabs(self):
        """Initialize and add all tabs to the notebook."""
        try:
            # Search & Dashboard Tab
            search_tab = SearchDashboardTab(self.notebook, self)
            self.notebook.add(search_tab, text="Search & Dashboard")
            self.tabs["Search & Dashboard"] = search_tab
            
            # Portal Data Merger Tab
            merger_tab = PortalDataMergerTab(self.notebook, self)
            self.notebook.add(merger_tab, text="Portal Merger")
            self.tabs["Portal Merger"] = merger_tab
            
            # Calendar Tab
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
            
            self.logger.info("All tabs initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing tabs: {e}")
            messagebox.showerror("Initialization Error", f"Failed to initialize application tabs:\n{str(e)}")

    def _on_tab_changed(self, event):
        """Handle tab change event."""
        try:
            current_tab = self.notebook.select()
            if current_tab:
                tab_text = self.notebook.tab(current_tab, "text")
                self.logger.debug(f"Switched to tab: {tab_text}")
                
                # Get the tab instance
                tab_instance = self.tabs.get(tab_text)
                
                # Call on_tab_selected if the tab has this method
                if tab_instance and hasattr(tab_instance, 'on_tab_selected'):
                    tab_instance.on_tab_selected()
        except Exception as e:
            self.logger.error(f"Error handling tab change: {e}")

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