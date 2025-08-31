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

if TYPE_CHECKING:
    from ui.main_window import MainApplication # Use absolute import

logger = logging.getLogger(__name__)

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

        self.data_processor = TenderDataProcessor(self.main_app.global_config)
        # --- ensure filtered_data attribute exists even before any load ---
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data is None:
            self.data_processor.filtered_data = pd.DataFrame()

        self.loaded_files: List[str] = []

        # UI Variables
        self.dept_filter_var = tk.StringVar()
        self.global_search_var = tk.StringVar()
        self.selected_folders_var = tk.StringVar(value="No folders selected.")
        self.custom_date_start_var = tk.StringVar()
        self.custom_date_end_var = tk.StringVar()
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

    def _toggle_data_folders_panel(self):
        """Toggle the visibility of data folders panel"""
        if self.data_folders_frame_visible:
            # Hide the panel content
            self.data_folders_content.pack_forget()
            self.toggle_button.config(text="► Data Folders")
        else:
            # Show the panel content
            self.data_folders_content.pack(side=tk.TOP, fill=tk.X)
            self.toggle_button.config(text="▼ Data Folders")
            
        self.data_folders_frame_visible = not self.data_folders_frame_visible

    def _create_dashboard_widgets(self, parent: Union[ttk.Frame, ttk.LabelFrame]):
        """Create dashboard widgets in a single row with solid color backgrounds."""
        # Container for all cards
        dashboard_container = ttk.Frame(parent)
        dashboard_container.pack(fill=tk.X, expand=True, pady=SPACING['small'])
        
        # Configure grid with equal column weights - Updated for 11 metrics
        for i in range(11):  # We now have 11 metrics
            dashboard_container.columnconfigure(i, weight=1)
        
        # Define metrics with their properties - Reorder with Live and Expired first
        self.dashboard_labels = {}
        metrics = [
            # key, title, color - Live and Expired are now first with prominent colors
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
            card_frame = tk.Frame(dashboard_container, bg=color, width=90, height=100)  # Slightly narrower
            card_frame.grid(row=0, column=i, padx=1, sticky="nsew")  # Reduced padding
            card_frame.grid_propagate(False)  # Fix the size
            
            # Create centered content inside card
            if key == "current_date":
                # Date and time are special cases
                self.current_time_var = tk.StringVar(value="00:00:00")
                self.current_date_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
                
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
                                      font=FONTS.get('small') or ('TkDefaultFont', 9, 'bold'))
                title_label.pack(anchor=tk.CENTER, pady=(10, 0))
                
                value_label = tk.Label(card_frame, text="0", bg=color, fg="white",
                                      font=FONTS.get('heading') or ('TkDefaultFont', 24, 'bold'))
                value_label.pack(anchor=tk.CENTER, expand=True)
                
                # Store reference for updating later
                self.dashboard_labels[key] = value_label
                
        # Make container row expand
        parent.rowconfigure(0, weight=1)

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
        create_action_button(action_frame, "Refresh Data", self._load_data_from_folders, width=12).pack(pady=SPACING['small']//2, fill=tk.X)
        create_action_button(action_frame, "Clear Folders", self._clear_folders, button_type='secondary', width=12).pack(pady=SPACING['small']//2, fill=tk.X)

        selected_folders_label = create_info_label(parent, "", textvariable=self.selected_folders_var, wraplength=600, justify=tk.LEFT)
        selected_folders_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=SPACING['small'])
        self._update_selected_folders_display()

    def _create_search_filter_widgets(self, parent: Union[ttk.Frame, ttk.LabelFrame]):
        # Using a sub-frame for better organization
        text_search_frame = ttk.Frame(parent)
        text_search_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['small']))

        # Department Filter
        dept_label = create_info_label(text_search_frame, "Department(s):")
        dept_label.grid(row=0, column=0, padx=(SPACING['small'], 0), pady=SPACING['small'], sticky="w")
        dept_entry = create_input_entry(text_search_frame, self.dept_filter_var, width=35) # Increased width
        dept_entry.grid(row=0, column=1, padx=(SPACING['small']//2, 0), pady=SPACING['small'], sticky="ew")
        dept_entry.bind("<KeyRelease>", self._on_live_search_key)  # was _apply_filters_on_event
        # Department search operator radio buttons
        dept_op_frame = ttk.Frame(text_search_frame)
        dept_op_frame.grid(row=0, column=2, padx=(SPACING['small']//2, 0), sticky="w")
        
        self.dept_operator_var = tk.StringVar(value="OR")
        ttk.Radiobutton(dept_op_frame, text="OR", variable=self.dept_operator_var, 
                        value="OR", command=self._apply_filters_on_event).pack(side=tk.LEFT, padx=1)
        ttk.Radiobutton(dept_op_frame, text="AND", variable=self.dept_operator_var, 
                        value="AND", command=self._apply_filters_on_event).pack(side=tk.LEFT, padx=1)
        
        create_info_label(text_search_frame, "CSV", font_style=FONTS['small']).grid(row=0, column=3, padx=(SPACING['small']//2, SPACING['small']), sticky='w') # Changed label and reduced padding

        # Global Search
        search_label = create_info_label(text_search_frame, "Global Search:")
        search_label.grid(row=0, column=4, padx=(SPACING['medium'], 0), pady=SPACING['small'], sticky="w") # Adjusted padding
        search_entry = create_input_entry(text_search_frame, self.global_search_var, width=50) # Increased width
        search_entry.grid(row=0, column=5, padx=(SPACING['small']//2, 0), pady=SPACING['small'], sticky="ew")
        search_entry.bind("<KeyRelease>", self._on_live_search_key)  # was _apply_filters_on_event
        # Global search operator radio buttons
        global_op_frame = ttk.Frame(text_search_frame)
        global_op_frame.grid(row=0, column=6, padx=(SPACING['small']//2, 0), sticky="w")
        
        self.global_operator_var = tk.StringVar(value="AND")
        ttk.Radiobutton(global_op_frame, text="OR", variable=self.global_operator_var, 
                        value="OR", command=self._apply_filters_on_event).pack(side=tk.LEFT, padx=1)
        ttk.Radiobutton(global_op_frame, text="AND", variable=self.global_operator_var, 
                        value="AND", command=self._apply_filters_on_event).pack(side=tk.LEFT, padx=1)
        
        create_info_label(text_search_frame, "CSV", font_style=FONTS['small']).grid(row=0, column=7, padx=(SPACING['small']//2, SPACING['small']), sticky='w') # Changed label and reduced padding
        
        text_search_frame.grid_columnconfigure(1, weight=1) # Allow dept entry to expand
        text_search_frame.grid_columnconfigure(5, weight=2) # Allow global search entry to expand more

        # Only keep the Reset button since we have live search
        btn_frame = ttk.Frame(text_search_frame)
        btn_frame.grid(row=0, column=8, padx=(SPACING['medium'], SPACING['small']), sticky="e")
        create_action_button(btn_frame, "Reset All Filters", self._reset_filters, button_type='danger').pack(side=tk.LEFT, padx=SPACING['small']//2)

        # Add a saved search section
        saved_search_frame = ttk.Frame(text_search_frame)
        saved_search_frame.grid(row=1, column=0, columnspan=9, sticky="ew", padx=SPACING['small'], pady=(SPACING['small'], 0)) # Adjusted columnspan and pady
        
        create_info_label(saved_search_frame, "Saved Searches:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        # Dropdown for saved searches
        self.saved_search_var = tk.StringVar()
        self.saved_searches_combo = ttk.Combobox(saved_search_frame, textvariable=self.saved_search_var, width=30)
        self.saved_searches_combo.pack(side=tk.LEFT, padx=SPACING['small'])
        self.saved_searches_combo.bind("<<ComboboxSelected>>", self._load_saved_search)
        
        # Buttons for saved search operations
        saved_search_buttons = ttk.Frame(saved_search_frame)
        saved_search_buttons.pack(side=tk.LEFT, padx=SPACING['small'])
        
        create_action_button(saved_search_buttons, "Load", self._load_saved_search, width=8, 
                            button_type='info_outline').pack(side=tk.LEFT, padx=2)
        create_action_button(saved_search_buttons, "Save Current", self._save_current_search, width=12, 
                            button_type='success_outline').pack(side=tk.LEFT, padx=2)
        create_action_button(saved_search_buttons, "Delete", self._delete_saved_search, width=8, 
                            button_type='danger_outline').pack(side=tk.LEFT, padx=2)
        
        # Update the saved searches dropdown
        self._update_saved_searches_list()

    def _create_date_filter_widgets(self, parent: Union[ttk.Frame, ttk.LabelFrame]):
        # Main date filter container
        date_filter_frame = ttk.Frame(parent)
        date_filter_frame.pack(side=tk.TOP, fill=tk.X, pady=SPACING['small'])

        # Create a professional header
        header_frame = ttk.Frame(date_filter_frame)
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['small']))
        
        create_info_label(header_frame, "Date Filters", 
                         font_style=FONTS.get('subheading', ('TkDefaultFont', 11, 'bold'))).pack(side=tk.LEFT)

        # Main content frame with two sections
        content_frame = ttk.Frame(date_filter_frame)
        content_frame.pack(side=tk.TOP, fill=tk.X, pady=SPACING['small'])

        # Left section: Status-based filters (Radio buttons)
        status_section = ttk.LabelFrame(content_frame, text="Status Filter", padding=SPACING['small'])
        status_section.pack(side=tk.LEFT, fill=tk.Y, padx=(0, SPACING['medium']))

        # Radio button variable for mutually exclusive status filters
        self.status_filter_var = tk.StringVar(value="live")  # Default to Live
        self.active_date_filter = "live"  # Set default active filter
        
        # Status filter options with radio buttons
        status_options = [
            ("All Records", "all", "Show all tender records regardless of status"),
            ("Live Tenders", "live", "Show only active/open tenders"),
            ("Expired Tenders", "expired", "Show only expired/closed tenders")
        ]
        
        for text, value, tooltip in status_options:
            radio_btn = ttk.Radiobutton(
                status_section, 
                text=text, 
                variable=self.status_filter_var,
                value=value,
                command=lambda v=value: self._apply_status_filter(v)
            )
            radio_btn.pack(anchor=tk.W, pady=2)
            
            # Store reference for potential styling later
            if not hasattr(self, 'date_filter_buttons'):
                self.date_filter_buttons = {}
            self.date_filter_buttons[value] = radio_btn

        # Right section: Time-based filters  
        time_section = ttk.LabelFrame(content_frame, text="Time Range Filter", padding=SPACING['small'])
        time_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Time filter buttons frame
        time_buttons_frame = ttk.Frame(time_section)
        time_buttons_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['small']))

        # Quick time filter buttons
        time_presets = [
            ("Today", "today", "Tenders closing today"),
            ("Next 3 Days", "next_3_days", "Tenders closing in next 3 days"), 
            ("Next 7 Days", "next_7_days", "Tenders closing in next 7 days"),
            ("Next 30 Days", "next_30_days", "Tenders closing in next 30 days")
        ]
        
        for text, preset_key, tooltip in time_presets:
            btn = create_action_button(
                time_buttons_frame,
                text,
                lambda p=preset_key: self._apply_time_filter(p),
                width=12,
                button_type='info_outline'
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.date_filter_buttons[preset_key] = btn

        # Custom date range section
        custom_frame = ttk.Frame(time_section)
        custom_frame.pack(side=tk.TOP, fill=tk.X, pady=(SPACING['small'], 0))
        
        # Custom date range label
        create_info_label(custom_frame, "Custom Date Range:", 
                         font_style=FONTS.get('body', ('TkDefaultFont', 10, 'bold'))).pack(side=tk.LEFT)

        # Custom Date Range with Calendar Pickers (only if tkcalendar is available)
        if HAS_TKCALENDAR and DateEntry is not None:
            custom_controls_frame = ttk.Frame(custom_frame)
            custom_controls_frame.pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
            
            # Start date picker
            start_date_frame = ttk.Frame(custom_controls_frame)
            start_date_frame.pack(side=tk.LEFT, padx=SPACING['small']//2)
            
            create_info_label(start_date_frame, "From:").pack(side=tk.LEFT)
            self.start_date_picker = DateEntry(
                start_date_frame, 
                width=10,
                background=COLORS.get('primary', 'blue'),
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                selectmode='day'
            )
            self.start_date_picker.pack(side=tk.LEFT, padx=(2, 0))
            self.start_date_picker.bind("<<DateEntrySelected>>", self._on_calendar_date_selected)

            # Start time spinboxes (HH:MM)
            hh_sb = ttk.Spinbox(start_date_frame, from_=0, to=23, width=3,
                                textvariable=self.start_hour_var, format="%02.0f")
            hh_sb.pack(side=tk.LEFT, padx=1)
            ttk.Label(start_date_frame, text=":").pack(side=tk.LEFT)
            mm_sb = ttk.Spinbox(start_date_frame, from_=0, to=59, width=3,
                                textvariable=self.start_min_var, format="%02.0f")
            mm_sb.pack(side=tk.LEFT, padx=(0, 4))

            # "to" label
            create_info_label(custom_controls_frame, "To:").pack(side=tk.LEFT, padx=(4, 0))

            # End date picker
            end_date_frame = ttk.Frame(custom_controls_frame)
            end_date_frame.pack(side=tk.LEFT, padx=SPACING['small']//2)
            
            self.end_date_picker = DateEntry(
                end_date_frame, 
                width=10,
                background=COLORS.get('primary', 'blue'),
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                selectmode='day'
            )
            self.end_date_picker.pack(side=tk.LEFT, padx=(2, 0))
            self.end_date_picker.bind("<<DateEntrySelected>>", self._on_calendar_date_selected)

            # End time spinboxes (HH:MM)
            ehh_sb = ttk.Spinbox(end_date_frame, from_=0, to=23, width=3,
                                 textvariable=self.end_hour_var, format="%02.0f")
            ehh_sb.pack(side=tk.LEFT, padx=1)
            ttk.Label(end_date_frame, text=":").pack(side=tk.LEFT)
            emm_sb = ttk.Spinbox(end_date_frame, from_=0, to=59, width=3,
                                 textvariable=self.end_min_var, format="%02.0f")
            emm_sb.pack(side=tk.LEFT, padx=(0, 4))

            # Apply button for custom range
            apply_custom_btn = create_action_button(
                custom_controls_frame, "Apply Range", self._apply_custom_date_filter, 
                button_type='primary', width=12
            )
            apply_custom_btn.pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
        else:
            # Fallback: text entries
            custom_controls_frame = ttk.Frame(custom_frame)
            custom_controls_frame.pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
            
            create_info_label(custom_controls_frame, "From (YYYY-MM-DD):").pack(side=tk.LEFT)
            self.start_date_entry = create_input_entry(custom_controls_frame, self.custom_date_start_var, width=12)
            self.start_date_entry.pack(side=tk.LEFT, padx=2)
            
            # Time spinboxes for fallback
            ttk.Spinbox(custom_controls_frame, from_=0, to=23, width=3,
                        textvariable=self.start_hour_var, format="%02.0f").pack(side=tk.LEFT, padx=1)
            ttk.Label(custom_controls_frame, text=":").pack(side=tk.LEFT)
            ttk.Spinbox(custom_controls_frame, from_=0, to=59, width=3,
                        textvariable=self.start_min_var, format="%02.0f").pack(side=tk.LEFT, padx=(0, 4))
            
            create_info_label(custom_controls_frame, "To:").pack(side=tk.LEFT, padx=(4, 0))
            self.end_date_entry = create_input_entry(custom_controls_frame, self.custom_date_end_var, width=12)
            self.end_date_entry.pack(side=tk.LEFT, padx=2)
            
            ttk.Spinbox(custom_controls_frame, from_=0, to=23, width=3,
                        textvariable=self.end_hour_var, format="%02.0f").pack(side=tk.LEFT, padx=1)
            ttk.Label(custom_controls_frame, text=":").pack(side=tk.LEFT)
            ttk.Spinbox(custom_controls_frame, from_=0, to=59, width=3,
                        textvariable=self.end_min_var, format="%02.0f").pack(side=tk.LEFT, padx=(0, 4))
            
            apply_custom_btn = create_action_button(
                custom_controls_frame, "Apply Range", self._apply_custom_date_filter_text, 
                button_type='primary', width=12
            )
            apply_custom_btn.pack(side=tk.LEFT, padx=(SPACING['medium'], 0))

        # Apply default Live filter on initialization
        self._apply_status_filter("live")

    def _apply_status_filter(self, status_type: str):
        """Apply status-based filter (All, Live, Expired)."""
        self.logger.info(f"Applying status filter: {status_type}")
        
        # Clear any time-based filters first
        self._clear_time_filter_selection()
        
        # Set the active filter
        self.active_date_filter = status_type
        self.current_date_filter = {'type': status_type}
        
        # Apply the filter
        self._apply_all_filters()

    def _apply_time_filter(self, time_preset: str):
        """Apply time-based filter (Today, Next 3 Days, etc.)."""
        self.logger.info(f"Applying time filter: {time_preset}")
        
        # Keep the current status filter but add time constraint
        current_status = self.status_filter_var.get()
        
        # Set the active filter to combine status + time
        self.active_date_filter = f"{current_status}_{time_preset}"
        self.current_date_filter = {
            'type': 'combined',
            'status': current_status,
            'time_range': time_preset
        }
        
        # Reset custom date inputs
        today = datetime.now().strftime("%Y-%m-%d")
        if HAS_TKCALENDAR and hasattr(self, 'start_date_picker') and hasattr(self, 'end_date_picker'):
            self.start_date_picker.set_date(today)
            self.end_date_picker.set_date(today)
        else:
            if hasattr(self, 'custom_date_start_var') and hasattr(self, 'custom_date_end_var'):
                self.custom_date_start_var.set("")
                self.custom_date_end_var.set("")
        
        # Reset time spinboxes to full day
        self.start_hour_var.set("00")
        self.start_min_var.set("00")
        self.end_hour_var.set("23")
        self.end_min_var.set("59")
        
        # Apply the filter
        self._apply_all_filters()

    def _clear_time_filter_selection(self):
        """Clear visual selection of time filter buttons."""
        # This would be used if we had visual state indication for the time buttons
        # For now, it's a placeholder for future enhancement
        pass

    def _filter_by_date_preset_with_visual(self, preset: str, button_text: str):
        """Legacy method - redirect to new structure."""
        if preset in ["all", "live", "expired"]:
            self.status_filter_var.set(preset)
            self._apply_status_filter(preset)
        else:
            self._apply_time_filter(preset)

    def update_dashboard(self):
        """Update dashboard metrics with current data state."""
        # Ensure filtered_data exists
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data is None:
            self.data_processor.filtered_data = pd.DataFrame()
        
        # Ensure raw_data exists
        if not hasattr(self.data_processor, 'raw_data') or self.data_processor.raw_data is None:
            self.data_processor.raw_data = pd.DataFrame()
        
        # Calculate metrics
        total_tenders = len(self.data_processor.raw_data) if not self.data_processor.raw_data.empty else 0
        filtered_tenders = len(self.data_processor.filtered_data) if not self.data_processor.filtered_data.empty else 0
        
        # Calculate match percentage
        match_percentage = 0
        if total_tenders > 0:
            match_percentage = round((filtered_tenders / total_tenders) * 100, 1)
        
        # Count unique departments
        unique_departments = 0
        if not self.data_processor.filtered_data.empty:
            dept_col = next((c for c in self.data_processor.filtered_data.columns if 'department' in c.lower() or 'dept' in c.lower()), None)
            if dept_col:
                unique_departments = self.data_processor.filtered_data[dept_col].nunique()
        
        # Calculate date-based metrics
        live_tenders = expired_tenders = closing_today = closing_next_3_days = closing_next_7_days = 0
        
        if not self.data_processor.filtered_data.empty:
            date_col = next((c for c in self.data_processor.filtered_data.columns if 'closing' in c.lower() or 'due' in c.lower() or 'deadline' in c.lower()), None)
            if date_col:
                df = self.data_processor.filtered_data.copy()
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df = df.dropna(subset=[date_col])
                
                now = pd.Timestamp.now()
                today = now.date()
                
                # Live vs Expired
                live_tenders = len(df[df[date_col] >= now])
                expired_tenders = len(df[df[date_col] < now])
                
                # Closing timeframes
                closing_today = len(df[df[date_col].dt.date == today])
                closing_next_3_days = len(df[(df[date_col].dt.date > today) & (df[date_col].dt.date <= today + timedelta(days=3))])
                closing_next_7_days = len(df[(df[date_col].dt.date > today) & (df[date_col].dt.date <= today + timedelta(days=7))])
        
        # Data sources count
        data_sources = len(self.loaded_files)
        
        # Update dashboard labels
        dashboard_values = {
            "live_tenders": live_tenders,
            "expired_tenders": expired_tenders,
            "total_tenders": total_tenders,
            "filtered_tenders": filtered_tenders,
            "match_percentage": f"{match_percentage}%",
            "unique_departments": unique_departments,
            "closing_today": closing_today,
            "closing_next_3_days": closing_next_3_days,
            "closing_next_7_days": closing_next_7_days,
            "data_sources": data_sources
        }
        
        # Update the dashboard labels
        for key, value in dashboard_values.items():
            if key in self.dashboard_labels:
                self.dashboard_labels[key].config(text=str(value))

    def _get_custom_range_datetimes(self):
        """Combine selected dates + time spinboxes into ISO strings (start, end)."""
        start_date = self.custom_date_start_var.get()
        end_date = self.custom_date_end_var.get()
        sh = self.start_hour_var.get() or "00"
        sm = self.start_min_var.get() or "00"
        eh = self.end_hour_var.get() or "23"
        em = self.end_min_var.get() or "59"
        # Zero pad & validate
        try:
            sh_i, sm_i, eh_i, em_i = int(sh), int(sm), int(eh), int(em)
            if not (0 <= sh_i <= 23 and 0 <= eh_i <= 23 and 0 <= sm_i <= 59 and 0 <= em_i <= 59):
                raise ValueError
        except Exception:
            raise ValueError("Invalid time (HH:MM) values.")
        
        # Create proper ISO datetime strings with seconds
        start_iso = f"{start_date} {sh_i:02d}:{sm_i:02d}:00"
        end_iso = f"{end_date} {eh_i:02d}:{em_i:02d}:59"
        
        # Validate ordering
        try:
            sd_dt = datetime.strptime(start_iso, "%Y-%m-%d %H:%M:%S")
            ed_dt = datetime.strptime(end_iso, "%Y-%m-%d %H:%M:%S")
            if ed_dt < sd_dt:
                raise ValueError("End datetime is before start datetime.")
        except ValueError as ve:
            raise ValueError(str(ve))
        return start_iso, end_iso

    def _on_calendar_date_selected(self, event=None):
        """Update the custom date variables when a date is selected in the calendar."""
        if HAS_TKCALENDAR and hasattr(self, 'start_date_picker') and hasattr(self, 'end_date_picker'):
            self.custom_date_start_var.set(self.start_date_picker.get())
            self.custom_date_end_var.set(self.end_date_picker.get())
            self.logger.debug(f"Selected dates - Start: {self.custom_date_start_var.get()}, End: {self.custom_date_end_var.get()}")

    def _apply_custom_date_filter(self):
        """Apply the custom date range filter selected from the calendar pickers."""
        if not HAS_TKCALENDAR or not hasattr(self, 'start_date_picker'):
            return
        self.custom_date_start_var.set(self.start_date_picker.get())
        self.custom_date_end_var.set(self.end_date_picker.get())
        try:
            start_iso, end_iso = self._get_custom_range_datetimes()
        except ValueError as e:
            messagebox.showerror("Invalid Time", str(e))
            return
        
        self.logger.info(f"Applying custom date-time filter: {start_iso} -> {end_iso}")
        
        # Clear any existing date filter first
        self._reset_date_filter_buttons()
        
        self.current_date_filter = {
            'type': 'custom',
            'start_date': self.custom_date_start_var.get(),
            'end_date': self.custom_date_end_var.get(),
            'start_datetime': start_iso,
            'end_datetime': end_iso
        }
        
        # Set visual indicator for custom filter
        self.active_date_filter = 'custom'
        
        try:
            self._apply_all_filters()
        except Exception as e:
            self.logger.error(f"Error applying custom date-time filter: {e}")
            messagebox.showerror("Filter Error", f"Error applying date-time filter: {str(e)}")

    def _apply_custom_date_filter_text(self):
        """Apply the custom date range filter from text entries (fallback when tkcalendar is not available)."""
        start_raw = self.custom_date_start_var.get().strip()
        end_raw = self.custom_date_end_var.get().strip()
        if not start_raw or not end_raw:
            messagebox.showwarning("Date Range Required", "Please enter both start and end dates.")
            return
        
        # Allow optional time in the text (YYYY-MM-DD HH:MM); if absent we use spinboxes/defaults
        def split_dt(txt):
            parts = txt.split()
            if len(parts) == 2:
                return parts[0], parts[1]
            return parts[0], None
            
        start_date, start_time = split_dt(start_raw)
        end_date, end_time = split_dt(end_raw)
        
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date Format", "Use YYYY-MM-DD or YYYY-MM-DD HH:MM.")
            return
            
        if start_time:
            try:
                datetime.strptime(start_time, "%H:%M")
                sh, sm = start_time.split(":")
                self.start_hour_var.set(sh)
                self.start_min_var.set(sm)
            except ValueError:
                messagebox.showerror("Invalid Time", "Start time must be HH:MM.")
                return
                
        if end_time:
            try:
                datetime.strptime(end_time, "%H:%M")
                eh, em = end_time.split(":")
                self.end_hour_var.set(eh)
                self.end_min_var.set(em)
            except ValueError:
                messagebox.showerror("Invalid Time", "End time must be HH:MM.")
                return
                
        try:
            start_iso, end_iso = self._get_custom_range_datetimes()
        except ValueError as e:
            messagebox.showerror("Invalid Time", str(e))
            return
            
        self.logger.info(f"Applying custom date-time filter (text): {start_iso} -> {end_iso}")
        
        # Clear any existing date filter first
        self._reset_date_filter_buttons()
        
        self.current_date_filter = {
            'type': 'custom',
            'start_date': start_date,
            'end_date': end_date,
            'start_datetime': start_iso,
            'end_datetime': end_iso
        }
        
        # Set visual indicator for custom filter
        self.active_date_filter = 'custom'
        
        try:
            self._apply_all_filters()
        except Exception as e:
            self.logger.error(f"Error applying custom date-time filter: {e}")
            messagebox.showerror("Filter Error", f"Error applying date-time filter: {str(e)}")

    def _reset_filters(self):
        """Reset all search and date filters to default values."""
        # Clear text filters
        self.dept_filter_var.set("")
        self.global_search_var.set("")
        
        # Reset date filters and visual feedback
        self.current_date_filter = {}
        self._reset_date_filter_buttons()
        
        # Reset date pickers to today
        today = datetime.now().strftime("%Y-%m-%d")
        if HAS_TKCALENDAR and hasattr(self, 'start_date_picker') and hasattr(self, 'end_date_picker'):
            self.start_date_picker.set_date(today)
            self.end_date_picker.set_date(today)
        else:
            if hasattr(self, 'custom_date_start_var') and hasattr(self, 'custom_date_end_var'):
                self.custom_date_start_var.set("")
                self.custom_date_end_var.set("")
        
        # Reset time spinboxes
        if hasattr(self, 'start_hour_var'):
            self.start_hour_var.set("00")
            self.start_min_var.set("00")
            self.end_hour_var.set("23")
            self.end_min_var.set("59")
            
        # Reset status filter to default (Live)
        if hasattr(self, 'status_filter_var'):
            self.status_filter_var.set("live")
            
        # Apply changes to refresh data
        self._apply_all_filters()
        
        self.logger.info("All filters have been reset")

    def _reset_date_filter_buttons(self):
        """Clear active date filter selection."""
        self.active_date_filter = None
        self.logger.debug("Date filter selection cleared")

    def load_initial_data_if_any(self):
        """Called from MainApplication after UI is ready."""
        # First try to restore folders
        persisted_folders = self.main_app.global_config.get("last_used_folders", [])
        if persisted_folders and isinstance(persisted_folders, list):
            self.loaded_files = [f for f in persisted_folders if isinstance(f, str) and os.path.isdir(f)]
            if self.loaded_files:
                self._update_selected_folders_display()
    
        # Now try to restore specific file paths (higher priority)
        persisted_files = self.main_app.global_config.get("last_loaded_files", [])
        if persisted_files and isinstance(persisted_files, list):
            valid_files = [f for f in persisted_files if isinstance(f, str) and os.path.isfile(f)]
            if valid_files:
                # Load the specific files
                success, message = self.data_processor.load_data_from_files(valid_files)
                if success:
                    self._update_treeview()
                    self.update_dashboard()
                    self.logger.info(f"Restored previous session data from {len(valid_files)} files")
                    return
        
        # If no specific files were loaded but we have folders, load from them
        if self.loaded_files:
            self._load_data_from_folders()

    def _on_closing(self):
        """Clean up when tab is closed or application exits"""
        self.clock_running = False
        self._filter_thread_running = False

    def _create_tender_data_widgets(self, parent: Union[ttk.Frame, ttk.LabelFrame]):
        """Create toolbar, treeview and status bar."""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill='both', expand=True)

        toolbar = ttk.Frame(main_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['small']))
        create_action_button(toolbar, "Column Settings", self._show_column_config_dialog,
                             button_type='info_outline', width=15).pack(side=tk.LEFT, padx=SPACING['small'])
        export_frame = ttk.Frame(toolbar)
        export_frame.pack(side=tk.RIGHT, padx=SPACING['small'])
        create_action_button(export_frame, "Export Excel", self._export_to_excel,
                             button_type='success_outline', width=12).pack(side=tk.LEFT, padx=2)
        create_action_button(export_frame, "Export CSV", self._export_to_csv,
                             button_type='success_outline', width=10).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="Ready. No data loaded.")
        ttk.Label(parent, textvariable=self.status_var, anchor=tk.W, padding=(5, 2)).pack(side='bottom', fill='x')

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(side=tk.TOP, fill='both', expand=True)
        self.tree = ttk.Treeview(tree_frame, show='headings', style='Custom.Treeview')
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        self.tree.pack(side='left', fill='both', expand=True)

        style = ttk.Style()
        style.configure("Custom.Treeview", font=FONTS.get('body', ('TkDefaultFont', 10)))
        style.map('Custom.Treeview', background=[('selected', '#3366CC')])
        style.configure("Treeview", rowheight=25)
        self.tree.tag_configure('oddrow', background='#F5F5F5')
        self.tree.tag_configure('evenrow', background='#FFFFFF')

        self.url_columns: List[str] = []
        self.column_config = {
            "Department": {"visible": True, "order": 0, "width": 250},
            "Closing Date": {"visible": True, "order": 1, "width": 120},
            "Title": {"visible": True, "order": 2, "width": 500},
            "Tender ID": {"visible": True, "order": 3, "width": 200},
            "Direct URL": {"visible": True, "order": 4, "width": 80},
            "Status URL": {"visible": True, "order": 5, "width": 80},
        }
        self.default_column_order = 100

    def _setup_treeview_bindings(self):
        """Bind treeview events (call after tree exists)."""
        if not hasattr(self, 'tree'):
            return
        self.tree.bind("<Double-1>", self._on_treeview_double_click)
        self.tree.bind("<Button-3>", self._show_treeview_context_menu)

    def _add_folder(self):
        default_folder = self.main_app.global_config.get("default_data_folder", "") or os.path.expanduser("~")
        folder = filedialog.askdirectory(title="Select Folder Containing Excel/CSV Files", initialdir=default_folder)
        if folder and folder not in self.loaded_files:
            self.loaded_files.append(folder)
            self.main_app.global_config.set("last_used_folders", self.loaded_files)
            self.main_app.global_config.save_config()
            self._update_selected_folders_display()
            self.logger.info(f"Added folder: {folder}")
            self._load_data_from_folders()

    def _clear_folders(self):
        self.loaded_files = []
        self.main_app.global_config.set("last_used_folders", [])
        self.main_app.global_config.save_config()
        self._update_selected_folders_display()
        self.data_processor.raw_data = pd.DataFrame()
        self.data_processor.filtered_data = pd.DataFrame()
        self._update_treeview()
        self.update_dashboard()
        self.logger.info("Cleared selected folders and data.")

    def _update_selected_folders_display(self):
        if not self.loaded_files:
            self.selected_folders_var.set("No folders selected. Click 'Add Folder'.")
        else:
            folder_list = []
            for path in self.loaded_files:
                folder_list.append(f"- {path}")
            self.selected_folders_var.set("Selected:\n" + "\n".join(folder_list))

    def _get_all_files_from_selected_folders(self) -> List[str]:
        files = []
        for folder in self.loaded_files:
            try:
                for f in os.listdir(folder):
                    if f.lower().endswith(('.xlsx', '.xls', '.csv')):
                        files.append(os.path.join(folder, f))
            except Exception as e:
                self.logger.error(f"Error scanning {folder}: {e}")
        return files

    def _load_data_from_folders(self):
        file_list = self._get_all_files_from_selected_folders()
        if not file_list:
            messagebox.showwarning("No Files", "No Excel or CSV files found in the selected folder(s).")
            return
        ok, msg = self.data_processor.load_data_from_files(file_list)
        if ok:
            messagebox.showinfo("Load Success", msg)
            self._update_treeview()
        else:
            messagebox.showerror("Load Error", msg)
        self.update_dashboard()

    def _on_live_search_key(self, event=None):
        if self._filter_after_id:
            self.after_cancel(self._filter_after_id)
        self._filter_after_id = self.after(self.filter_delay_ms, self._schedule_async_filter)

    def _schedule_async_filter(self):
        self._filter_after_id = None
        row_count = len(getattr(self.data_processor, 'raw_data', []))
        if row_count < 50000:
            self._apply_all_filters()
            return
        if getattr(self, '_filter_thread_running', False):
            self._pending_refilter = True
            return
        self._pending_refilter = False
        self._filter_thread_running = True
        def worker():
            try:
                self._apply_all_filters()
            finally:
                self._filter_thread_running = False
                if getattr(self, '_pending_refilter', False):
                    self._pending_refilter = False
                    self.after(10, self._schedule_async_filter)
        threading.Thread(target=worker, daemon=True).start()

    def _apply_filters_on_event(self, event=None):
        self._on_live_search_key()

    def _apply_all_filters(self):
        def compute():
            filters: Dict[str, Any] = {'CaseInsensitive': True}
            if self.dept_filter_var.get():
                filters['Department'] = self.dept_filter_var.get()
                filters['DepartmentOperator'] = self.dept_operator_var.get()
            if self.global_search_var.get():
                filters['GlobalSearch'] = self.global_search_var.get()
                filters['GlobalSearchOperator'] = self.global_operator_var.get()
            if self.current_date_filter:
                filters['DateFilter'] = self.current_date_filter
            self.data_processor.apply_filters(filters)
            return filters
        filters_used = compute()
        def ui():
            self._update_treeview()
            self.update_dashboard()
            self.logger.info(f"Applied filters: {filters_used}")
        if threading.current_thread().name == "MainThread":
            ui()
        else:
            self.after(0, ui)

    def _update_treeview(self):
        if not hasattr(self, 'tree'):
            return
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data is None:
            self.data_processor.filtered_data = pd.DataFrame()
        self.tree.delete(*self.tree.get_children())
        df = self.data_processor.filtered_data
        if df.empty:
            if hasattr(self, 'status_var'):
                self.status_var.set("No data to display.")
            return

        all_cols = df.columns.tolist()
        for c in all_cols:
            if c not in self.column_config:
                self.column_config[c] = {"visible": True, "order": self.default_column_order, "width": 150}
                self.default_column_order += 1
        mapping = self._build_column_mapping(all_cols)
        priority = ["Department", "Closing Date", "Title", "Tender ID", "Direct URL", "Status URL"]
        visible = []
        for std in priority:
            actual = mapping.get(std, std)
            if actual in all_cols and self.column_config.get(actual, {}).get("visible", True):
                visible.append(actual)
        for c in sorted([c for c in all_cols if c not in visible],
                        key=lambda x: self.column_config.get(x, {}).get("order", 999)):
            if self.column_config.get(c, {}).get("visible", True):
                visible.append(c)

        self.tree.configure(columns=visible)
        self.url_columns = []
        for col in visible:
            lower = col.lower()
            if any(k in lower for k in ['url', 'link', 'http']):
                self.url_columns.append(col)
            width = self.column_config.get(col, {}).get("width", 150)
            heading = col + (" ↑" if col == self.sort_column and self.sort_ascending else
                             " ↓" if col == self.sort_column else "")
            self.tree.heading(col, text=heading,
                              command=lambda c=col: self._on_treeview_heading_click(c))
            anchor = 'center' if (col in self.url_columns or any(k in lower for k in
                                                                 ['date', 'time', 'deadline', 'closing'])) else 'w'
            self.tree.column(col, width=width, minwidth=80, anchor=anchor)

        for _, row in df.iterrows():
            vals = []
            for col in visible:
                v = row.get(col)
                if isinstance(v, (pd.Series, pd.DataFrame)) or v is None or pd.isna(v):
                    vals.append("")
                    continue
                if pd.api.types.is_datetime64_any_dtype(df[col].dtype):
                    dt = pd.to_datetime(v, errors='coerce')
                    vals.append("" if pd.isna(dt) else dt.strftime("%Y-%m-%d %H:%M" if dt.hour or dt.minute else "%Y-%m-%d"))
                    continue
                if col in self.url_columns and isinstance(v, str) and (v.startswith('http') or v.startswith('www')):
                    vals.append("🔗")
                    continue
                vals.append(str(v))
            item_id = self.tree.insert("", "end", values=vals)
            base_tag = 'evenrow' if len(self.tree.get_children()) % 2 == 0 else 'oddrow'
            self.tree.item(item_id, tags=[base_tag])

        if hasattr(self, 'status_var'):
            self.status_var.set(f"Showing {len(df)} tender records.")
        self.logger.info(f"Treeview updated with {len(df)} rows.")

    def _build_column_mapping(self, all_columns: List[str]) -> Dict[str, str]:
        """Build a resilient mapping from standardized logical names to actual dataset columns."""
        mapping: Dict[str, str] = {}
        for col in all_columns:
            cl = str(col).lower()
            if ("department" in cl or "dept" in cl) and "Department" not in mapping:
                mapping["Department"] = col
            if any(k in cl for k in ("closing", "due date", "deadline", "expiry")) and "Closing Date" not in mapping:
                mapping["Closing Date"] = col
            if any(k in cl for k in ("title", "name", "description", "subject")) and "Title" not in mapping:
                mapping["Title"] = col
            if (("tender" in cl and "id" in cl) or "ref.no" in cl or "reference" in cl) and "Tender ID" not in mapping:
                mapping["Tender ID"] = col
            if ("url" in cl or "link" in cl) and "direct" in cl and "Direct URL" not in mapping:
                mapping["Direct URL"] = col
            if ("url" in cl or "link" in cl) and "status" in cl and "Status URL" not in mapping:
                mapping["Status URL"] = col
        return mapping

    def _show_data_visualization(self):
        """Basic department + monthly charts (matplotlib optional)."""
        if (not hasattr(self.data_processor, 'filtered_data') or
                self.data_processor.filtered_data is None):
            self.data_processor.filtered_data = pd.DataFrame()
        if self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "No data to visualize.")
            return
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            messagebox.showerror("Missing Dependency", "Install matplotlib to view charts.")
            return
        df = self.data_processor.filtered_data
        dept_col = next((c for c in df.columns if 'department' in c.lower() or 'dept' in c.lower()), None)
        if not dept_col:
            messagebox.showinfo("Missing Column", "No department column found.")
            return
        win = tk.Toplevel(self)
        win.title("Charts")
        nb = ttk.Notebook(win)
        nb.pack(fill='both', expand=True)
        tab1 = ttk.Frame(nb)
        tab2 = ttk.Frame(nb)
        nb.add(tab1, text="Departments")
        nb.add(tab2, text="Monthly")
        fig1, ax1 = plt.subplots(figsize=(9,5))
        df[dept_col].value_counts().head(15).plot(kind='bar', ax=ax1, color=COLORS.get('primary', '#1976d2'))
        ax1.set_title("Top 15 Departments")
        ax1.set_ylabel("Count")
        ax1.grid(axis='y', linestyle='--', alpha=0.4)
        FigureCanvasTkAgg(fig1, master=tab1).get_tk_widget().pack(fill='both', expand=True)
        self.logger.info("Visualization window opened")

    def _update_saved_searches_list(self):
        saved = self.main_app.global_config.get("saved_searches", {})
        names = list(saved.keys())
        if hasattr(self, 'saved_searches_combo'):
            self.saved_searches_combo['values'] = names
            if not names:
                self.saved_searches_combo.set("No saved searches")
            elif self.saved_search_var.get() not in names:
                self.saved_searches_combo.set("")

    def _save_current_search(self):
        profile = {
            "department_filter": self.dept_filter_var.get(),
            "global_search": self.global_search_var.get(),
            "date_filter": self.current_date_filter.copy() if self.current_date_filter else {}
        }
        name = tkinter.simpledialog.askstring("Save Search Profile", "Enter profile name:", parent=self)
        if not name:
            return
        saved = self.main_app.global_config.get("saved_searches", {})
        if name in saved:
            if not messagebox.askyesno("Overwrite", f"Profile '{name}' exists. Overwrite?", parent=self):
                return
        saved[name] = profile
        self.main_app.global_config.set("saved_searches", saved)
        self.main_app.global_config.save_config()
        self._update_saved_searches_list()
        self.saved_search_var.set(name)
        self.logger.info(f"Saved search profile '{name}'")

    def _load_saved_search(self, event=None):
        name = self.saved_search_var.get()
        saved = self.main_app.global_config.get("saved_searches", {})
        if name not in saved:
            return
        profile = saved[name]
        self.dept_filter_var.set(profile.get("department_filter", ""))
        self.global_search_var.set(profile.get("global_search", ""))
        self.current_date_filter = profile.get("date_filter", {})
        self._apply_all_filters()
        self.logger.info(f"Loaded search profile '{name}'")

    def _delete_saved_search(self):
        name = self.saved_search_var.get()
        if not name:
            return
        saved = self.main_app.global_config.get("saved_searches", {})
        if name not in saved:
            return
        if not messagebox.askyesno("Confirm", f"Delete search profile '{name}'?", parent=self):
            return
        del saved[name]
        self.main_app.global_config.set("saved_searches", saved)
        self.main_app.global_config.save_config()
        self._update_saved_searches_list()
        self.saved_search_var.set("")
        self.logger.info(f"Deleted search profile '{name}'")

    def _show_column_config_dialog(self):
        """Lightweight column visibility/order dialog."""
        if not hasattr(self, 'tree'):
            return
        win = tk.Toplevel(self)
        win.title("Column Settings")
        win.grab_set()
        frm = ttk.Frame(win, padding=10)
        frm.pack(fill='both', expand=True)
        cols = list(self.column_config.keys())
        for c in self.tree['columns']:
            if c not in cols:
                cols.append(c)
        cols = sorted(cols, key=lambda c: self.column_config.get(c, {}).get("order", 999))
        self._col_vars = {}
        for i, c in enumerate(cols):
            cfg = self.column_config.setdefault(c, {"visible": True, "order": 100+i, "width": 150})
            var = tk.BooleanVar(value=cfg.get("visible", True))
            self._col_vars[c] = var
            row = ttk.Frame(frm)
            row.pack(fill='x', pady=2)
            ttk.Checkbutton(row, text=c, variable=var).pack(side='left')
        btn_bar = ttk.Frame(frm)
        btn_bar.pack(fill='x', pady=(8,0))
        ttk.Button(btn_bar, text="Apply",
                   command=lambda: (self._apply_column_visibility_changes(), self._update_treeview(), win.destroy())
                  ).pack(side='right', padx=4)
        ttk.Button(btn_bar, text="Cancel", command=win.destroy).pack(side='right')

    def _apply_column_visibility_changes(self):
        for name, var in self._col_vars.items():
            self.column_config[name]["visible"] = bool(var.get())

    def _on_treeview_double_click(self, event):
        """Handle double-click on treeview."""
        if not hasattr(self, 'tree'):
            return
        item_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not item_id or not col_id.startswith("#"):
            return
        try:
            col_index = int(col_id[1:]) - 1
        except ValueError:
            return
        columns = self.tree['columns']
        if col_index < 0 or col_index >= len(columns):
            return
        col_name = columns[col_index]
        val = self.tree.item(item_id, 'values')[col_index]
        if col_name in getattr(self, 'url_columns', []) and val == "🔗":
            url = None
            for tag in self.tree.item(item_id, 'tags'):
                if tag.startswith(f"url_{col_index}_"):
                    url = tag.split("_", 2)[2]
                    break
            if url:
                if not (url.startswith("http://") or url.startswith("https://")):
                    url = "http://" + url
                try:
                    webbrowser.open_new_tab(url)
                    if hasattr(self, 'status_var'):
                        self.status_var.set(f"Opened URL: {url}")
                except Exception as e:
                    messagebox.showerror("Open URL Failed", str(e))

    def _show_treeview_context_menu(self, event):
        """Show context menu for treeview."""
        if not hasattr(self, 'tree'):
            return
        menu = tk.Menu(self, tearoff=0)
        item_id = self.tree.identify_row(event.y)
        if item_id:
            if item_id not in self.tree.selection():
                self.tree.selection_set(item_id)
            menu.add_command(label="Copy Row", command=lambda i=item_id: self._copy_single_treeview_row(i))
        if menu.index(tk.END) is not None:
            menu.tk_popup(event.x_root, event.y_root)

    def _copy_single_treeview_row(self, item_id: str):
        if not item_id:
            return
        vals = self.tree.item(item_id, 'values')
        self.clipboard_clear()
        self.clipboard_append("\t".join(map(str, vals)))

    def _on_treeview_heading_click(self, column: str):
        """Toggle sort on a column and refresh tree."""
        try:
            if self.sort_column == column:
                self.sort_ascending = not self.sort_ascending
            else:
                self.sort_column = column
                self.sort_ascending = True
            self.logger.info(f"Sorting by {column} {'ASC' if self.sort_ascending else 'DESC'}")
            self._update_treeview()
        except Exception as e:
            self.logger.error(f"Error sorting column {column}: {e}")

    def _export_to_excel(self):
        """Export currently filtered + visible columns to Excel."""
        if self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "There is no data to export.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Export Data to Excel"
        )
        if not filename:
            return
        try:
            cols = list(self.tree["columns"])
            self.data_processor.filtered_data[cols].to_excel(filename, index=False, engine='openpyxl')
            messagebox.showinfo("Export", "Exported to Excel successfully.")
            self.logger.info(f"Excel export: {filename}")
        except Exception as e:
            self.logger.error(f"Excel export failed: {e}", exc_info=True)
            messagebox.showerror("Export Error", str(e))

    def _export_to_csv(self):
        """Export currently filtered + visible columns to CSV."""
        if self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "There is no data to export.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Data to CSV"
        )
        if not filename:
            return
        try:
            cols = list(self.tree["columns"])
            self.data_processor.filtered_data[cols].to_csv(filename, index=False)
            messagebox.showinfo("Export", "Exported to CSV successfully.")
            self.logger.info(f"CSV export: {filename}")
        except Exception as e:
            self.logger.error(f"CSV export failed: {e}", exc_info=True)
            messagebox.showerror("Export Error", str(e))

    # ...existing code through load_initial_data_if_any method...