"""
Settings Tab module - UI component for application configuration.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
import sys
from typing import TYPE_CHECKING, Dict, List, Any, Optional
import re
import pandas as pd

# Fix imports by adding parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can use the absolute imports
from utils.constants import SPACING, FONTS, COLORS
from ui.common_widgets import create_labeled_frame, create_action_button, create_info_label, create_input_entry
from core.file_merger import PortalDataMerger  # Import directly for instantiation

if TYPE_CHECKING:
    from ui.main_window import MainApplication

logger = logging.getLogger(__name__)

class SettingsTab(ttk.Frame):
    """
    Settings Tab for configuring application parameters.
    """
    def __init__(self, parent: ttk.Notebook, main_app: 'MainApplication'):
        super().__init__(parent)
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # UI variables for paths with appropriate defaults
        # Default: dummy data for development, production for live use
        default_dummy_data = r"C:\Users\kalia\Downloads\dummy_data"
        default_production_data = r"H:\My Drive\CRM T84\0 Live App\Search data\merged_data"

        # Try to determine if we're in development vs production
        import os
        current_user = os.environ.get('USERNAME', '')
        # Check if production paths exist or if username suggests production environment
        production_paths = [default_production_data, r"H:\My Drive"]
        is_production = any(os.path.exists(path) for path in production_paths) or current_user.lower() not in ['kalia', 'saleem']

        if is_production and os.path.exists(default_production_data):
            default_data_default = default_production_data
            default_merged_default = default_production_data
        else:
            default_data_default = default_dummy_data
            default_merged_default = default_dummy_data

        self.default_data_folder_var = tk.StringVar(value=self.main_app.global_config.get("default_data_folder", default_data_default))
        self.merged_data_folder_var = tk.StringVar(value=self.main_app.global_config.get("merged_data_folder", default_merged_default))
        
        # UI variables for merger parameters
        self.merger_unique_keys_var = tk.StringVar(value=self._format_list_for_display(
            self.main_app.global_config.get("merger_preferred_unique_keys", 
                                           ["Tender ID (Extracted)", "Title and Ref.No./Tender ID", "Tender ID"])
        ))
        
        self.merger_critical_fields_var = tk.StringVar(value=self._format_list_for_display(
            self.main_app.global_config.get("merger_critical_fields", 
                                           ["Closing Date", "Status", "Value"])
        ))
        
        self.merger_max_backups_var = tk.StringVar(value=str(
            self.main_app.global_config.get("merger_max_backups", 5)
        ))
        
        # Status message
        self.status_var = tk.StringVar(value="Ready")
        
        # Track whether settings have been changed
        self.settings_changed = False
        
        self._create_widgets()
        self.logger.info("SettingsTab initialized")
    
    def _format_list_for_display(self, items: List[str]) -> str:
        """Format a list of strings for display in a text field."""
        if not items:
            return ""
        return ", ".join(items)
    
    def _parse_comma_separated_list(self, text: str) -> List[str]:
        """Parse a comma-separated string into a list of trimmed strings."""
        if not text or not text.strip():
            return []
        # Split by commas and trim whitespace
        return [item.strip() for item in text.split(",") if item.strip()]
    
    def _create_widgets(self):
        """Create the UI components."""
        # Main container with scrolling capability
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['medium'], pady=SPACING['medium'])
        
        # Main settings content
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Section 1: File Paths Settings
        paths_frame = create_labeled_frame(content_frame, "File Paths")
        paths_frame.pack(fill=tk.X, pady=SPACING['medium'])
        
        # Default Data Folder
        default_data_row = ttk.Frame(paths_frame)
        default_data_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        info_label = create_info_label(default_data_row, "Default Data Folder:")
        info_label.pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        default_data_entry = ttk.Entry(default_data_row, textvariable=self.default_data_folder_var, width=50)
        default_data_entry.pack(side=tk.LEFT, padx=(0, SPACING['small']), fill=tk.X, expand=True)
        
        browse_btn = create_action_button(
            default_data_row, "Browse...", 
            lambda: self._browse_folder(self.default_data_folder_var),
            width=10
        )
        browse_btn.pack(side=tk.LEFT)
        
        # Help text for default data folder
        create_info_label(
            paths_frame, 
            "This folder is used as the starting directory when adding data folders in the Search tab.",
            font_style=FONTS.get('small', ('TkDefaultFont', 9, 'italic'))
        ).pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))
        
        # Merged Data Folder
        merged_data_row = ttk.Frame(paths_frame)
        merged_data_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        create_info_label(merged_data_row, "Merged Data Folder:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        merged_data_entry = ttk.Entry(merged_data_row, textvariable=self.merged_data_folder_var, width=50)
        merged_data_entry.pack(side=tk.LEFT, padx=(0, SPACING['small']), fill=tk.X, expand=True)
        
        create_action_button(
            merged_data_row, "Browse...", 
            lambda: self._browse_folder(self.merged_data_folder_var),
            width=10
        ).pack(side=tk.LEFT)
        
        # Help text for merged data folder
        create_info_label(
            paths_frame, 
            "This folder is used as the default output location for merged files in the Portal Merger tab.",
            font_style=FONTS.get('small', ('TkDefaultFont', 9, 'italic'))
        ).pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))
        
        # Section 2: Merger Settings
        merger_frame = create_labeled_frame(content_frame, "File Merger Settings")
        merger_frame.pack(fill=tk.X, pady=SPACING['medium'])
        
        # Unique Keys
        unique_keys_row = ttk.Frame(merger_frame)
        unique_keys_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        create_info_label(unique_keys_row, "Preferred Unique Keys:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        unique_keys_entry = ttk.Entry(unique_keys_row, textvariable=self.merger_unique_keys_var, width=60)
        unique_keys_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Help text for unique keys
        create_info_label(
            merger_frame, 
            "Comma-separated list of column names to try as unique identifiers when merging files.\n"
            "These are checked in order, and the first one found in both files is used.",
            font_style=FONTS.get('small', ('TkDefaultFont', 9, 'italic'))
        ).pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))
        
        # Critical Fields
        critical_fields_row = ttk.Frame(merger_frame)
        critical_fields_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        create_info_label(critical_fields_row, "Critical Fields:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        critical_fields_entry = ttk.Entry(critical_fields_row, textvariable=self.merger_critical_fields_var, width=60)
        critical_fields_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Help text for critical fields
        create_info_label(
            merger_frame, 
            "Comma-separated list of column names considered critical for change detection when merging files.",
            font_style=FONTS.get('small', ('TkDefaultFont', 9, 'italic'))
        ).pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))
        
        # Max Backups
        max_backups_row = ttk.Frame(merger_frame)
        max_backups_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        create_info_label(max_backups_row, "Maximum Backups per Portal:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        # Use a Spinbox for numeric entry
        max_backups_spinbox = ttk.Spinbox(
            max_backups_row, 
            from_=1, 
            to=20,
            textvariable=self.merger_max_backups_var,
            width=5
        )
        max_backups_spinbox.pack(side=tk.LEFT)
        
        # Help text for max backups
        create_info_label(
            merger_frame, 
            "The maximum number of backup files to keep for each portal's consolidated master file.",
            font_style=FONTS.get('small', ('TkDefaultFont', 9, 'italic'))
        ).pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))
        
        # Section 3: Treeview Column Settings
        treeview_frame = create_labeled_frame(content_frame, "Treeview Column Settings")
        treeview_frame.pack(fill=tk.X, pady=SPACING['medium'])

        # Initialize column settings variables
        self.column_settings = self.main_app.global_config.get("treeview_column_settings", {})
        self.column_vars = {}  # Dictionary to store checkbox variables
        self.width_vars = {}   # Dictionary to store width variables
        self.column_order = []  # List to maintain column order
        self.selected_column = None  # Currently selected column for moving
        self.column_frames = {}  # Dictionary to store frame references

        # Default column sequence and settings
        self._initialize_default_column_settings()

        # Create scrollable frame for column settings
        columns_container = ttk.Frame(treeview_frame)
        columns_container.pack(fill=tk.BOTH, expand=True, padx=SPACING['medium'], pady=SPACING['small'])

        # Header row with ordering controls
        header_frame = ttk.Frame(columns_container)
        header_frame.pack(fill=tk.X, pady=(0, SPACING['small']))

        ttk.Label(header_frame, text="Order", font=FONTS.get('subheading', ('TkDefaultFont', 10, 'bold')), width=8).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Column Name", font=FONTS.get('subheading', ('TkDefaultFont', 10, 'bold'))).pack(side=tk.LEFT, padx=(0, SPACING['large']))
        ttk.Label(header_frame, text="Visible", font=FONTS.get('subheading', ('TkDefaultFont', 10, 'bold'))).pack(side=tk.LEFT, padx=(0, SPACING['large']))
        ttk.Label(header_frame, text="Width", font=FONTS.get('subheading', ('TkDefaultFont', 10, 'bold'))).pack(side=tk.LEFT, padx=(0, SPACING['medium']))

        # Separator line
        ttk.Separator(columns_container, orient="horizontal").pack(fill=tk.X, pady=SPACING['small'])

        # Scrollable frame for column list
        columns_scroll_frame = ttk.Frame(columns_container)
        columns_scroll_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas and scrollbar for scrolling
        canvas = tk.Canvas(columns_scroll_frame, height=150)
        scrollbar = ttk.Scrollbar(columns_scroll_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Store reference to scrollable frame for adding columns
        self.columns_scrollable_frame = scrollable_frame

        # Load and display current column settings
        self._load_column_settings()

        # Buttons for column management
        buttons_frame = ttk.Frame(treeview_frame)
        buttons_frame.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])

        # First row of buttons
        buttons_row1 = ttk.Frame(buttons_frame)
        buttons_row1.pack(fill=tk.X, pady=(0, SPACING['small']))

        create_action_button(
            buttons_row1, "Move Up", self._move_column_up,
            button_type='secondary', width=12
        ).pack(side=tk.LEFT, padx=(0, SPACING['small']))

        create_action_button(
            buttons_row1, "Move Down", self._move_column_down,
            button_type='secondary', width=12
        ).pack(side=tk.LEFT, padx=(0, SPACING['small']))

        create_action_button(
            buttons_row1, "Reset Order", self._reset_column_order,
            button_type='warning', width=12
        ).pack(side=tk.LEFT, padx=(0, SPACING['small']))

        create_action_button(
            buttons_row1, "Reset All Settings", self._reset_column_settings,
            button_type='danger', width=15
        ).pack(side=tk.LEFT, padx=(0, SPACING['small']))

        # Second row of buttons
        buttons_row2 = ttk.Frame(buttons_frame)
        buttons_row2.pack(fill=tk.X, pady=(0, SPACING['small']))

        create_action_button(
            buttons_row2, "Apply to Current View", self._apply_column_settings_to_current_view,
            button_type='info', width=18
        ).pack(side=tk.LEFT, padx=(0, SPACING['small']))

        create_action_button(
            buttons_row2, "Export Settings", self._export_column_settings,
            button_type='success_outline', width=14
        ).pack(side=tk.LEFT, padx=(0, SPACING['small']))

        create_action_button(
            buttons_row2, "Import Settings", self._import_column_settings,
            button_type='info_outline', width=14
        ).pack(side=tk.LEFT)

        # Help text for column settings
        create_info_label(
            treeview_frame,
            "Configure column order, visibility, and widths for the Search & Dashboard treeview.\n"
            "Use Move Up/Down to reorder columns. Changes apply automatically on data refresh.\n"
            "Default hidden columns: 'Sr number', 'Data source Path'.",
            font_style=FONTS.get('small', ('TkDefaultFont', 9, 'italic'))
        ).pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))

        # Section 4: Performance Settings
        performance_frame = create_labeled_frame(content_frame, "Performance")
        performance_frame.pack(fill=tk.X, pady=SPACING['medium'])

        # Benchmark settings
        benchmark_row = ttk.Frame(performance_frame)
        benchmark_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])

        create_info_label(benchmark_row, "Benchmark Window:").pack(side=tk.LEFT, padx=(0, SPACING['small']))

        create_action_button(
            benchmark_row, "Open Benchmark Monitor",
            self._open_benchmark_window,
            button_type='primary', width=20
        ).pack(side=tk.LEFT, padx=(0, SPACING['small']))

        # Performance monitoring settings
        perf_settings_frame = ttk.Frame(performance_frame)
        perf_settings_frame.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])

        # Auto-refresh interval
        refresh_row = ttk.Frame(perf_settings_frame)
        refresh_row.pack(fill=tk.X, pady=2)

        create_info_label(refresh_row, "Monitoring Refresh Rate (seconds):").pack(side=tk.LEFT, padx=(0, SPACING['small']))

        self.refresh_rate_var = tk.StringVar(value=str(self.main_app.global_config.get("performance_refresh_rate", 1)))
        ttk.Spinbox(refresh_row, from_=1, to=10, textvariable=self.refresh_rate_var,
                   width=5, command=self._on_setting_changed).pack(side=tk.LEFT)

        # Help text for performance settings
        create_info_label(
            performance_frame,
            "Monitor system performance and run detailed benchmarks in a separate window.\n"
            "The Benchmark Monitor provides real-time graphs and industry-standard performance tests.",
            font_style=FONTS.get('small', ('TkDefaultFont', 9, 'italic'))
        ).pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))

        # Section 5: Advanced Settings (placeholder for future)
        advanced_frame = create_labeled_frame(content_frame, "Advanced Settings")
        advanced_frame.pack(fill=tk.X, pady=SPACING['medium'])

        # Placeholder for future advanced settings
        ttk.Label(
            advanced_frame,
            text="Additional advanced settings will be available in future updates.",
            padding=SPACING['medium'],
            font=FONTS.get('body', ('TkDefaultFont', 10, 'italic'))
        ).pack(fill=tk.X)
        
        # Action Buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill=tk.X, pady=SPACING['medium'])
        
        create_action_button(
            button_frame, "Reset to Defaults", self._reset_to_defaults,
            button_type='secondary', width=15
        ).pack(side=tk.LEFT, padx=SPACING['small'])
        
        # Save button right-aligned
        create_action_button(
            button_frame, "Save Settings", self._save_settings,
            button_type='primary', width=15
        ).pack(side=tk.RIGHT, padx=SPACING['small'])
        
        # Status message at the bottom
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(SPACING['small'], 0))
        
        # Bind change events to track modifications
        self.default_data_folder_var.trace_add("write", self._on_setting_changed)
        self.merged_data_folder_var.trace_add("write", self._on_setting_changed)
        self.merger_unique_keys_var.trace_add("write", self._on_setting_changed)
        self.merger_critical_fields_var.trace_add("write", self._on_setting_changed)
        self.merger_max_backups_var.trace_add("write", self._on_setting_changed)
        self.refresh_rate_var.trace_add("write", self._on_setting_changed)

    def _on_column_setting_changed(self, *args):
        """Track when column settings have been changed."""
        self.settings_changed = True
        self.status_var.set("Column settings changed. Click 'Save Settings' to apply.")

    def _reset_column_settings(self):
        """Reset column settings to defaults."""
        confirm = messagebox.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset all column settings to their default values?",
            parent=self
        )

        if not confirm:
            return

        # Clear current settings
        self.main_app.global_config.set("treeview_column_settings", {})

        # Reload column settings (will use defaults)
        self._load_column_settings()

        self.settings_changed = True
        self.status_var.set("Column settings reset to defaults. Click 'Save Settings' to apply.")

    def _apply_column_settings_to_current_view(self):
        """Apply column settings to the current Search & Dashboard view."""
        try:
            # Get the Search & Dashboard tab
            search_tab = self.main_app.tabs.get("Search & Dashboard")
            if not search_tab or not hasattr(search_tab, 'tree'):
                messagebox.showwarning("No Active View", "Search & Dashboard tab is not available or has no data loaded.")
                return

            # Save current settings first
            self._save_column_settings()

            # Apply settings to current treeview using search tab's method
            search_tab._apply_column_settings_to_treeview()

            messagebox.showinfo("Settings Applied", "Column settings applied to current view successfully.")

        except Exception as e:
            self.logger.error(f"Error applying column settings to current view: {e}")
            messagebox.showerror("Apply Error", f"Failed to apply column settings:\n{str(e)}")



    def _apply_column_settings_to_treeview(self, treeview):
        """Apply column settings to a specific treeview widget."""
        if not treeview:
            return

        try:
            column_settings = self.main_app.global_config.get("treeview_column_settings", {})

            # Get current columns
            current_columns = treeview['columns']

            for col in current_columns:
                settings = column_settings.get(col, {})

                # Set visibility (hide/show column)
                if not settings.get("visible", True):
                    # Hide column by setting width to 0
                    treeview.column(col, width=0, minwidth=0)
                else:
                    # Show column with configured width
                    width = settings.get("width", 100)
                    treeview.column(col, width=width, minwidth=50)

        except Exception as e:
            self.logger.error(f"Error applying column settings to treeview: {e}")

    def _open_benchmark_window(self):
        """Open the benchmark monitor window."""
        try:
            # Import the benchmark window
            from ui.benchmark_window import BenchmarkWindow

            # Create and show the benchmark window
            benchmark_window = BenchmarkWindow(self, self.main_app)

            self.logger.info("Benchmark window opened from settings")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open benchmark window: {e}", parent=self)
            self.logger.error(f"Error opening benchmark window: {e}")

    def _on_setting_changed(self, *args):
        """Track when settings have been changed."""
        self.settings_changed = True
        self.status_var.set("Settings changed. Click 'Save Settings' to apply.")
    
    def _browse_folder(self, string_var: tk.StringVar):
        """Open a folder browser dialog and update the specified StringVar."""
        folder_path = filedialog.askdirectory(
            title="Select Folder",
            initialdir=string_var.get() or os.path.expanduser("~")
        )
        if folder_path:
            string_var.set(folder_path)
            self.settings_changed = True
            self.status_var.set("Settings changed. Click 'Save Settings' to apply.")
    
    def _reset_to_defaults(self):
        """Reset all settings to their default values."""
        confirm = messagebox.askyesno(
            "Confirm Reset", 
            "Are you sure you want to reset all settings to their default values?",
            parent=self
        )
        
        if not confirm:
            return
        
        # Default values - use relative paths for portability
        default_config = {
            "default_data_folder": "./data/input_excel_files/",
            "merged_data_folder": "./data/merged_data/",
            "merger_preferred_unique_keys": ["Tender ID (Extracted)", "Title and Ref.No./Tender ID", "Tender ID"],
            "merger_critical_fields": ["Closing Date", "Status", "Value"],
            "merger_max_backups": 5
        }
        
        # Update UI variables
        self.default_data_folder_var.set(default_config["default_data_folder"])
        self.merged_data_folder_var.set(default_config["merged_data_folder"])
        self.merger_unique_keys_var.set(self._format_list_for_display(default_config["merger_preferred_unique_keys"]))
        self.merger_critical_fields_var.set(self._format_list_for_display(default_config["merger_critical_fields"]))
        self.merger_max_backups_var.set(str(default_config["merger_max_backups"]))
        
        self.settings_changed = True
        self.status_var.set("Settings reset to defaults. Click 'Save Settings' to apply.")
    
    def _save_settings(self):
        """Save the current settings to config."""
        try:
            # Validate max backups (must be a positive integer)
            try:
                max_backups = int(self.merger_max_backups_var.get())
                if max_backups < 1:
                    raise ValueError("Maximum backups must be at least 1")
            except ValueError as e:
                messagebox.showerror("Invalid Setting", f"Invalid value for maximum backups: {str(e)}", parent=self)
                return

            # Validate refresh rate
            try:
                refresh_rate = int(self.refresh_rate_var.get())
                if refresh_rate < 1 or refresh_rate > 10:
                    raise ValueError("Refresh rate must be between 1 and 10 seconds")
            except ValueError as e:
                messagebox.showerror("Invalid Setting", f"Invalid refresh rate: {str(e)}", parent=self)
                return

            # Prepare the settings to save
            settings_to_save = {
                "default_data_folder": self.default_data_folder_var.get(),
                "merged_data_folder": self.merged_data_folder_var.get(),
                "merger_preferred_unique_keys": self._parse_comma_separated_list(self.merger_unique_keys_var.get()),
                "merger_critical_fields": self._parse_comma_separated_list(self.merger_critical_fields_var.get()),
                "merger_max_backups": max_backups,
                "performance_refresh_rate": refresh_rate
            }

            # Save column settings
            self._save_column_settings()
            
            # Create directories if they don't exist
            for path_key in ["default_data_folder", "merged_data_folder"]:
                path = settings_to_save[path_key]
                if path and not os.path.exists(path):
                    try:
                        os.makedirs(path, exist_ok=True)
                        self.logger.info(f"Created directory: {path}")
                    except Exception as e:
                        messagebox.showwarning(
                            "Directory Creation Failed", 
                            f"Could not create directory '{path}':\n{str(e)}",
                            parent=self
                        )
            
            # Update global config
            for key, value in settings_to_save.items():
                self.main_app.global_config.set(key, value)
            
            # Save to file
            self.main_app.global_config.save_config()
            
            # Reset change tracking
            self.settings_changed = False
            self.status_var.set("Settings saved successfully.")
            
            # Notify relevant components of config changes
            self._propagate_config_changes(settings_to_save)
            
            self.logger.info("Settings saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}", exc_info=True)
            messagebox.showerror("Save Error", f"Failed to save settings:\n{str(e)}", parent=self)
    
    def _propagate_config_changes(self, new_settings: Dict[str, Any]):
        """Notify other components of configuration changes."""
        try:
            # Update Search tab's data processor with new paths if it exists
            search_tab = self.main_app.tabs.get("Search & Dashboard")
            if search_tab and hasattr(search_tab, "data_processor"):
                if hasattr(search_tab.data_processor, 'update_config'):
                    search_tab.data_processor.update_config(self.main_app.global_config)
                    self.logger.info("Updated Search tab's data processor with new config")
                else:
                    # Recreate the data processor with new config
                    from core.data_processor import TenderDataProcessor
                    search_tab.data_processor = TenderDataProcessor(self.main_app.global_config)
                    self.logger.info("Recreated Search tab's data processor with new config")
            
            # Update Portal Merger tab with new merger settings if it exists
            merger_tab = self.main_app.tabs.get("Portal Merger")
            if merger_tab and hasattr(merger_tab, "merger"):
                merger_tab.merger = None  # Force recreation with new config
                # Create a new PortalDataMerger instance directly
                merger_tab.merger = PortalDataMerger(self.main_app.global_config)
                self.logger.info("Updated Portal Merger tab with new config")
                
        except Exception as e:
            self.logger.error(f"Error propagating config changes: {e}")
            # Don't raise the error, just log it so settings still save
    
    def on_tab_selected(self):
        """Called when this tab is selected."""
        # Refresh displayed values from current config with smart defaults
        # Default: dummy data for development, production for live use
        default_dummy_data = r"C:\Users\kalia\Downloads\dummy_data"
        default_production_data = r"H:\My Drive\CRM T84\0 Live App\Search data\merged_data"

        # Try to determine if we're in development vs production
        current_user = os.environ.get('USERNAME', '')
        # Check if production paths exist or if username suggests production environment
        production_paths = [default_production_data, r"H:\My Drive"]
        is_production = any(os.path.exists(path) for path in production_paths) or current_user.lower() not in ['kalia', 'saleem']

        if is_production and os.path.exists(default_production_data):
            default_data_default = default_production_data
            default_merged_default = default_production_data
        else:
            default_data_default = default_dummy_data
            default_merged_default = default_dummy_data

        self.default_data_folder_var.set(self.main_app.global_config.get("default_data_folder", default_data_default))
        self.merged_data_folder_var.set(self.main_app.global_config.get("merged_data_folder", default_merged_default))
        
        self.merger_unique_keys_var.set(self._format_list_for_display(
            self.main_app.global_config.get("merger_preferred_unique_keys", [])
        ))
        
        self.merger_critical_fields_var.set(self._format_list_for_display(
            self.main_app.global_config.get("merger_critical_fields", [])
        ))
        
        self.merger_max_backups_var.set(str(
            self.main_app.global_config.get("merger_max_backups", 5)
        ))
        
        # Reset change tracking
        self.settings_changed = False
        self.status_var.set("Ready")
        
        self.logger.info("Settings tab selected and refreshed")

    def check_unsaved_changes(self) -> bool:
        """
        Check if there are unsaved changes when switching tabs or closing the application.
        Returns True if it's safe to proceed, False if the operation should be cancelled.
        """
        if not self.settings_changed:
            return True

        response = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved settings changes. Would you like to save them before continuing?",
            parent=self
        )

        if response is None:  # Cancel
            return False
        if response is True:  # Yes, save
            self._save_settings()
            return not self.settings_changed  # Only proceed if save was successful
        return True  # No, discard changes

    def _initialize_default_column_settings(self):
        """Initialize default column settings with proper sequence and hidden columns."""
        self.default_column_sequence = [
            "Department", "Closing Date", "Tender ID", "Tender Name", "Direct URL",
            "Status URL", "e-Publish Date", "Opening Date"
        ]

        # Columns to hide by default
        self.columns_hidden_by_default = ["Sr number", "Data source Path"]

        # Default widths for proportionate sizing
        self.default_column_widths = {
            "Tender ID": 120,
            "Tender Name": 250,
            "Title": 250,
            "Department": 150,
            "Closing Date": 120,
            "Status": 100,
            "Value": 100,
            "Location": 150,
            "Source File": 150,
            "Description": 300,
            "Agency": 180,
            "Ministry": 180,
            "Tender ID (Extracted)": 120,
            "Title and Ref.No./Tender ID": 200,
            "Direct URL": 120,
            "Status URL": 120,
            "e-Publish Date": 120,
            "Opening Date": 120
        }

        self.logger.info("Default column settings initialized")

    def _load_column_settings(self):
        """Load and display column settings from config in ordered manner."""
        # Clear existing column settings
        for widget in self.columns_scrollable_frame.winfo_children():
            widget.destroy()

        self.column_vars = {}
        self.width_vars = {}
        self.column_order = []

        # Get current column settings from config
        column_settings = self.main_app.global_config.get("treeview_column_settings", {})

        # If no settings exist, create default settings
        if not column_settings:
            column_settings = self._create_default_column_settings()

        # Get column order from config or use default sequence
        column_order = self.main_app.global_config.get("treeview_column_order", self.default_column_sequence.copy())

        # Add any new columns from data that aren't in the order yet
        for col_name in column_settings:
            if col_name not in column_order:
                column_order.append(col_name)

        # Update stored order
        self.column_order = column_order

        # Create UI elements for each column in order
        for order_num, col_name in enumerate(column_order, 1):
            if col_name in column_settings:
                settings = column_settings[col_name]
                self._create_column_setting_row(order_num, col_name, settings)

        self.logger.info(f"Loaded column settings for {len(column_order)} columns")

    def _create_default_column_settings(self):
        """Create default column settings with proper defaults."""
        column_settings = {}

        # Common tender columns
        common_columns = [
            "Tender ID", "Tender Name", "Title", "Department", "Closing Date", "Status",
            "Value", "Location", "Source File", "Description", "Agency", "Ministry",
            "Tender ID (Extracted)", "Title and Ref.No./Tender ID", "Direct URL",
            "Status URL", "e-Publish Date", "Opening Date", "Sr number", "Data source Path"
        ]

        for col in common_columns:
            # Check if column should be hidden by default
            is_visible = col not in self.columns_hidden_by_default
            width = self.default_column_widths.get(col, 100)

            column_settings[col] = {
                "visible": is_visible,
                "width": width
            }

        return column_settings

    def _create_column_setting_row(self, order_num: int, col_name: str, settings: dict):
        """Create a single column setting row in the UI."""
        col_frame = ttk.Frame(self.columns_scrollable_frame)
        col_frame.pack(fill=tk.X, pady=1)

        # Store the column name and frame reference for selection/movement
        # Use a custom attribute stored in our own dict instead
        if not hasattr(self, 'column_frames'):
            self.column_frames = {}
        self.column_frames[col_name] = col_frame

        # Make the frame clickable for selection
        def select_column(event=None, frame=col_frame, name=col_name):
            self._select_column(name)

        col_frame.bind("<Button-1>", select_column)
        col_frame.configure(cursor="hand2")  # Change cursor on hover

        # Order number label
        order_label = ttk.Label(col_frame, text=str(order_num), width=6, anchor="center")
        order_label.pack(side=tk.LEFT, padx=(0, SPACING['small']))
        order_label.bind("<Button-1>", select_column)

        # Column name label
        name_label = ttk.Label(col_frame, text=col_name, width=25, anchor="w")
        name_label.pack(side=tk.LEFT, padx=(0, SPACING['medium']))
        name_label.bind("<Button-1>", select_column)

        # Visibility checkbox
        visible_var = tk.BooleanVar(value=settings.get("visible", True))
        self.column_vars[col_name] = visible_var

        visible_cb = ttk.Checkbutton(col_frame, variable=visible_var,
                                   command=self._on_column_setting_changed)
        visible_cb.pack(side=tk.LEFT, padx=(0, SPACING['medium']))

        # Width spinbox
        width_var = tk.StringVar(value=str(settings.get("width", 100)))
        self.width_vars[col_name] = width_var

        width_sb = ttk.Spinbox(col_frame, from_=50, to=500, textvariable=width_var,
                             width=5, command=self._on_column_setting_changed)
        width_sb.pack(side=tk.LEFT)

        # Bind width variable change
        width_var.trace_add("write", self._on_column_setting_changed)

    def _select_column(self, col_name: str):
        """Select a column for movement operations."""
        # Clear previous selection visual indicator
        if hasattr(self, 'selected_column') and self.selected_column:
            if self.selected_column in self.column_frames:
                frame = self.column_frames[self.selected_column]
                # Reset background color
                frame.configure(style="TFrame")

        # Set new selection
        self.selected_column = col_name

        # Apply selection visual indicator
        if col_name in self.column_frames:
            frame = self.column_frames[col_name]
            # Make it look selected (light blue background)
            style = ttk.Style()
            style.configure("Selected.TFrame", background="#e3f2fd")  # Light blue background
            frame.configure(style="Selected.TFrame")

        self.logger.info(f"Selected column: {col_name}")

    def _move_column_up(self):
        """Move selected column up in the order."""
        if not self.selected_column or self.selected_column not in self.column_order:
            messagebox.showwarning("No Column Selected", "Please click on a column row to select it first.")
            return

        current_index = self.column_order.index(self.selected_column)
        if current_index > 0:
            # Swap with the previous item
            self.column_order[current_index], self.column_order[current_index - 1] = \
                self.column_order[current_index - 1], self.column_order[current_index]

            # Reload the UI with new order
            self._load_column_settings()
            self.settings_changed = True
            self.status_var.set("Column moved up. Click 'Save Settings' to apply.")
        else:
            messagebox.showinfo("Can't Move Up", "This column is already at the top.")

    def _move_column_down(self):
        """Move selected column down in the order."""
        if not self.selected_column or self.selected_column not in self.column_order:
            messagebox.showwarning("No Column Selected", "Please click on a column row to select it first.")
            return

        current_index = self.column_order.index(self.selected_column)
        if current_index < len(self.column_order) - 1:
            # Swap with the next item
            self.column_order[current_index], self.column_order[current_index + 1] = \
                self.column_order[current_index + 1], self.column_order[current_index]

            # Reload the UI with new order
            self._load_column_settings()
            self.settings_changed = True
            self.status_var.set("Column moved down. Click 'Save Settings' to apply.")
        else:
            messagebox.showinfo("Can't Move Down", "This column is already at the bottom.")

    def _reset_column_order(self):
        """Reset column order to the default sequence."""
        confirm = messagebox.askyesno(
            "Confirm Reset Order",
            "Reset column order to default sequence?",
            parent=self
        )

        if not confirm:
            return

        # Reset to default order
        self.column_order = self.default_column_sequence.copy()
        self.main_app.global_config.set("treeview_column_order", self.column_order)

        # Reload column settings
        self._load_column_settings()

        self.settings_changed = True
        self.status_var.set("Column order reset. Click 'Save Settings' to apply.")

    def _export_column_settings(self):
        """Export column settings to a JSON file."""
        try:
            column_settings = self.main_app.global_config.get("treeview_column_settings", {})
            column_order = self.main_app.global_config.get("treeview_column_order", self.column_order)

            export_data = {
                "column_settings": column_settings,
                "column_order": column_order,
                "export_date": str(pd.Timestamp.now())
            }

            file_path = filedialog.asksaveasfilename(
                title="Export Column Settings",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )

            if file_path:
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                messagebox.showinfo("Export Successful",
                                  f"Column settings exported to:\n{file_path}")
                self.logger.info(f"Column settings exported to: {file_path}")

        except Exception as e:
            self.logger.error(f"Error exporting column settings: {e}")
            messagebox.showerror("Export Error", f"Failed to export settings: {str(e)}")

    def _import_column_settings(self):
        """Import column settings from a JSON file."""
        try:
            file_path = filedialog.askopenfilename(
                title="Import Column Settings",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )

            if not file_path:
                return

            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            if "column_settings" in import_data:
                self.main_app.global_config.set("treeview_column_settings", import_data["column_settings"])
            if "column_order" in import_data:
                self.main_app.global_config.set("treeview_column_order", import_data["column_order"])

            # Reload the UI
            self._load_column_settings()

            messagebox.showinfo("Import Successful",
                              f"Column settings imported from:\n{file_path}")
            self.logger.info(f"Column settings imported from: {file_path}")

            self.settings_changed = True
            self.status_var.set("Column settings imported. Click 'Save Settings' to apply.")

        except Exception as e:
            self.logger.error(f"Error importing column settings: {e}")
            messagebox.showerror("Import Error", f"Failed to import settings: {str(e)}")

    def _save_column_settings(self):
        """Save current column settings to config."""
        column_settings = {}

        for col_name in self.column_vars:
            visible = self.column_vars[col_name].get()
            try:
                width = int(self.width_vars[col_name].get())
            except ValueError:
                width = 100  # Default width if invalid

            column_settings[col_name] = {
                "visible": visible,
                "width": width
            }

        self.main_app.global_config.set("treeview_column_settings", column_settings)

        # Save column order
        if self.column_order:
            self.main_app.global_config.set("treeview_column_order", self.column_order)
