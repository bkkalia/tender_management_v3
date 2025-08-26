"""
Logs Tab module - UI component for viewing application logs.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
import sys
import queue
import threading
import time
from typing import TYPE_CHECKING, Dict, List, Any, Optional
from datetime import datetime

# Fix imports by adding parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can use absolute imports
from utils.constants import SPACING, FONTS, COLORS
from ui.common_widgets import create_labeled_frame, create_action_button, create_info_label
from utils.logger_setup import TextWidgetLogger

if TYPE_CHECKING:
    from ui.main_window import MainApplication

logger = logging.getLogger(__name__)

class LogsTab(ttk.Frame):
    """Logs tab for viewing and managing application logs."""
    
    def __init__(self, parent: ttk.Notebook, main_app: 'MainApplication'):
        super().__init__(parent)
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Log message queue and thread control
        self.log_queue = queue.Queue()
        self.log_thread_running = True
        
        # UI Variables
        self.level_filter_var = tk.StringVar(value="INFO")
        self.search_filter_var = tk.StringVar()
        self.autoscroll_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        
        # Create the UI elements
        self._create_widgets()
        
        # Set up the log handler
        self._setup_log_handler()
        
        # Start the log message consumer thread
        self._start_log_consumer()
        
    def _create_widgets(self):
        """Create the UI elements."""
        # Main frame
        main_frame = ttk.Frame(self, padding=SPACING['medium'])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Controls frame (top)
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, SPACING['small']))
        
        # Log level filter
        level_frame = ttk.Frame(controls_frame)
        level_frame.pack(side=tk.LEFT, padx=(0, SPACING['medium']))
        
        ttk.Label(level_frame, text="Log Level:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        level_combo = ttk.Combobox(level_frame, textvariable=self.level_filter_var, width=10, 
                                  values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        level_combo.pack(side=tk.LEFT)
        level_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        
        # Search filter
        search_frame = ttk.Frame(controls_frame)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, SPACING['medium']))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, SPACING['small']))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_filter_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", self._apply_filters)
        
        create_action_button(search_frame, "Clear", lambda: self.search_filter_var.set(""), 
                           button_type='secondary_outline', width=8).pack(side=tk.LEFT, padx=SPACING['small'])
        
        # Auto-scroll checkbox
        autoscroll_check = ttk.Checkbutton(controls_frame, text="Auto-scroll", variable=self.autoscroll_var)
        autoscroll_check.pack(side=tk.LEFT, padx=SPACING['medium'])
        
        # Action buttons
        actions_frame = ttk.Frame(controls_frame)
        actions_frame.pack(side=tk.RIGHT)
        
        create_action_button(actions_frame, "Clear Logs", self._clear_logs, 
                           button_type='danger_outline', width=10).pack(side=tk.LEFT, padx=SPACING['small']//2)
        
        create_action_button(actions_frame, "Save Logs", self._save_logs, 
                           button_type='primary_outline', width=10).pack(side=tk.LEFT, padx=SPACING['small']//2)
        
        create_action_button(actions_frame, "Refresh", self._refresh_logs, 
                           button_type='info_outline', width=10).pack(side=tk.LEFT, padx=SPACING['small']//2)
        
        # Log display area
        log_frame = create_labeled_frame(main_frame, "Application Logs")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create text widget with scrollbars
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['small'], pady=SPACING['small'])
        
        self.log_text = tk.Text(text_frame, wrap=tk.WORD, font=FONTS.get('body', ('Courier', 10)))
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=self.log_text.xview)
        
        self.log_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure tag styles for different log levels
        self.log_text.tag_configure('DEBUG', foreground='gray')
        self.log_text.tag_configure('INFO', foreground='black')
        self.log_text.tag_configure('WARNING', foreground=COLORS.get('warning', 'orange'))
        self.log_text.tag_configure('ERROR', foreground=COLORS.get('danger', 'red'))
        self.log_text.tag_configure('CRITICAL', foreground='red', font=FONTS.get('body_bold', ('Courier', 10, 'bold')))
        
        # Tag for search highlights
        self.log_text.tag_configure('highlight', background='yellow')
        
        # Pack the widgets
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Status bar at the bottom
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(SPACING['small'], 0))
        
        # Add right-click menu for copy operations
        self._add_context_menu()
        
    def _add_context_menu(self):
        """Add right-click context menu to the log text widget."""
        context_menu = tk.Menu(self.log_text, tearoff=0)
        context_menu.add_command(label="Copy Selected", command=self._copy_selected)
        context_menu.add_command(label="Copy All", command=self._copy_all)
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=lambda: self.log_text.tag_add(tk.SEL, "1.0", tk.END))
        
        # Bind right-click event
        self.log_text.bind("<Button-3>", lambda e: context_menu.tk_popup(e.x_root, e.y_root))
        
    def _copy_selected(self):
        """Copy selected text to clipboard."""
        try:
            selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.update()  # Update to ensure clipboard persists
            self.status_var.set("Selected text copied to clipboard")
        except tk.TclError:  # No selection
            self.status_var.set("No text selected")
            
    def _copy_all(self):
        """Copy all text to clipboard."""
        all_text = self.log_text.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(all_text)
        self.update()  # Update to ensure clipboard persists
        self.status_var.set("All log text copied to clipboard")
        
    def _setup_log_handler(self):
        """Set up and attach the log handler to the root logger."""
        # Create a custom handler that writes to our queue
        self.log_handler = TextWidgetLogger(self.log_queue)
        self.log_handler.setLevel(logging.DEBUG)  # Capture all logs
        
        # Add the handler to the root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        
        self.logger.info("Log handler attached to root logger")
        
    def _start_log_consumer(self):
        """Start a background thread to consume log messages from the queue."""
        def consume_logs():
            while self.log_thread_running:
                try:
                    # Get log message from queue with timeout
                    log_record = self.log_queue.get(timeout=0.1)
                    
                    # Process the log message in the main thread
                    self.after(0, self._process_log_message, log_record)
                    
                except queue.Empty:
                    # No messages in queue, continue waiting
                    continue
                except Exception as e:
                    # Handle any other exceptions
                    print(f"Error in log consumer thread: {e}")
        
        # Start the consumer thread
        self.consumer_thread = threading.Thread(target=consume_logs, daemon=True)
        self.consumer_thread.start()
        
    def _process_log_message(self, log_message: str):
        """Process and display a log message from the queue."""
        # Check if the message passes the current level filter
        level_str = self.level_filter_var.get()
        level_pos = log_message.find(f" - {level_str} - ")
        
        # Determine the log level of this message
        for level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
            if f" - {level} - " in log_message:
                message_level = level
                break
        else:
            message_level = "INFO"  # Default if no level found
        
        # Check if this message should be displayed based on level filter
        level_values = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level_values.index(message_level) < level_values.index(level_str):
            return  # Skip messages below the filter level
        
        # Check if the message passes the search filter
        search_term = self.search_filter_var.get()
        if search_term and search_term.lower() not in log_message.lower():
            return  # Skip messages that don't match the search term
        
        # Add the message to the text widget
        self.log_text.insert(tk.END, log_message + "\n", message_level)
        
        # Apply search highlighting if needed
        if search_term:
            self._highlight_search_term(search_term)
        
        # Auto-scroll to the end if enabled
        if self.autoscroll_var.get():
            self.log_text.see(tk.END)
            
    def _highlight_search_term(self, search_term: str):
        """Highlight search terms in the text widget."""
        # Remove existing highlights
        self.log_text.tag_remove('highlight', '1.0', tk.END)
        
        if not search_term:
            return
            
        # Case-insensitive search
        search_term = search_term.lower()
        
        # Start at the beginning of the text
        start_pos = '1.0'
        while True:
            # Find the next occurrence
            start_pos = self.log_text.search(search_term, start_pos, tk.END, nocase=True)
            if not start_pos:
                break
                
            # Calculate end position
            end_pos = f"{start_pos}+{len(search_term)}c"
            
            # Add highlight tag
            self.log_text.tag_add('highlight', start_pos, end_pos)
            
            # Move past this occurrence
            start_pos = end_pos
            
    def _apply_filters(self, event=None):
        """Apply the current level and search filters to the log display."""
        # Clear the text widget
        self.log_text.delete('1.0', tk.END)
        
        # Re-process all logs from the log file
        self._refresh_logs()
        
    def _clear_logs(self):
        """Clear the log display."""
        self.log_text.delete('1.0', tk.END)
        self.status_var.set("Logs cleared from display")
        
    def _save_logs(self):
        """Save displayed logs to a file."""
        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Logs As"
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            # Get all text from the widget
            log_text = self.log_text.get('1.0', tk.END)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(log_text)
                
            self.status_var.set(f"Logs saved to: {os.path.basename(file_path)}")
            self.logger.info(f"Logs saved to file: {file_path}")
            
        except Exception as e:
            self.status_var.set(f"Error saving logs: {str(e)}")
            self.logger.error(f"Error saving logs to file: {e}", exc_info=True)
            messagebox.showerror("Save Error", f"Failed to save logs: {str(e)}")
            
    def _refresh_logs(self):
        """Reload logs from the log file."""
        # Get the log file path
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file_path = os.path.join(app_root, 'logs', 'tender_management.log')
        
        if not os.path.exists(log_file_path):
            self.status_var.set("Log file not found")
            return
            
        try:
            # Clear the text widget
            self.log_text.delete('1.0', tk.END)
            
            # Get current filters
            level_str = self.level_filter_var.get()
            search_term = self.search_filter_var.get().lower()
            
            # Map level string to numeric value
            level_map = {
                "DEBUG": 10,
                "INFO": 20,
                "WARNING": 30,
                "ERROR": 40,
                "CRITICAL": 50
            }
            level_value = level_map.get(level_str, 20)  # Default to INFO
            
            # Read the log file
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # Process each line
            for line in log_lines:
                # Determine the log level of this line
                for level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
                    if f" - {level} - " in line:
                        line_level = level
                        break
                else:
                    line_level = "INFO"  # Default if no level found
                
                # Check if this line passes the level filter
                line_level_value = level_map.get(line_level, 20)
                if line_level_value < level_value:
                    continue  # Skip lines below the filter level
                
                # Check if this line passes the search filter
                if search_term and search_term not in line.lower():
                    continue  # Skip lines that don't match the search term
                
                # Add the line to the text widget
                self.log_text.insert(tk.END, line, line_level)
            
            # Apply search highlighting if needed
            if search_term:
                self._highlight_search_term(search_term)
            
            # Auto-scroll to the end if enabled
            if self.autoscroll_var.get():
                self.log_text.see(tk.END)
                
            # Update status
            self.status_var.set(f"Logs refreshed. Filter: {level_str}" + 
                               (f", Search: '{search_term}'" if search_term else ""))
                
        except Exception as e:
            self.status_var.set(f"Error refreshing logs: {str(e)}")
            self.logger.error(f"Error refreshing logs: {e}", exc_info=True)
    
    def on_tab_selected(self):
        """Called when this tab is selected."""
        # Refresh logs when tab is selected
        self._refresh_logs()
        self.logger.info("Logs tab selected")
    
    def on_closing(self):
        """Handle cleanup when the application is closing."""
        # Stop the log consumer thread
        self.log_thread_running = False
        
        # Remove our handler from the root logger
        if hasattr(self, 'log_handler'):
            root_logger = logging.getLogger()
            root_logger.removeHandler(self.log_handler)
            
        self.logger.info("Logs tab closing, resources released")

