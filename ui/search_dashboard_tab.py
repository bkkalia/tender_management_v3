# ui/search_dashboard_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd # For Treeview population
import logging
import os
import sys
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Union
import webbrowser # For opening URLs
from datetime import datetime, timedelta # For date filters
import threading
import time
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
    def __init__(self, parent: ttk.Notebook, main_app: 'MainApplication'):
        super().__init__(parent)
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self.data_processor = TenderDataProcessor(self.main_app.global_config)
        self.loaded_files: List[str] = []

        # UI Variables
        self.dept_filter_var = tk.StringVar()
        self.global_search_var = tk.StringVar()
        self.selected_folders_var = tk.StringVar(value="No folders selected.")
        self.custom_date_start_var = tk.StringVar()
        self.custom_date_end_var = tk.StringVar()
        
        # Date filter state
        self.current_date_filter: Dict[str, Any] = {}

        # Add state for clock/date display
        self.clock_running = False
        self.current_time_var = tk.StringVar(value="Loading...")
        self.current_date_var = tk.StringVar(value="")
        
        # Initialize tooltip attribute
        self.tooltip = None

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

        # Create collapsible data folders frame
        self.data_folders_frame_container = ttk.Frame(top_frame)
        self.data_folders_frame_container.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['small']))
        self.data_folders_frame_visible = True
        
        # Header frame with collapse button
        header_frame = ttk.Frame(self.data_folders_frame_container)
        header_frame.pack(side=tk.TOP, fill=tk.X)
        
        # More compact layout for header controls
        self.toggle_button = ttk.Button(
            header_frame, 
            text="▼", 
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
        
        # Create the collapsible content frame
        self.data_folders_content = create_labeled_frame(self.data_folders_frame_container, "")
        self.data_folders_content.pack(side=tk.TOP, fill=tk.X)
        self._create_data_folder_widgets(self.data_folders_content)

        # Use PanedWindow for better space management of search and results areas
        main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, sashwidth=4, sashrelief="raised")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=SPACING['medium'], pady=(0, SPACING['small']))

        # Search and filter section with reduced padding
        search_filter_frame = create_labeled_frame(main_pane, "Search, Filter & Dates")
        main_pane.add(search_filter_frame, height=120, minsize=80)
        self._create_search_filter_widgets(search_filter_frame)
        self._create_date_filter_widgets(search_filter_frame)

        # Results section with flexible height
        tender_data_frame = create_labeled_frame(main_pane, "Tender Data")
        main_pane.add(tender_data_frame, height=400, minsize=200)
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
        
        # Configure grid with equal column weights
        for i in range(10):  # We have 10 metrics
            dashboard_container.columnconfigure(i, weight=1)
        
        # Define metrics with their properties
        self.dashboard_labels = {}
        metrics = [
            # key, title, color
            ("total_tenders", "Total\nTenders", COLORS.get('primary', '#1976d2')),
            ("filtered_tenders", "Filtered\nResults", COLORS.get('info', '#0288d1')),
            ("match_percentage", "Filter\nMatch %", COLORS.get('success', '#4caf50')),
            ("unique_departments", "Depts", COLORS.get('warning', '#ff9800')),
            ("closing_today", "Due\nToday", COLORS.get('danger', '#f44336')),
            ("closing_next_3_days", "Due in\n3 Days", COLORS.get('secondary', '#9c27b0')),
            ("closing_next_7_days", "Due in\n7 Days", COLORS.get('info_dark', '#01579b')),
            ("expired_tenders", "Expired\nTenders", COLORS.get('danger_light', '#ef5350')),
            ("data_sources", "Data\nSources", COLORS.get('secondary_light', '#ba68c8')),
            ("current_date", "Date &\nTime", COLORS.get('primary_dark', '#1a237e'))
        ]
        
        # Create a card for each metric
        for i, (key, title, color) in enumerate(metrics):
            # Create card frame with solid background
            card_frame = tk.Frame(dashboard_container, bg=color, width=100, height=100)
            card_frame.grid(row=0, column=i, padx=2, sticky="nsew")
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
        dept_entry.bind("<KeyRelease>", self._apply_filters_on_event)  # Live search
        
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
        search_entry.bind("<KeyRelease>", self._apply_filters_on_event)  # Live search
        
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
        date_filter_frame = ttk.Frame(parent)
        date_filter_frame.pack(side=tk.TOP, fill=tk.X, pady=SPACING['small'])

        create_info_label(date_filter_frame, "Closing Date Filters:").pack(side=tk.LEFT, padx=(0, SPACING['medium']))

        # Preset date filter buttons
        presets = {
            "Today": "today", 
            "Next 3 Days": "next_3_days", 
            "Next 7 Days": "next_7_days", 
            "Next 30 Days": "next_30_days",
            "Expired": "expired"  # New filter for expired tenders
        }
        
        for text, preset_key in presets.items():
            btn_type = 'danger_outline' if preset_key == 'expired' else 'info_outline'
            btn = create_action_button(date_filter_frame, text, lambda p=preset_key: self._filter_by_date_preset(p), 
                                      width=12, button_type=btn_type)
            btn.pack(side=tk.LEFT, padx=SPACING['small']//2)

        # Custom Date Range with Calendar Pickers (only if tkcalendar is available)
        if HAS_TKCALENDAR and DateEntry is not None:
            custom_frame = ttk.Frame(date_filter_frame)
            custom_frame.pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
            create_info_label(custom_frame, "Custom:").pack(side=tk.LEFT)
            
            # Start date picker
            start_date_frame = ttk.Frame(custom_frame)
            start_date_frame.pack(side=tk.LEFT, padx=SPACING['small']//2)
            
            self.start_date_picker = DateEntry(
                start_date_frame, 
                width=12,
                background=COLORS.get('primary', 'blue'),
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                selectmode='day'
            )
            self.start_date_picker.pack(side=tk.LEFT)
            self.start_date_picker.bind("<<DateEntrySelected>>", self._on_calendar_date_selected)
            
            create_info_label(custom_frame, "to").pack(side=tk.LEFT)
            
            # End date picker
            end_date_frame = ttk.Frame(custom_frame)
            end_date_frame.pack(side=tk.LEFT, padx=SPACING['small']//2)
            
            self.end_date_picker = DateEntry(
                end_date_frame, 
                width=12,
                background=COLORS.get('primary', 'blue'),
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                selectmode='day'
            )
            self.end_date_picker.pack(side=tk.LEFT)
            self.end_date_picker.bind("<<DateEntrySelected>>", self._on_calendar_date_selected)
            
            # Apply custom date filter button
            apply_custom_btn = create_action_button(custom_frame, "Apply", self._apply_custom_date_filter, button_type='info')
            apply_custom_btn.pack(side=tk.LEFT, padx=SPACING['small']//2)
        else:
            # Fallback: Simple text entry for dates
            custom_frame = ttk.Frame(date_filter_frame)
            custom_frame.pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
            create_info_label(custom_frame, "Custom (YYYY-MM-DD):").pack(side=tk.LEFT)
            
            self.start_date_entry = create_input_entry(custom_frame, self.custom_date_start_var, width=12)
            self.start_date_entry.pack(side=tk.LEFT, padx=SPACING['small']//2)
            
            create_info_label(custom_frame, "to").pack(side=tk.LEFT)
            
            self.end_date_entry = create_input_entry(custom_frame, self.custom_date_end_var, width=12)
            self.end_date_entry.pack(side=tk.LEFT, padx=SPACING['small']//2)
            
            apply_custom_btn = create_action_button(custom_frame, "Apply", self._apply_custom_date_filter_text, button_type='info')
            apply_custom_btn.pack(side=tk.LEFT, padx=SPACING['small']//2)

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
            
        start_date = self.start_date_picker.get()
        end_date = self.end_date_picker.get()
        
        if not start_date or not end_date:
            messagebox.showwarning("Date Range Required", "Please select both start and end dates.")
            return
            
        self.logger.info(f"Applying custom date filter: {start_date} to {end_date}")
        self.current_date_filter = {
            'type': 'custom',
            'start_date': start_date,
            'end_date': end_date
        }
        
        self._apply_all_filters()

    def _apply_custom_date_filter_text(self):
        """Apply the custom date range filter from text entries (fallback when tkcalendar is not available)."""
        start_date = self.custom_date_start_var.get()
        end_date = self.custom_date_end_var.get()
        
        if not start_date or not end_date:
            messagebox.showwarning("Date Range Required", "Please enter both start and end dates in YYYY-MM-DD format.")
            return
            
        # Validate date format
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date Format", "Please enter dates in YYYY-MM-DD format (e.g., 2024-12-31).")
            return
            
        self.logger.info(f"Applying custom date filter: {start_date} to {end_date}")
        self.current_date_filter = {
            'type': 'custom',
            'start_date': start_date,
            'end_date': end_date
        }
        
        self._apply_all_filters()

    def _setup_treeview_bindings(self):
        self.tree.bind("<Double-1>", self._on_treeview_double_click)
        self.tree.bind("<Button-3>", self._show_treeview_context_menu)  # Right-click for context menu

    def _show_treeview_context_menu(self, event):
        self.tree.focus_set()
        item_id = self.tree.identify_row(event.y)
        
        context_menu = tk.Menu(self, tearoff=0)
        
        if item_id:
            # Select the item if not already part of a multi-selection
            if item_id not in self.tree.selection():
                self.tree.selection_set(item_id)
            
            context_menu.add_command(label="Copy Cell Value", command=lambda e=event: self._copy_treeview_cell_value(e))
            context_menu.add_command(label="Copy This Row", command=lambda i=item_id: self._copy_single_treeview_row(i))
            
            # Add separator before Calendar option
            context_menu.add_separator()
            
            # Only keep Calendar option
            context_menu.add_command(label="Add to Calendar", command=lambda i=item_id: self._add_to_calendar(i))
        
        selected_items = self.tree.selection()
        if selected_items:
            label = f"Copy {len(selected_items)} Selected Row(s)" if len(selected_items) > 1 else "Copy Selected Row"
            context_menu.add_command(label=label, command=self._copy_selected_treeview_rows)
            
            # Add multi-selection option for Calendar only
            if len(selected_items) > 1:
                context_menu.add_separator()
                context_menu.add_command(label=f"Add {len(selected_items)} Items to Calendar", 
                                    command=self._add_multiple_to_calendar)

        # Fix: properly indent these lines to be part of the method
        if context_menu.index(tk.END) is not None:
            context_menu.tk_popup(event.x_root, event.y_root)

    def _copy_treeview_cell_value(self, event):
        item_id = self.tree.identify_row(event.y)
        col_id_str = self.tree.identify_column(event.x)
        if item_id and col_id_str:
            try:
                if not col_id_str.startswith("#") or not col_id_str[1:].isdigit():
                    self.logger.warning(f"Invalid column identifier: {col_id_str}")
                    return
                col_index = int(col_id_str.replace('#', '')) - 1
                
                if col_index >= 0 and col_index < len(self.tree["columns"]):
                    value = self.tree.item(item_id, 'values')[col_index]
                    
                    # If the value is the link icon, get the actual URL from tags
                    if value == "🔗":
                        col_name = self.tree["columns"][col_index]
                        if col_name in self.url_columns:
                            # Get the URL from the item's tags
                            tags = self.tree.item(item_id, 'tags')
                            url = None
                            
                            if tags:
                                for tag in tags:
                                    if isinstance(tag, str) and tag.startswith(f"url_{col_index}_"):
                                        url = tag[len(f"url_{col_index}_"):]

                                        break
                            
                            if url:
                                value = url  # Use the URL instead of the icon
                                self.logger.info(f"Retrieved URL from tag: {url}")
                            else:
                                self.logger.warning(f"No URL found in tags for link icon at column {col_index}")
                    
                    self.clipboard_clear()
                    self.clipboard_append(str(value))
                    self.logger.info(f"Copied cell value: {value}")
                else:
                    self.logger.warning(f"Column index {col_index} out of bounds for item {item_id}.")
            except IndexError:
                self.logger.warning(f"Could not copy cell value: column index out of bounds for item {item_id}.")
            except Exception as e:
                self.logger.error(f"Error copying cell value: {e}")

    def _copy_single_treeview_row(self, item_id: str):
        if item_id:
            values = self.tree.item(item_id, 'values')
            row_string = "\t".join(map(str, values))
            self.clipboard_clear()
            self.clipboard_append(row_string)
            self.logger.info(f"Copied row: {item_id}")

    def _copy_selected_treeview_rows(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        all_rows_data = []
        # Add header
        headers = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
        all_rows_data.append("\t".join(headers))

        for item_id in selected_items:
            values = self.tree.item(item_id, 'values')
            all_rows_data.append("\t".join(map(str, values)))
        
        self.clipboard_clear()
        self.clipboard_append("\n".join(all_rows_data))
        self.logger.info(f"Copied {len(selected_items)} selected rows.")

    def _on_treeview_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column_id_str = self.tree.identify_column(event.x)

        if not item_id or not column_id_str:
            return

        try:
            if not column_id_str.startswith("#") or not column_id_str[1:].isdigit():
                self.logger.warning(f"Invalid column identifier on double click: {column_id_str}")
                return
            column_index = int(column_id_str.replace('#', '')) - 1
            if column_index < 0 or column_index >= len(self.tree["columns"]):
                self.logger.warning(f"Column index {column_index} out of bounds on double click.")
                return

            column_name = self.tree["columns"][column_index]
            cell_value = self.tree.item(item_id, 'values')[column_index]

            # Check if this is a URL column
            if column_name in self.url_columns:
                # Get the original URL from the item's tags if it exists
                tags = self.tree.item(item_id, 'tags')
                url = None
                
                if tags:
                    for tag in tags:
                        if isinstance(tag, str) and tag.startswith(f"url_{column_index}_"):
                            url = tag[len(f"url_{column_index}_"):]

                            break
                
                # If no URL found in tags, use the cell value
                if not url and cell_value == "🔗":
                    # If we're displaying the link icon but no URL tag, try to find it
                    for tag in self.tree.item(item_id, 'tags'):
                        if isinstance(tag, str) and tag.startswith("url_"):
                            parts = tag.split("_", 2)
                            if len(parts) >= 3:
                                url = parts[2]
                                break
                elif not url:
                    url = cell_value
                
                # Debug log the tags we found
                self.logger.debug(f"Double-click on URL column. Tags: {tags}, URL found: {url}")
                    
                if url and isinstance(url, str):
                    url = url.strip()
                    if url == "🔗":
                        self.logger.warning("Link icon clicked but no URL found.")
                        return
                        
                    # Add http:// prefix if needed
                    if not (url.startswith('http://') or url.startswith('https://')):
                        url = 'http://' + url
                    
                    try:
                        webbrowser.open_new_tab(url)
                        self.status_var.set(f"Opened URL: {url}")
                        self.logger.info(f"Opened URL: {url}")
                    except Exception as e:
                        self.logger.error(f"Failed to open URL {url}: {e}")
                        messagebox.showerror("Open URL Failed", f"Could not open URL: {url}\nError: {e}")
        
        except Exception as e:
            self.logger.error(f"Error processing treeview double-click: {e}", exc_info=True)

    def _create_tender_data_widgets(self, parent: Union[ttk.Frame, ttk.LabelFrame]):
        # Create a frame to hold both controls and treeview
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill='both', expand=True)
        
        # Add toolbar above treeview
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['small']))
        
        # Add column config button
        column_config_btn = create_action_button(
            toolbar_frame, "Column Settings", self._show_column_config_dialog, 
            button_type='info_outline', width=15
        )
        column_config_btn.pack(side=tk.LEFT, padx=SPACING['small'])
        
        # Add export buttons
        export_frame = ttk.Frame(toolbar_frame)
        export_frame.pack(side=tk.RIGHT, padx=SPACING['small'])
        
        create_action_button(
            export_frame, "Export Excel", self._export_to_excel,
            button_type='success_outline', width=12
        ).pack(side=tk.LEFT, padx=2)
        
        create_action_button(
            export_frame, "Export CSV", self._export_to_csv,
            button_type='success_outline', width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Add a status bar at the bottom
        self.status_var = tk.StringVar(value="Ready. No data loaded.")
        status_bar = ttk.Label(parent, textvariable=self.status_var, anchor=tk.W, padding=(5, 2))
        status_bar.pack(side='bottom', fill='x')
        
        # Create the treeview with scrollbars in its own frame
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(side=tk.TOP, fill='both', expand=True)
        
        self.tree = ttk.Treeview(tree_frame, show='headings', style='Custom.Treeview')
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure row colors
        style = ttk.Style()
        style.configure("Custom.Treeview", font=FONTS.get('body', ('TkDefaultFont', 10)))
        style.map('Custom.Treeview', background=[('selected', '#3366CC')])
        style.configure("Treeview", rowheight=25)  # Increase row height for better readability
        
        # Setup tags for alternating row colors
        self.tree.tag_configure('oddrow', background='#F5F5F5')
        self.tree.tag_configure('evenrow', background='#FFFFFF')

        # Pack scrollbars and treeview
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        self.tree.pack(side='left', fill='both', expand=True)
        
        # Store URL columns to show link icons
        self.url_columns = []
        
        # Store column configuration with preferred order and visibility
        self.column_config = {
            "Department": {"visible": True, "order": 0, "width": 250},
            "Closing Date": {"visible": True, "order": 1, "width": 120},
            "Title": {"visible": True, "order": 2, "width": 500},
            "Tender ID": {"visible": True, "order": 3, "width": 200},
            "Direct URL": {"visible": True, "order": 4, "width": 80},
            "Status URL": {"visible": True, "order": 5, "width": 80},
        }
        # Default order for columns not explicitly configured
        self.default_column_order = 100

    def _show_column_config_dialog(self):
        """Show dialog to configure column visibility, order and width"""
        # Create a new toplevel window
        config_dialog = tk.Toplevel(self)
        config_dialog.title("Column Configuration")
        config_dialog.geometry("600x500")  # Wider to accommodate width controls
        # Fix the transient call to use the toplevel window instead of self
        config_dialog.transient(self.winfo_toplevel())  # Make the dialog a child of the main window
        config_dialog.grab_set()  # Make dialog modal
        
        # Main frame inside dialog
        main_frame = ttk.Frame(config_dialog, padding=SPACING['medium'])
        main_frame.pack(fill='both', expand=True)
        
        # Instructions
        ttk.Label(main_frame, text="Select columns to display and arrange their order:", 
                 font=FONTS.get('subheading', ('TkDefaultFont', 12, 'bold'))).pack(anchor='w', pady=(0, SPACING['medium']))
        
        # Create header row for column list
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(header_frame, text="Visible", width=8).pack(side='left', padx=(5, 0))
        ttk.Label(header_frame, text="Column Name", width=30).pack(side='left', padx=(5, 0))
        ttk.Label(header_frame, text="Width", width=8).pack(side='left', padx=(5, 0))
        ttk.Label(header_frame, text="Order", width=10).pack(side='left', padx=(5, 0))
        
        # Create scrollable frame for column list
        canvas = tk.Canvas(main_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
    
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
    
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
    
        # Add to main frame
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
        # Get all available columns from current data
        all_columns = []
        if not self.data_processor.filtered_data.empty:
            all_columns = list(self.data_processor.filtered_data.columns)
    
        # Create dictionaries to store UI variables
        self.column_vars = {}     # For visibility checkboxes
        self.width_vars = {}      # For width spinboxes
        self.row_frames = {}      # To reference each row for visual feedback
    
        # Update column_config with any new columns
        for col in all_columns:
            if col not in self.column_config:
                self.column_config[col] = {
                    "visible": True,  # New columns are visible by default
                    "order": self.default_column_order,
                    "width": 150  # Default width
                }
                self.default_column_order += 1
    
        # Sort columns by their order
        sorted_columns = sorted(self.column_config.items(), key=lambda x: x[1]["order"])
    
        # Create control rows for each column
        for i, (col_name, config) in enumerate(sorted_columns):
            # Skip if column doesn't exist in actual data
            if all_columns and col_name not in all_columns:
                continue
                
            # Create a frame for each column row with consistent coloring
            bg_color = '#f0f0f0' if i % 2 == 0 else '#ffffff'
            row_frame = ttk.Frame(scrollable_frame)
            row_frame.pack(fill='x', pady=2)
            self.row_frames[col_name] = row_frame
            
            # Left side: visibility checkbox
            var = tk.BooleanVar(value=config["visible"])
            self.column_vars[col_name] = var
            
            chk = ttk.Checkbutton(row_frame, variable=var, width=5)
            chk.pack(side='left', padx=(5, 2))
            
            # Column name label
            name_label = ttk.Label(row_frame, text=col_name, width=30, anchor='w')
            name_label.pack(side='left', padx=2)
            
            # Width control with spinbox
            width_var = tk.IntVar(value=config.get("width", 150))
            self.width_vars[col_name] = width_var
            
            width_spinbox = ttk.Spinbox(row_frame, from_=50, to=1000, increment=10, 
                                       textvariable=width_var, width=6)
            width_spinbox.pack(side='left', padx=5)
            
            # Order control buttons
            btn_frame = ttk.Frame(row_frame)
            btn_frame.pack(side='left', padx=5)
            
            up_btn = ttk.Button(btn_frame, text="▲", width=3, 
                               command=lambda name=col_name: self._move_column_up(name, config_dialog))
            up_btn.pack(side='left', padx=2)
            
            down_btn = ttk.Button(btn_frame, text="▼", width=3, 
                                 command=lambda name=col_name: self._move_column_down(name, config_dialog))
            down_btn.pack(side='left', padx=2)
        
        # Add buttons at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=SPACING['medium'])
        
        ttk.Button(button_frame, text="Apply", command=lambda: self._apply_column_config(config_dialog)).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=config_dialog.destroy).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Reset to Default", command=lambda: self._reset_column_config(config_dialog)).pack(side='left', padx=5)

    def _move_column_up(self, column_name, dialog=None):
        """Move a column up in the order with visual feedback"""
        current_order = self.column_config[column_name]["order"]
        
        # Find the column that's right before this one
        columns_before = [col for col, cfg in self.column_config.items() 
                         if cfg["order"] < current_order]
        
        if not columns_before:
            return  # Already at the top
            
        prev_col = max(columns_before, key=lambda col: self.column_config[col]["order"])
        prev_order = self.column_config[prev_col]["order"]
        
        # Swap the orders
        self.column_config[column_name]["order"] = prev_order
        self.column_config[prev_col]["order"] = current_order
        
        # If dialog is provided, refresh the dialog UI to show new order
        if dialog and hasattr(self, 'row_frames'):
            self._refresh_column_order_dialog(dialog)

    def _move_column_down(self, column_name, dialog=None):
        """Move a column down in the order with visual feedback"""
        current_order = self.column_config[column_name]["order"]
        
        # Find the column that's right after this one
        columns_after = [col for col, cfg in self.column_config.items() 
                        if cfg["order"] > current_order]
        
        if not columns_after:
            return  # Already at the bottom
            
        next_col = min(columns_after, key=lambda col: self.column_config[col]["order"])
        next_order = self.column_config[next_col]["order"]
        
        # Swap the orders
        self.column_config[column_name]["order"] = next_order
        self.column_config[next_col]["order"] = current_order
        
        # If dialog is provided, refresh the dialog UI to show new order
        if dialog and hasattr(self, 'row_frames'):
            self._refresh_column_order_dialog(dialog)

    def _refresh_column_order_dialog(self, dialog):
        """Refresh the column order display in the dialog to show current order"""
        # Initialize canvas and scrollable_frame to avoid unbound variables
        canvas = None
        scrollable_frame = None
        
        # Get the canvas and scrollable frame widgets
        for widget in dialog.winfo_children():
            if isinstance(widget, ttk.Frame):  # Main frame
                for child in widget.winfo_children():
                    if isinstance(child, tk.Canvas):  # Canvas with scrollable frame
                        canvas = child
                        # Get the scrollable frame
                        if canvas.winfo_children():
                            scrollable_frame = canvas.winfo_children()[0]
                        break
                break
        
        # Check if we found the widgets to avoid unbound variable errors
        if canvas is None or scrollable_frame is None:
            self.logger.warning("Could not find canvas or scrollable frame in dialog")
            return
            
        # Remember current scroll position to maintain it after refresh
        current_scroll = canvas.yview()
        
        # Remove all existing rows
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        
        # Sort columns by their order
        sorted_columns = sorted(self.column_config.items(), key=lambda x: x[1]["order"])
        
        # Recreate all rows in new order
        for i, (col_name, config) in enumerate(sorted_columns):
            # Skip columns that don't exist in the actual data
            if not hasattr(self, 'column_vars') or col_name not in self.column_vars:
                continue
                
            # Create a frame for each column row with consistent coloring
            bg_color = '#f0f0f0' if i % 2 == 0 else '#ffffff'
            row_frame = ttk.Frame(scrollable_frame)
            row_frame.pack(fill='x', pady=2)
            self.row_frames[col_name] = row_frame
            
            # Left side: visibility checkbox
            var = self.column_vars[col_name]  # Reuse existing variable
            
            chk = ttk.Checkbutton(row_frame, variable=var, width=5)
            chk.pack(side='left', padx=(5, 2))
            
            # Column name label
            name_label = ttk.Label(row_frame, text=col_name, width=30, anchor='w')
            name_label.pack(side='left', padx=2)
            
            # Width control with spinbox
            width_var = self.width_vars[col_name]  # Reuse existing variable
            
            width_spinbox = ttk.Spinbox(row_frame, from_=50, to=1000, increment=10, 
                                       textvariable=width_var, width=6)
            width_spinbox.pack(side='left', padx=5)
            
            # Order control buttons
            btn_frame = ttk.Frame(row_frame)
            btn_frame.pack(side='left', padx=5)
            
            up_btn = ttk.Button(btn_frame, text="▲", width=3, 
                               command=lambda name=col_name: self._move_column_up(name, dialog))
            up_btn.pack(side='left', padx=2)
            
            down_btn = ttk.Button(btn_frame, text="▼", width=3, 
                                 command=lambda name=col_name: self._move_column_down(name, dialog))
            down_btn.pack(side='left', padx=2)
        
        # Restore scroll position
        canvas.yview_moveto(current_scroll[0])

    def _reset_column_config(self, dialog):
        """Reset column configuration to default values"""
        # Default column order
        default_order = {
            "Department Name": 0,
            "Closing Date": 1,
            "Title and Ref.No./Tender ID": 2,
            "Tender ID (Extracted)": 3,
            "Direct URL": 4,
            "Status URL": 5
        }
        
        # Reset column order and width
        for i, (col_name, config) in enumerate(self.column_config.items()):
            if col_name in default_order:
                self.column_config[col_name]["order"] = default_order[col_name]
            else:
                self.column_config[col_name]["order"] = 100 + i
                
            # Reset width based on column type
            col_lower = col_name.lower()
            if 'title' in col_lower or 'name' in col_lower or 'description' in col_lower:
                self.column_config[col_name]["width"] = 500
            elif 'id' in col_lower or 'tender' in col_lower or 'reference' in col_lower:
                self.column_config[col_name]["width"] = 200
            elif 'department' in col_lower or 'dept' in col_lower:
                self.column_config[col_name]["width"] = 250
            elif 'date' in col_lower or 'time' in col_lower:
                self.column_config[col_name]["width"] = 120
            elif 'url' in col_lower or 'link' in col_lower:
                self.column_config[col_name]["width"] = 80
            else:
                self.column_config[col_name]["width"] = 150
                
            # Make all columns visible by default
            self.column_config[col_name]["visible"] = True
            
            # Update UI variables if they exist
            if hasattr(self, 'column_vars') and col_name in self.column_vars:
                self.column_vars[col_name].set(True)
            if hasattr(self, 'width_vars') and col_name in self.width_vars:
                self.width_vars[col_name].set(self.column_config[col_name]["width"])
        
        # Refresh dialog UI
        self._refresh_column_order_dialog(dialog)

    def _apply_column_config(self, dialog):
        """Apply the column configuration and close the dialog"""
        # Update visibility and width based on UI variables
        for col in self.column_vars:
            self.column_config[col]["visible"] = self.column_vars[col].get()
            
        for col in self.width_vars:
            self.column_config[col]["width"] = self.width_vars[col].get()
        
        # Update the treeview
        self._update_treeview()
        
        # Close the dialog
        dialog.destroy()

    def _update_treeview(self):
        """Update the Treeview with current filtered data and apply column configuration."""
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Get filtered data from data processor
        filtered_data = self.data_processor.filtered_data
        
        if filtered_data.empty:
            # No data to display
            self.status_var.set("No data to display. Apply different filters or load data.")
            return
        
        # Get search terms for highlighting
        search_terms = getattr(self.data_processor, 'search_terms', [])
        
        # Get all available columns
        all_columns = filtered_data.columns.tolist()
        
        # Update column config with any new columns
        for col in all_columns:
            if col not in self.column_config:
                self.column_config[col] = { # Added missing assignment and corrected structure
                    "visible": True,  # New columns are visible by default
                    "order": self.default_column_order,
                    "width": 150  # Default width
                }
                self.default_column_order += 1
        
        # Map standard column names to actual column names in the data
        # This handles variations in column naming
        column_mapping = {}
        
        # Try to find Department column
        dept_keywords = ['department', 'dept']
        for col in all_columns:
            col_lower = col.lower()
            # Check for each type of column and map to standard name
            if any(keyword in col_lower for keyword in dept_keywords):
                column_mapping["Department"] = col
            elif 'closing' in col_lower or 'due date' in col_lower:
                column_mapping["Closing Date"] = col
            elif 'title' in col_lower or 'name' in col_lower or 'description' in col_lower:
                column_mapping["Title"] = col
            elif ('tender' in col_lower and 'id' in col_lower) or 'ref.no' in col_lower:
                column_mapping["Tender ID"] = col
            elif ('url' in col_lower or 'link' in col_lower) and 'direct' in col_lower:
                column_mapping["Direct URL"] = col
            elif ('url' in col_lower or 'link' in col_lower) and 'status' in col_lower:
                column_mapping["Status URL"] = col
        
        # Determine which columns to display and in what order
        visible_columns = []
        
        # First add the priority columns if they exist in the data (using mapping)
        priority_cols = ["Department", "Closing Date", "Title", "Tender ID", "Direct URL", "Status URL"]
        
        for std_col in priority_cols:
            # Use mapped column if available, otherwise use standard name if it exists in data
            actual_col = column_mapping.get(std_col, std_col)
            if actual_col in all_columns and self.column_config.get(actual_col, {}).get("visible", True):
                visible_columns.append(actual_col)
        
        # Add remaining columns in order of their defined order
        remaining_cols = [col for col in all_columns if col not in visible_columns]
        ordered_remaining = sorted(remaining_cols, 
                                key=lambda col: self.column_config.get(col, {}).get("order", 999))
        
        for col in ordered_remaining:
            if self.column_config.get(col, {}).get("visible", True):
                visible_columns.append(col)
        
        # Set the visible columns in the treeview
        self.tree["columns"] = visible_columns
        
        # Reset URL columns tracking
        self.url_columns = []
        
        # Set column headings and properties
        for col in visible_columns:
            self.tree.heading(col, text=col)
            
            # Get width from configuration or use default based on column type
            col_width = self.column_config.get(col, {}).get("width", 150)
            col_lower = str(col).lower()
            
            # Override width for standard column types if not explicitly set
            if "width" not in self.column_config.get(col, {}):
                # Title columns need much more space
                if any(keyword in col_lower for keyword in ['title', 'name', 'description', 'subject']):
                    col_width = 500
                # ID columns with sufficient width
                elif any(keyword in col_lower for keyword in ['id', 'tender id', 'reference', 'ref.no']):
                    col_width = 200
                # Department columns with enough width
                elif any(keyword in col_lower for keyword in ['dept', 'department']):
                    col_width = 250
                # Date columns with moderate width
                elif any(keyword in col_lower for keyword in ['date', 'time', 'deadline']):
                    col_width = 120
                
                # Save the width back to config
                if col in self.column_config:
                    self.column_config[col]["width"] = col_width
            
            # Check if it's a URL column
            url_keywords = ['url', 'link', 'website', 'site', 'http']
            if any(keyword in col_lower for keyword in url_keywords):
                self.url_columns.append(col)
                # URL columns can be narrower since we'll show an icon
                if "width" not in self.column_config.get(col, {}):
                    col_width = 80
                    if col in self.column_config:
                        self.column_config[col]["width"] = col_width
            
            # Set the column width
            self.tree.column(col, width=col_width, minwidth=80)
        
        # Insert data rows with proper handling of values
        for _, row in filtered_data.iterrows():
            values = []
            for col in visible_columns:
                value = row[col]
                
                # Handle null values - safely handle DataFrame, Series and scalar values
                if isinstance(value, pd.DataFrame):
                    # Handle DataFrame value (fix for indexing errors)
                    if len(value) == 0:
                        values.append("")
                    else:
                        try:
                            # Safely extract first value from DataFrame
                            first_val = value.iat[0, 0] if value.shape[1] > 0 else ""
                            values.append("" if pd.isna(first_val) else str(first_val))
                        except (IndexError, TypeError):
                            values.append(str(value))
                elif isinstance(value, pd.Series):
                    # Handle Series value
                    if len(value) == 0:
                        values.append("")
                    else:
                        try:
                            first_val = value.iloc[0]
                            values.append("" if pd.isna(first_val) else str(first_val))
                        except (IndexError, TypeError):
                            values.append(str(value))
                elif value is None or (not isinstance(value, (pd.DataFrame, pd.Series)) and pd.isna(value)):
                    values.append("")
                # Format date values consistently
                elif pd.api.types.is_datetime64_any_dtype(filtered_data[col].dtype):
                    try:
                        date_str = value.strftime("%Y-%m-%d")
                        values.append(date_str)
                    except:
                        values.append("")
                # Handle URL columns - Fix for pandas Series comparison
                elif col in self.url_columns and isinstance(value, str) and value.strip():
                    # Fix comparison of pandas Series objects - This was the problematic line
                    # Use explicit string methods to avoid Series boolean operations
                    if isinstance(value, str) and (value.startswith('http') or value.startswith('www')):
                        values.append("🔗")  # Link icon
                    else:
                        values.append(value)
                # All other values - with highlighting
                else:
                    str_value = str(value)
                    
                    # Highlight search terms in the displayed value
                    if search_terms and isinstance(str_value, str):
                        highlighted_value = str_value
                        for term in search_terms:
                            if term.lower() in str_value.lower():
                                # Mark matching terms with special characters for highlighting
                                pattern = re.compile(f"({re.escape(term)})", re.IGNORECASE)
                                highlighted_value = pattern.sub(r"••\1••", highlighted_value)
                        values.append(highlighted_value)
                    else:
                        values.append(str_value)
            
            # Store the original row data in the tree item
            item_id = self.tree.insert("", "end", values=values)
            
            # Store original URLs in tags - but don't overwrite item tags completely
            url_tags = []
            for i, col in enumerate(visible_columns):
                if col in self.url_columns:
                    value = row[col]
                    # Fix for pandas Series comparison - Simplify condition to avoid Series operations
                    if isinstance(value, str) and (value.startswith('http') or value.startswith('www')):
                        url_tags.append(f"url_{i}_{value}")
            
            # Apply row color tag
            if len(self.tree.get_children()) % 2 == 0:
                row_tag = 'evenrow'
            else:
                row_tag = 'oddrow'
            
            # Combine URL tags with row color tag
            all_tags = url_tags + [row_tag]
            self.tree.item(item_id, tags=all_tags)
        
        # Create a highlight tag and apply it to cells containing the highlight markers
        self.tree.tag_configure('highlight', background='#FFFF00')  # Yellow background
        
        # After inserting all rows, find and apply highlighting
        self._apply_search_term_highlighting()
        
        self.status_var.set(f"Showing {len(filtered_data)} tender records.")
        self.logger.info(f"Updated treeview with {len(filtered_data)} rows.")

    def _apply_search_term_highlighting(self):
        """Apply visual highlighting to cells that contain search terms."""
        import re
        
        # Configure a tag for highlighted text
        self.tree.tag_configure('highlight', background='#FFFF00')  # Yellow background
        
        # For each item in the treeview
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, 'values')
            
            # Check each cell for highlighting markers
            for i, value in enumerate(values):
                if isinstance(value, str) and '••' in value:
                    # Extract text without the markers
                    clean_text = re.sub(r'••([^•]+)••', r'\1', value)
                    
                    # Update the cell with the clean text
                    new_values = list(values)
                    new_values[i] = clean_text
                    self.tree.item(item_id, values=new_values)
                    
                    # Apply highlight tag to this cell
                    current_tags = list(self.tree.item(item_id, 'tags') or [])
                    if 'highlight' not in current_tags:
                        current_tags.append('highlight')
                        self.tree.item(item_id, tags=current_tags)

    def _clear_folders_for_new_load(self):
        """Clears loaded files and data without user prompting, for internal use."""
        self.loaded_files = []
        # Do not clear global config for last_used_folders here, as this is an internal clear
        self.data_processor.raw_data = pd.DataFrame()
        self.data_processor.filtered_data = pd.DataFrame()
        self._update_treeview()
        self.update_dashboard()
        self.logger.info("Internal: Cleared selected folders and data for new load.")

    def load_single_file_into_processor(self, file_path: str):
        """Loads a single specified file into the data processor and updates the UI."""
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("File Error", f"The file specified for loading does not exist:\n{file_path}", parent=self)
            self.logger.error(f"Attempted to load non-existent file: {file_path}")
            return

        self.logger.info(f"Attempting to load single file: {file_path}")
        # Clear any existing data first
        self._clear_folders_for_new_load() # Use the new internal clear method

        # Update loaded_files to reflect this single file's parent directory for consistency,
        # or treat it as a special "single file load" mode.
        # For simplicity, let's set its directory as the "loaded folder"
        # and the file itself as the only one to load from that "folder".
        
        # This approach is a bit of a hack for _get_all_files_from_selected_folders.
        # A cleaner way would be to have load_data_from_files accept a list of direct file paths
        # For now, we'll make it work with the folder structure.
        
        # Let's assume data_processor.load_data_from_files can handle a list containing a single file path
        success, message = self.data_processor.load_data_from_files([file_path])
        
        if success:
            # Update the selected folders display to show the parent directory of the loaded file
            # This is for UI consistency, though only one file was loaded.
            parent_dir = os.path.dirname(file_path)
            self.loaded_files = [parent_dir] # Show the directory as "loaded"
            self._update_selected_folders_display() # Update UI
            
            self._update_treeview()
            messagebox.showinfo("Load Success", f"Successfully loaded:\n{os.path.basename(file_path)}\n{message}", parent=self)
        else:
            messagebox.showerror("Load Error", message, parent=self)
        self.update_dashboard()


    def _add_folder(self):
        folder_selected = filedialog.askdirectory(
            title="Select Folder Containing Excel/CSV Files",
            initialdir=self.main_app.global_config.get("default_data_folder")
        )
        if folder_selected:
            if folder_selected not in self.loaded_files:
                self.loaded_files.append(folder_selected)
                self.main_app.global_config.set("last_used_folders", self.loaded_files)
                self.main_app.global_config.save_config()
            self._update_selected_folders_display()
            self.logger.info(f"Added folder: {folder_selected}")
            self._load_data_from_folders  # Live load data when folder is added

    def _clear_folders(self):
        self.loaded_files = []
        self.main_app.global_config.set("last_used_folders", [])
        self.main_app.global_config.save_config()
        self._update_selected_folders_display()
        self.data_processor.raw_data = pd.DataFrame() # Clear loaded data
        self.data_processor.filtered_data = pd.DataFrame()
        self._update_treeview()
        self.update_dashboard()
        self.logger.info("Cleared selected folders and data.")

    def _update_selected_folders_display(self):
        if not self.loaded_files:
            self.selected_folders_var.set("No folders selected. Click 'Add Folder'.")
        else:
            display_text = "Selected:\n" + "\n".join([f"- {os.path.basename(f)}" for f in self.loaded_files])
            self.selected_folders_var.set(display_text)

    def _get_all_files_from_selected_folders(self) -> List[str]:
        all_files = []
        for folder_path in self.loaded_files:
            try:
                for item in os.listdir(folder_path):
                    if item.endswith(('.xlsx', '.xls', '.csv')):
                        all_files.append(os.path.join(folder_path, item))
            except Exception as e:
                self.logger.error(f"Error reading folder {folder_path}: {e}")
        return all_files

    def _load_data_from_folders(self):
        excel_files = self._get_all_files_from_selected_folders()
        if not excel_files:
            messagebox.showwarning("No Files", "No Excel or CSV files found in the selected folder(s).")
            return

        success, message = self.data_processor.load_data_from_files(excel_files)
        if success:
            messagebox.showinfo("Load Success", message)
            self._update_treeview()
        else:
            messagebox.showerror("Load Error", message)
        self.update_dashboard()

    def _apply_filters_on_event(self, event=None):
        """Wrapper to call _apply_all_filters from event bindings for live search."""
        self._apply_all_filters()

    def _apply_all_filters(self):
        filters = {}
        # Always apply case-insensitive search for better user experience
        filters['CaseInsensitive'] = True
        
        if self.dept_filter_var.get():
            filters['Department'] = self.dept_filter_var.get()
            filters['DepartmentOperator'] = self.dept_operator_var.get()
            
        if self.global_search_var.get():
            filters['GlobalSearch'] = self.global_search_var.get()
            filters['GlobalSearchOperator'] = self.global_operator_var.get()
        
        # Add date filters if any are active
        if self.current_date_filter:
            filters['DateFilter'] = self.current_date_filter
            
        self.data_processor.apply_filters(filters)
        self._update_treeview()
        self.update_dashboard()
        self.logger.info(f"Applied filters: {filters}")
        
    def _reset_filters(self):
        """Reset all search and date filters to default values."""
        # Clear text filters
        self.dept_filter_var.set("")
        self.global_search_var.set("")
        
        # Reset date filters
        self.current_date_filter = {}
        
        # Reset date pickers to today
        today = datetime.now().strftime("%Y-%m-%d")
        if HAS_TKCALENDAR and hasattr(self, 'start_date_picker'):
            self.start_date_picker.set_date(today)
            self.end_date_picker.set_date(today)
        else:
            # Reset text entries
            self.custom_date_start_var.set("")
            self.custom_date_end_var.set("")
        
        # Apply changes to refresh data
        self._apply_all_filters()
        
        self.logger.info("All filters have been reset")

    def _filter_by_date_preset(self, preset: str):
        """Apply a preset date filter"""
        self.logger.info(f"Applying date filter preset: {preset}")
        self.current_date_filter = {'type': preset}
        
        # Clear custom date fields visually
        today = datetime.now().strftime("%Y-%m-%d")
        self.start_date_picker.set_date(today)
        self.end_date_picker.set_date(today)
        
        self._apply_all_filters()
        
        # Update UI to show which filter is active
        self._highlight_active_date_filter(preset)

    def _highlight_active_date_filter(self, active_preset: str):
        """Update the UI to highlight the active date filter"""
        # Implementation depends on how we want to highlight the active filter
        # This could be done by changing button colors or adding indicators
        pass

    def update_dashboard(self):
        """Update all dashboard stats based on current data."""
        stats = self.data_processor.get_dashboard_stats()
        
        # Update each dashboard card with latest data
        for key, value_label in self.dashboard_labels.items():
            if key in stats:
                if key == "match_percentage":
                    value_label.config(text=f"{stats[key]}%")
                else:
                    value_label.config(text=str(stats[key]))
                    
        self.logger.debug(f"Dashboard updated: {stats}")

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

    def _export_to_excel(self):
        """Export the currently filtered data to Excel"""
        if self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "There is no data to export.")
            return
            
        # Ask user for location to save file
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Export Data to Excel"
        )
        
        if not filename:
            return  # User cancelled
            
        try:
            # Get visible columns in current order
            visible_columns = self.tree["columns"]
            
            # Export only visible columns in the order shown in treeview
            export_df = self.data_processor.filtered_data[visible_columns].copy()
            
            # Save to Excel
            export_df.to_excel(filename, index=False, engine='openpyxl')
            
            messagebox.showinfo("Export Successful", f"Data exported successfully to {filename}")
            self.logger.info(f"Exported {len(export_df)} rows to Excel: {filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
            self.logger.error(f"Excel export error: {e}", exc_info=True)
    
    def _export_to_csv(self):
        """Export the currently filtered data to CSV"""
        if self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "There is no data to export.")
            return
            
        # Ask user for location to save file
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Data to CSV"
        )
        
        if not filename:
            return  # User cancelled
            
        try:
            # Get visible columns in current order
            visible_columns = self.tree["columns"]
            
            # Export only visible columns in the order shown in treeview
            export_df = self.data_processor.filtered_data[visible_columns].copy()
            
            # Save to CSV
            export_df.to_csv(filename, index=False)
            
            messagebox.showinfo("Export Successful", f"Data exported successfully to {filename}")
            self.logger.info(f"Exported {len(export_df)} rows to CSV: {filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
            self.logger.error(f"CSV export error: {e}", exc_info=True)
    
    def _update_saved_searches_list(self):
        """Update the dropdown list of saved searches"""
        # Get saved searches from config
        saved_searches = self.main_app.global_config.get("saved_searches", {})
        
        # Update the combobox
        search_names = list(saved_searches.keys())
        self.saved_searches_combo['values'] = search_names
        
        # Fix: use .set() method instead of directly assigning to value
        if not search_names:
            self.saved_searches_combo.set("No saved searches")
        elif self.saved_search_var.get() not in search_names:
            self.saved_searches_combo.set("")
    
    def _save_current_search(self):
        """Save the current search filters as a named profile"""
        # Get current filter values
        current_search = {
            "department_filter": self.dept_filter_var.get(),
            "global_search": self.global_search_var.get(),
            "date_filter": self.current_date_filter.copy() if self.current_date_filter else {}
        }
        
        # Show dialog to get a name for this search
        search_name = tkinter.simpledialog.askstring( # Changed tk.simpledialog to tkinter.simpledialog
            "Save Search Profile", 
            "Enter a name for this search profile:",
            parent=self
        )
        
        if not search_name:
            return  # User cancelled
            
        # Get existing saved searches
        saved_searches = self.main_app.global_config.get("saved_searches", {})
        
        # Check if name already exists
        if search_name in saved_searches:
            overwrite = messagebox.askyesno(
                "Overwrite Existing",
                f"A search profile named '{search_name}' already exists. Overwrite it?",
                parent=self
            )
            if not overwrite:
                return
        
        # Save the search
        saved_searches[search_name] = current_search
        self.main_app.global_config.set("saved_searches", saved_searches)
        self.main_app.global_config.save_config()
        
        # Update the dropdown
        self._update_saved_searches_list()
        self.saved_search_var.set(search_name)
        
        self.logger.info(f"Saved search profile: {search_name}")
    
    def _load_saved_search(self, event=None):
        """Load a saved search profile"""
        search_name = self.saved_search_var.get()
        if not search_name or search_name == "No saved searches":
            return
            
        # Get saved searches from config
        saved_searches = self.main_app.global_config.get("saved_searches", {})
        
        if search_name not in saved_searches:
            self.logger.warning(f"Saved search profile not found: {search_name}")
            return
            
        # Get the saved search
        search_profile = saved_searches[search_name]
        
        # Apply the saved search filters
        self.dept_filter_var.set(search_profile.get("department_filter", ""))
        self.global_search_var.set(search_profile.get("global_search", ""))
        
        # Apply date filter if present
        date_filter = search_profile.get("date_filter", {})
        self.current_date_filter = date_filter.copy()
        
        # Apply the filters
        self._apply_all_filters()
        
        self.logger.info(f"Loaded search profile: {search_name}")
    
    def _delete_saved_search(self):
        """Delete a saved search profile"""
        search_name = self.saved_search_var.get()
        if not search_name or search_name == "No saved searches":
            return
            
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete the search profile '{search_name}'?",
            parent=self
        )
        
        if not confirm:
            return
            
        # Get saved searches from config
        saved_searches = self.main_app.global_config.get("saved_searches", {})
        
        if search_name in saved_searches:
            del saved_searches[search_name]
            self.main_app.global_config.set("saved_searches", saved_searches)
            self.main_app.global_config.save_config()
            
            # Update the dropdown
            self._update_saved_searches_list()
            
            self.logger.info(f"Deleted search profile: {search_name}")

    def _show_data_visualization(self):
        """Show a simple data visualization of tender distribution"""
        if self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "There is no data to visualize.")
            return
            
        try:
            # Try to import required libraries
            try:
                import matplotlib.pyplot as plt
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                HAS_MATPLOTLIB = True
            except ImportError:
                messagebox.showerror("Missing Dependency", 
                                    "Matplotlib is required for visualization. Please install it using 'pip install matplotlib'.")
                return
                
            # Create a new top-level window for the chart
            chart_window = tk.Toplevel(self)
            chart_window.title("Tender Data Visualization")
            chart_window.geometry("800x600")
            chart_window.transient(self.winfo_toplevel())  # Make it modal
            
            # Find the department column if it exists
            dept_col = None
            for col in self.data_processor.filtered_data.columns:
                if 'department' in col.lower() or 'dept' in col.lower():
                    dept_col = col
                    break
                    
            if not dept_col:
                messagebox.showinfo("Missing Data", "No department column found in the data.")
                chart_window.destroy()
                return
                
            # Create a figure with tabs for different charts
            tab_control = ttk.Notebook(chart_window)
            tab1 = ttk.Frame(tab_control)
            tab2 = ttk.Frame(tab_control)
            tab_control.add(tab1, text='Department Distribution')
            tab_control.add(tab2, text='Time Series')
            tab_control.pack(expand=1, fill="both")
            
            # Count tenders by department - limit to top 15 for readability
            dept_tender_counts = self.data_processor.filtered_data[dept_col].value_counts().head(15)
            
            # Create a figure and axis for the first tab
            fig1, ax1 = plt.subplots(figsize=(10, 6))
            
            # Plot a bar chart
            dept_tender_counts.plot(kind='bar', ax=ax1, color=COLORS.get('primary', '#1976d2'))
            
            # Set chart title and labels
            ax1.set_title("Top 15 Departments by Number of Tenders", fontsize=14)
            ax1.set_xlabel("Department", fontsize=12)
            ax1.set_ylabel("Number of Tenders", fontsize=12)
            
            # Rotate x labels for better readability
            plt.xticks(rotation=45, ha='right')
            
            # Add gridlines for better readability
            ax1.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Adjust layout to prevent cutoff
            plt.tight_layout()
            
            # Embed the chart in the first tab
            canvas1 = FigureCanvasTkAgg(fig1, master=tab1)
            canvas1.draw()
            canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Create a time-based chart on the second tab if date column exists
            date_col = None
            for col in self.data_processor.filtered_data.columns:
                if 'date' in col.lower() or 'closing' in col.lower():
                    # Check if it's a datetime column
                    if pd.api.types.is_datetime64_any_dtype(self.data_processor.filtered_data[col]):
                        date_col = col
                        break
            
            if date_col:
                # Create time series data
                fig2, ax2 = plt.subplots(figsize=(10, 6))
                
                # Group by month and count
                time_data = self.data_processor.filtered_data.copy()
                time_data['month'] = time_data[date_col].dt.to_period('M')
                monthly_counts = time_data.groupby('month').size()
                
                # Plot time series
                monthly_counts.plot(kind='line', marker='o', ax=ax2, color=COLORS.get('info', '#0288d1'))
                
                ax2.set_title("Tender Distribution by Month", fontsize=14)
                ax2.set_xlabel("Month", fontsize=12)
                ax2.set_ylabel("Number of Tenders", fontsize=12)
                ax2.grid(True, linestyle='--', alpha=0.7)
                
                plt.tight_layout()
                
                # Embed the chart in the second tab
                canvas2 = FigureCanvasTkAgg(fig2, master=tab2)
                canvas2.draw()
                canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            else:
                # If no date column, show a message
                ttk.Label(tab2, text="No date column found in the data.", 
                         font=FONTS.get('heading', ('TkDefaultFont', 12, 'bold'))).pack(expand=True)
            
            # Create control buttons at the bottom
            button_frame = ttk.Frame(chart_window)
            button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
            
            ttk.Button(button_frame, text="Close", command=chart_window.destroy).pack(side=tk.RIGHT)
            
            self.logger.info("Displayed data visualization chart")
            
        except Exception as e:
            messagebox.showerror("Visualization Error", f"Failed to generate chart: {str(e)}")
            self.logger.error(f"Chart visualization error: {e}", exc_info=True)

    def _add_to_calendar(self, item_id):
        """Add the selected item to the calendar."""
        if not item_id:
            return
            
        # Get the item data
        item_values = self.tree.item(item_id, 'values')
        if not item_values:
            return
            
        # Find the calendar tab
        calendar_tab = self.main_app.tabs.get("Calendar")
        if not calendar_tab:
            messagebox.showwarning("Feature Unavailable", "Calendar tab is not available.")
            return
            
        # Convert treeview row to a dictionary
        item_data = {}
        for i, col in enumerate(self.tree["columns"]):
            if i < len(item_values):
                item_data[col] = item_values[i]
                
        # Look for a closing date column
        closing_date = None
        for col in self.tree["columns"]:
            if 'closing' in col.lower() or 'due' in col.lower():
                closing_date_idx = self.tree["columns"].index(col)
                if closing_date_idx < len(item_values):
                    closing_date = item_values[closing_date_idx]
                break
                
        if not closing_date:
            # If no closing date is found, ask the user to select a date
            closing_date = self._show_date_picker_dialog("Select Date", "Select a date for this calendar entry:")
            if not closing_date:  # User cancelled
                return
                
        # Show notes dialog
        notes = self._show_notes_dialog("Add to Calendar", "Add notes for this calendar entry:")
        if notes is None:  # Cancel was pressed
            return
            
        item_data["notes"] = notes
        item_data["closing_date"] = closing_date
        
        # Call the calendar's add_event method
        success = calendar_tab.add_event(item_data)
        
        if success:
            title = item_data.get('Title', item_data.get('title', 'Unnamed item'))
            self.status_var.set(f"Added to calendar: {title}")
            self.logger.info(f"Added item to calendar: {title}")
        else:
            self.status_var.set("Failed to add item to calendar")
            self.logger.warning("Failed to add item to calendar")

    def _add_multiple_to_calendar(self):
        """Add multiple selected items to the calendar."""
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        # Find the calendar tab
        calendar_tab = self.main_app.tabs.get("Calendar")
        if not calendar_tab:
            messagebox.showwarning("Feature Unavailable", "Calendar tab is not available.")
            return
            
        # Show notes dialog (one note for all items)
        notes = self._show_notes_dialog("Add to Calendar", "Add notes for these calendar entries:")
        if notes is None:  # Cancel was pressed
            return
            
        added_count = 0
        for item_id in selected_items:
            item_values = self.tree.item(item_id, 'values')
            if not item_values:
                continue
                
            # Convert treeview row to a dictionary
            item_data = {}
            for i, col in enumerate(self.tree["columns"]):
                if i < len(item_values):
                    item_data[col] = item_values[i]
            
            # Look for a closing date column
            closing_date = None
            for col in self.tree["columns"]:
                if 'closing' in col.lower() or 'due' in col.lower():
                    closing_date_idx = self.tree["columns"].index(col)
                    if closing_date_idx < len(item_values):
                        closing_date = item_values[closing_date_idx]
                    break
            
            if not closing_date:
                # Skip items without a closing date in batch mode
                continue
                
            item_data["notes"] = notes
            item_data["closing_date"] = closing_date
            
            # Call the calendar's add_event method
            if calendar_tab.add_event(item_data):
                added_count += 1
            
        if added_count > 0:
            self.status_var.set(f"Added {added_count} items to calendar")
            self.logger.info(f"Added {added_count} items to calendar")
        else:
            self.status_var.set("No items were added to calendar")
            self.logger.warning("No items were added to calendar")

    def _show_notes_dialog(self, title, prompt):
        """Show a dialog to enter notes and return the text."""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("400x400")  # Increased height to ensure buttons are visible
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Move the buttons to the top
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Use colored action buttons instead of plain ttk.Button
        create_action_button(button_frame, "OK", lambda: on_ok(), 
                       button_type='primary', width=10).pack(side=tk.RIGHT, padx=5)
        create_action_button(button_frame, "Cancel", lambda: on_cancel(), 
                       button_type='secondary', width=10).pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(dialog, text=prompt, font=FONTS.get('subheading', ('TkDefaultFont', 11))).pack(pady=10, padx=10, anchor="w")
        
        # Notes text area
        notes_frame = ttk.Frame(dialog)
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        notes_text = tk.Text(notes_frame, wrap=tk.WORD, font=FONTS.get('body', ('TkDefaultFont', 10)))
        notes_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(notes_frame, orient="vertical", command=notes_text.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        notes_text.configure(yscrollcommand=scrollbar.set)
        
        # Result variable to store the return value
        result = {"value": ""}
        
        def on_ok():
            result["value"] = notes_text.get("1.0", tk.END).strip()
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
    
        # Center the dialog on parent
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.winfo_width() - width) // 2 + self.winfo_rootx()
        y = (self.winfo_height() - height) // 2 + self.winfo_rooty()
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Wait for dialog to close
        self.wait_window(dialog)
        
        return result["value"]

    def _show_date_picker_dialog(self, title, prompt):
        """Show a dialog with a date picker and return the selected date."""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("300x250")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Move buttons to the top
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Use colored action buttons
        create_action_button(button_frame, "OK", lambda: on_ok(), 
                       button_type='primary', width=10).pack(side=tk.RIGHT, padx=5)
        create_action_button(button_frame, "Cancel", lambda: on_cancel(), 
                       button_type='secondary', width=10).pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(dialog, text=prompt, font=FONTS.get('subheading', ('TkDefaultFont', 11))).pack(pady=10, padx=10, anchor="w")
        
        # Date picker or fallback entry
        if HAS_TKCALENDAR and DateEntry is not None:
            date_picker = DateEntry(
                dialog,
                width=12,
                background=COLORS.get('primary', '#4169E1'),
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                selectmode='day'
            )
            date_picker.pack(pady=20)
            
            def get_date():
                return date_picker.get()
        else:
            # Fallback: text entry
            ttk.Label(dialog, text="Enter date (YYYY-MM-DD):").pack(pady=5)
            date_var = tk.StringVar()
            date_entry = create_input_entry(dialog, date_var, width=15)
            date_entry.pack(pady=10)
            
            def get_date():
                date_str = date_var.get()
                try:
                    # Validate format
                    datetime.strptime(date_str, "%Y-%m-%d")
                    return date_str
                except ValueError:
                    messagebox.showerror("Invalid Date", "Please enter date in YYYY-MM-DD format.")
                    return None
        
        # Result variable to store the return value
        result = {"value": None}
        
        def on_ok():
            result["value"] = get_date()
            if result["value"] is not None:
                dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
    
        # Center the dialog on parent
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.winfo_width() - width) // 2 + self.winfo_rootx()
        y = (self.winfo_height() - height) // 2 + self.winfo_rooty()
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Wait for dialog to close
        self.wait_window(dialog)
        
        return result["value"]