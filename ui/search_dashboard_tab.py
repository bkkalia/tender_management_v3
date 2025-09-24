# ui/search_dashboard_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd # For Treeview population
import logging
import os
import sys
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Union
import webbrowser # For opening URLs
from datetime import datetime, timedelta, time # For date filters - Added time import
import threading
import time as time_module  # Renamed to avoid conflict with datetime.time
import re
import tkinter.simpledialog

# Try to import PIL for image creation
try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PIL = True
except ImportError:
    Image = None
    ImageDraw = None
    ImageTk = None
    HAS_PIL = False
    print("Warning: PIL not available. URL icons will use text representation.")

# Handle optional imports
try:
    from tkcalendar import DateEntry  # For calendar picker
    HAS_TKCALENDAR = True
except ImportError:
    DateEntry = None
    HAS_TKCALENDAR = False
    print("Warning: tkcalendar not available. Date picker features will be limited.")

# Fix imports by adding parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can use the absolute imports
from utils.constants import SPACING, FONTS, COLORS
from ui.common_widgets import create_labeled_frame, create_action_button, create_input_entry, create_info_label
from core.data_processor import TenderDataProcessor
from core.remote_data_loader import RemoteDataLoader

if TYPE_CHECKING:
    from ui.main_window import MainApplication # Use absolute import

logger = logging.getLogger(__name__)

