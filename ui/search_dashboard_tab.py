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

        # Initialize remote data loader
        self.remote_loader = RemoteDataLoader()
        
        # Add UI variables for remote sources
        self.remote_urls: List[str] = []

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

    def _refresh_tree_data(self):
        """Refresh the treeview with current filtered data."""
        if self.tree is None:
            return

        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Check if data exists
        if (not hasattr(self.data_processor, 'filtered_data') or
            self.data_processor.filtered_data is None or
            self.data_processor.filtered_data.empty):
            self.results_count_var.set("No data to display")
            return

        df = self.data_processor.filtered_data

        # Configure columns
        cols = df.columns.tolist()
        self.tree["columns"] = cols

        for col in cols:
            width = 100
            if any(kw in col.lower() for kw in ['title', 'description', 'summary']):
                width = 300
            elif any(kw in col.lower() for kw in ['department', 'ministry', 'agency']):
                width = 200
            elif any(kw in col.lower() for kw in ['date', 'time']):
                width = 120
            self.tree.column(col, width=width, minwidth=50)
            self.tree.heading(col, text=col)

        # Insert data rows - limit for performance
        max_rows = 1000
        display_df = df.head(max_rows) if len(df) > max_rows else df
        for _, row in display_df.iterrows():
            values = [str(val) if pd.notna(val) else "" for val in row]
            self.tree.insert("", "end", values=values)

        total_records = len(df)
        if total_records > max_rows:
            self.results_count_var.set(f"Showing first {max_rows} of {total_records} records (limit for performance)")
        else:
            self.results_count_var.set(f"Showing all {total_records} records")

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

        self.data_processor.filtered_data = self.data_processor.raw_data.copy()

        # Global search
        global_search = self.global_search_var.get().strip()
        if global_search:
            terms = [t.strip() for t in global_search.split(',') if t.strip()]
            if terms:
                operator = self.global_operator_var.get()
                mask = None
                for term in terms:
                    term_mask = None
                    for col in self.data_processor.filtered_data.columns:
                        col_mask = self.data_processor.filtered_data[col].astype(str).str.contains(term, case=False, na=False)
                        # FIX: correct inline conditional
                        term_mask = col_mask if term_mask is None else (term_mask | col_mask)
                    if term_mask is not None:
                        if mask is None:
                            mask = term_mask
                        elif operator == "AND":
                            mask = mask & term_mask
                        else:
                            mask = mask | term_mask
                if mask is not None:
                    self.data_processor.filtered_data = self.data_processor.filtered_data[mask]

        # Department filter
        dept_filter = self.dept_filter_var.get().strip()
        if dept_filter:
            terms = [t.strip() for t in dept_filter.split(',') if t.strip()]
            if terms:
                operator = self.dept_operator_var.get()
                dept_cols = [c for c in self.data_processor.filtered_data.columns
                             if any(kw in c.lower() for kw in ['department', 'dept', 'agency', 'organisation'])]
                if dept_cols:
                    mask = None
                    for term in terms:
                        term_mask = None
                        for col in dept_cols:
                            col_mask = self.data_processor.filtered_data[col].astype(str).str.contains(term, case=False, na=False)
                            # FIX: correct inline conditional
                            term_mask = col_mask if term_mask is None else (term_mask | col_mask)
                        if term_mask is not None:
                            if mask is None:
                                mask = term_mask
                            elif operator == "AND":
                                mask = mask & term_mask
                            else:
                                mask = mask | term_mask
                    if mask is not None:
                        self.data_processor.filtered_data = self.data_processor.filtered_data[mask]

        # Status/date filters
        if hasattr(self, 'current_date_filter') and self.current_date_filter:
            ftype = self.current_date_filter.get('type', '')
            if ftype == 'live':
                self._apply_live_tenders_filter()
            elif ftype == 'expired':
                self._apply_expired_tenders_filter()
            elif ftype == 'combined':
                status = self.current_date_filter.get('status', 'live')
                if status == 'live':
                    self._apply_live_tenders_filter()
                elif status == 'expired':
                    self._apply_expired_tenders_filter()
                time_range = self.current_date_filter.get('time_range', '')
                if time_range:
                    self._apply_time_range_filter(time_range)
        elif hasattr(self, 'current_date_filter') and self.current_date_filter.get('type') == 'custom_date_range':
            pass

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
        for key in ["today", "next_3_days", "next_7_days", "next_30_days"]:
            if key in self.date_filter_buttons:
                btn = self.date_filter_buttons[key]
                if isinstance(btn, ttk.Button):
                    # For ttk buttons, use state
                    if hasattr(btn, 'state'):
                        btn.state(['!pressed'])
                elif isinstance(btn, tk.Button):
                    # For tk buttons, use configure
                    if hasattr(btn, 'configure'):
                        btn['background'] = "#f0f0f0"
                        btn['foreground'] = "black"
        
        # Highlight the selected time filter button
        if preset in self.date_filter_buttons:
            btn = self.date_filter_buttons[preset]
            if isinstance(btn, ttk.Button):
                # For ttk buttons, use state
                if hasattr(btn, 'state'):
                    btn.state(['pressed'])
            elif isinstance(btn, tk.Button):
                # For tk.Button, use configure
                if hasattr(btn, 'configure'):
                    btn['background'] = "#006400"
                    btn['foreground'] = "white"
        
        # Apply the filter
        self._apply_time_range_filter(preset)

    def _load_saved_search(self, event=None):
        """Load a saved search configuration."""
        search_name = self.saved_search_var.get()
        if not search_name:
            return
        
        # Get saved searches from config
        saved_searches_data = self.main_app.global_config.get("saved_searches_data", {})
        
        if search_name not in saved_searches_data:
            messagebox.showinfo("Not Found", f"Search '{search_name}' not found.")
            return
        
        # Get the saved search configuration
        search_config = saved_searches_data[search_name]
        
        # Apply saved search parameters to UI
        if 'dept_filter' in search_config:
            self.dept_filter_var.set(search_config['dept_filter'])
        
        if 'global_search' in search_config:
            self.global_search_var.set(search_config['global_search'])
        
        if 'dept_operator' in search_config:
            self.dept_operator_var.set(search_config['dept_operator'])
        
        if 'global_operator' in search_config:
            self.global_operator_var.set(search_config['global_operator'])
        
        if 'status_filter' in search_config:
            self.status_filter_var.set(search_config['status_filter'])
            self._apply_status_filter(search_config['status_filter'])
        
        # Apply the filters
        self._apply_filters()
        
        messagebox.showinfo("Search Loaded", f"Search '{search_name}' loaded successfully.")

    def _save_current_search(self):
        """Save the current search configuration."""
        # Ask for a name for the search
        search_name = tkinter.simpledialog.askstring(
            "Save Search", 
            "Enter a name for this search:",
            parent=self
        )
        
        if not search_name:
            return  # User canceled
        
        # Create search configuration
        search_config = {
            'dept_filter': self.dept_filter_var.get(),
            'global_search': self.global_search_var.get(),
            'dept_operator': self.dept_operator_var.get(),
            'global_operator': self.global_operator_var.get(),
            'status_filter': self.status_filter_var.get()
        }
        
        # Get existing saved searches
        saved_searches_data = self.main_app.global_config.get("saved_searches_data", {})
        saved_searches_list = self.main_app.global_config.get("saved_searches", [])
        
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

    def _delete_saved_search(self):
        """Delete a saved search configuration."""
        search_name = self.saved_search_var.get()
        
        if not search_name:
            messagebox.showinfo("No Selection", "Please select a saved search to delete.")
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the saved search '{search_name}'?"):
            return
        
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

    def _on_calendar_date_selected(self, event=None):
        """Handle date selection in the calendar widgets."""
        # This method is primarily a placeholder as the actual filtering happens
        # when the user clicks the GO button, but we could do validation here
        try:
            # Validate that the end date is not before the start date
            if HAS_TKCALENDAR and hasattr(self, 'start_date_picker') and hasattr(self, 'end_date_picker'):
                start_date = self.start_date_picker.get_date()
                end_date = self.end_date_picker.get_date()
                
                if end_date < start_date:
                    # Silently correct by setting end date to start date
                    self.end_date_picker.set_date(start_date)
        except Exception as e:
            self.logger.error(f"Error in calendar date selection: {e}")

    def _apply_custom_date_filter(self):
        """Apply a custom date filter using the calendar date pickers."""
        try:
            # Get dates from the date pickers
            start_date = self.start_date_picker.get_date()
            end_date = self.end_date_picker.get_date()
            
            # Get times from the spinboxes
            try:
                start_hour = int(self.start_hour_var.get())
                start_min = int(self.start_min_var.get())
                end_hour = int(self.end_hour_var.get())
                end_min = int(self.end_min_var.get())
            except ValueError:
                # Use defaults if values are invalid
                start_hour, start_min = 0, 0
                end_hour, end_min = 23, 59
            
            # Create datetime objects
            start_datetime = datetime.combine(start_date, time(start_hour, start_min))
            end_datetime = datetime.combine(end_date, time(end_hour, end_min))
            
            # Apply the filter
            self._apply_custom_date_range_filter(start_datetime, end_datetime)
            
        except Exception as e:
            self.logger.error(f"Error applying custom date filter: {e}")
            messagebox.showerror("Date Filter Error", f"Error applying date filter: {str(e)}")

    def _apply_custom_date_filter_text(self):
        """Apply a custom date filter using text entry fields."""
        try:
            # Parse date strings
            start_date_str = self.custom_date_start_var.get().strip()
            end_date_str = self.custom_date_end_var.get().strip()
            
            if not start_date_str or not end_date_str:
                messagebox.showwarning("Missing Dates", "Please enter both start and end dates.")
                return
            
            # Parse times
            try:
                start_hour = int(self.start_hour_var.get())
                start_min = int(self.start_min_var.get())
                end_hour = int(self.end_hour_var.get())
                end_min = int(self.end_min_var.get())
            except ValueError:
                # Use defaults if values are invalid
                start_hour, start_min = 0, 0
                end_hour, end_min = 23, 59
            
            # Parse dates
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Invalid Date Format", "Please use YYYY-MM-DD format for dates.")
                return
            
            # Create datetime objects
            start_datetime = datetime.combine(start_date, time(start_hour, start_min))
            end_datetime = datetime.combine(end_date, time(end_hour, end_min))
            
            # Apply the filter
            self._apply_custom_date_range_filter(start_datetime, end_datetime)
            
        except Exception as e:
            self.logger.error(f"Error applying custom date filter: {e}")
            messagebox.showerror("Date Filter Error", f"Error applying date filter: {str(e)}")

    def _apply_custom_date_range_filter(self, start_datetime, end_datetime):
        """Apply a date range filter to the data."""
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "No data available to filter.")
            return
        
        # Set the filter state
        self.current_date_filter = {
            'type': 'custom_date_range',
            'start_date': start_datetime,
            'end_date': end_datetime
        }
        
        # Clear any time filter button selection
        self._clear_time_filter_selection()
        
        # Start with raw data
        self.data_processor.filtered_data = self.data_processor.raw_data.copy()
        
        # Find date columns
        date_cols = [col for col in self.data_processor.filtered_data.columns 
                    if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]
        
        if not date_cols:
            messagebox.showinfo("Date Column Not Found", "Could not find a suitable date column to filter.")
            return
        
        date_col = date_cols[0]
        
        # Convert column to datetime if needed
        try:
            if not pd.api.types.is_datetime64_dtype(self.data_processor.filtered_data[date_col]):
                self.data_processor.filtered_data[date_col] = pd.to_datetime(
                    self.data_processor.filtered_data[date_col], errors='coerce')
        except Exception as e:
            self.logger.error(f"Error converting date column: {e}")
            messagebox.showerror("Date Conversion Error", f"Could not convert dates: {str(e)}")
            return
        
        # Apply the date range filter
        try:
            start_ts = pd.Timestamp(start_datetime)
            end_ts = pd.Timestamp(end_datetime)
            
            mask = (
                (self.data_processor.filtered_data[date_col] >= start_ts) & 
                (self.data_processor.filtered_data[date_col] <= end_ts)
            )
            
            self.data_processor.filtered_data = self.data_processor.filtered_data[mask]
            
            # Refresh the display
            self._refresh_tree_data()
            self.update_dashboard()
            
            # Show confirmation
            record_count = len(self.data_processor.filtered_data)
            self.logger.info(f"Applied custom date range filter: {start_datetime} to {end_datetime}, {record_count} records matching")
            
        except Exception as e:
            self.logger.error(f"Error applying date range filter: {e}")
            messagebox.showerror("Filter Error", f"Error filtering by date: {str(e)}")

    def update_dashboard(self):
        """Update the dashboard metrics."""
        if not hasattr(self, 'dashboard_labels'):
            return
        
        try:
            # Default values
            metrics = {
                "total_tenders": 0,
                "live_tenders":  0,
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
            if hasattr(self.data_processor, 'raw_data') and self.data_processor.raw_data is not None and not self.data_processor.raw_data.empty:
                raw_data = self.data_processor.raw_data
                
                # Basic counts
                metrics["total_tenders"] = len(raw_data)
                
                # Find status column
                status_cols = [col for col in raw_data.columns if 'status' in col.lower()]
                if status_cols:
                    status_col = status_cols[0]
                    live_mask = raw_data[status_col].astype(str).str.lower().str.contains('active|live|open', na=False)
                    metrics["live_tenders"] = int(live_mask.sum())
                    metrics["expired_tenders"] = len(raw_data) - metrics["live_tenders"]
                
                # Department metrics
                dept_cols = [col for col in raw_data.columns 
                           if any(kw in col.lower() for kw in ['department', 'dept', 'agency', 'organisation'])]
                if dept_cols and len(dept_cols) > 0:
                    metrics["unique_departments"] = raw_data[dept_cols[0]].nunique()
                
                # Date-based metrics
                date_cols = [col for col in raw_data.columns 
                           if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline'])]
                if date_cols and len(date_cols) > 0:
                    date_col = date_cols[0]
                    
                    # Convert to datetime if needed
                    if not pd.api.types.is_datetime64_dtype(raw_data[date_col]):
                        try:
                            date_series = pd.to_datetime(raw_data[date_col], errors='coerce')
                            
                            # Calculate date-based metrics safely
                            if date_series is not None:
                                today = pd.Timestamp.today().normalize()
                                
                                # Handle NaT values by filtering them out
                                valid_dates = date_series.dropna()
                                
                                # Calculate closing today
                                today_mask = (valid_dates.dt.normalize() == today)
                                metrics["closing_today"] = int(today_mask.sum())
                                
                                # Calculate next 3 days safely
                                next_3_days_mask = ((valid_dates.dt.normalize() > today) & 
                                                  (valid_dates.dt.normalize() <= today + pd.Timedelta(days=3)))
                                metrics["closing_next_3_days"] = int(next_3_days_mask.sum())
                                
                                # Calculate next 7 days safely
                                next_7_days_mask = ((valid_dates.dt.normalize() > today) & 
                                                  (valid_dates.dt.normalize() <= today + pd.Timedelta(days=7)))
                                metrics["closing_next_7_days"] = int(next_7_days_mask.sum())
                        except Exception as e:
                            self.logger.error(f"Error calculating date metrics: {e}")
                    else:
                        # Already a datetime column
                        date_series = raw_data[date_col]
                        today = pd.Timestamp.today().normalize()
                        
                        # Handle NaT values by filtering them out
                        valid_dates = date_series.dropna()
                        
                        # Calculate date metrics
                        today_mask = (valid_dates.dt.normalize() == today)
                        metrics["closing_today"] = int(today_mask.sum())
                        
                        next_3_days_mask = ((valid_dates.dt.normalize() > today) & 
                                          (valid_dates.dt.normalize() <= today + pd.Timedelta(days=3)))
                        metrics["closing_next_3_days"] = int(next_3_days_mask.sum())
                        
                        next_7_days_mask = ((valid_dates.dt.normalize() > today) & 
                                          (valid_dates.dt.normalize() <= today + pd.Timedelta(days=7)))
                        metrics["closing_next_7_days"] = int(next_7_days_mask.sum())
                
                # Source metrics
                source_cols = [col for col in raw_data.columns 
                             if any(kw in col.lower() for kw in ['source', 'portal', 'origin'])]
                if source_cols and len(source_cols) > 0:
                    metrics["data_sources"] = raw_data[source_cols[0]].nunique()
                elif 'Source File' in raw_data.columns:
                    # Count number of unique source files
                    metrics["data_sources"] = raw_data['Source File'].nunique()
            
            # Filtered data metrics
            if hasattr(self.data_processor, 'filtered_data') and self.data_processor.filtered_data is not None and not self.data_processor.filtered_data.empty:
                filtered_data = self.data_processor.filtered_data
                metrics["filtered_tenders"] = len(filtered_data)
                
                # Calculate match percentage
                if metrics["total_tenders"] > 0:
                    match_pct = (len(filtered_data) / metrics["total_tenders"]) * 100
                    metrics["match_percentage"] = f"{match_pct:.1f}%"
        
            # Update dashboard labels
            for key, value in metrics.items():
                if key in self.dashboard_labels:
                    self.dashboard_labels[key].configure(text=str(value))
        
        except Exception as e:
            self.logger.error(f"Error updating dashboard: {e}", exc_info=True)

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
        
        # Second row for additional controls or information
        # This row is currently empty but can be used for future enhancements
        empty_frame = ttk.Frame(parent)
        empty_frame.pack(fill=tk.X, expand=True, padx=SPACING['small'], pady=(0, SPACING['small']))
        empty_frame.grid_rowconfigure(0, weight=1)
        empty_frame.grid_columnconfigure(0, weight=1)

    def _create_search_filter_widgets(self, parent):
        """Create search and filter widgets."""
        # Search section
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, SPACING['small']))
        
        # Global search
        global_search_frame = ttk.Frame(search_frame)
        global_search_frame.pack(fill=tk.X, pady=SPACING['small']//2)
        
        ttk.Label(global_search_frame, text="Global Search:").pack(side=tk.LEFT)
        global_search_entry = create_input_entry(global_search_frame, textvariable=self.global_search_var, width=30)
        global_search_entry.pack(side=tk.LEFT, padx=SPACING['small'])
        global_search_entry.bind('<KeyRelease>', self._on_live_search_key)
        
        # Global search operator
        self.global_operator_var = tk.StringVar(value="AND")
        ttk.Label(global_search_frame, text="Op:").pack(side=tk.LEFT, padx=(SPACING['small'], 0))
        global_op_combo = ttk.Combobox(global_search_frame, textvariable=self.global_operator_var, values=["AND", "OR"], width=5, state="readonly")
        global_op_combo.pack(side=tk.LEFT, padx=SPACING['small']//2)
        
        # Department filter
        dept_filter_frame = ttk.Frame(search_frame)
        dept_filter_frame.pack(fill=tk.X, pady=SPACING['small']//2)
        
        ttk.Label(dept_filter_frame, text="Department Filter:").pack(side=tk.LEFT)
        dept_filter_entry = create_input_entry(dept_filter_frame, textvariable=self.dept_filter_var, width=30)
        dept_filter_entry.pack(side=tk.LEFT, padx=SPACING['small'])
        dept_filter_entry.bind('<KeyRelease>', self._on_live_search_key)
        
        # Department filter operator
        self.dept_operator_var = tk.StringVar(value="OR")
        ttk.Label(dept_filter_frame, text="Op:").pack(side=tk.LEFT, padx=(SPACING['small'], 0))
        dept_op_combo = ttk.Combobox(dept_filter_frame, textvariable=self.dept_operator_var, values=["AND", "OR"], width=5, state="readonly")
        dept_op_combo.pack(side=tk.LEFT, padx=SPACING['small']//2)
        
        # Status filter
        status_frame = ttk.Frame(search_frame)
        status_frame.pack(fill=tk.X, pady=SPACING['small']//2)
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        self.status_filter_var = tk.StringVar(value="live")
        status_combo = ttk.Combobox(status_frame, textvariable=self.status_filter_var, 
                                   values=["all", "live", "expired"], width=10, state="readonly")
        status_combo.pack(side=tk.LEFT, padx=SPACING['small'])
        status_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_status_filter(self.status_filter_var.get()))
        
        # Action buttons
        buttons_frame = ttk.Frame(search_frame)
        buttons_frame.pack(fill=tk.X, pady=SPACING['small'])
        
        create_action_button(buttons_frame, "Reset Filters", self._reset_filters, button_type='secondary', width=12).pack(side=tk.LEFT, padx=2)
        create_action_button(buttons_frame, "Apply Filters", self._apply_filters, width=12).pack(side=tk.LEFT, padx=2)
        
        # Saved searches
        saved_search_frame = ttk.Frame(buttons_frame)
        saved_search_frame.pack(side=tk.RIGHT)
        
        ttk.Label(saved_search_frame, text="Saved:").pack(side=tk.LEFT)
        self.saved_search_var = tk.StringVar()
        self.saved_searches_combo = ttk.Combobox(saved_search_frame, textvariable=self.saved_search_var, width=15, state="readonly")
        self.saved_searches_combo.pack(side=tk.LEFT, padx=2)
        self.saved_searches_combo.bind('<<ComboboxSelected>>', self._load_saved_search)
        
        create_action_button(saved_search_frame, "Save", self._save_current_search, button_type='info_outline', width=8).pack(side=tk.LEFT, padx=2)
        create_action_button(saved_search_frame, "Delete", self._delete_saved_search, button_type='danger_outline', width=8).pack(side=tk.LEFT, padx=2)
        
        # Update saved searches list
        self._update_saved_searches_list()

    def _create_date_filter_widgets(self, parent):
        """Create date filter widgets."""
        date_frame = ttk.Frame(parent)
        date_frame.pack(fill=tk.X, pady=SPACING['small'])
        
        # Status and time filter buttons in one row
        filter_buttons_frame = ttk.Frame(date_frame)
        filter_buttons_frame.pack(fill=tk.X, pady=SPACING['small']//2)
        
        # Time range filter buttons
        ttk.Label(filter_buttons_frame, text="Quick Filters:").pack(side=tk.LEFT)
        
        time_filters = [
            ("Today", "today"),
            ("Next 3 Days", "next_3_days"),
            ("Next 7 Days", "next_7_days"),
            ("Next 30 Days", "next_30_days")
        ]
        
        for label, filter_key in time_filters:
            btn = create_action_button(
                filter_buttons_frame, label, 
                lambda f=filter_key: self._apply_time_filter(f),
                button_type='info_outline', width=12
            )
            if btn:
                btn.pack(side=tk.LEFT, padx=2)
                self.date_filter_buttons[filter_key] = btn
        
        # Custom date range section
        if HAS_TKCALENDAR and DateEntry is not None:
            custom_date_frame = ttk.LabelFrame(date_frame, text="Custom Date Range")
            custom_date_frame.pack(fill=tk.X, pady=SPACING['small'])
            
            # Date pickers row
            date_row = ttk.Frame(custom_date_frame)
            date_row.pack(fill=tk.X, padx=SPACING['small'], pady=SPACING['small']//2)
            
            ttk.Label(date_row, text="From:").pack(side=tk.LEFT)
            self.start_date_picker = DateEntry(date_row, width=12, background='darkblue',
                                             foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.start_date_picker.pack(side=tk.LEFT, padx=SPACING['small'])
            self.start_date_picker.bind('<<DateEntrySelected>>', self._on_calendar_date_selected)
            
            ttk.Label(date_row, text="To:").pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
            self.end_date_picker = DateEntry(date_row, width=12, background='darkblue',
                                           foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.end_date_picker.pack(side=tk.LEFT, padx=SPACING['small'])
            self.end_date_picker.bind('<<DateEntrySelected>>', self._on_calendar_date_selected)
            
            # Time spinboxes row
            time_row = ttk.Frame(custom_date_frame)
            time_row.pack(fill=tk.X, padx=SPACING['small'], pady=SPACING['small']//2)
            
            # Start time
            ttk.Label(time_row, text="Start Time:").pack(side=tk.LEFT)
            start_hour_spin = tk.Spinbox(time_row, from_=0, to=23, width=3, textvariable=self.start_hour_var, format="%02.0f")
            start_hour_spin.pack(side=tk.LEFT, padx=2)
            ttk.Label(time_row, text=":").pack(side=tk.LEFT)
            start_min_spin = tk.Spinbox(time_row, from_=0, to=59, width=3, textvariable=self.start_min_var, format="%02.0f")
            start_min_spin.pack(side=tk.LEFT, padx=2)
            
            # End time
            ttk.Label(time_row, text="End Time:").pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
            end_hour_spin = tk.Spinbox(time_row, from_=0, to=23, width=3, textvariable=self.end_hour_var, format="%02.0f")
            end_hour_spin.pack(side=tk.LEFT, padx=2)
            ttk.Label(time_row, text=":").pack(side=tk.LEFT)
            end_min_spin = tk.Spinbox(time_row, from_=0, to=59, width=3, textvariable=self.end_min_var, format="%02.0f")
            end_min_spin.pack(side=tk.LEFT, padx=2)
            
            # Apply button
            create_action_button(time_row, "Apply Date Range", self._apply_custom_date_filter,
                               button_type='success', width=15).pack(side=tk.RIGHT, padx=SPACING['medium'])
        else:
            # Fallback to text entry if tkcalendar is not available
            custom_date_frame = ttk.LabelFrame(date_frame, text="Custom Date Range (YYYY-MM-DD)")
            custom_date_frame.pack(fill=tk.X, pady=SPACING['small'])
            
            date_entry_frame = ttk.Frame(custom_date_frame)
            date_entry_frame.pack(fill=tk.X, padx=SPACING['small'], pady=SPACING['small'])
            
            ttk.Label(date_entry_frame, text="Start Date:").pack(side=tk.LEFT)
            start_date_entry = create_input_entry(date_entry_frame, textvariable=self.custom_date_start_var, width=12)
            start_date_entry.pack(side=tk.LEFT, padx=SPACING['small'])
            
            ttk.Label(date_entry_frame, text="End Date:").pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
            end_date_entry = create_input_entry(date_entry_frame, textvariable=self.custom_date_end_var, width=12)
            end_date_entry.pack(side=tk.LEFT, padx=SPACING['small'])
            
            create_action_button(date_entry_frame, "Apply", self._apply_custom_date_filter_text,
                               button_type='success', width=10).pack(side=tk.RIGHT, padx=SPACING['medium'])

    def _create_tender_data_widgets(self, parent):
        """Create the widgets for displaying and interacting with tender data."""
        # Container frame for all tender data elements
        tender_container = ttk.Frame(parent)
        tender_container.pack(fill=tk.BOTH, expand=True, padx=SPACING['small'], pady=SPACING['small'])
        
        # Create top controls frame
        controls_frame = ttk.Frame(tender_container)
        controls_frame.pack(fill=tk.X, pady=(0, SPACING['small']))
        
        # Info label showing record count
        count_label = ttk.Label(controls_frame, textvariable=self.results_count_var)
        count_label.pack(side=tk.LEFT)
        
        # Export buttons on the right
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(side=tk.RIGHT)
        
        # Export to Excel button
        export_excel_btn = create_action_button(
            buttons_frame, "Export Excel", self._export_to_excel,
            button_type='success_outline', width=12
        )
        if export_excel_btn:
            export_excel_btn.pack(side=tk.LEFT, padx=2)
        
        # Export to CSV button
        export_csv_btn = create_action_button(
            buttons_frame, "Export CSV", self._export_to_csv,
            button_type='info_outline', width=12
        )
        if export_csv_btn:
            export_csv_btn.pack(side=tk.LEFT, padx=2)
        
        # Create the treeview for tender data
        tree_frame = ttk.Frame(tender_container)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview with columns for tender data
        self.tree = ttk.Treeview(tree_frame, show="headings", style="Custom.Treeview")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for tree and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Style the treeview
        style = ttk.Style()
        style.configure("Custom.Treeview", 
                   font=FONTS.get('body', ('TkDefaultFont', 10)), 
                   rowheight=24)
        style.map("Custom.Treeview", 
             background=[('selected', COLORS.get('primary', '#1976d2'))])

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
            # Store URL with credentials (if provided) for loading
            if username and password:
                url_with_auth = f"{url}||{username}||{password}"  # Simple encoding
            else:
                url_with_auth = url
            
            if url_with_auth not in self.remote_urls:
                self.remote_urls.append(url_with_auth)
                self._update_selected_folders_display()
                messagebox.showinfo("URL Added", f"Remote URL added successfully:\n{url}")

    def _clear_folders(self):
        """Clear selected folders and remote URLs."""
        self.loaded_files = []
        self.remote_urls = []
        # Cleanup remote files
        if hasattr(self, 'remote_loader'):
            self.remote_loader.cleanup_temp_files()
        self._update_selected_folders_display()

    def _update_selected_folders_display(self):
        """Update label with selected folders and remote URLs."""
        sources = []
        
        # Add local folders
        if self.loaded_files:
            sources.extend([f"📁 {folder}" for folder in self.loaded_files])
        
        # Add remote URLs
        if self.remote_urls:
            for url_entry in self.remote_urls:
                url = url_entry.split('||')[0]  # Remove credentials for display
                sources.append(f"🌐 {url}")
        
        if sources:
            text = "\n".join(sources)
        else:
            text = "No data sources selected."
        
        self.selected_folders_var.set(text)

    def _export_to_excel(self):
        """Export filtered data to Excel."""
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "No data available to export.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Export to Excel"
        )
        if not filename:
            return
        try:
            self.data_processor.filtered_data.to_excel(filename, index=False)
            messagebox.showinfo("Export Complete", f"Data exported to {filename}")
        except Exception as e:
            self.logger.error(f"Excel export error: {e}")
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def _export_to_csv(self):
        """Export filtered data to CSV."""
        if not hasattr(self.data_processor, 'filtered_data') or self.data_processor.filtered_data.empty:
            messagebox.showinfo("No Data", "No data available to export.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export to CSV"
        )
        if not filename:
            return
        try:
            self.data_processor.filtered_data.to_csv(filename, index=False)
            messagebox.showinfo("Export Complete", f"Data exported to {filename}")
        except Exception as e:
            self.logger.error(f"CSV export error: {e}")
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def _on_row_double_click(self, event):
        """Open URL if present or show details dialog."""
        if self.tree is None:
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return
        values = self.tree.item(item, 'values')
        if not values:
            return
        for val in values:
            if isinstance(val, str) and (val.startswith('http') or val.startswith('www')):
                webbrowser.open_new_tab(val)
                return
        messagebox.showinfo("Tender Details", "Detailed view will be implemented in a future update.")

    def _show_context_menu(self, event):
        """Right-click menu on tree rows."""
        if self.tree is None:
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy Row", command=lambda: self._copy_row(item))
        menu.add_command(label="View Details", command=lambda: self._show_row_details(item))
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_row(self, item_id):
        """Copy selected row values to clipboard."""
        if self.tree is None:
            return
        values = self.tree.item(item_id, 'values')
        if not values:
            return
        text = "\t".join(str(v) for v in values)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Row data copied to clipboard.")

    def _show_row_details(self, item_id):
        """Show a simple details dialog of the row."""
        if self.tree is None:
            return
        values = self.tree.item(item_id, 'values')
        if not values:
            return
        columns = self.tree["columns"]
        details = "\n".join(f"{col}: {val}" for col, val in zip(columns, values))
        messagebox.showinfo("Tender Details", details)


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

    def _setup_treeview_bindings(self):
        """Bind treeview events."""
        if hasattr(self, 'tree') and self.tree:
            self.tree.bind("<Double-1>", self._on_row_double_click)
            self.tree.bind("<Button-3>", self._show_context_menu)

    def _reset_filters(self):
        """Reset all filters to their default state."""
        # Clear search fields
        self.dept_filter_var.set("")
        self.global_search_var.set("")
        
        # Reset operators to defaults
        self.dept_operator_var.set("OR")
        self.global_operator_var.set("AND")
        
        # Reset status filter to live
        self.status_filter_var.set("live")
        
        # Clear date filter state
        self.current_date_filter = {}
        self.active_date_filter = "live"
        
        # Reset time filter button states
        self._clear_time_filter_selection()
        
        # Clear custom date fields if they exist
        if hasattr(self, 'custom_date_start_var'):
            self.custom_date_start_var.set("")
        if hasattr(self, 'custom_date_end_var'):
            self.custom_date_end_var.set("")
        
        # Reset time spinboxes to defaults
        self.start_hour_var.set("00")
        self.start_min_var.set("00")
        self.end_hour_var.set("23")
        self.end_min_var.set("59")
        
        # Apply default live filter
        self._apply_status_filter("live")

    def _update_saved_searches_list(self):
        """Update the saved searches dropdown list."""
        if not hasattr(self, 'saved_searches_combo'):
            return
        
        # Get saved searches from config
        saved_searches_list = self.main_app.global_config.get("saved_searches", [])
        
        # Update the combobox values
        self.saved_searches_combo['values'] = saved_searches_list

    def _apply_status_filter(self, status):
        """Apply status-based filter (all, live, expired)."""
        self.logger.info(f"Applying status filter: {status}")
        
        # Set the current filter state
        self.active_date_filter = status
        self.current_date_filter = {
            'type': status
        }
        
        # Apply the filter based on status
        if status == "all":
            # Show all records - just copy raw data
            if hasattr(self.data_processor, 'raw_data') and self.data_processor.raw_data is not None:
                self.data_processor.filtered_data = self.data_processor.raw_data.copy()
        elif status == "live":
            self._apply_live_tenders_filter()
        elif status == "expired":
            self._apply_expired_tenders_filter()
        
        # Refresh display
        self._refresh_tree_data()
        self.update_dashboard()

    def _apply_live_tenders_filter(self):
        """Filter to show only live/active tenders."""
        if (not hasattr(self.data_processor, 'raw_data') or
            self.data_processor.raw_data is None or
            self.data_processor.raw_data.empty):
            return
        
        # Start with raw data
        self.data_processor.filtered_data = self.data_processor.raw_data.copy()
        
        # Find date columns for closing dates
        date_cols = [col for col in self.data_processor.filtered_data.columns 
                    if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]
        
        if date_cols:
            date_col = date_cols[0]
            
            # Convert to datetime if needed
            if not pd.api.types.is_datetime64_dtype(self.data_processor.filtered_data[date_col]):
                self.data_processor.filtered_data[date_col] = pd.to_datetime(
                    self.data_processor.filtered_data[date_col], errors='coerce')
            
            # Filter for dates/times in the future (live tenders) - USE CURRENT DATETIME
            current_datetime = pd.Timestamp.now()  # This includes time
            mask = self.data_processor.filtered_data[date_col] > current_datetime
            self.data_processor.filtered_data = self.data_processor.filtered_data[mask]
            
            self.logger.info(f"Live tenders filter: {len(self.data_processor.filtered_data)} records closing after {current_datetime}")
        else:
            # Fallback: look for status column
            status_cols = [col for col in self.data_processor.filtered_data.columns if 'status' in col.lower()]
            if status_cols:
                status_col = status_cols[0]
                mask = self.data_processor.filtered_data[status_col].astype(str).str.lower().str.contains('active|live|open', na=False)
                self.data_processor.filtered_data = self.data_processor.filtered_data[mask]

    def _apply_expired_tenders_filter(self):
        """Filter to show only expired/closed tenders."""
        if (not hasattr(self.data_processor, 'raw_data') or
            self.data_processor.raw_data is None or
            self.data_processor.raw_data.empty):
            return
        
        # Start with raw data
        self.data_processor.filtered_data = self.data_processor.raw_data.copy()
        
        # Find date columns for closing dates
        date_cols = [col for col in self.data_processor.filtered_data.columns 
                    if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]
        
        if date_cols:
            date_col = date_cols[0]
            
            # Convert to datetime if needed
            if not pd.api.types.is_datetime64_dtype(self.data_processor.filtered_data[date_col]):
                self.data_processor.filtered_data[date_col] = pd.to_datetime(
                    self.data_processor.filtered_data[date_col], errors='coerce')
            
            # Filter for dates/times in the past (expired tenders) - USE CURRENT DATETIME
            current_datetime = pd.Timestamp.now()  # This includes time
            mask = self.data_processor.filtered_data[date_col] < current_datetime
            self.data_processor.filtered_data = self.data_processor.filtered_data[mask]
            
            self.logger.info(f"Expired tenders filter: {len(self.data_processor.filtered_data)} records closed before {current_datetime}")
        else:
            # Fallback: look for status column
            status_cols = [col for col in self.data_processor.filtered_data.columns if 'status' in col.lower()]
            if status_cols:
                status_col = status_cols[0]
                mask = ~self.data_processor.filtered_data[status_col].astype(str).str.lower().str.contains('active|live|open', na=False)
                self.data_processor.filtered_data = self.data_processor.filtered_data[mask]

    def _apply_time_range_filter(self, time_range):
        """Apply time range filter (today, next_3_days, etc.)."""
        if (not hasattr(self.data_processor, 'filtered_data') or
            self.data_processor.filtered_data is None or
            self.data_processor.filtered_data.empty):
            return
        
        # Find date columns
        date_cols = [col for col in self.data_processor.filtered_data.columns 
                    if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]
        
        if not date_cols:
            return
        
        date_col = date_cols[0]
        
        # Convert to datetime if needed
        if not pd.api.types.is_datetime64_dtype(self.data_processor.filtered_data[date_col]):
            self.data_processor.filtered_data[date_col] = pd.to_datetime(
                self.data_processor.filtered_data[date_col], errors='coerce')
        
        # Calculate date ranges using current datetime for precise filtering
        current_datetime = pd.Timestamp.now()
        today_start = current_datetime.normalize()  # Start of today (00:00:00)
        
        if time_range == "today":
            # Today: from now until end of today
            end_date = today_start + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            mask = (
                (self.data_processor.filtered_data[date_col] >= current_datetime) & 
                (self.data_processor.filtered_data[date_col] <= end_date)
            )
        elif time_range == "next_3_days":
            # Next 3 days: from now until end of 3 days from today
            end_date = today_start + pd.Timedelta(days=3, hours=23, minutes=59, seconds=59)
            mask = (
                (self.data_processor.filtered_data[date_col] >= current_datetime) & 
                (self.data_processor.filtered_data[date_col] <= end_date)
            )
        elif time_range == "next_7_days":
            # Next 7 days: from now until end of 7 days from today
            end_date = today_start + pd.Timedelta(days=7, hours=23, minutes=59, seconds=59)
            mask = (
                (self.data_processor.filtered_data[date_col] >= current_datetime) & 
                (self.data_processor.filtered_data[date_col] <= end_date)
            )
        elif time_range == "next_30_days":
            # Next 30 days: from now until end of 30 days from today
            end_date = today_start + pd.Timedelta(days=30, hours=23, minutes=59, seconds=59)
            mask = (
                (self.data_processor.filtered_data[date_col] >= current_datetime) & 
                (self.data_processor.filtered_data[date_col] <= end_date)
            )
        else:
            return
        
        # Apply the date range filter
        self.data_processor.filtered_data = self.data_processor.filtered_data[mask]
        
        self.logger.info(f"Time range filter ({time_range}): {len(self.data_processor.filtered_data)} records from {current_datetime}")
        
        # Refresh display
        self._refresh_tree_data()
        self.update_dashboard()

    def _clear_time_filter_selection(self):
        """Clear the visual selection of time filter buttons."""
        # Reset all time filter buttons to default state
        for key in ["today", "next_3_days", "next_7_days", "next_30_days"]:
            if key in self.date_filter_buttons:
                btn = self.date_filter_buttons[key]
                if isinstance(btn, ttk.Button):
                    # For ttk buttons, use state
                    if hasattr(btn, 'state'):
                        btn.state(['!pressed'])
                elif isinstance(btn, tk.Button):
                    # For tk buttons, use configure
                    if hasattr(btn, 'configure'):
                        btn['background'] = "#f0f0f0"
                        btn['foreground'] = "black"