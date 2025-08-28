"""
Calendar Tab module - UI component for viewing tender deadlines.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import logging
import os
import sys
import json
import uuid
from typing import TYPE_CHECKING, Dict, List, Any, Optional
from datetime import datetime, timedelta
from tkcalendar import Calendar

# Fix imports by adding parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can use the absolute imports
from ui.common_widgets import create_labeled_frame, create_action_button
from utils.constants import SPACING, FONTS, COLORS

if TYPE_CHECKING:
    from ui.main_window import MainApplication  # Also use absolute import here

logger = logging.getLogger(__name__)

class CalendarTab(ttk.Frame):
    """
    Calendar Tab for viewing tender deadlines.
    """
    def __init__(self, parent: ttk.Notebook, main_app: 'MainApplication'):
        super().__init__(parent)
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize data storage
        self.calendar_events = []
        self.selected_date = datetime.now().date().isoformat()
        self.selected_event_id = None
        
        # Default file path for saving calendar events
        app_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(app_data_dir, exist_ok=True)
        self.default_save_path = os.path.join(app_data_dir, "calendar_events.json")
        
        # UI Variables
        self.status_var = tk.StringVar(value="Ready")

        self._create_widgets()
        self._load_calendar_events()  # Load saved events if they exist
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=(SPACING['medium'], SPACING['small']))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top controls (e.g., view type, filters) - reduced vertical padding
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, SPACING['small']))
        
        ttk.Label(controls_frame, text="View:", font=FONTS.get('subheading', 'TkDefaultFont')).pack(side=tk.LEFT, padx=(0, SPACING['small']))
        # Placeholder for view type (Month/Week/Day)
        self.view_type_var = tk.StringVar(value="Month")
        view_type_combo = ttk.Combobox(controls_frame, textvariable=self.view_type_var, values=["Month", "Week", "Day"], 
                                      state="readonly", width=10)
        view_type_combo.pack(side=tk.LEFT, padx=(0, SPACING['large']))
        view_type_combo.bind("<<ComboboxSelected>>", self._on_view_change)

        # Action buttons
        action_frame = ttk.Frame(controls_frame)
        action_frame.pack(side=tk.RIGHT)
        
        # Use narrower buttons with smaller padding for better space usage
        create_action_button(action_frame, "Import", self._import_events, 
                            button_type='info_outline', width=8).pack(side=tk.LEFT, padx=SPACING['small']//2)
        create_action_button(action_frame, "Export", self._export_events, 
                            button_type='info_outline', width=8).pack(side=tk.LEFT, padx=SPACING['small']//2)
        create_action_button(action_frame, "Export ICS", self._export_to_ics, 
                            button_type='primary_outline', width=10).pack(side=tk.LEFT, padx=SPACING['small']//2)
        create_action_button(action_frame, "Add", self._add_new_event, 
                            button_type='success', width=8).pack(side=tk.LEFT, padx=SPACING['small']//2)

        # Use PanedWindow for more flexible resizing between calendar and events
        split_frame = tk.PanedWindow(main_frame, orient=tk.HORIZONTAL, sashwidth=4, sashrelief="raised")
        split_frame.pack(fill=tk.BOTH, expand=True, pady=(0, SPACING['small']))
        
        # Left side: Calendar (give it 40% of space)
        calendar_frame = create_labeled_frame(split_frame, "Calendar")
        
        # Create the calendar widget
        self.calendar = Calendar(calendar_frame, selectmode='day', 
                                year=datetime.now().year, 
                                month=datetime.now().month, 
                                day=datetime.now().day,
                                font=FONTS.get('body', ('TkDefaultFont', 10)),
                                headersfont=FONTS.get('subheading', ('TkDefaultFont', 11, 'bold')),
                                selectbackground=COLORS.get('primary', '#007bff'))
        self.calendar.pack(fill="both", expand=True, padx=SPACING['small'], pady=SPACING['small'])
        self.calendar.bind("<<CalendarSelected>>", self._on_date_selected)
        
        # Right side: Events for selected date (give it 60% of space)
        events_frame = create_labeled_frame(split_frame, "Events")
        
        # Add the frames to the paned window with proper weights
        split_frame.add(calendar_frame, width=300, minsize=250)  # Calendar gets 300px
        split_frame.add(events_frame, width=450, minsize=300)   # Events list gets 450px
        
        # Create events list with scrollbar
        events_list_frame = ttk.Frame(events_frame)
        events_list_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING['small'], pady=SPACING['small'])
        
        # Define columns
        columns = ("title", "time", "status")
        
        self.events_tree = ttk.Treeview(events_list_frame, columns=columns, show="headings", style="Custom.Treeview")
        
        # Define column headings
        self.events_tree.heading("title", text="Event Title")
        self.events_tree.column("title", width=300)
        
        self.events_tree.heading("time", text="Time")
        self.events_tree.column("time", width=100, anchor=tk.CENTER)
        
        self.events_tree.heading("status", text="Status")
        self.events_tree.column("status", width=100, anchor=tk.CENTER)
        
        # Scrollbars
        vsb = ttk.Scrollbar(events_list_frame, orient="vertical", command=self.events_tree.yview)
        hsb = ttk.Scrollbar(events_list_frame, orient="horizontal", command=self.events_tree.xview)
        self.events_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.events_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure row styles
        style = ttk.Style()
        style.map('Custom.Treeview', background=[('selected', COLORS.get('primary_highlight', '#AED6F1'))])
        self.events_tree.tag_configure('oddrow', background=COLORS.get('background_light', '#F5F5F5'))
        self.events_tree.tag_configure('evenrow', background=COLORS.get('background', '#FFFFFF'))
        self.events_tree.tag_configure('overdue', foreground=COLORS.get('danger', '#FF0000'))
        
        # Bind selection event
        self.events_tree.bind("<<TreeviewSelect>>", self._on_event_select)
        self.events_tree.bind("<Button-3>", self._show_event_context_menu)
        
        # Event details area - use another PanedWindow for vertical resizing
        details_pane = tk.PanedWindow(main_frame, orient=tk.VERTICAL, sashwidth=4, sashrelief="raised")
        details_pane.pack(fill=tk.BOTH, expand=False, pady=(0, SPACING['small']))
        
        # Event details frame with smaller padding and height
        details_frame = create_labeled_frame(details_pane, "Event Details")
        details_pane.add(details_frame, height=180, minsize=120)  # Limit initial height
        
        # Create two columns in the details frame
        details_columns = ttk.Frame(details_frame)
        details_columns.pack(fill=tk.BOTH, expand=True, padx=SPACING['small'], pady=SPACING['small'])
        
        # Left column - Basic details
        left_col = ttk.Frame(details_columns)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, SPACING['small']))
        
        # Event title - Keep as label but make it copyable
        self.title_var = tk.StringVar(value="No event selected")
        copy_frame = ttk.Frame(left_col)
        copy_frame.pack(fill=tk.X, pady=(0, SPACING['small']))
        
        title_label = ttk.Label(copy_frame, textvariable=self.title_var, 
                 font=FONTS.get('subheading', ('TkDefaultFont', 10, 'bold')), wraplength=350)
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True) 
        
        # Add copy button for title
        copy_title_btn = create_action_button(copy_frame, "📋", 
                                         lambda: self._copy_to_clipboard(self.title_var.get()), 
                                         button_type='info_outline', width=3)
        copy_title_btn.pack(side=tk.RIGHT)
        
        # Details grid - more compact layout
        details_grid = ttk.Frame(left_col)
        details_grid.pack(fill=tk.X, pady=(0, SPACING['small']))
        
        # More compact labels for basic info
        row = 0
        
        # Department - Make selectable with readonly Entry widget
        ttk.Label(details_grid, text="Dept:").grid(row=row, column=0, sticky=tk.W, padx=(0, SPACING['small']), pady=1)
        self.dept_var = tk.StringVar()
        dept_entry = ttk.Entry(details_grid, textvariable=self.dept_var, state="readonly", width=40)
        dept_entry.grid(row=row, column=1, sticky=tk.W, pady=1)
        # Add context menu for copy
        self._add_copy_context_menu(dept_entry)
        row += 1
        
        # Date - Make selectable with readonly Entry widget
        ttk.Label(details_grid, text="Date:").grid(row=row, column=0, sticky=tk.W, padx=(0, SPACING['small']), pady=1)
        self.date_var = tk.StringVar()
        date_entry = ttk.Entry(details_grid, textvariable=self.date_var, state="readonly", width=20)
        date_entry.grid(row=row, column=1, sticky=tk.W, pady=1)
        # Add context menu for copy
        self._add_copy_context_menu(date_entry)
        row += 1
        
        # Time - Keep existing interactive controls but more compact
        ttk.Label(details_grid, text="Time:").grid(row=row, column=0, sticky=tk.W, padx=(0, SPACING['small']), pady=1)
        time_frame = ttk.Frame(details_grid)
        time_frame.grid(row=row, column=1, sticky=tk.W, pady=1)
        
        self.hour_var = tk.StringVar(value="00")
        self.minute_var = tk.StringVar(value="00")
        
        hour_spinbox = ttk.Spinbox(time_frame, from_=0, to=23, width=3, format="%02.0f", textvariable=self.hour_var)
        hour_spinbox.pack(side=tk.LEFT)
        
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        
        minute_spinbox = ttk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f", textvariable=self.minute_var)
        minute_spinbox.pack(side=tk.LEFT)
        row += 1
        
        # Status - Keep existing combobox
        ttk.Label(details_grid, text="Status:").grid(row=row, column=0, sticky=tk.W, padx=(0, SPACING['small']), pady=1)
        self.status_combo_var = tk.StringVar(value="Pending")
        status_combo = ttk.Combobox(details_grid, textvariable=self.status_combo_var, 
                                   values=["Pending", "In Progress", "Completed", "Cancelled"], 
                                   width=15, state="readonly")
        status_combo.grid(row=row, column=1, sticky=tk.W, pady=1)
        
        # Right column - Notes
        right_col = ttk.Frame(details_columns)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Notes frame with copy button
        notes_header_frame = ttk.Frame(right_col)
        notes_header_frame.pack(fill=tk.X)
        
        ttk.Label(notes_header_frame, text="Notes", font=FONTS.get('subheading', ('TkDefaultFont', 10, 'bold'))).pack(side=tk.LEFT)
        copy_notes_btn = create_action_button(notes_header_frame, "📋", 
                                     lambda: self._copy_to_clipboard(self.notes_text.get(1.0, tk.END).strip()), 
                                     button_type='info_outline', width=3)
        copy_notes_btn.pack(side=tk.RIGHT)
        
        # Notes frame without border to save space
        notes_frame = ttk.Frame(right_col)
        notes_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notes text area with scrollbar
        self.notes_text = tk.Text(notes_frame, wrap=tk.WORD, height=3, font=FONTS.get('body', ('TkDefaultFont', 10)))
        notes_scrollbar = ttk.Scrollbar(notes_frame, orient=tk.VERTICAL, command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=notes_scrollbar.set)
        
        notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Button bar at the bottom - make sure this is always visible
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, SPACING['small']))
        
        # Organize buttons in two rows if needed to ensure visibility
        button_left = ttk.Frame(button_frame)
        button_left.pack(side=tk.LEFT)
        
        button_right = ttk.Frame(button_frame)
        button_right.pack(side=tk.RIGHT)
        
        create_action_button(button_left, "Copy All Details", self._copy_all_event_details, 
                            button_type='info', width=15).pack(side=tk.LEFT, padx=(0, SPACING['small']))
        
        create_action_button(button_right, "Delete Event", self._delete_selected_event, 
                            button_type='danger', width=12).pack(side=tk.LEFT, padx=SPACING['small'])
        
        create_action_button(button_right, "Save Changes", self._save_event_details, 
                            button_type='success', width=15).pack(side=tk.LEFT)
        
        # Status bar at the bottom - ensure it's always visible
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add any days with events to the calendar
        self._highlight_calendar_dates()
        
        self.logger.info("CalendarTab initialized")

    def _on_date_selected(self, event=None):
        """Handle selection of a date in the calendar."""
        selected_date_str = self.calendar.get_date()
        self.logger.info(f"Date selected: {selected_date_str}")
        
        # Convert to ISO format for internal consistency
        try:
            # Try parsing using multiple date formats
            date_formats = [
                "%Y-%m-%d",  # ISO format: 2025-06-09
                "%m/%d/%y",  # US format: 6/9/25
                "%d/%m/%y",  # UK format: 9/6/25
                "%m/%d/%Y",  # US format with 4-digit year: 6/9/2025
                "%d/%m/%Y",  # UK format with 4-digit year: 9/6/2025
            ]
            
            dt = None
            for date_format in date_formats:
                try:
                    dt = datetime.strptime(selected_date_str, date_format)
                    self.logger.debug(f"Successfully parsed date '{selected_date_str}' using format '{date_format}'")
                    break
                except ValueError:
                    continue
            
            if dt is None:
                raise ValueError(f"Could not parse date with any known format: {selected_date_str}")
                
            self.selected_date = dt.date().isoformat()
        except Exception as e:
            # Handle date format errors gracefully
            self.logger.warning(f"Could not parse date: {selected_date_str}. Error: {e}")
            self.selected_date = datetime.now().date().isoformat()
        
        # Update the events list for the selected date
        self._update_events_list()
    
    def _on_view_change(self, event=None):
        """Handle change of view type (Month/Week/Day)."""
        view_type = self.view_type_var.get()
        self.logger.info(f"View changed to: {view_type}")
        
        # Currently only Month view is implemented
        # Week and Day views would be added in future enhancements
        
        # Refresh the events list for the current selection
        self._update_events_list()
    
    def _update_events_list(self):
        """Update the events list for the selected date."""
        # Clear existing items
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        
        # Filter events for the selected date
        date_events = [event for event in self.calendar_events 
                      if event.get("date") == self.selected_date]
        
        # Sort events by time
        date_events.sort(key=lambda e: f"{e.get('hour', '00')}:{e.get('minute', '00')}")
        
        # Add events to the tree
        for i, event in enumerate(date_events):
            # Format the time
            time_str = f"{int(event.get('hour', 0)):02d}:{int(event.get('minute', 0)):02d}"
            
            values = (
                event["title"],
                time_str,
                event.get("status", "Pending")
            )
            
            # Determine row tag (for styling)
            if i % 2 == 0:
                row_tag = 'evenrow'
            else:
                row_tag = 'oddrow'
            
            # Add the event to the treeview
            item_id = self.events_tree.insert("", tk.END, values=values, tags=(f"event_{event['id']}", row_tag))
        
        # Update status message
        if date_events:
            self.status_var.set(f"{len(date_events)} events on {self.selected_date}")
        else:
            self.status_var.set(f"No events on {self.selected_date}")
    
    def _on_event_select(self, event=None):
        """Handle selection of an event in the treeview."""
        selection = self.events_tree.selection()
        if not selection:
            self._clear_event_details()
            self.selected_event_id = None
            return
        
        # Get the selected item
        item_id = selection[0]
        
        # Get the event ID from the tags
        tags = self.events_tree.item(item_id, "tags")
        event_id = None
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("event_"):
                event_id = tag[6:]  # Remove "event_" prefix
                break
        
        if not event_id:
            self._clear_event_details()
            self.selected_event_id = None
            return
        
        # Find the event in our list
        selected_event = next((event for event in self.calendar_events if event["id"] == event_id), None)
        if not selected_event:
            self._clear_event_details()
            self.selected_event_id = None
            return
        
        # Update the details panel
        self.title_var.set(selected_event["title"])
        self.dept_var.set(selected_event.get("department", ""))
        self.date_var.set(selected_event["date"])
        self.hour_var.set(f"{int(selected_event.get('hour', 0)):02d}")
        self.minute_var.set(f"{int(selected_event.get('minute', 0)):02d}")
        self.status_combo_var.set(selected_event.get("status", "Pending"))
        
        # Update notes
        self.notes_text.delete(1.0, tk.END)
        self.notes_text.insert(tk.END, selected_event.get("notes", ""))
        
        # Store the selected event ID
        self.selected_event_id = event_id
    
    def _clear_event_details(self):
        """Clear the event details panel."""
        self.title_var.set("No event selected")
        self.dept_var.set("")
        self.date_var.set("")
        self.hour_var.set("00")
        self.minute_var.set("00")
        self.status_combo_var.set("Pending")
        self.notes_text.delete(1.0, tk.END)
    
    def _save_event_details(self):
        """Save the details of the selected event."""
        if not self.selected_event_id:
            messagebox.showinfo("No Selection", "Please select an event first.", parent=self)
            return
        
        # Find the event
        event_index = next((i for i, event in enumerate(self.calendar_events) 
                           if event["id"] == self.selected_event_id), None)
        if event_index is None:
            return
        
        # Update event with current values
        event = self.calendar_events[event_index]
        
        # Handle time changes - validate first
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time values")
        except ValueError:
            messagebox.showerror("Invalid Time", "Please enter valid time values (00-23:00-59).", parent=self)
            return
        
        # Update event
        event["hour"] = hour
        event["minute"] = minute
        event["status"] = self.status_combo_var.get()
        event["notes"] = self.notes_text.get(1.0, tk.END).strip()
        
        # Save changes
        self._save_calendar_events()
        
        # Refresh display
        self._update_events_list()
        
        self.status_var.set("Event updated successfully")
        self.logger.info(f"Updated event: {event['title']}")
    
    def _delete_selected_event(self):
        """Delete the selected event."""
        if not self.selected_event_id:
            messagebox.showinfo("No Selection", "Please select an event to delete.", parent=self)
            return
        
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            "Are you sure you want to delete this event?",
            parent=self
        )
        
        if not confirm:
            return
        
        # Find and remove the event
        event_index = next((i for i, event in enumerate(self.calendar_events) 
                           if event["id"] == self.selected_event_id), None)
        if event_index is not None:
            removed_event = self.calendar_events.pop(event_index)
            self.logger.info(f"Deleted event: {removed_event['title']}")
        
        # Save changes
        self._save_calendar_events()
        
        # Clear selection and refresh display
        self.selected_event_id = None
        self._clear_event_details()
        self._update_events_list()
        self._highlight_calendar_dates()  # Refresh calendar highlights
        
        self.status_var.set("Event deleted")
    
    def _add_new_event(self):
        """Add a new event on the selected date."""
        # Use the currently selected date
        selected_date_str = self.calendar.get_date()
        
        # Show dialog to get event details
        title = simpledialog.askstring("New Event", "Enter event title:", parent=self)
        if not title:
            return  # User cancelled or provided empty title
        
        # Create new event
        new_event = {
            "id": str(uuid.uuid4()),
            "title": title,
            "date": self.selected_date,
            "hour": 12,  # Default noon
            "minute": 0,
            "status": "Pending",
            "notes": "",
            "department": ""
        }
        
        # Add to events list
        self.calendar_events.append(new_event)
        
        # Save changes
        self._save_calendar_events()
        
        # Refresh display
        self._update_events_list()
        self._highlight_calendar_dates()  # Add highlight to calendar
        
        # Select the new event
        self.selected_event_id = new_event["id"]
        self._select_event_in_treeview(new_event["id"])
        
        self.status_var.set(f"Added new event: {title}")
        self.logger.info(f"Added new event: {title} on {self.selected_date}")
    
    def _select_event_in_treeview(self, event_id):
        """Select an event in the treeview by its ID."""
        for item_id in self.events_tree.get_children():
            tags = self.events_tree.item(item_id, "tags")
            if f"event_{event_id}" in tags:
                self.events_tree.selection_set(item_id)
                self.events_tree.see(item_id)
                self._on_event_select()  # Update details panel
                break
    
    def _show_event_context_menu(self, event):
        """Show context menu for an event."""
        item_id = self.events_tree.identify_row(event.y)
        if not item_id:
            return
        
        # Select the item under cursor
        self.events_tree.selection_set(item_id)
        self._on_event_select()  # Update details panel
        
        if not self.selected_event_id:
            return
        
        # Create context menu
        context_menu = tk.Menu(self, tearoff=0)
        
        # Add menu items
        context_menu.add_command(label="Edit", command=lambda: self._select_event_in_treeview(self.selected_event_id))
        context_menu.add_separator()
        
        # Status submenu
        status_submenu = tk.Menu(context_menu, tearoff=0)
        for status in ["Pending", "In Progress", "Completed", "Cancelled"]:
            status_submenu.add_command(
                label=status,
                command=lambda s=status: self._update_event_status(s)
            )
        context_menu.add_cascade(label="Change Status", menu=status_submenu)
        
        context_menu.add_separator()
        context_menu.add_command(label="Delete", command=self._delete_selected_event)
        
        # Display the menu
        context_menu.tk_popup(event.x_root, event.y_root)
    
    def _update_event_status(self, status):
        """Update the status of the selected event."""
        if not self.selected_event_id:
            return
        
        # Find the event
        event_index = next((i for i, event in enumerate(self.calendar_events) 
                           if event["id"] == self.selected_event_id), None)
        if event_index is None:
            return
        
        # Update status
        self.calendar_events[event_index]["status"] = status
        
        # Save changes
        self._save_calendar_events()
        
        # Refresh display
        self._update_events_list()
        self.status_combo_var.set(status)
        
        self.status_var.set(f"Event status updated to: {status}")
    
    def _highlight_calendar_dates(self):
        """Highlight dates that have events on the calendar."""
        # Clear existing tags first if the calendar supports it
        if hasattr(self.calendar, 'calevent_remove'):
            self.calendar.calevent_remove('all')
        
        # Get unique dates with events
        event_dates = set(event["date"] for event in self.calendar_events)
        
        # Add visual markers to calendar
        for date_str in event_dates:
            try:
                date_obj = datetime.fromisoformat(date_str).date()
                
                # Find events for this date
                date_events = [event for event in self.calendar_events if event["date"] == date_str]
                
                # Determine the highlight color based on event statuses
                if any(event["status"] == "Completed" for event in date_events):
                    color = COLORS.get('success', '#4caf50')  # Green for dates with completed events
                elif any(event["status"] == "In Progress" for event in date_events):
                    color = COLORS.get('warning', '#ff9800')  # Orange for in-progress
                elif any(event["status"] == "Cancelled" for event in date_events):
                    color = COLORS.get('danger', '#f44336')  # Red for cancelled
                else:
                    color = COLORS.get('primary', '#1976d2')  # Blue for pending/default
                
                # Add event marker with tag
                if hasattr(self.calendar, 'calevent_create'):
                    self.calendar.calevent_create(date_obj, "", tags=date_str)
                    self.calendar.tag_config(date_str, background=color)
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid date format in calendar events: {date_str}")
    
    def _save_calendar_events(self):
        """Save calendar events to JSON file."""
        try:
            with open(self.default_save_path, 'w') as f:
                json.dump(self.calendar_events, f, indent=2)
            
            self.logger.info(f"Saved {len(self.calendar_events)} calendar events to {self.default_save_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving calendar events: {e}")
            messagebox.showerror("Save Error", f"Failed to save calendar events: {e}", parent=self)
            return False
    
    def _load_calendar_events(self):
        """Load calendar events from JSON file."""
        if not os.path.exists(self.default_save_path):
            self.logger.info(f"No calendar events file found at {self.default_save_path}")
            return
        
        try:
            with open(self.default_save_path, 'r') as f:
                self.calendar_events = json.load(f)
            
            self.logger.info(f"Loaded {len(self.calendar_events)} calendar events from {self.default_save_path}")
            self._highlight_calendar_dates()  # Add highlights to calendar
        except Exception as e:
            self.logger.error(f"Error loading calendar events: {e}")
            messagebox.showerror("Load Error", f"Failed to load calendar events: {e}", parent=self)
    
    def _import_events(self):
        """Import events from a JSON file."""
        file_path = filedialog.askopenfilename(
            title="Import Calendar Events",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.default_save_path)
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                imported_events = json.load(f)
            
            # Validate imported data
            if not isinstance(imported_events, list):
                raise ValueError("Invalid format: expected a list of events")
            
            # Ask if user wants to replace or append
            if self.calendar_events:
                choice = messagebox.askyesnocancel(
                    "Import Options",
                    "Do you want to replace existing events?\n\nYes: Replace all existing events\nNo: Append imported events\nCancel: Abort import",
                    parent=self
                )
                
                if choice is None:
                    # User cancelled
                    return
                
                if choice:
                    # Replace existing events
                    self.calendar_events = imported_events
                else:
                    # Append imported events (avoiding duplicates by ID)
                    existing_ids = set(event["id"] for event in self.calendar_events)
                    for event in imported_events:
                        if event["id"] not in existing_ids:
                            self.calendar_events.append(event)
                            existing_ids.add(event["id"])
            else:
                # No existing events, just use imported ones
                self.calendar_events = imported_events
            
            # Save and refresh
            self._save_calendar_events()
            self._update_events_list()
            self._highlight_calendar_dates()
            
            self.status_var.set(f"Imported {len(imported_events)} events from {os.path.basename(file_path)}")
            self.logger.info(f"Imported {len(imported_events)} events from {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error importing events: {e}")
            messagebox.showerror("Import Error", f"Failed to import events: {e}", parent=self)
    
    def _export_events(self):
        """Export events to a JSON file."""
        if not self.calendar_events:
            messagebox.showinfo("No Events", "There are no events to export.", parent=self)
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Calendar Events",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.default_save_path)
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.calendar_events, f, indent=2)
            
            self.status_var.set(f"Exported {len(self.calendar_events)} events to {os.path.basename(file_path)}")
            self.logger.info(f"Exported {len(self.calendar_events)} events to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting events: {e}")
            messagebox.showerror("Export Error", f"Failed to export events: {e}", parent=self)
    
    def _export_to_ics(self):
        """Export calendar events to iCalendar (.ics) format."""
        if not self.calendar_events:
            messagebox.showinfo("No Events", "There are no events to export.", parent=self)
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export to iCalendar",
            defaultextension=".ics",
            filetypes=[("iCalendar files", "*.ics"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.default_save_path)
        )
        
        if not file_path:
            return
        
        try:
            # Try to import icalendar package
            try:
                from icalendar import Calendar, Event
                import pytz
            except ImportError:
                messagebox.showwarning(
                    "Missing Package", 
                    "The icalendar package is required for ICS export.\n"
                    "Please install it with: pip install icalendar pytz",
                    parent=self
                )
                return
            
            # Create calendar
            cal = Calendar()
            cal.add('prodid', '-//Tender Management System//Calendar Export//EN')
            cal.add('version', '2.0')
            
            # Local timezone - use UTC if pytz not available
            try:
                local_tz = pytz.timezone('UTC')
            except:
                local_tz = None
            
            # Add events
            for event_data in self.calendar_events:
                event = Event()
                
                # Set basic properties
                event.add('summary', event_data['title'])
                
                # Construct date and time
                try:
                    date_obj = datetime.fromisoformat(event_data['date'])
                    hour = int(event_data.get('hour', 0))
                    minute = int(event_data.get('minute', 0))
                    
                    # Create datetime with timezone if available
                    dt = datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)
                    if local_tz:
                        dt = local_tz.localize(dt)
                    
                    event.add('dtstart', dt)
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Skipping event with invalid date: {e}")
                    continue
                
                # Add description with notes and department
                description = ""
                if event_data.get('department'):
                    description += f"Department: {event_data['department']}\n\n"
                if event_data.get('notes'):
                    description += event_data['notes']
                
                event.add('description', description)
                
                # Add status
                if event_data.get('status'):
                    event.add('status', event_data['status'].lower())
                
                # Add unique ID
                event.add('uid', event_data['id'])
                
                # Add to calendar
                cal.add_component(event)
            
            # Write to file
            with open(file_path, 'wb') as f:
                f.write(cal.to_ical())
            
            self.status_var.set(f"Exported {len(self.calendar_events)} events to ICS: {os.path.basename(file_path)}")
            self.logger.info(f"Exported {len(self.calendar_events)} events to ICS: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting to ICS: {e}", exc_info=True)
            messagebox.showerror("Export Error", f"Failed to export to ICS: {e}", parent=self)
    
    def add_event(self, item_data):
        """Add an event from external data (e.g., from Search tab)."""
        # Extract relevant information with more robust handling
        
        # First try to find the exact "Title and Ref.No./Tender ID" field
        title = item_data.get('Title and Ref.No./Tender ID', '')
        
        # If not found, try other similar fields
        if not title:
            title = item_data.get('Title', item_data.get('title', ''))
            # Try to find any tender ID field to append
            tender_id = None
            for key in item_data:
                if 'tender id' in key.lower() or 'ref' in key.lower():
                    tender_id = item_data[key]
                    if tender_id and tender_id.strip():
                        title = f"{title} - {tender_id}"
                        break
        
        if not title:
            # Try to find any title-like field
            for key in item_data:
                if 'title' in key.lower() or 'name' in key.lower() or 'description' in key.lower():
                    title = item_data[key]
                    break

        if not title:
            title = "Untitled Event"
            
        # Extract department information - now used as secondary info, not the title
        department = item_data.get('Department', item_data.get('department', ''))
        if not department:
            # Try to find any column that might contain department info
            for key in item_data:
                if 'dept' in key.lower() or 'department' in key.lower() or 'agency' in key.lower():
                    department = item_data[key]
                    break
    
        # Get notes or create a comprehensive description
        notes = item_data.get('notes', '')
        if not notes:
            # Create automatic notes from tender details if not provided
            auto_notes = []
            
            # Add department info to notes
            if department:
                auto_notes.append(f"Department: {department}")
            
            # Add tender ID if available
            tender_id = None
            for key in item_data:
                if 'id' in key.lower() or 'reference' in key.lower() or 'ref' in key.lower():
                    tender_id = item_data[key]
                    if tender_id:
                        auto_notes.append(f"Tender ID: {tender_id}")
                        break
        
            # Add value if available
            value = None
            for key in item_data:
                if 'value' in key.lower() or 'amount' in key.lower() or 'budget' in key.lower():
                    value = item_data[key]
                    if value:
                        auto_notes.append(f"Value: {value}")
                    break
            
            # Add URL if available
            url = None
            for key in item_data:
                if 'url' in key.lower() or 'link' in key.lower() or 'website' in key.lower():
                    url = item_data[key]
                    if url and url != "🔗":  # Skip if it's just an icon
                        auto_notes.append(f"URL: {url}")
                    break
            for key in item_data:
                if 'id' in key.lower() or 'reference' in key.lower() or 'ref' in key.lower():
                    tender_id = item_data[key]
                    if tender_id:
                        auto_notes.append(f"Tender ID: {tender_id}")
                    break
            
            # Add value if available
            value = None
            for key in item_data:
                if 'value' in key.lower() or 'amount' in key.lower() or 'budget' in key.lower():
                    value = item_data[key]
                    if value:
                        auto_notes.append(f"Value: {value}")
                    break
            
            # Add URL if available
            url = None
            for key in item_data:
                if 'url' in key.lower() or 'link' in key.lower() or 'website' in key.lower():
                    url = item_data[key]
                    if url and url != "🔗":  # Skip if it's just an icon
                        auto_notes.append(f"URL: {url}")
                    break
            
            if auto_notes:
                notes = "\n".join(auto_notes)
        
        # Format the event title as "Title and Ref.No./Tender ID + Notes"
        if notes:
            # Include a short preview of notes in the title (first 30 chars)
            notes_preview = notes.split('\n')[0][:30]
            if len(notes_preview) < len(notes.split('\n')[0]):
                notes_preview += "..."
                
            # Create title with the required format
            combined_title = f"{title} + {notes_preview}"
        else:
            combined_title = title
    
        # Handle date
        date_str = item_data.get('closing_date', '')
        date_obj = None
        
        if date_str:
            try:
                # Try to parse various date formats
                for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                    try:
                        date_obj = datetime.strptime(date_str, date_format)
                        break
                    except ValueError:
                        continue
                
                if not date_obj and '/' in date_str:
                    # Try different arrangements of day/month/year
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        # Try both DMY and MDY
                        try:
                            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                        except ValueError:
                            try:
                                date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                            except ValueError:
                                pass
            except Exception as e:
                self.logger.warning(f"Could not parse date '{date_str}': {e}")
        
        # If date parsing failed, ask user to select a date
        if not date_obj:
            messagebox.showinfo(
                "Date Required",
                "Please select a date for this event.",
                parent=self
            )
            
            # Show calendar for date selection
            self.calendar.selection_set(datetime.now().date())
            self.lift()  # Bring this tab to front
            return False
        
        # Create new event with the combined title
        new_event = {
            "id": str(uuid.uuid4()),
            "title": combined_title,  # Use new title format
            "date": date_obj.date().isoformat(),
            "hour": 12,  # Default noon
            "minute": 0,
            "status": "Pending",
            "notes": notes,
            "department": department,
            "original_data": item_data  # Store original data for reference
        }
        
        # Add to events list
        self.calendar_events.append(new_event)
        
        # Save changes
        self._save_calendar_events()
        
        # Select the date of this event
        try:
            self.calendar.selection_set(date_obj.date())
            self._on_date_selected()  # Update events list
        except:
            # If calendar selection fails, just update the events list
            self._update_events_list()
            
        self._highlight_calendar_dates()  # Refresh calendar highlights
        
        # Select the new event if it's on the current date
        if new_event["date"] == self.selected_date:
            self.selected_event_id = new_event["id"]
            self._select_event_in_treeview(new_event["id"])
        
        messagebox.showinfo(
            "Event Added",
            f"Added event '{title}' on {date_obj.strftime('%Y-%m-%d')}",
            parent=self
        )
        
        self.status_var.set(f"Added new event: {title}")
        self.logger.info(f"Added new event from external data: {title} on {new_event['date']}")
        
        # Make sure to update the calendar visualization
        self._highlight_calendar_dates()
        
        # Select the date of this event and make sure it's visible in the events list
        try:
            # Update the calendar selection to show the new event's date
            date_obj = datetime.fromisoformat(new_event["date"]).date()
            self.calendar.selection_set(date_obj)
        except Exception as e:
            self.logger.warning(f"Could not select date in calendar: {e}")
    
    # Add these new methods for copy functionality
    def _add_copy_context_menu(self, widget):
        """Add right-click context menu with copy option to a widget."""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Copy", command=lambda: self._copy_widget_text(widget))
        
        def show_context_menu(event):
            if widget.cget('state') == 'readonly':  # Temporarily enable selection for readonly widgets
                widget.config(state='normal')
                widget.selection_range(0, tk.END)
                widget.config(state='readonly')
            menu.post(event.x_root, event.y_root)
        
        widget.bind("<Button-3>", show_context_menu)  # Right-click

    def _copy_widget_text(self, widget):
        """Copy text from a widget to clipboard."""
        if hasattr(widget, "get"):
            if callable(widget.get):
                try:
                    if isinstance(widget, tk.Text):
                        text = widget.get(1.0, tk.END).strip()
                    else:
                        text = widget.get()
                    self._copy_to_clipboard(text)
                    self.status_var.set("Text copied to clipboard")
                except Exception as e:
                    self.logger.error(f"Error copying text: {e}")
        else:
            self.logger.warning(f"Widget {widget} doesn't have a get method")

    def _copy_to_clipboard(self, text):
        """Copy given text to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # Ensure clipboard contents persist after function ends

    def _copy_all_event_details(self):
        """Copy all event details to clipboard."""
        if not self.selected_event_id:
            messagebox.showinfo("No Selection", "Please select an event first.", parent=self)
            return
        
        event = next((event for event in self.calendar_events if event["id"] == self.selected_event_id), None)
        if not event:
            return
        
        # Format all event details
        details = []
        details.append(f"Title: {event.get('title', '')}")
        details.append(f"Department: {event.get('department', '')}")
        details.append(f"Date: {event.get('date', '')}")
        details.append(f"Time: {event.get('hour', '00')}:{event.get('minute', '00')}")
        details.append(f"Status: {event.get('status', '')}")
        details.append(f"Notes: {event.get('notes', '')}")
        
        # Join details and copy to clipboard
        details_text = "\n".join(details)
        self._copy_to_clipboard(details_text)
        self.status_var.set("All event details copied to clipboard")
        self.logger.info("Copied all event details to clipboard")
