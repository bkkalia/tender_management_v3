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
        
        # UI variables for paths
        self.default_data_folder_var = tk.StringVar(value=self.main_app.global_config.get("default_data_folder", ""))
        self.merged_data_folder_var = tk.StringVar(value=self.main_app.global_config.get("merged_data_folder", ""))
        
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
        
        create_info_label(default_data_row, "Default Data Folder:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        default_data_entry = ttk.Entry(default_data_row, textvariable=self.default_data_folder_var, width=50)
        default_data_entry.pack(side=tk.LEFT, padx=(0, SPACING['small']), fill=tk.X, expand=True)
        
        create_action_button(
            default_data_row, "Browse...", 
            lambda: self._browse_folder(self.default_data_folder_var),
            width=10
        ).pack(side=tk.LEFT)
        
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
        
        # Section 3: Advanced Settings (placeholder for future)
        advanced_frame = create_labeled_frame(content_frame, "Advanced Settings")
        advanced_frame.pack(fill=tk.X, pady=SPACING['medium'])
        
        # Placeholder for future advanced settings
        ttk.Label(
            advanced_frame, 
            text="Advanced settings will be available in a future update.",
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
            
            # Prepare the settings to save
            settings_to_save = {
                "default_data_folder": self.default_data_folder_var.get(),
                "merged_data_folder": self.merged_data_folder_var.get(),
                "merger_preferred_unique_keys": self._parse_comma_separated_list(self.merger_unique_keys_var.get()),
                "merger_critical_fields": self._parse_comma_separated_list(self.merger_critical_fields_var.get()),
                "merger_max_backups": max_backups
            }
            
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
        # Refresh displayed values from current config
        self.default_data_folder_var.set(self.main_app.global_config.get("default_data_folder", ""))
        self.merged_data_folder_var.set(self.main_app.global_config.get("merged_data_folder", ""))
        
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