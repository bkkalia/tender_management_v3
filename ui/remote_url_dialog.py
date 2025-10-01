"""
Remote URL Dialog for adding cloud/remote data sources.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Tuple
import threading

# Fix imports by adding parent directory to path if needed
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from utils.constants import SPACING, FONTS, COLORS
from ui.common_widgets import create_labeled_frame, create_action_button, create_info_label, create_input_entry
from core.remote_data_loader import RemoteDataLoader

logger = logging.getLogger(__name__)

class RemoteUrlDialog(tk.Toplevel):
    """Dialog for adding remote URL data sources."""
    
    def __init__(self, parent, remote_loader: RemoteDataLoader):
        super().__init__(parent)
        self.parent = parent
        self.remote_loader = remote_loader
        self.result = None
        
        # Configure window
        self.title("Add Remote Data Source")
        self.geometry("600x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Variables
        self.url_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Enter remote data source details")
        self.test_result_var = tk.StringVar()
        
        self._create_widgets()
        
        # Focus on URL entry
        self.url_entry.focus_set()
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['medium'], pady=SPACING['medium'])
        
        # Title and description
        title_label = ttk.Label(main_frame, text="Add Remote Data Source", 
                               font=FONTS.get('heading', ('TkDefaultFont', 14, 'bold')))
        title_label.pack(pady=(0, SPACING['medium']))
        
        desc_label = ttk.Label(main_frame, 
                              text="Add cloud-based data sources including HTTP/HTTPS URLs, FTP, SFTP servers, and IP addresses.",
                              font=FONTS.get('body', ('TkDefaultFont', 10)))
        desc_label.pack(pady=(0, SPACING['medium']))
        
        # URL section
        url_frame = create_labeled_frame(main_frame, "Data Source URL")
        url_frame.pack(fill=tk.X, pady=(0, SPACING['medium']))
        
        # URL input
        url_row = ttk.Frame(url_frame)
        url_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        ttk.Label(url_row, text="URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var, width=60)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(SPACING['small'], 0))
        
        # URL examples
        examples_text = (
            "Examples:\n"
            "• https://example.com/data/tenders.xlsx\n"
            "• ftp://ftp.example.com/public/data.csv\n"
            "• sftp://server.example.com/reports/tenders.xlsx\n"
            "• http://192.168.1.100/api/export/data.csv"
        )
        examples_label = ttk.Label(url_frame, text=examples_text, 
                                  font=FONTS.get('small', ('TkDefaultFont', 9)),
                                  foreground='gray')
        examples_label.pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))
        
        # Authentication section
        auth_frame = create_labeled_frame(main_frame, "Authentication (Optional)")
        auth_frame.pack(fill=tk.X, pady=(0, SPACING['medium']))
        
        # Username
        username_row = ttk.Frame(auth_frame)
        username_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        ttk.Label(username_row, text="Username:").pack(side=tk.LEFT)
        username_entry = ttk.Entry(username_row, textvariable=self.username_var, width=30)
        username_entry.pack(side=tk.LEFT, padx=(SPACING['small'], 0))
        
        # Password
        password_row = ttk.Frame(auth_frame)
        password_row.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        ttk.Label(password_row, text="Password:").pack(side=tk.LEFT)
        password_entry = ttk.Entry(password_row, textvariable=self.password_var, width=30, show="*")
        password_entry.pack(side=tk.LEFT, padx=(SPACING['small'], 0))
        
        # Auth note
        auth_note = ttk.Label(auth_frame, 
                             text="Note: Credentials are required for SFTP and private FTP/HTTP sources.",
                             font=FONTS.get('small', ('TkDefaultFont', 9)),
                             foreground='gray')
        auth_note.pack(fill=tk.X, padx=SPACING['medium'], pady=(0, SPACING['small']))
        
        # Protocol support info
        support_frame = create_labeled_frame(main_frame, "Supported Protocols")
        support_frame.pack(fill=tk.X, pady=(0, SPACING['medium']))
        
        protocols = self.remote_loader.get_supported_protocols()
        support_text = ""
        for protocol, supported in protocols.items():
            status = "✓" if supported else "✗"
            support_text += f"{status} {protocol}\n"
        
        support_label = ttk.Label(support_frame, text=support_text.strip(),
                                 font=FONTS.get('small', ('TkDefaultFont', 9)))
        support_label.pack(fill=tk.X, padx=SPACING['medium'], pady=SPACING['small'])
        
        # Test connection frame
        test_frame = ttk.Frame(main_frame)
        test_frame.pack(fill=tk.X, pady=(0, SPACING['medium']))
        
        test_btn = create_action_button(test_frame, "Test Connection", self._test_connection,
                                       button_type='info_outline', width=15)
        test_btn.pack(side=tk.LEFT)
        
        self.test_result_label = ttk.Label(test_frame, textvariable=self.test_result_var,
                                          font=FONTS.get('small', ('TkDefaultFont', 9)))
        self.test_result_label.pack(side=tk.LEFT, padx=(SPACING['medium'], 0))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(SPACING['medium'], 0))
        
        # Cancel button
        cancel_btn = create_action_button(button_frame, "Cancel", self._cancel,
                                         button_type='secondary', width=12)
        cancel_btn.pack(side=tk.RIGHT, padx=(SPACING['small'], 0))
        
        # Add button
        add_btn = create_action_button(button_frame, "Add Source", self._add_source,
                                      button_type='primary', width=12)
        add_btn.pack(side=tk.RIGHT, padx=(SPACING['small'], 0))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Label(status_frame, textvariable=self.status_var,
                 font=FONTS.get('small', ('TkDefaultFont', 9)),
                 foreground='blue').pack(side=tk.LEFT)
        
        # Bind Enter key to add
        self.bind('<Return>', lambda e: self._add_source())
        self.bind('<Escape>', lambda e: self._cancel())
    
    def _test_connection(self):
        """Test the connection to the remote source."""
        url = self.url_var.get().strip()
        if not url:
            self.test_result_var.set("❌ Please enter a URL first")
            return
        
        # Validate URL format first
        is_valid, message = self.remote_loader.validate_url(url)
        if not is_valid:
            self.test_result_var.set(f"❌ {message}")
            return
        
        if "Warning" in message:
            self.test_result_var.set(f"⚠️ {message}")
        else:
            self.test_result_var.set("🔄 Testing connection...")
            self.update_idletasks()
            
            # Test in a separate thread to avoid blocking UI
            def test_thread():
                try:
                    username = self.username_var.get().strip() or None
                    password = self.password_var.get().strip() or None
                    
                    success, message, local_file = self.remote_loader.load_from_remote_source(url, username, password)
                    
                    if success:
                        # Clean up test file
                        if local_file and os.path.exists(local_file):
                            try:
                                os.remove(local_file)
                            except:
                                pass
                        
                        self.after(0, lambda: self.test_result_var.set(f"✅ Connection successful! {message}"))
                    else:
                        self.after(0, lambda: self.test_result_var.set(f"❌ {message}"))
                        
                except Exception as e:
                    self.after(0, lambda: self.test_result_var.set(f"❌ Test failed: {str(e)}"))
            
            threading.Thread(target=test_thread, daemon=True).start()
    
    def _add_source(self):
        """Add the remote source."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Please enter a URL for the remote data source.")
            return
        
        # Validate URL
        is_valid, message = self.remote_loader.validate_url(url)
        if not is_valid:
            messagebox.showerror("Invalid URL", message)
            return
        
        username = self.username_var.get().strip() or None
        password = self.password_var.get().strip() or None
        
        # Check if credentials are provided for protocols that might need them
        url_lower = url.lower()
        if (username and not password) or (password and not username):
            if not messagebox.askyesno("Incomplete Credentials", 
                                     "You've provided either username or password but not both. Continue anyway?"):
                return
        
        self.result = (url, username, password)
        self.destroy()
    
    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
        self.destroy()