class RemoteUrlDialog(tk.Toplevel):
    """Dialog for entering remote URL and credentials."""
    
    def __init__(self, parent, remote_loader):
        super().__init__(parent)
        self.parent = parent
        self.remote_loader = remote_loader
        self.result = None
        
        self.title("Add Remote URL")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self._create_widgets()
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # URL field
        ttk.Label(main_frame, text="URL:").pack(anchor=tk.W)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=50)
        url_entry.pack(fill=tk.X, pady=(0, 10))
        url_entry.focus()
        
        # Username field
        ttk.Label(main_frame, text="Username (optional):").pack(anchor=tk.W)
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(main_frame, textvariable=self.username_var, width=50)
        username_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Password field
        ttk.Label(main_frame, text="Password (optional):").pack(anchor=tk.W)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(main_frame, textvariable=self.password_var, width=50, show="*")
        password_entry.pack(fill=tk.X, pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="OK", command=self._ok).pack(side=tk.RIGHT)
        
        # Bind Enter key to OK
        self.bind('<Return>', lambda e: self._ok())
        self.bind('<Escape>', lambda e: self._cancel())
        
    def _ok(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a URL.")
            return
            
        username = self.username_var.get().strip() or None
        password = self.password_var.get().strip() or None
        
        self.result = (url, username, password)
        self.destroy()
        
    def _cancel(self):
        self.result = None
        self.destroy()

class SearchDashboardTab(ttk.Frame):
    """
    Search & Dashboard Tab: Load data, search, filter, and view statistics.
    """
    def __init__(self, parent: ttk.Notebook, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Add filter state tracking
        self.active_filters = set()
        self.filter_buttons = {}
        self.current_filtered_data = None

        # Initialize UI elements that are referenced before creation
        self.results_count_var = tk.StringVar(value="No data loaded")
        self.tree = None  # Will be created in _create_tender_data_widgets
        self.dashboard_labels = {}  # Will be populated in _create_dashboard_widgets

        self.data_processor = TenderDataProcessor(self.main_app.global_config)
        # --- ensure filtered_data attribute exists even before any load ---
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data is None:
            self.data_processor.filtered_data = pd.DataFrame()

        self.loaded_files: List[str] = []

        # UI Variables - Add missing variables
        self.dept_filter_var = tk.StringVar()
        self.global_search_var = tk.StringVar()
        self.selected_folders_var = tk.StringVar(value="No folders selected.")
        self.custom_date_start_var = tk.StringVar()
        self.custom_date_end_var = tk.StringVar()
        
        # Add missing operator variables
        self.dept_operator_var = tk.StringVar(value="OR")
        self.global_operator_var = tk.StringVar(value="AND")
        self.status_filter_var = tk.StringVar(value="live")
        
        # Add missing saved search variable
        self.saved_search_var = tk.StringVar()
        
        # --- NEW time vars for custom range ---
        self.start_hour_var = tk.StringVar(value="00")
        self.start_min_var = tk.StringVar(value="00")
        self.end_hour_var = tk.StringVar(value="23")
        self.end_min_var = tk.StringVar(value="59")
        
        # Date filter state
        self.current_date_filter: Dict[str, Any] = {}

        # Add state for clock/date display
        self.clock_running = False
        self.current_time_var = tk.StringVar(value="Loading...")
        self.current_date_var = tk.StringVar(value="")
        
        # Initialize tooltip attribute
        self.tooltip = None
        # Performance: debounce + async filter state
        self._filter_after_id = None
        self.filter_delay_ms = 250  # typing debounce
        self._filter_thread = None
        self._filter_thread_running = False

        # --- added sort state ---
        self.sort_column: Optional[str] = None
        self.sort_ascending: bool = True

        # --- In-memory inverted index (experimental) ---
        self._token_index: Dict[str, set] = {}
        self._indexed_columns: List[str] = []  # columns used to build index
        self._index_ready: bool = False
        self._index_min_rows = 5000  # threshold to build index

        self.date_filter_buttons: Dict[str, tk.Widget] = {}  # typed to suppress bool expectation

        # Initialize remote data loader
        self.remote_loader = RemoteDataLoader()

        # Add UI variables for remote sources
        self.remote_urls: List[str] = []

        # URL handling attributes
        self.url_columns: List[str] = []
        self.link_icons: Dict[str, tk.PhotoImage] = {}

        self._create_widgets()
        self._setup_treeview_bindings()
        self.update_dashboard() # Initial dashboard state

    def _create_widgets(self):
        # Main layout with reduced vertical padding
        top_frame = ttk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])

        # Modern dashboard with solid background
        dashboard_frame = ttk.Frame(top_frame, style='Dashboard.TFrame')
        dashboard_frame.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(0, SPACING['small']))
        self._create_dashboard_widgets(dashboard_frame)

        # Create collapsible data folders frame - COLLAPSED BY DEFAULT
        self.data_folders_frame_container = ttk.Frame(top_frame)
        self.data_folders_frame_container.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['small']))
        self.data_folders_frame_visible = False  # Changed to False for collapsed by default
        
        # Header frame with collapse button
        header_frame = ttk.Frame(self.data_folders_frame_container)
        header_frame.pack(side=tk.TOP, fill=tk.X)
        
        # More compact layout for header controls
        self.toggle_button = ttk.Button(
            header_frame, 
            text="►",  # Changed to right-pointing arrow for collapsed state
            command=self._toggle_data_folders_panel,
            style="Collapse.TButton",
            width=2
        )
        self.toggle_button.pack(side=tk.LEFT)
        
        ttk.Label(header_frame, text="Data Folders", font=FONTS.get('subheading', ('TkDefaultFont', 11, 'bold'))).pack(side=tk.LEFT, padx=SPACING['small'])
        
        # Add View Charts button in the header frame (moved from bottom)
        charts_btn = create_action_button(
            header_frame, "📊 Charts", self._show_data_visualization, 
            button_type='info_outline', width=10
        )
        if charts_btn:
            charts_btn.pack(side=tk.RIGHT)
        
        # Create the collapsible content frame - START HIDDEN
        self.data_folders_content = create_labeled_frame(self.data_folders_frame_container, "")
        # Don't pack it initially since we want it collapsed by default
        self._create_data_folder_widgets(self.data_folders_content)

        # Use PanedWindow for better space management of search and results areas
        main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, sashwidth=4, sashrelief="raised")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=SPACING['medium'], pady=(0, SPACING['small']))

        # Search and filter section with increased height to accommodate all filter buttons
        search_filter_frame = create_labeled_frame(main_pane, "Search, Filter & Dates")
        main_pane.add(search_filter_frame, height=220, minsize=180)  # Increased from 180 to 220
        self._create_search_filter_widgets(search_filter_frame)
        self._create_date_filter_widgets(search_filter_frame)

        # Results section with flexible height
        tender_data_frame = create_labeled_frame(main_pane, "Tender Data")
        main_pane.add(tender_data_frame, height=320, minsize=200)  # Slightly reduced to compensate
        self._create_tender_data_widgets(tender_data_frame)
        
        # Configure collapse button style - make it more compact
        style = ttk.Style()
        style.configure("Collapse.TButton", font=FONTS.get('subheading', ('TkDefaultFont', 11, 'bold')), padding=0)


    def _start_clock(self):
        """Start the clock that updates the date/time display using Tkinter's after method."""
        if hasattr(self, 'clock_running') and self.clock_running:
            return
            
        self.clock_running = True
        
        def update_clock():
            if not self.clock_running:
                return
                
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")
            date_str = now.strftime("%d/%m/%Y")
            
            self.current_time_var.set(time_str)
            self.current_date_var.set(date_str)
            
            # Schedule the next update in 1000ms (1 second)
            if self.clock_running:
                self.after(1000, update_clock)
        
        # Start the first update
        update_clock()

    def _create_data_folder_widgets(self, parent: Union[ttk.Frame, ttk.LabelFrame]):
        action_frame = ttk.Frame(parent)
        action_frame.pack(side=tk.LEFT, padx=(0, SPACING['medium']))

        create_action_button(action_frame, "Add Folder", self._add_folder, width=12).pack(pady=SPACING['small']//2, fill=tk.X)
        create_action_button(action_frame, "Add Cloud URL", self._add_remote_url, width=12).pack(pady=SPACING['small']//2, fill=tk.X)
        create_action_button(action_frame, "Refresh Data", self._load_data_from_folders, width=12).pack(pady=SPACING['small']//2, fill=tk.X)
        create_action_button(action_frame, "Clear All", self._clear_folders, button_type='secondary', width=12).pack(pady=SPACING['small']//2, fill=tk.X)

        selected_folders_label = create_info_label(parent, "", textvariable=self.selected_folders_var, wraplength=600, justify=tk.LEFT)
        selected_folders_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=SPACING['small'])
        self._update_selected_folders_display()

    def _load_data_from_folders(self):
        """Load data from all selected folders and remote URLs."""
        if not self.loaded_files and not self.remote_urls:
            messagebox.showinfo("No Sources", "Please add one or more data folders or remote URLs first.")
            return

        all_files = []
        
        # Load from local folders
        for folder in self.loaded_files:
            try:
                excel_files = [f for f in os.listdir(folder) if f.lower().endswith(('.xlsx', '.xls', '.csv'))]
                for file in excel_files:
                    all_files.append(os.path.join(folder, file))
            except Exception as e:
                self.logger.error(f"Error accessing folder {folder}: {e}")
        
        # Load from remote URLs
        remote_files = []
        for url_entry in self.remote_urls:
            try:
                # Parse URL and credentials
                parts = url_entry.split('||')
                url = parts[0]
                username = parts[1] if len(parts) > 1 else None
                password = parts[2] if len(parts) > 2 else None
                
                self.results_count_var.set(f"Downloading from {url}...")
                self.update_idletasks()
                
                success, message, local_file = self.remote_loader.load_from_remote_source(url, username, password)
                
                if success and local_file:
                    remote_files.append(local_file)
                    self.logger.info(f"Successfully downloaded: {message}")
                else:
                    self.logger.error(f"Failed to download from {url}: {message}")
                    messagebox.showwarning("Download Failed", f"Failed to download from {url}:\n{message}")
                    
            except Exception as e:
                self.logger.error(f"Error downloading from {url_entry}: {e}")
                messagebox.showwarning("Download Error", f"Error downloading from remote source:\n{str(e)}")
        
        # Combine local and remote files
        all_files.extend(remote_files)
        
        if not all_files:
            messagebox.showinfo("No Files", "No Excel or CSV files found in the selected sources.")
            return

        # Show loading indicator
        self.results_count_var.set("Loading data, please wait...")
        self.update_idletasks()  # Force UI update
        
        try:
            # Load data from files
            dfs = []
            for file in all_files:
                try:
                    if file.lower().endswith('.csv'):
                        df = pd.read_csv(file, encoding='utf-8', low_memory=False)
                    else:
                        df = pd.read_excel(file)
                    
                    if not df.empty:
                        # Add source file column
                        df['Source File'] = os.path.basename(file)
                        dfs.append(df)
                except Exception as e:
                    self.logger.error(f"Error loading file {file}: {e}")
            
            if not dfs:
                messagebox.showinfo("No Data", "Could not load any data from the selected files.")
                self.results_count_var.set("No data loaded")
                return
            
            # Combine all dataframes
            combined_df = pd.concat(dfs, ignore_index=True)
            
            # Store in data processor
            self.data_processor.raw_data = combined_df
            self.data_processor.filtered_data = combined_df.copy()
            
            # Update record count
            record_count = len(combined_df)
            messagebox.showinfo("Data Loaded", f"Successfully loaded {record_count} records from {len(all_files)} files.")
            
            # Refresh the display - important!
            self._refresh_tree_data()
            self.update_dashboard()
            
            # Apply default filter (live tenders)
            self._apply_status_filter("live")
        except Exception as e:
            self.logger.error(f"Error loading data: {e}", exc_info=True)
            messagebox.showerror("Error", f"An error occurred while loading data: {str(e)}")
            self.results_count_var.set("Error loading data")


    def _create_dashboard_widgets(self, parent):
        """Create dashboard widgets in a single row with solid color backgrounds."""
        # Container for all cards
        dashboard_container = ttk.Frame(parent)
        dashboard_container.pack(fill=tk.X, expand=True, pady=SPACING['small'])
        
        # Configure grid with equal column weights
        for i in range(11):  # 11 metrics
            dashboard_container.columnconfigure(i, weight=1)
        
        # Define metrics with their properties
        self.dashboard_labels = {}  # Initialize as empty dict
        metrics = [
            # key, title, color
            ("live_tenders", "Live\nTenders", "#006400"),  # Dark Green for Live
            ("expired_tenders", "Expired\nTenders", "#000000"),  # Black for Expired
            ("total_tenders", "Total\nTenders", COLORS.get('primary', '#1976d2')),
            ("filtered_tenders", "Filtered\nResults", COLORS.get('info', '#0288d1')),
            ("match_percentage", "Filter\nMatch %", COLORS.get('success', '#4caf50')),
            ("unique_departments", "Depts", COLORS.get('warning', '#ff9800')),
            ("closing_today", "Due\nToday", COLORS.get('danger', '#f44336')),
            ("closing_next_3_days", "Due in\n3 Days", COLORS.get('secondary', '#9c27b0')),
            ("closing_next_7_days", "Due in\n7 Days", COLORS.get('info_dark', '#01579b')),
            ("data_sources", "Data\nSources", COLORS.get('secondary_light', '#ba68c8')),
            ("current_date", "Date &\nTime", COLORS.get('primary_dark', '#1a237e'))
        ]
        
        # Create a card for each metric
        for i, (key, title, color) in enumerate(metrics):
            # Create card frame with solid background
            card_frame = tk.Frame(dashboard_container, bg=color, width=90, height=100)
            card_frame.grid(row=0, column=i, padx=1, sticky="nsew")
            card_frame.grid_propagate(False)  # Fix the size
            
            # Create centered content inside card
            if key == "current_date":
                # Date and time are special cases
                title_label = tk.Label(card_frame, text=title, bg=color, fg="white",
                                      font=FONTS.get('small', ('TkDefaultFont', 9, 'bold')))
                title_label.pack(anchor=tk.CENTER, pady=(10, 0))
                
                time_label = tk.Label(card_frame, textvariable=self.current_time_var, 
                                     bg=color, fg="white", font=FONTS.get('heading', ('TkDefaultFont', 16, 'bold')))
                time_label.pack(anchor=tk.CENTER, pady=(5, 0))
                
                date_label = tk.Label(card_frame, textvariable=self.current_date_var, 
                                     bg=color, fg="white", font=FONTS.get('small', ('TkDefaultFont', 9)))
                date_label.pack(anchor=tk.CENTER, pady=(0, 5))
                
                # Start clock
                self._start_clock()
            else:
                # Regular metric cards
                title_label = tk.Label(card_frame, text=title, bg=color, fg="white",
                                  font=FONTS.get('small', ('TkDefaultFont', 9, 'bold')))
                title_label.pack(anchor=tk.CENTER, pady=(10, 0))
                
                value_label = tk.Label(card_frame, text="0", bg=color, fg="white",
                                  font=FONTS.get('heading', ('TkDefaultFont', 24, 'bold')))
                value_label.pack(anchor=tk.CENTER, expand=True)
                
                # Store reference for updating later
                self.dashboard_labels[key] = value_label

        # Bottom separator line
        separator = ttk.Separator(parent, orient="horizontal")
        separator.pack(fill=tk.X, padx=SPACING['small'], pady=(0, SPACING['small']))

    def _create_search_filter_widgets(self, parent: Union[ttk.Frame, ttk.LabelFrame]):
        """Create redesigned search and filter widgets with better visual layout."""
        # Main container for all search components
        search_container = ttk.Frame(parent)
        search_container.pack(side=tk.TOP, fill=tk.X, pady=SPACING['small'])
        
        # Top Row: Side-by-side Department and Global Search with colored borders
        search_row_frame = ttk.Frame(search_container)
        search_row_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['medium']))
        
        # Left: Department Search Section
        dept_section = ttk.LabelFrame(search_row_frame, text="Department Search", 
                                     style="Primary.TLabelframe", padding=SPACING['medium'])
        dept_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, SPACING['small']))
        
        # Department input with increased height
        dept_input_frame = ttk.Frame(dept_section)
        dept_input_frame.pack(fill=tk.X, pady=(0, SPACING['small']))
        
        # Custom style for colored border
        style = ttk.Style()
        style.configure("Department.TEntry", fieldbackground="#E8F4FD", relief="solid", borderwidth=2)
        
        self.dept_entry = ttk.Entry(dept_input_frame, textvariable=self.dept_filter_var, 
                                   style="Department.TEntry", font=('TkDefaultFont', 11))
        self.dept_entry.pack(fill=tk.X, ipady=8)  # Increased height
        self.dept_entry.bind("<KeyRelease>", self._on_live_search_key)
        
        # Department operator buttons
        dept_op_frame = ttk.Frame(dept_section)
        dept_op_frame.pack(fill=tk.X, pady=(SPACING['small'], 0))
        
        ttk.Label(dept_op_frame, text="Match:", font=('TkDefaultFont', 9)).pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        ttk.Radiobutton(dept_op_frame, text="Any (OR)", variable=self.dept_operator_var, 
                       value="OR", command=self._on_live_search_key).pack(side=tk.LEFT, padx=(0, SPACING['small']))
        ttk.Radiobutton(dept_op_frame, text="All (AND)", variable=self.dept_operator_var, 
                       value="AND", command=self._on_live_search_key).pack(side=tk.LEFT)
        
        ttk.Label(dept_op_frame, text="(use commas to separate terms)", 
                 font=('TkDefaultFont', 8), foreground='gray').pack(side=tk.RIGHT)
        
        # Right: Global Search Section
        global_section = ttk.LabelFrame(search_row_frame, text="Global Search", 
                                       style="Success.TLabelframe", padding=SPACING['medium'])
        global_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(SPACING['small'], 0))
        
        # Global search input with increased height
        global_input_frame = ttk.Frame(global_section)
        global_input_frame.pack(fill=tk.X, pady=(0, SPACING['small']))
        
        style.configure("Global.TEntry", fieldbackground="#E8F8E8", relief="solid", borderwidth=2)
        
        self.global_entry = ttk.Entry(global_input_frame, textvariable=self.global_search_var, 
                                     style="Global.TEntry", font=('TkDefaultFont', 11))
        self.global_entry.pack(fill=tk.X, ipady=8)  # Increased height
        self.global_entry.bind("<KeyRelease>", self._on_live_search_key)
        
        # Global search operator buttons
        global_op_frame = ttk.Frame(global_section)
        global_op_frame.pack(fill=tk.X, pady=(SPACING['small'], 0))
        
        ttk.Label(global_op_frame, text="Match:", font=('TkDefaultFont', 9)).pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        ttk.Radiobutton(global_op_frame, text="Any (OR)", variable=self.global_operator_var, 
                       value="OR", command=self._on_live_search_key).pack(side=tk.LEFT, padx=(0, SPACING['small']))
        ttk.Radiobutton(global_op_frame, text="All (AND)", variable=self.global_operator_var, 
                       value="AND", command=self._on_live_search_key).pack(side=tk.LEFT)
        
        ttk.Label(global_op_frame, text="(use commas to separate terms)", 
                 font=('TkDefaultFont', 8), foreground='gray').pack(side=tk.RIGHT)
        
        # Configure custom LabelFrame styles
        style.configure("Primary.TLabelframe", borderwidth=2, relief="solid")
        style.configure("Primary.TLabelframe.Label", foreground="#1976d2", font=('TkDefaultFont', 10, 'bold'))
        style.configure("Success.TLabelframe", borderwidth=2, relief="solid")
        style.configure("Success.TLabelframe.Label", foreground="#4caf50", font=('TkDefaultFont', 10, 'bold'))

    def _create_date_filter_widgets(self, parent: Union[ttk.Frame, ttk.LabelFrame]):
        """Create redesigned date filter widgets in four horizontal sections with responsive layout."""
        # Main date filter container with responsive grid
        date_container = ttk.Frame(parent)
        date_container.pack(side=tk.TOP, fill=tk.X, pady=SPACING['small'])
        
        # Configure grid with four equal columns and consistent spacing
        for i in range(4):
            date_container.grid_columnconfigure(i, weight=1, minsize=180)  # Minimum width for each section
        date_container.grid_rowconfigure(0, weight=1)
        
        # Calculate dynamic spacing based on container width
        section_padding = SPACING['small']
        internal_padding = (SPACING['small'], SPACING['medium'])
        
        # Section 1: Status Filter (Column 0)
        status_section = ttk.LabelFrame(date_container, text="📊 Status Filter", 
                                       padding=internal_padding)
        status_section.grid(row=0, column=0, sticky="nsew", padx=(0, section_padding//2))
        
        # Status content with consistent height
        status_content = ttk.Frame(status_section)
        status_content.pack(fill=tk.BOTH, expand=True)
        
        status_label = ttk.Label(status_content, text="Show tenders:", font=('TkDefaultFont', 9, 'bold'))
        status_label.pack(anchor=tk.W, pady=(0, SPACING['small']//2))
        
        status_options = [
            ("All Records", "all"),
            ("Live Tenders", "live"), 
            ("Expired Tenders", "expired")
        ]
        
        for text, value in status_options:
            radio_btn = ttk.Radiobutton(status_content, text=text, variable=self.status_filter_var,
                                       value=value, command=lambda v=value: self._apply_status_filter(v))
            radio_btn.pack(anchor=tk.W, pady=1)
        
        # Section 2: Time Range Filter (Column 1)
        time_section = ttk.LabelFrame(date_container, text="📅 Time Range Filter", 
                                     padding=internal_padding)
        time_section.grid(row=0, column=1, sticky="nsew", padx=(section_padding//2, section_padding//2))
        
        # Time content with consistent height
        time_content = ttk.Frame(time_section)
        time_content.pack(fill=tk.BOTH, expand=True)
        
        quick_label = ttk.Label(time_content, text="Quick filters:", font=('TkDefaultFont', 9, 'bold'))
        quick_label.pack(anchor=tk.W, pady=(0, SPACING['small']//2))
        
        # Time filter buttons in compact 2x2 grid
        button_grid = ttk.Frame(time_content)
        button_grid.pack(fill=tk.X, expand=True)
        
        # Configure button grid for equal distribution
        button_grid.grid_columnconfigure(0, weight=1)
        button_grid.grid_columnconfigure(1, weight=1)
        
        time_presets = [
            ("Today", "today"),
            ("3 Days", "next_3_days"),
            ("7 Days", "next_7_days"), 
            ("30 Days", "next_30_days")
        ]
        
        for i, (text, preset_key) in enumerate(time_presets):
            row = i // 2
            col = i % 2
            btn = create_action_button(button_grid, text, 
                                      lambda p=preset_key: self._apply_time_filter(p),
                                      width=8, button_type='info_outline')
            if btn:
                btn.grid(row=row, column=col, padx=1, pady=1, sticky="ew")
                self.date_filter_buttons[preset_key] = btn
        
        # Reset button below the grid
        reset_btn = create_action_button(time_content, "🔄 Reset", self._reset_filters, 
                                        button_type='danger', width=12)
        if reset_btn:
            reset_btn.pack(fill=tk.X, pady=(SPACING['small']//2, 0))
        
        # Section 3: Custom Date Range (Column 2)
        custom_section = ttk.LabelFrame(date_container, text="🗓️ Custom Date Range", 
                                       padding=internal_padding)
        custom_section.grid(row=0, column=2, sticky="nsew", padx=(section_padding//2, section_padding//2))
        
        # Custom content with consistent height
        custom_content = ttk.Frame(custom_section)
        custom_content.pack(fill=tk.BOTH, expand=True)
        
        custom_label = ttk.Label(custom_content, text="Date Range:", font=('TkDefaultFont', 9, 'bold'))
        custom_label.pack(anchor=tk.W, pady=(0, SPACING['small']//2))
        
        if HAS_TKCALENDAR and DateEntry is not None:
            # Compact date picker layout
            date_row = ttk.Frame(custom_content)
            date_row.pack(fill=tk.X, pady=(0, 2))
            
            ttk.Label(date_row, text="From:", font=('TkDefaultFont', 8)).pack(side=tk.LEFT)
            self.start_date_picker = DateEntry(date_row, width=8,
                                              background=COLORS.get('primary', 'blue'),
                                              foreground='white', borderwidth=1,
                                              date_pattern='yyyy-mm-dd')
            self.start_date_picker.pack(side=tk.LEFT, padx=(2, 4))
            
            ttk.Label(date_row, text="To:", font=('TkDefaultFont', 8)).pack(side=tk.LEFT)
            self.end_date_picker = DateEntry(date_row, width=8,
                                            background=COLORS.get('primary', 'blue'),
                                            foreground='white', borderwidth=1,
                                            date_pattern='yyyy-mm-dd')
            self.end_date_picker.pack(side=tk.LEFT, padx=2)
            
            # Compact time row
            time_row = ttk.Frame(custom_content)
            time_row.pack(fill=tk.X, pady=(2, 2))
            
            ttk.Label(time_row, text="Time:", font=('TkDefaultFont', 8)).pack(side=tk.LEFT)
            
            # Start time - more compact
            ttk.Spinbox(time_row, from_=0, to=23, width=2, textvariable=self.start_hour_var, 
                       format="%02.0f").pack(side=tk.LEFT, padx=1)
            ttk.Label(time_row, text=":", font=('TkDefaultFont', 8)).pack(side=tk.LEFT)
            ttk.Spinbox(time_row, from_=0, to=59, width=2, textvariable=self.start_min_var, 
                       format="%02.0f").pack(side=tk.LEFT, padx=(0, 3))
            
            ttk.Label(time_row, text="to", font=('TkDefaultFont', 8)).pack(side=tk.LEFT, padx=1)
            
            # End time - more compact
            ttk.Spinbox(time_row, from_=0, to=23, width=2, textvariable=self.end_hour_var, 
                       format="%02.0f").pack(side=tk.LEFT, padx=1)
            ttk.Label(time_row, text=":", font=('TkDefaultFont', 8)).pack(side=tk.LEFT)
            ttk.Spinbox(time_row, from_=0, to=59, width=2, textvariable=self.end_min_var, 
                       format="%02.0f").pack(side=tk.LEFT)
            
            # Apply button
            go_btn = create_action_button(custom_content, "Apply", 
                                         self._apply_custom_date_filter,
                                         button_type='primary', width=10)
            if go_btn:
                go_btn.pack(fill=tk.X, pady=(SPACING['small']//2, 0))
        else:
            # Fallback text entries - also compact
            date_inputs = ttk.Frame(custom_content)
            date_inputs.pack(fill=tk.X, pady=(0, 2))
            
            ttk.Label(date_inputs, text="From:", font=('TkDefaultFont', 8)).pack(anchor=tk.W)
            self.start_date_entry = ttk.Entry(date_inputs, textvariable=self.custom_date_start_var, width=12)
            self.start_date_entry.pack(fill=tk.X, pady=1)
            
            ttk.Label(date_inputs, text="To:", font=('TkDefaultFont', 8)).pack(anchor=tk.W)
            self.end_date_entry = ttk.Entry(date_inputs, textvariable=self.custom_date_end_var, width=12)
            self.end_date_entry.pack(fill=tk.X, pady=1)
            
            go_btn = create_action_button(custom_content, "Apply", 
                                         self._apply_custom_date_filter_text,
                                         button_type='primary', width=10)
            if go_btn:
                go_btn.pack(fill=tk.X, pady=(SPACING['small']//2, 0))
        
        # Section 4: Saved Searches (Column 3)
        saved_section = ttk.LabelFrame(date_container, text="💾 Saved Searches", 
                                      padding=internal_padding)
        saved_section.grid(row=0, column=3, sticky="nsew", padx=(section_padding//2, 0))
        
        # Saved content with consistent height
        saved_content = ttk.Frame(saved_section)
        saved_content.pack(fill=tk.BOTH, expand=True)
        
        saved_label = ttk.Label(saved_content, text="Searches:", font=('TkDefaultFont', 9, 'bold'))
        saved_label.pack(anchor=tk.W, pady=(0, SPACING['small']//2))
        
        # Compact combobox
        self.saved_searches_combo = ttk.Combobox(saved_content, textvariable=self.saved_search_var, 
                                                width=12, state="readonly", font=('TkDefaultFont', 8))
        self.saved_searches_combo.pack(fill=tk.X, pady=(0, SPACING['small']//2))
        self.saved_searches_combo.bind("<<ComboboxSelected>>", self._load_saved_search)
        
        # Compact 2x3 button grid
        buttons_container = ttk.Frame(saved_content)
        buttons_container.pack(fill=tk.X, expand=True)
        
        # Configure button grid for equal distribution
        for i in range(3):
            buttons_container.grid_columnconfigure(i, weight=1)
        
        # Button definitions with shorter labels for space
        button_configs = [
            # Row 0
            ("Load", self._load_saved_search, 'info_outline'),
            ("Save", self._save_current_search, 'success_outline'),
            ("Del", self._delete_saved_search, 'danger_outline'),
            # Row 1
            ("Export", self._export_saved_searches, 'secondary'),
            ("Import", self._import_saved_searches, 'secondary'),
            ("Clean", self._clean_corrupted_searches, 'warning')
        ]
        
        for i, (text, command, btn_type) in enumerate(button_configs):
            row = i // 3
            col = i % 3
            btn = create_action_button(buttons_container, text, command, 
                                     width=5, button_type=btn_type)
            if btn:
                btn.grid(row=row, column=col, padx=1, pady=1, sticky="ew")
        
        # Update saved searches list
        self._update_saved_searches_list()
        
        # Apply default Live filter
        self._apply_status_filter("live")

    def _create_link_icon(self):
        """Create a link icon image for URL display."""
        if not HAS_PIL or Image is None or ImageDraw is None or ImageTk is None:
            # Return None if PIL is not available - will use text fallback
            return None

        try:
            # Create a simple link icon (chain link)
            size = (16, 16)
            image = Image.new('RGBA', size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(image)

            # Draw a simple chain link
            # Left loop
            draw.arc([2, 2, 10, 10], 45, 315, fill='#1976d2', width=2)
            # Right loop
            draw.arc([6, 6, 14, 14], 225, 135, fill='#1976d2', width=2)
            # Connecting lines
            draw.line([6, 4, 10, 8], fill='#1976d2', width=2)
            draw.line([10, 4, 6, 8], fill='#1976d2', width=2)

            # Convert to PhotoImage
            return ImageTk.PhotoImage(image)
        except Exception as e:
            self.logger.error(f"Error creating link icon: {e}")
            return None

    def _detect_url_columns(self, df):
        """Detect columns that contain URLs."""
        if df is None or df.empty or not hasattr(df, 'columns'):
            return []

        url_columns = []
        url_keywords = ['url', 'link', 'website', 'site', 'http', 'web']

        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in url_keywords):
                url_columns.append(col)

        self.logger.info(f"Detected URL columns: {url_columns}")
        return url_columns

    def _refresh_tree_data(self):
        """Refresh the treeview with current filtered data."""
        if self.tree is None:
            return

        # Clear existing data - add null check for get_children()
        try:
            children = self.tree.get_children()
            if children:  # Only iterate if children exist
                for item in children:
                    self.tree.delete(item)
        except Exception as e:
            self.logger.error(f"Error clearing tree data: {e}")
            return

        # Check if data exists
        if (not hasattr(self.data_processor, 'filtered_data') or
            self.data_processor.filtered_data is None or
            self.data_processor.filtered_data.empty):
            self.results_count_var.set("No data to display")
            return

        df = self.data_processor.filtered_data

        # Detect URL columns
        self.url_columns = self._detect_url_columns(df)

        # Create link icon if needed
        if self.url_columns and not hasattr(self, 'link_icon'):
            self.link_icon = self._create_link_icon()

        # Configure columns - add safety check
        try:
            cols = df.columns.tolist() if hasattr(df, 'columns') and df.columns is not None else []
            if not cols:
                self.results_count_var.set("No columns to display")
                return

            self.tree["columns"] = cols

            for col in cols:
                width = 100
                anchor = 'w'  # Default left alignment

                if col in self.url_columns:
                    # URL columns can be narrower since we'll show an icon
                    width = 80
                    anchor = 'center'  # Center align URLs
                elif any(kw in col.lower() for kw in ['title', 'description', 'summary']):
                    width = 300
                elif any(kw in col.lower() for kw in ['department', 'ministry', 'agency']):
                    width = 200
                elif any(kw in col.lower() for kw in ['date', 'time', 'closing', 'close', 'due', 'deadline', 'end']):
                    width = 120
                    anchor = 'center'  # Center align dates

                self.tree.column(col, width=width, minwidth=50, anchor=anchor)

                # Add sorting functionality to column headers
                sort_indicator = " ▲" if col == self.sort_column and self.sort_ascending else " ▼" if col == self.sort_column else ""
                self.tree.heading(col, text=col + sort_indicator, command=lambda c=col: self._sort_by_column(c))

            # Insert data rows - limit for performance
            max_rows = 1000
            display_df = df.head(max_rows) if len(df) > max_rows else df

            for row_index, (_, row) in enumerate(display_df.iterrows()):
                try:
                    values = []
                    tags = []

                    for i, col in enumerate(cols):
                        val = row[col]
                        display_val = str(val) if pd.notna(val) else ""

                        # Handle URL columns
                        if col in self.url_columns and display_val:
                            if display_val.startswith(('http://', 'https://', 'www.')):
                                # Store URL in tags for double-click functionality
                                tags.append(f"url_{i}_{val}")
                                # Show chain link icon instead of text
                                if hasattr(self, 'link_icon') and self.link_icon:
                                    display_val = ""  # Empty text, will show icon
                                    # Note: Tkinter Treeview doesn't directly support images in cells
                                    # We'll use a text representation that looks like a link
                                    display_val = "🔗"  # Chain link emoji as visual indicator
                                else:
                                    # Fallback: show shortened URL
                                    if len(display_val) > 25:
                                        display_val = display_val[:22] + "..."
                            else:
                                tags.append(f"url_{i}_{display_val}")

                        values.append(display_val)

                    # Insert row with tags and alternate row coloring
                    item_id = self.tree.insert("", "end", values=values)

                    # Apply alternate row coloring using tags
                    if row_index % 2 == 0:
                        tags.append('evenrow')
                    else:
                        tags.append('oddrow')

                    if tags:
                        self.tree.item(item_id, tags=tags)

                except Exception as e:
                    self.logger.error(f"Error inserting row: {e}")
                    continue

            total_records = len(df)
            if total_records > max_rows:
                self.results_count_var.set(f"Showing first {max_rows} of {total_records} records (limit for performance)")
            else:
                self.results_count_var.set(f"Showing all {total_records} records")

        except Exception as e:
            self.logger.error(f"Error refreshing tree data: {e}")
            self.results_count_var.set("Error displaying data")

    def update_dashboard(self):
        """Update the dashboard metrics."""
        if not hasattr(self, 'dashboard_labels') or not self.dashboard_labels:
            return
        
        try:
            # Default values
            metrics = {
                "total_tenders": 0,
                "live_tenders": 0,
                "expired_tenders": 0,
                "filtered_tenders": 0,
                "match_percentage": "0%",
                "unique_departments": 0,
                "closing_today": 0,
                "closing_next_3_days": 0,
                "closing_next_7_days": 0,
                "data_sources": 0
            }
            
            # Calculate metrics if data is available
            if (hasattr(self.data_processor, 'raw_data') and 
                self.data_processor.raw_data is not None and 
                not self.data_processor.raw_data.empty):
                
                raw_data = self.data_processor.raw_data
                metrics["total_tenders"] = len(raw_data)
                
                # Safe column access
                if hasattr(raw_data, 'columns') and raw_data.columns is not None:
                    # Department metrics
                    dept_cols = [col for col in raw_data.columns 
                               if any(kw in col.lower() for kw in ['department', 'dept', 'agency', 'organisation'])]
                    if dept_cols:
                        try:
                            metrics["unique_departments"] = raw_data[dept_cols[0]].nunique()
                        except Exception:
                            metrics["unique_departments"] = 0
            # Filtered data metrics
            if (hasattr(self.data_processor, 'filtered_data') and 
                self.data_processor.filtered_data is not None and 
                not self.data_processor.filtered_data.empty):
                
                filtered_data = self.data_processor.filtered_data
                metrics["filtered_tenders"] = len(filtered_data)
                
                # Calculate match percentage
                if metrics["total_tenders"] > 0:
                    match_pct = (len(filtered_data) / metrics["total_tenders"]) * 100
                    metrics["match_percentage"] = f"{match_pct:.1f}%"
            
            # Data sources count
            metrics["data_sources"] = len(self.loaded_files) + len(self.remote_urls)
            
            # Update dashboard labels safely
            for key, value in metrics.items():
                if key in self.dashboard_labels and self.dashboard_labels[key] is not None:
                    try:
                        self.dashboard_labels[key].configure(text=str(value))
                    except Exception as e:
                        self.logger.error(f"Error updating dashboard label {key}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error updating dashboard: {e}")

    def _apply_custom_date_range_filter(self, start_datetime, end_datetime):
        """Apply a date range filter to the data."""
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "No data available to filter.")
            return
        
        self.current_date_filter = {
            'type': 'custom_date_range',
            'start_date': start_datetime,
            'end_date': end_datetime
        }
        
        self._clear_time_filter_selection()
        
        self.data_processor.filtered_data = self.data_processor.raw_data.copy()
        
        date_cols = [col for col in self.data_processor.filtered_data.columns 
                    if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]
        
        if not date_cols:
            messagebox.showinfo("Date Column Not Found", "Could not find a suitable date column to filter.")
            return
        
        date_col = date_cols[0]
        
        try:
            if not pd.api.types.is_datetime64_dtype(self.data_processor.filtered_data[date_col]):
                self.data_processor.filtered_data[date_col] = pd.to_datetime(
                    self.data_processor.filtered_data[date_col], errors='coerce')
        except Exception as e:
            self.logger.error(f"Error converting date column: {e}")
            messagebox.showerror("Date Conversion Error", f"Could not convert dates: {str(e)}")
            return
        
        try:
            start_ts = pd.Timestamp(start_datetime)
            end_ts = pd.Timestamp(end_datetime)
            
            mask = (
                (self.data_processor.filtered_data[date_col] >= start_ts) & 
                (self.data_processor.filtered_data[date_col] <= end_ts)
            )
            
            self.data_processor.filtered_data = self.data_processor.filtered_data[mask]
            
            self._refresh_tree_data()
            self.update_dashboard()
            
            record_count = len(self.data_processor.filtered_data)
            self.logger.info(f"Applied custom date range filter: {start_datetime} to {end_datetime}, {record_count} records matching")
            
        except Exception as e:
            self.logger.error(f"Error applying date range filter: {e}")
            messagebox.showerror("Filter Error", f"Error filtering by date: {str(e)}")

    def _on_live_search_key(self, event=None):
        """Handle key press in search fields with debouncing to avoid excessive filtering."""
        if hasattr(self, '_filter_after_id') and self._filter_after_id:
            self.after_cancel(self._filter_after_id)
        self._filter_after_id = self.after(self.filter_delay_ms, self._apply_filters)

    def _apply_filters(self):
        """Apply all filters to the dataset."""
        if (not hasattr(self.data_processor, 'raw_data') or
            self.data_processor.raw_data is None or
            self.data_processor.raw_data.empty):
            return

        # Start with raw data
        df = self.data_processor.raw_data.copy()
        
        # Apply status filter first (live/expired/all)
        current_status = getattr(self, 'status_filter_var', tk.StringVar()).get()
        if current_status == "live":
            df = self._apply_live_filter_to_df(df)
        elif current_status == "expired":
            df = self._apply_expired_filter_to_df(df)
        # For "all", no status filtering needed

        # Apply department filter
        dept_filter = self.dept_filter_var.get().strip()
        if dept_filter:
            df = self._apply_department_filter_to_df(df, dept_filter)

        # Apply global search filter
        global_search = self.global_search_var.get().strip()
        if global_search:
            df = self._apply_global_search_to_df(df, global_search)

        # Apply any time range filters if active
        if hasattr(self, 'current_date_filter') and self.current_date_filter:
            time_range = self.current_date_filter.get('time_range', '')
            if time_range:
                df = self._apply_time_range_to_df(df, time_range, current_status)

        # Update filtered data - ensure df is not None before assignment
        if df is not None:
            self.data_processor.filtered_data = df
        
        # Refresh display
        self._refresh_tree_data()
        self.update_dashboard()

    def _apply_time_filter(self, preset):
        """Apply a time-based filter preset."""
        self.logger.info(f"Applying time filter: {preset}")
        
        # Get current status
        current_status = self.status_filter_var.get()
        
        # Set filter state
        self.active_date_filter = f"{current_status}_{preset}"
        self.current_date_filter = {
            'type': 'combined',
            'status': current_status,
            'time_range': preset
        }
        
        # Update UI - reset all time filter buttons
        self._clear_time_filter_selection()
        
        # Highlight the selected time filter button
        if preset in self.date_filter_buttons:
            btn = self.date_filter_buttons[preset]
            if isinstance(btn, ttk.Button):
                if hasattr(btn, 'state'):
                    btn.state(['pressed'])
            elif isinstance(btn, tk.Button):
                if hasattr(btn, 'configure'):
                    btn['background'] = "#006400"
                    btn['foreground'] = "white"
        
        # Apply the filter
        self._apply_filters()

    def _sort_by_column(self, col):
        """Sort the treeview data by the specified column."""
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data is None or self.data_processor.filtered_data.empty:
            return

        try:
            # Toggle sort direction if same column clicked
            if self.sort_column == col:
                self.sort_ascending = not self.sort_ascending
            else:
                self.sort_column = col
                self.sort_ascending = True

            # Sort the dataframe
            df = self.data_processor.filtered_data.copy()

            # Handle different data types for sorting
            if col in df.columns:
                try:
                    # Try to sort as numeric first
                    if df[col].dtype in ['int64', 'float64']:
                        df = df.sort_values(col, ascending=self.sort_ascending, na_position='last')
                    else:
                        # Try to convert to datetime for date columns
                        if any(kw in col.lower() for kw in ['date', 'time', 'closing', 'close', 'due', 'deadline', 'end']):
                            try:
                                temp_col = pd.to_datetime(df[col], errors='coerce')
                                df = df.assign(**{f'__sort_{col}': temp_col})
                                df = df.sort_values(f'__sort_{col}', ascending=self.sort_ascending, na_position='last')
                                df = df.drop(columns=[f'__sort_{col}'])
                            except:
                                # Fall back to string sorting
                                df = df.sort_values(col, ascending=self.sort_ascending, na_position='last', key=lambda x: x.astype(str))
                        else:
                            # String sorting for other columns
                            df = df.sort_values(col, ascending=self.sort_ascending, na_position='last', key=lambda x: x.astype(str).str.lower())
                except Exception as e:
                    self.logger.warning(f"Error sorting column {col}: {e}")
                    # Fallback to simple sort
                    df = df.sort_values(col, ascending=self.sort_ascending, na_position='last')

            # Update the filtered data
            self.data_processor.filtered_data = df

            # Refresh the display
            self._refresh_tree_data()

            self.logger.info(f"Sorted by column '{col}' ({'ascending' if self.sort_ascending else 'descending'})")

        except Exception as e:
            self.logger.error(f"Error sorting by column {col}: {e}")

    def _setup_treeview_bindings(self):
        """Bind treeview events."""
        if hasattr(self, 'tree') and self.tree:
            self.tree.bind("<Double-1>", self._on_row_double_click)
            self.tree.bind("<Button-3>", self._show_context_menu)

    def _create_context_menu(self):
        """Create context menu for treeview."""
        menu = tk.Menu(self, tearoff=0)

        # Get current selection
        if not self.tree or not self.tree.selection():
            return menu

        item_id = self.tree.selection()[0]
        values = self.tree.item(item_id, "values") or []

        # Copy options
        menu.add_command(label="Copy Row", command=lambda: self._copy_row(item_id))
        menu.add_command(label="Copy Cell", command=lambda: self._copy_cell(item_id))
        menu.add_separator()

        # Show details
        menu.add_command(label="Show Details", command=lambda: self._show_row_details(item_id))

        # Add to calendar option (if applicable)
        if self._can_add_to_calendar(values):
            menu.add_separator()
            menu.add_command(label="Add to Calendar", command=lambda: self._add_to_calendar(item_id))

        return menu

    def _export_to_excel(self):
        """Export the current filtered data to Excel."""
        if not hasattr(self, 'data_processor') or self.data_processor is None:
            messagebox.showerror("Export Error", "No data available to export.")
            return
        
        try:
            # Get the filtered data
            df = self.data_processor.filtered_data
            
            if df is None or df.empty:
                messagebox.showerror("Export Error", "No data available to export.")
                return
            
            # Ask for file save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
                title="Export to Excel"
            )
            
            if not file_path:
                return  # User canceled
            
            # Export to Excel
            df.to_excel(file_path, index=False)
            
            messagebox.showinfo("Export Successful", f"Data exported to Excel successfully:\n{file_path}")
            self.logger.info(f"Data exported to Excel: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting to Excel: {e}")
            messagebox.showerror("Export Error", f"Failed to export to Excel: {str(e)}")

    def _export_to_csv(self):
        """Export the current filtered data to CSV."""
        if not hasattr(self, 'data_processor') or self.data_processor is None:
            messagebox.showerror("Export Error", "No data available to export.")
            return
        
        try:
            # Get the filtered data
            df = self.data_processor.filtered_data
            
            if df is None or df.empty:
                messagebox.showerror("Export Error", "No data available to export.")
                return
            
            # Ask for file save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                title="Export to CSV"
            )
            
            if not file_path:
                return  # User canceled
            
            # Export to CSV
            df.to_csv(file_path, index=False, encoding='utf-8')
            
            messagebox.showinfo("Export Successful", f"Data exported to CSV successfully:\n{file_path}")
            self.logger.info(f"Data exported to CSV: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            messagebox.showerror("Export Error", f"Failed to export to CSV: {str(e)}")

    def _on_row_double_click(self, event):
        """Handle double-click on a treeview row to show details or open URLs."""
        try:
            if not self.tree:
                return

            # Get the clicked item and column
            item = self.tree.identify_row(event.y)
            if not item:
                return

            column = self.tree.identify_column(event.x)
            if not column:
                return

            # Extract column index from column identifier (e.g., '#1' -> 0)
            try:
                col_index = int(column[1:]) - 1  # #1 -> 0, #2 -> 1, etc.
            except (ValueError, IndexError):
                col_index = -1

            # Get column names to check if this is a URL column
            columns = self.tree['columns']
            if col_index >= 0 and col_index < len(columns):
                col_name = columns[col_index]

                # Check if this column is a URL column
                if col_name in self.url_columns:
                    # Get the tags for this item
                    tags = self.tree.item(item, 'tags') or []

                    # Look for URL tag for this column
                    url = None
                    for tag in tags:
                        if isinstance(tag, str) and tag.startswith(f"url_{col_index}_"):
                            url = tag[len(f"url_{col_index}_"):]
                            break

                    # If we found a URL, open it
                    if url and url.startswith(('http://', 'https://', 'www.')):
                        try:
                            # Ensure it has http/https prefix
                            if url.startswith('www.'):
                                url = 'http://' + url

                            webbrowser.open_new_tab(url)
                            self.logger.info(f"Opened URL: {url}")
                            return  # Don't show details window
                        except Exception as e:
                            self.logger.error(f"Failed to open URL {url}: {e}")
                            messagebox.showerror("Open URL Failed", f"Could not open URL: {url}\nError: {e}")
                            return

            # Default behavior: show row details
            if self.tree.selection():
                item = self.tree.selection()[0]
                self._show_row_details(item)

        except Exception as e:
            self.logger.error(f"Error on row double click: {e}")

    def _show_context_menu(self, event):
        """Show context menu on right-click in treeview."""
        try:
            if self.tree:
                item = self.tree.identify_row(event.y)
                if item:
                    self.tree.selection_set(item)
                    
                    # Show the context menu
                    menu = self._create_context_menu()
                    menu.post(event.x_root, event.y_root)
        except Exception as e:
            self.logger.error(f"Error showing context menu: {e}")

    def _copy_row(self, item_id):
        """Copy the selected row's data to clipboard."""
        try:
            if self.tree:
                values = self.tree.item(item_id, "values")
                if values:
                    # Create a tab-separated string
                    data = "\t".join(str(v) for v in values)

                    # Copy to clipboard
                    self.clipboard_clear()
                    self.clipboard_append(data)

                    messagebox.showinfo("Copy Successful", "Row data copied to clipboard.")
        except Exception as e:
            self.logger.error(f"Error copying row data: {e}")

    def _copy_cell(self, item_id):
        """Copy the selected cell's data to clipboard."""
        try:
            if self.tree and self.tree.selection():
                # Get the focused cell
                focused = self.tree.focus()
                if focused:
                    # Get column and item
                    column = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
                    if column:
                        col_index = int(column[1:]) - 1  # #1 -> 0, #2 -> 1, etc.
                        values = self.tree.item(item_id, "values")
                        if values and 0 <= col_index < len(values):
                            cell_value = str(values[col_index])

                            # Copy to clipboard
                            self.clipboard_clear()
                            self.clipboard_append(cell_value)

                            messagebox.showinfo("Copy Successful", f"Cell data copied to clipboard:\n{cell_value}")
        except Exception as e:
            self.logger.error(f"Error copying cell data: {e}")

    def _can_add_to_calendar(self, values):
        """Check if the selected row can be added to calendar."""
        # Check if we have date/time information
        if not values:
            return False

        # Look for date/time columns in the data
        try:
            if hasattr(self.data_processor, 'filtered_data') and not self.data_processor.filtered_data.empty:
                df = self.data_processor.filtered_data
                # Check if any date-related columns exist
                date_cols = [col for col in df.columns
                           if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end', 'date', 'time'])]
                return len(date_cols) > 0
        except Exception:
            pass

        return False

    def _add_to_calendar(self, item_id):
        """Add the selected tender to calendar."""
        try:
            messagebox.showinfo("Calendar Integration", "Calendar integration is under development.\n\nThis feature will allow adding tender deadlines to your calendar application.")
        except Exception as e:
            self.logger.error(f"Error adding to calendar: {e}")

    def _show_row_details(self, item_id):
        """Show detailed information about the selected row in a new window."""
        try:
            if self.tree:
                values = self.tree.item(item_id, "values")
                if not values:
                    return
                
                # Create a new top-level window
                details_window = tk.Toplevel(self)
                details_window.title("Row Details")
                details_window.geometry("600x400")
                
                # Add a close button
                close_button = ttk.Button(details_window, text="Close", command=details_window.destroy)
                close_button.pack(side=tk.BOTTOM, pady=10)
                
                # Create a text widget to display the details
                text = tk.Text(details_window, wrap=tk.WORD)
                text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # Insert the data into the text widget
                for value in values:
                    text.insert(tk.END, str(value) + "\n")
                
                # Make the text widget read-only
                text.config(state=tk.DISABLED)
                
        except Exception as e:
            self.logger.error(f"Error showing row details: {e}")

    def _create_tender_data_widgets(self, tender_data_frame):
        """Create the widgets for displaying and interacting with tender data."""
        # Status bar at top
        status_frame = ttk.Frame(tender_data_frame)
        status_frame.pack(fill=tk.X, padx=SPACING['small'], pady=(SPACING['small'], 0))
        
        # Results count label
        results_label = ttk.Label(status_frame, textvariable=self.results_count_var)
        results_label.pack(side=tk.LEFT)
        
        # Export buttons
        export_frame = ttk.Frame(status_frame)
        export_frame.pack(side=tk.RIGHT)
        
        create_action_button(export_frame, "Export Excel", self._export_to_excel, 
                           button_type='success_outline', width=12).pack(side=tk.LEFT, padx=(0, SPACING['small']))
        create_action_button(export_frame, "Export CSV", self._export_to_csv, 
                           button_type='info_outline', width=12).pack(side=tk.LEFT)
        
        # Create frame for treeview and scrollbars
        tree_frame = ttk.Frame(tender_data_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['small'], pady=SPACING['small'])
        
        # Treeview for displaying tender data
        self.tree = ttk.Treeview(tree_frame, show="headings")

        # Configure tags for alternate row colors
        self.tree.tag_configure('evenrow', background='#ffffff')  # White for even rows
        self.tree.tag_configure('oddrow', background='#f8f9fa')   # Light gray for odd rows
        self.tree.tag_configure('selected', background='#0078d4', foreground='white')  # Selection color
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Horizontal scrollbar frame
        hsb_frame = ttk.Frame(tender_data_frame)
        hsb_frame.pack(fill=tk.X, padx=SPACING['small'])
        
        hsb = ttk.Scrollbar(hsb_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(fill=tk.X)
        self.tree.configure(xscrollcommand=hsb.set)

    def _apply_status_filter(self, status):
        """Apply status-based filter (all, live, expired)."""
        self.logger.info(f"Applying status filter: {status}")
        
        self.active_date_filter = status
        self.current_date_filter = {
            'type': status
        }
        
        # Apply the filters
        self._apply_filters()

    def _toggle_data_folders_panel(self):
        """Toggle visibility of data folders panel."""
        if getattr(self, 'data_folders_frame_visible', False):
            self.data_folders_content.pack_forget()
            self.toggle_button.config(text="►")
        else:
            self.data_folders_content.pack(side=tk.TOP, fill=tk.X)
            self.toggle_button.config(text="▼")
        self.data_folders_frame_visible = not getattr(self, 'data_folders_frame_visible', False)

    def _show_data_visualization(self):
        """Placeholder for charts."""
        messagebox.showinfo("Charts", "Chart functionality is under development.")

    def _add_folder(self):
        """Add a folder to the list."""
        folder = filedialog.askdirectory(title="Select Data Folder")
        if folder and folder not in self.loaded_files:
            self.loaded_files.append(folder)
        self._update_selected_folders_display()

    def _add_remote_url(self):
        """Add a remote URL data source."""
        dialog = RemoteUrlDialog(self, self.remote_loader)
        self.wait_window(dialog)
        
        if dialog.result:
            url, username, password = dialog.result
            if username and password:
                url_with_auth = f"{url}||{username}||{password}"
            else:
                url_with_auth = url
            
            if url_with_auth not in self.remote_urls:
                self.remote_urls.append(url_with_auth)
                self._update_selected_folders_display()
                messagebox.showinfo("URL Added", f"Remote URL added successfully:\n{url}")

    def _load_merged_file_from_path(self, file_path):
        """Load a single merged file directly into the tree view for analysis using a provided file path."""
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path is invalid or file does not exist: {file_path}")
            return

        # Show loading indicator
        self.results_count_var.set("Loading merged file, please wait...")
        self.update_idletasks()  # Force UI update

        try:
            # Load the file
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
            else:
                df = pd.read_excel(file_path, engine='openpyxl')

            if df.empty:
                messagebox.showinfo("Empty File", "The selected file is empty or could not be loaded.")
                self.results_count_var.set("No data loaded")
                return

            # Store in data processor
            self.data_processor.raw_data = df
            self.data_processor.filtered_data = df.copy()

            # Clear any existing folder/remote sources since we're loading a direct file
            self.loaded_files = []
            self.remote_urls = []
            self._update_selected_folders_display()

            # Update record count
            record_count = len(df)
            messagebox.showinfo("Merged File Loaded",
                              f"Successfully loaded merged file for analysis:\n{os.path.basename(file_path)}\n\n"
                              f"Records: {record_count}")

            # Refresh the display
            self._refresh_tree_data()
            self.update_dashboard()

            # Apply default filter (live tenders)
            self._apply_status_filter("live")

            self.logger.info(f"Loaded merged file for analysis: {file_path} ({record_count} records)")

        except Exception as e:
            self.logger.error(f"Error loading merged file: {e}", exc_info=True)
            messagebox.showerror("Error", f"An error occurred while loading the merged file:\n{str(e)}")
            self.results_count_var.set("Error loading merged file")

    def _load_merged_file(self):
        """Load a single merged file directly into the tree view for analysis."""
        # Ask user to select a merged file
        file_path = filedialog.askopenfilename(
            title="Select Merged File for Analysis",
            filetypes=[
                ("Excel Files", "*.xlsx"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ],
            initialdir="data/merged_data"  # Default to merged data folder
        )

        if not file_path:
            return  # User canceled

        # Use the path-based method
        self._load_merged_file_from_path(file_path)

    def _clear_folders(self):
        """Clear selected folders and remote URLs."""
        self.loaded_files = []
        self.remote_urls = []
        if hasattr(self, 'remote_loader'):
            self.remote_loader.cleanup_temp_files()
        self._update_selected_folders_display()

    def _update_selected_folders_display(self):
        """Update label with selected folders and remote URLs."""
        sources = []
        
        if self.loaded_files:
            sources.extend([f"📁 {folder}" for folder in self.loaded_files])
        
        if self.remote_urls:
            for url_entry in self.remote_urls:
                url = url_entry.split('||')[0]
                sources.append(f"🌐 {url}")
        
        if sources:
            text = "\n".join(sources)
        else:
            text = "No data sources selected."
        
        self.selected_folders_var.set(text)

    def _update_saved_searches_list(self):
        """Update the saved searches dropdown list."""
        if not hasattr(self, 'saved_searches_combo'):
            return
        
        saved_searches_list = self.main_app.global_config.get("saved_searches", [])
        self.saved_searches_combo['values'] = saved_searches_list

    def _clear_time_filter_selection(self):
        """Clear the visual selection of time filter buttons."""
        for key in ["today", "next_3_days", "next_7_days", "next_30_days"]:
            if key in self.date_filter_buttons:
                btn = self.date_filter_buttons[key]
                if isinstance(btn, ttk.Button):
                    if hasattr(btn, 'state'):
                        btn.state(['!pressed'])
                elif isinstance(btn, tk.Button):
                    if hasattr(btn, 'configure'):
                        btn['background'] = "#f0f0f0"
                        btn['foreground'] = "black"

    def _reset_filters(self):
        """Reset all filters to their default state."""
        self.dept_filter_var.set("")
        self.global_search_var.set("")
        self.dept_operator_var.set("OR")
        self.global_operator_var.set("AND")
        self.status_filter_var.set("live")
        self.current_date_filter = {}
        self.active_date_filter = "live"
        self._clear_time_filter_selection()
        
        if hasattr(self, 'custom_date_start_var'):
            self.custom_date_start_var.set("")
        if hasattr(self, 'custom_date_end_var'):
            self.custom_date_end_var.set("")
        
        self.start_hour_var.set("00")
        self.start_min_var.set("00")
        self.end_hour_var.set("23")
        self.end_min_var.set("59")
        
        self._apply_status_filter("live")

    def _apply_custom_date_filter(self):
        """Apply a custom date filter using the calendar date pickers."""
        try:
            start_date = self.start_date_picker.get_date()
            end_date = self.end_date_picker.get_date()
            
            try:
                start_hour = int(self.start_hour_var.get())
                start_min = int(self.start_min_var.get())
                end_hour = int(self.end_hour_var.get())
                end_min = int(self.end_min_var.get())
            except ValueError:
                start_hour, start_min = 0, 0
                end_hour, end_min = 23, 59
            
            start_datetime = datetime.combine(start_date, time(start_hour, start_min))
            end_datetime = datetime.combine(end_date, time(end_hour, end_min))
            
            self._apply_custom_date_range_filter(start_datetime, end_datetime)
            
        except Exception as e:
            self.logger.error(f"Error applying custom date filter: {e}")
            messagebox.showerror("Date Filter Error", f"Error applying date filter: {str(e)}")

    def _apply_custom_date_filter_text(self):
        """Apply a custom date filter using text entry fields."""
        try:
            start_date_str = self.custom_date_start_var.get().strip()
            end_date_str = self.custom_date_end_var.get().strip()
            
            if not start_date_str or not end_date_str:
                messagebox.showwarning("Missing Dates", "Please enter both start and end dates.")
                return
            
            try:
                start_hour = int(self.start_hour_var.get())
                start_min = int(self.start_min_var.get())
                end_hour = int(self.end_hour_var.get())
                end_min = int(self.end_min_var.get())
            except ValueError:
                start_hour, start_min = 0, 0
                end_hour, end_min = 23, 59
            
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Invalid Date Format", "Please use YYYY-MM-DD format for dates.")
                return
            
            start_datetime = datetime.combine(start_date, time(start_hour, start_min))
            end_datetime = datetime.combine(end_date, time(end_hour, end_min))
            
            self._apply_custom_date_range_filter(start_datetime, end_datetime)
            
        except Exception as e:
            self.logger.error(f"Error applying custom date filter: {e}")
            messagebox.showerror("Date Filter Error", f"Error applying date filter: {str(e)}")

    def _apply_department_filter_to_df(self, df, dept_filter):
        """Apply department filter to a dataframe."""
        if df is None or df.empty or not dept_filter:
            return df
            
        # Parse comma-separated terms
        terms = [t.strip() for t in dept_filter.split(',') if t.strip()]
        if not terms:
            return df
            
        # Find department columns - ensure df.columns exists and is iterable
        if not hasattr(df, 'columns') or df.columns is None:
            return df
            
        dept_cols = [c for c in df.columns
                     if any(kw in c.lower() for kw in ['department', 'dept', 'agency', 'organisation', 'ministry'])]
        
        if not dept_cols:
            self.logger.warning("No department columns found for filtering")
            return df
            
        operator = getattr(self, 'dept_operator_var', tk.StringVar(value="OR")).get()
        
        # Build the filter mask
        overall_mask = None
        
        for term in terms:
            term_mask = None
            # Search across all department columns for this term
            for col in dept_cols:
                try:
                    col_mask = df[col].astype(str).str.contains(term, case=False, na=False, regex=False)
                    term_mask = col_mask if term_mask is None else (term_mask | col_mask)
                except Exception as e:
                    self.logger.error(f"Error filtering department column {col}: {e}")
                    continue
            
            if term_mask is not None:
                if overall_mask is None:
                    overall_mask = term_mask
                elif operator == "AND":
                    overall_mask = overall_mask & term_mask
                else:  # OR
                    overall_mask = overall_mask | term_mask
        
        if overall_mask is not None:
            try:
                df = df[overall_mask]
                self.logger.info(f"Department filter applied: {len(df)} records match '{dept_filter}' with {operator} logic")
            except Exception as e:
                self.logger.error(f"Error applying department filter: {e}")
        
        return df

    def _apply_global_search_to_df(self, df, global_search):
        """Apply global search filter to a dataframe."""
        if df is None or df.empty or not global_search:
            return df
            
        # Parse comma-separated terms
        terms = [t.strip() for t in global_search.split(',') if t.strip()]
        if not terms:
            return df
            
        # Ensure df.columns exists and is iterable
        if not hasattr(df, 'columns') or df.columns is None:
            return df
            
        operator = getattr(self, 'global_operator_var', tk.StringVar(value="AND")).get()
        
        # Build the filter mask
        overall_mask = None
        
        for term in terms:
            term_mask = None
            # Search across ALL columns for this term
            for col in df.columns:
                try:
                    col_mask = df[col].astype(str).str.contains(term, case=False, na=False, regex=False)
                    term_mask = col_mask if term_mask is None else (term_mask | col_mask)
                except Exception as e:
                    self.logger.error(f"Error searching column {col}: {e}")
                    continue
            
            if term_mask is not None:
                if overall_mask is None:
                    overall_mask = term_mask
                elif operator == "AND":
                    overall_mask = overall_mask & term_mask
                else:  # OR
                    overall_mask = overall_mask | term_mask
        
        if overall_mask is not None:
            try:
                df = df[overall_mask]
                self.logger.info(f"Global search applied: {len(df)} records match '{global_search}' with {operator} logic")
            except Exception as e:
                self.logger.error(f"Error applying global search filter: {e}")
        
        return df

    def _apply_live_filter_to_df(self, df):
        """Apply live tenders filter to a dataframe."""
        if df is None or df.empty:
            return df
            
        # Ensure df.columns exists and is iterable
        if not hasattr(df, 'columns') or df.columns is None:
            return df
            
        # Find date columns for closing dates
        date_cols = [col for col in df.columns 
                    if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]
        
        if date_cols:
            date_col = date_cols[0]
            
            # Convert to datetime if needed
            if not pd.api.types.is_datetime64_dtype(df[date_col]):
                df = df.copy()  # Avoid modifying original
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            # Filter for dates/times in the future (live tenders)
            current_datetime = pd.Timestamp.now()
            mask = df[date_col] > current_datetime
            df = df[mask]
            
            self.logger.info(f"Live tenders filter: {len(df)} records closing after {current_datetime}")
        else:
            # Fallback: look for status column
            status_cols = [col for col in df.columns if 'status' in col.lower()]
            if status_cols:
                status_col = status_cols[0]
                mask = df[status_col].astype(str).str.lower().str.contains('active|live|open', na=False, regex=True)
                df = df[mask]
                self.logger.info(f"Live tenders filter (status-based): {len(df)} records")
        
        return df

    def _apply_expired_filter_to_df(self, df):
        """Apply expired tenders filter to a dataframe."""
        if df is None or df.empty:
            return df
            
        # Ensure df.columns exists and is iterable
        if not hasattr(df, 'columns') or df.columns is None:
            return df
            
        # Find date columns for closing dates
        date_cols = [col for col in df.columns 
                    if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]
        
        if date_cols:
            date_col = date_cols[0]
            
            # Convert to datetime if needed
            if not pd.api.types.is_datetime64_dtype(df[date_col]):
                df = df.copy()  # Avoid modifying original
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            # Filter for dates/times in the past (expired tenders)
            current_datetime = pd.Timestamp.now()
            mask = df[date_col] < current_datetime
            df = df[mask]
            
            self.logger.info(f"Expired tenders filter: {len(df)} records closed before {current_datetime}")
        else:
            # Fallback: look for status column
            status_cols = [col for col in df.columns if 'status' in col.lower()]
            if status_cols:
                status_col = status_cols[0]
                mask = ~df[status_col].astype(str).str.lower().str.contains('active|live|open', na=False, regex=True)
                df = df[mask]
                self.logger.info(f"Expired tenders filter (status-based): {len(df)} records")
        
        return df

    def _apply_time_range_to_df(self, df, time_range, current_status):
        """Apply time range filter to a dataframe."""
        if df is None or df.empty or not time_range:
            return df
            
        # Ensure df.columns exists and is iterable
        if not hasattr(df, 'columns') or df.columns is None:
            return df
            
        # Find date columns
        date_cols = [col for col in df.columns 
                    if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]
        
        if not date_cols:
            return df
        
        date_col = date_cols[0]
        
        # Convert to datetime if needed
        if not pd.api.types.is_datetime64_dtype(df[date_col]):
            df = df.copy()
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Calculate date ranges using current datetime for precise filtering
        current_datetime = pd.Timestamp.now()
        today_start = current_datetime.normalize()  # Start of today (00:00:00)
        today_end = today_start + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)  # End of today (23:59:59)
        
        if time_range == "today":
            if current_status == "expired":
                mask = (df[date_col] >= today_start) & (df[date_col] < current_datetime)
            elif current_status == "live":
                mask = (df[date_col] >= current_datetime) & (df[date_col] <= today_end)
            else:  # "all"
                mask = (df[date_col] >= today_start) & (df[date_col] <= today_end)
        elif time_range == "next_3_days":
            end_3_days = today_start + pd.Timedelta(days=3, hours=23, minutes=59, seconds=59)
            if current_status == "expired":
                start_3_days_ago = today_start - pd.Timedelta(days=3)
                mask = (df[date_col] >= start_3_days_ago) & (df[date_col] < current_datetime)
            elif current_status == "live":
                mask = (df[date_col] >= current_datetime) & (df[date_col] <= end_3_days)
            else:  # "all"
                mask = (df[date_col] >= today_start) & (df[date_col] <= end_3_days)
        elif time_range == "next_7_days":
            end_7_days = today_start + pd.Timedelta(days=7, hours=23, minutes=59, seconds=59)
            if current_status == "expired":
                start_7_days_ago = today_start - pd.Timedelta(days=7)
                mask = (df[date_col] >= start_7_days_ago) & (df[date_col] < current_datetime)
            elif current_status == "live":
                mask = (df[date_col] >= current_datetime) & (df[date_col] <= end_7_days)
            else:  # "all"
                mask = (df[date_col] >= today_start) & (df[date_col] <= end_7_days)
        elif time_range == "next_30_days":
            end_30_days = today_start + pd.Timedelta(days=30, hours=23, minutes=59, seconds=59)
            if current_status == "expired":
                start_30_days_ago = today_start - pd.Timedelta(days=30)
                mask = (df[date_col] >= start_30_days_ago) & (df[date_col] < current_datetime)
            elif current_status == "live":
                mask = (df[date_col] >= current_datetime) & (df[date_col] <= end_30_days)
            else:  # "all"
                mask = (df[date_col] >= today_start) & (df[date_col] <= end_30_days)
        else:
            return df
        
        # Apply the date range filter
        df = df[mask]
        self.logger.info(f"Time range filter ({time_range}) with status ({current_status}): {len(df)} records")
        
        return df

    def _load_saved_search(self, event=None):
        """Load a saved search configuration."""
        search_name = self.saved_search_var.get()
        if not search_name:
            return
        
        try:
            saved_searches_data = self.main_app.global_config.get("saved_searches_data", {})
            
            if search_name not in saved_searches_data:
                messagebox.showinfo("Not Found", f"Search '{search_name}' not found.")
                return
            
            search_config = saved_searches_data[search_name]
            
            # Only load text search terms - ignore complex filter data
            if 'dept_filter' in search_config:
                self.dept_filter_var.set(search_config['dept_filter'])
            if 'global_search' in search_config:
                self.global_search_var.set(search_config['global_search'])
            if 'dept_operator' in search_config:
                self.dept_operator_var.set(search_config['dept_operator'])
            if 'global_operator' in search_config:
                self.global_operator_var.set(search_config['global_operator'])
            
            # Apply the search filters
            self._apply_filters()
            
            messagebox.showinfo("Search Loaded", f"Search terms for '{search_name}' loaded successfully.")
            self.logger.info(f"Loaded search configuration: {search_name}")
            
        except Exception as e:
            self.logger.error(f"Error loading saved search: {e}")
            messagebox.showerror("Load Error", f"Error loading search '{search_name}'.\nThis search may be corrupted and should be deleted.")

    def _save_current_search(self):
        """Save the current search configuration - only text search terms."""
        # Check if there are any search terms to save
        dept_search = self.dept_filter_var.get().strip()
        global_search = self.global_search_var.get().strip()
        
        if not dept_search and not global_search:
            messagebox.showinfo("Nothing to Save", "Please enter some search terms before saving.")
            return
        
        # Ask for a name for the search
        search_name = tkinter.simpledialog.askstring(
            "Save Search", 
            "Enter a name for this search:",
            parent=self
        )
        
        if not search_name or not search_name.strip():
            return  # User canceled or entered empty name
        
        search_name = search_name.strip()
        
        # Create simplified search configuration - only text terms
        search_config = {
            'dept_filter': dept_search,
            'global_search': global_search,
            'dept_operator': self.dept_operator_var.get(),
            'global_operator': self.global_operator_var.get(),
            'saved_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # Get existing saved searches
            saved_searches_data = self.main_app.global_config.get("saved_searches_data", {})
            saved_searches_list = self.main_app.global_config.get("saved_searches", [])
            
            # Check if name already exists
            if search_name in saved_searches_data:
                if not messagebox.askyesno("Overwrite Search", 
                                         f"A search named '{search_name}' already exists. Overwrite it?"):
                    return
            # Add this search to the saved searches
            saved_searches_data[search_name] = search_config
            
            # Update the list of saved search names if needed
            if search_name not in saved_searches_list:
                saved_searches_list.append(search_name)
            
            # Update the config
            self.main_app.global_config.set("saved_searches_data", saved_searches_data)
            self.main_app.global_config.set("saved_searches", saved_searches_list)
            
            # Save the config
            self.main_app.global_config.save_config()
            
            # Update the UI
            self._update_saved_searches_list()
            self.saved_search_var.set(search_name)
            
            messagebox.showinfo("Search Saved", f"Search '{search_name}' saved successfully.")
            self.logger.info(f"Saved search configuration: {search_name}")
            
        except Exception as e:
            self.logger.error(f"Error saving search: {e}")
            messagebox.showerror("Save Error", f"Failed to save search: {str(e)}")

    def _delete_saved_search(self):
        """Delete a saved search configuration with better error handling."""
        search_name = self.saved_search_var.get()
        
        if not search_name:
            messagebox.showinfo("No Selection", "Please select a saved search to delete.")
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", 
                                 f"Are you sure you want to delete the saved search '{search_name}'?"):
            return
        
        try:
            # Get saved searches from config
            saved_searches_data = self.main_app.global_config.get("saved_searches_data", {})
            saved_searches_list = self.main_app.global_config.get("saved_searches", [])
            
            # Remove the search
            if search_name in saved_searches_data:
                del saved_searches_data[search_name]
            
            if search_name in saved_searches_list:
                saved_searches_list.remove(search_name)
            
            # Update the config
            self.main_app.global_config.set("saved_searches_data", saved_searches_data)
            self.main_app.global_config.set("saved_searches", saved_searches_list)
            
            # Save the config
            self.main_app.global_config.save_config()
            
            # Update the UI
            self._update_saved_searches_list()
            self.saved_search_var.set("")
            
            messagebox.showinfo("Search Deleted", f"Search '{search_name}' deleted successfully.")
            self.logger.info(f"Deleted search configuration: {search_name}")
            
        except Exception as e:
            self.logger.error(f"Error deleting saved search: {e}")
            messagebox.showerror("Delete Error", f"Failed to delete search: {str(e)}")

    def _export_saved_searches(self):
        """Export all saved searches to a JSON file."""
        try:
            saved_searches_data = self.main_app.global_config.get("saved_searches_data", {})
            
            if not saved_searches_data:
                messagebox.showinfo("No Searches", "No saved searches to export.")
                return
            
            # Ask for export file location
            filename = filedialog.asksaveasfilename(
                title="Export Saved Searches",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not filename:
                return
             
            # Export to JSON
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(saved_searches_data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Export Complete", f"Saved searches exported to:\n{filename}")
            self.logger.info(f"Exported saved searches to: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error exporting saved searches: {e}")
            messagebox.showerror("Export Error", f"Failed to export searches: {str(e)}")

    def _import_saved_searches(self):
        """Import saved searches from a JSON file."""
        try:
            # Ask for import file
            filename = filedialog.askopenfilename(
                title="Import Saved Searches",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not filename:
                return
            
            import json
            with open(filename, 'r', encoding='utf-8') as f:
                imported_searches = json.load(f)
            
            if not isinstance(imported_searches, dict):
                messagebox.showerror("Invalid File", "Invalid saved searches file format.")
                return
            
            # Get current saved searches
            current_searches = self.main_app.global_config.get("saved_searches_data", {})
            current_list = self.main_app.global_config.get("saved_searches", [])
            
            # Count new searches
            new_count = 0
            overwritten_count = 0
            
            for search_name, search_config in imported_searches.items():
                if search_name in current_searches:
                    overwritten_count += 1
                else:
                    new_count += 1
                
                current_searches[search_name] = search_config
                if search_name not in current_list:
                    current_list.append(search_name)
            
            # Update config
            self.main_app.global_config.set("saved_searches_data", current_searches)
            self.main_app.global_config.set("saved_searches", current_list)
            self.main_app.global_config.save_config()
            
            # Update UI
            self._update_saved_searches_list()
            
            message = f"Import complete!\n\nNew searches: {new_count}\nOverwritten: {overwritten_count}"
            messagebox.showinfo("Import Complete", message)
            self.logger.info(f"Imported saved searches from: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error importing saved searches: {e}")
            messagebox.showerror("Import Error", f"Failed to import searches: {str(e)}")

    def _clean_corrupted_searches(self):
        """Clean up corrupted saved searches."""
        try:
            saved_searches_data = self.main_app.global_config.get("saved_searches_data", {})
            saved_searches_list = self.main_app.global_config.get("saved_searches", [])
            
            cleaned_data = {}
            cleaned_list = []
            removed_count = 0
            
            for search_name in saved_searches_list[:]:  # Copy the list to modify during iteration
                if search_name in saved_searches_data:
                    search_config = saved_searches_data[search_name]
                    
                    # Check if it's a valid, simple search config
                    if (isinstance(search_config, dict) and 
                        ('dept_filter' in search_config or 'global_search' in search_config)):
                        # Keep valid searches
                        cleaned_data[search_name] = {
                            'dept_filter': search_config.get('dept_filter', ''),
                            'global_search': search_config.get('global_search', ''),
                            'dept_operator': search_config.get('dept_operator', 'OR'),
                            'global_operator': search_config.get('global_operator', 'AND'),
                            'saved_date': search_config.get('saved_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        }
                        cleaned_list.append(search_name)
                    else:
                        # Remove corrupted searches
                        removed_count += 1
                        self.logger.warning(f"Removed corrupted search: {search_name}")
                else:
                    # Remove references to non-existent searches
                    removed_count += 1
                    self.logger.warning(f"Removed reference to missing search: {search_name}")
            
            # Update config with cleaned data
            self.main_app.global_config.set("saved_searches_data", cleaned_data)
            self.main_app.global_config.set("saved_searches", cleaned_list)
            self.main_app.global_config.save_config()
            
            # Update UI
            self._update_saved_searches_list()
            self.saved_search_var.set("")
            
            if removed_count > 0:
                messagebox.showinfo("Cleanup Complete", 
                                  f"Removed {removed_count} corrupted saved search(es).")
            else:
                messagebox.showinfo("No Issues Found", "All saved searches are valid.")
            
            self.logger.info(f"Cleaned saved searches, removed {removed_count} corrupted entries")
            
        except Exception as e:
            self.logger.error(f"Error cleaning saved searches: {e}")
            messagebox.showerror("Cleanup Error", f"Failed to clean searches: {str(e)}")
