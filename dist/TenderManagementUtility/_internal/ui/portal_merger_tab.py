# ui/portal_merger_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Listbox, Scrollbar, MULTIPLE, END
import logging
import os
import sys
from typing import TYPE_CHECKING, Optional, List
import re

# Fix imports by adding parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can use the absolute imports
from ui.common_widgets import create_labeled_frame, create_action_button, create_info_label
from core.file_merger import PortalDataMerger
from utils.constants import SPACING, FONTS

if TYPE_CHECKING:
    from ui.main_window import MainApplication  # Use absolute import

logger = logging.getLogger(__name__)

def create_tooltip(widget, text):
    """Create a tooltip for a given widget"""
    def enter(event):
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        
        # Create a toplevel window
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        
        label = ttk.Label(tooltip, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief="solid", borderwidth=1,
                         font=("tahoma", 8, "normal"))
        label.pack(ipadx=1)
        
        widget.tooltip = tooltip
        
    def leave(event):
        if hasattr(widget, "tooltip"):
            widget.tooltip.destroy()
            
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)

class PortalDataMergerTab(ttk.Frame):
    """
    Tab for merging new portal scrape data with existing consolidated data.
    Allows selection of multiple new files for batch merging.
    """
    def __init__(self, parent: ttk.Notebook, main_app: 'MainApplication'):
        super().__init__(parent)
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.merger = PortalDataMerger(self.main_app.global_config)

        # UI Variables
        self.selected_new_files: List[str] = []
        self.output_folder_var = tk.StringVar(value=self.main_app.global_config.get("merged_data_folder", ""))
        self.status_var = tk.StringVar(value="Ready to merge.")

        self._create_widgets()

    def _create_widgets(self):
        main_frame = create_labeled_frame(self, "Portal Data Merger")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['medium'], pady=SPACING['medium'])

        # New Data Files Selection Area
        new_files_frame = create_labeled_frame(main_frame, "Select New Data Files (Daily Scrapes)")
        new_files_frame.pack(fill=tk.X, pady=SPACING['small'])

        listbox_frame = ttk.Frame(new_files_frame)
        listbox_frame.pack(fill=tk.X, expand=True, pady=(0, SPACING['small']))

        scrollbar = Scrollbar(listbox_frame, orient=tk.VERTICAL)
        self.new_files_listbox = Listbox(
            listbox_frame,
            selectmode=MULTIPLE,
            yscrollcommand=scrollbar.set,
            height=6,
            font=FONTS.get('body') or ("TkDefaultFont", 10)
        )
        scrollbar.config(command=self.new_files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.new_files_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)

        new_file_buttons_frame = ttk.Frame(new_files_frame)
        new_file_buttons_frame.pack(fill=tk.X)
        create_action_button(new_file_buttons_frame, "Add Files...", self._browse_new_files, width=12).pack(side=tk.LEFT, padx=(0, SPACING['small']))
        create_action_button(new_file_buttons_frame, "Remove Selected", self._remove_selected_files, width=15, button_type='secondary_outline').pack(side=tk.LEFT, padx=(0, SPACING['small']))
        create_action_button(new_file_buttons_frame, "Clear All", self._clear_all_files, width=10, button_type='danger_outline').pack(side=tk.LEFT)


        # REMOVED: Existing Data File Selection - This will be handled automatically

        # Output Folder Selection
        output_folder_frame = ttk.Frame(main_frame)
        output_folder_frame.pack(fill=tk.X, pady=SPACING['small'])
        create_info_label(output_folder_frame, "Output Folder for Merged Files:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        output_folder_entry = ttk.Entry(output_folder_frame, textvariable=self.output_folder_var, width=60) # Allow edit
        output_folder_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        create_action_button(output_folder_frame, "Browse...", lambda: self._browse_folder(self.output_folder_var), width=10).pack(side=tk.LEFT, padx=(SPACING['small'], 0))

        # Action Button
        create_action_button(main_frame, "Merge Selected Files", self._perform_merge, button_type='success').pack(pady=SPACING['medium'])

        # Status Area
        status_label = create_info_label(main_frame, "", textvariable=self.status_var, wraplength=700, justify=tk.LEFT)
        status_label.pack(fill=tk.X, pady=SPACING['small'])

        # Tooltips
        create_tooltip(output_folder_entry, "Folder where merged files will be saved.\nClick 'Browse...' to select a folder.")
        create_tooltip(self.new_files_listbox, "List of new data files selected for merging.\nUse 'Add Files...' to select files.")
        create_tooltip(new_file_buttons_frame.winfo_children()[0], "Add new data files to the list for merging.")
        create_tooltip(new_file_buttons_frame.winfo_children()[1], "Remove selected files from the list.")
        create_tooltip(new_file_buttons_frame.winfo_children()[2], "Clear the entire list of files.")

    def _browse_new_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Select New Data Files",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=self.main_app.global_config.get("default_data_folder")
        )
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.selected_new_files:
                    self.selected_new_files.append(file_path)
                    self.new_files_listbox.insert(END, os.path.basename(file_path))
            self.logger.info(f"Added new files for merging: {file_paths}")

    def _remove_selected_files(self):
        selected_indices = self.new_files_listbox.curselection()
        if not selected_indices:
            return
        # Remove in reverse order to avoid index shifting issues
        for i in sorted(selected_indices, reverse=True):
            removed_file_display_name = self.new_files_listbox.get(i)
            # Find the full path from self.selected_new_files to remove
            # This assumes basenames are unique enough for this display context.
            # A more robust way would be to store full paths in listbox items or a parallel list.
            # For now, let's find by basename.
            full_path_to_remove = next((fp for fp in self.selected_new_files if os.path.basename(fp) == removed_file_display_name), None)
            if full_path_to_remove:
                self.selected_new_files.remove(full_path_to_remove)
                self.logger.info(f"Removed file from merge list: {full_path_to_remove}")
            else:
                 self.logger.warning(f"Could not find full path for listbox item to remove: {removed_file_display_name}")
            self.new_files_listbox.delete(i)


    def _clear_all_files(self):
        self.selected_new_files.clear()
        self.new_files_listbox.delete(0, END)
        self.logger.info("Cleared all files from merge list.")

    def _browse_folder(self, string_var: tk.StringVar):
        folder_path = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.main_app.global_config.get("merged_data_folder")
        )
        if folder_path:
            string_var.set(folder_path)

    def _perform_merge(self):
        if not self.selected_new_files:
            messagebox.showerror("Error", "Please add new data file(s) to merge.", parent=self)
            return
        
        output_folder = self.output_folder_var.get()
        if not output_folder:
            messagebox.showerror("Error", "Please specify an output folder for merged files.", parent=self)
            return
        if not os.path.isdir(output_folder):
            messagebox.showerror("Error", f"The specified output folder does not exist:\n{output_folder}", parent=self)
            return

        # Group files by portal
        portal_files = {}
        for file_path in self.selected_new_files:
            try:
                # Use file_merger's function to extract portal name
                portal_name = self.merger._extract_portal_name(file_path)
                if portal_name not in portal_files:
                    portal_files[portal_name] = []
                portal_files[portal_name].append(file_path)
            except Exception as e:
                # Change self.main_app.logger to self.logger
                self.logger.error(f"Error extracting portal name from {file_path}: {e}")
                messagebox.showerror("Portal Name Error", f"Could not determine portal name for {os.path.basename(file_path)}")
                return

        self.status_var.set("Batch merging in progress...")
        # Change self.main_app.logger to self.logger
        self.logger.info(f"Starting batch merge process via UI. Output Folder='{output_folder}'")
        self.update_idletasks()

        success_count = 0
        fail_count = 0
        all_messages = []
        last_successful_output_path = None

        # Process each portal's files
        for portal_name, files in portal_files.items():
            # Change self.main_app.logger to self.logger
            self.logger.info(f"Processing portal {portal_name} with {len(files)} files")
            self.status_var.set(f"Processing portal: {portal_name} ({len(files)} files)...")
            self.update_idletasks()
            
            # Sort files by creation/modification time, oldest first
            sorted_files = self._sort_files_by_timestamp(files, portal_name)
            
            # Show the files being processed in order
            file_order_msg = f"Portal {portal_name}: Processing files in this order:\n"
            for i, f in enumerate(sorted_files):
                file_order_msg += f"  {i+1}. {os.path.basename(f)}\n"
            # Change self.main_app.logger to self.logger
            self.logger.info(file_order_msg)
            
            # Merge the files for this portal
            success, message, output_path = self.merger.merge_portal_files(
                files_list=sorted_files, 
                output_folder=output_folder,
                portal_name=portal_name
            )
            
            all_messages.append(f"Portal '{portal_name}':\n{message}")
            if success:
                success_count += 1
                if output_path:
                    last_successful_output_path = output_path
            else:
                fail_count += 1
        
        # Format the summary message with better spacing
        if len(portal_files) > 1:
            summary_message = f"Batch Merge Complete.\nProcessed {len(portal_files)} portals: {success_count} successful, {fail_count} failed.\n\n"
        else:
            summary_message = ""
            
        summary_message += "\n\n".join(all_messages)
        
        self.status_var.set(summary_message)

        # Create a formatted summary for the message box
        display_message = summary_message
        if len(summary_message) > 1000:  # If too long, truncate for message box
            display_message = summary_message[:1000] + "...\n\n(Full details in status area and log)"

        if fail_count > 0:
            messagebox.showwarning("Merge Partially Failed", display_message, parent=self)
        else:
            messagebox.showinfo("Merge Complete", display_message, parent=self)
        
        # Change self.main_app.logger to self.logger
        self.logger.info(f"Batch merge process completed. Success: {success_count}, Fail: {fail_count}")

        # Optionally, offer to load the LAST successfully merged file
        if success_count > 0 and last_successful_output_path:
            if messagebox.askyesno("Load Merged Data?", f"Do you want to load the last successfully merged file '{os.path.basename(last_successful_output_path)}' into the Search tab?", parent=self):
                search_tab = self.main_app.tabs.get("Search & Dashboard")
                if search_tab:
                    if hasattr(search_tab, '_clear_folders_for_new_load'):
                        search_tab._clear_folders_for_new_load()
                    
                    if hasattr(search_tab, 'load_single_file_into_processor'):
                         search_tab.load_single_file_into_processor(last_successful_output_path)
                         # Change self.main_app.logger to self.logger
                         self.logger.info(f"Automatically loading merged file '{last_successful_output_path}' into Search Tab.")
                    else:
                        messagebox.showwarning("Warning", "Could not automatically load. Search tab missing 'load_single_file_into_processor' method.", parent=self)
                else:
                    messagebox.showwarning("Warning", "Search & Dashboard tab not found. Cannot load merged file.", parent=self)
        
        # Clear the list of files to merge after processing
        self._clear_all_files()
    
    def _sort_files_by_timestamp(self, files: List[str], portal_name: str) -> List[str]:
        """
        Sort files from oldest to newest based on timestamps in filenames or file properties.
        This ensures older data is processed first, and newer data takes precedence.
        """
        files_with_timestamps = []
        
        for file_path in files:
            filename = os.path.basename(file_path)
            timestamp = None
            
            # Try to extract timestamp from filename using regex patterns
            # Common patterns like YYYYMMDD_HHMMSS or similar
            timestamp_patterns = [
                r'(\d{8}_\d{6})',  # YYYYMMDD_HHMMSS
                r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})',  # YYYY-MM-DD_HH-MM-SS
                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                r'(\d{8})',  # YYYYMMDD
            ]
            
            # Try each pattern to extract timestamp from filename
            for pattern in timestamp_patterns:
                match = re.search(pattern, filename)
                if match:
                    timestamp_str = match.group(1)
                    self.logger.debug(f"Found timestamp in filename: {timestamp_str}")
                    try:
                        # If successful, we have a valid timestamp
                        # No need to convert to datetime here, just use for ordering
                        timestamp = timestamp_str
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to parse timestamp {timestamp_str} from filename: {e}")
            
            # If no timestamp found in filename or parsing failed, use file's modification time
            if timestamp is None:
                try:
                    timestamp = os.path.getmtime(file_path)
                    self.logger.debug(f"Using file modification time for {filename}")
                except Exception as e:
                    self.logger.warning(f"Failed to get modification time for {filename}: {e}")
                    # As a last resort, use creation time
                    try:
                        timestamp = os.path.getctime(file_path)
                    except Exception as e2:
                        self.logger.error(f"Failed to get creation time for {filename}: {e2}")
                        # If all else fails, use 0 (will be at the beginning)
                        timestamp = 0
            
            files_with_timestamps.append((file_path, timestamp))
        
        # Sort by timestamp (oldest first)
        sorted_files = [f[0] for f in sorted(files_with_timestamps, key=lambda x: x[1])]
        
        self.logger.info(f"Sorted {len(sorted_files)} files for portal '{portal_name}', oldest first.")
        return sorted_files