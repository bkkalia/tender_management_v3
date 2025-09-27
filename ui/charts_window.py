import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import numpy as np
import os
import json

logger = logging.getLogger(__name__)

class ChartsWindow:
    """Separate window for displaying data visualizations and charts."""

    def __init__(self, parent, data: pd.DataFrame):
        self.parent = parent
        self.data = data
        self.window: Optional[tk.Toplevel] = None
        self.current_chart_type = tk.StringVar(value="bar")
        self.selected_column = tk.StringVar()
        self.selected_columns = []  # For multi-column charts
        self.selected_period = tk.StringVar(value="months")  # New: time period selection

        # Auto-refresh functionality - 2 seconds as requested
        self.auto_refresh_enabled = True
        self.refresh_timer = None
        self.refresh_interval = 2000  # 2 seconds
        self.last_data_hash = None  # For smart refresh detection

        # Calendar search debouncing
        self.calendar_search_after_id = None
        self.calendar_search_delay_ms = 300  # 300ms debounce for calendar search

        # Set up matplotlib style
        plt.style.use('default')

        # Create the window
        self._create_window()
        self._create_widgets()

        # Set smart default column and chart type
        self._set_smart_defaults()

        # Initialize data hash for change detection
        self._update_data_hash(self.data)

        # Initial chart
        self._update_chart()

        # Start auto-refresh
        self._start_auto_refresh()

    def _create_window(self):
        """Create the main charts window with resize support."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("📊 Data Charts & Visualizations")
        self.window.geometry("1200x800")  # Larger default size

        # Make window resizable with minimum size
        self.window.resizable(True, True)
        self.window.minsize(800, 600)

        # Center the window (removed transient setting to allow minimization)
        # self.window.transient(self.parent)

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        """Create all widgets for the charts window with tabbed interface."""
        if not self.window:
            return

        # Main container
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # TOP HORIZONTAL TOOLBAR - All controls in one bar
        self._create_top_toolbar(main_frame)

        # Main content area with tabbed interface
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Create tabbed notebook
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Charts Tab
        self._create_charts_tab()

        # Calendar Tab
        self._create_calendar_tab()

    def _create_top_toolbar(self, parent):
        """Create a comprehensive top horizontal toolbar with all controls."""
        # Top toolbar frame
        toolbar_frame = ttk.Frame(parent, style='Toolbar.TFrame')
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))

        # Configure toolbar style
        style = ttk.Style()
        style.configure('Toolbar.TFrame', background='#f0f0f0', borderwidth=1, relief='raised')

        # Left section - Chart type and column controls
        left_controls = ttk.Frame(toolbar_frame)
        left_controls.pack(side=tk.LEFT, padx=10, pady=5)

        # Chart type selection
        chart_type_frame = ttk.Frame(left_controls)
        chart_type_frame.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(chart_type_frame, text="Chart Type:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT)
        chart_combo = ttk.Combobox(chart_type_frame, textvariable=self.current_chart_type,
                                 values=["bar", "pie", "line", "histogram", "scatter"],
                                 state="readonly", width=12, font=('TkDefaultFont', 9))
        chart_combo.pack(side=tk.LEFT, padx=(5, 0))
        chart_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart_and_description())

        # Chart description
        self.chart_description_var = tk.StringVar(value="Select a chart type to see description")
        chart_desc_label = ttk.Label(chart_type_frame, textvariable=self.chart_description_var,
                                   font=('TkDefaultFont', 8), foreground='gray', wraplength=300)
        chart_desc_label.pack(side=tk.LEFT, padx=(15, 0))

        # Column selection
        column_frame = ttk.Frame(left_controls)
        column_frame.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(column_frame, text="Data Column:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT)
        self.column_combo = ttk.Combobox(column_frame, textvariable=self.selected_column,
                                       state="readonly", width=20, font=('TkDefaultFont', 9))
        self.column_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.column_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

        # Time period selection (for date columns)
        period_frame = ttk.Frame(left_controls)
        period_frame.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(period_frame, text="Time Period:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT)
        self.period_combo = ttk.Combobox(period_frame, textvariable=self.selected_period,
                                       values=["days", "weeks", "months", "years"],
                                       state="readonly", width=10, font=('TkDefaultFont', 9))
        self.period_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.period_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

        # Filter to only show relevant columns after widget creation
        self._filter_relevant_columns()

        # Center section - Matplotlib navigation tools
        center_controls = ttk.Frame(toolbar_frame)
        center_controls.pack(side=tk.LEFT, expand=True, padx=20, pady=5)

        # Create a frame for matplotlib toolbar
        matplotlib_toolbar_frame = ttk.Frame(center_controls)
        matplotlib_toolbar_frame.pack(expand=True)

        # Create matplotlib toolbar (will be populated when canvas is ready)
        self.matplotlib_toolbar_frame = matplotlib_toolbar_frame

        # Right section - Window controls and action buttons
        right_controls = ttk.Frame(toolbar_frame)
        right_controls.pack(side=tk.RIGHT, padx=10, pady=5)

        # Window control buttons (minimize, maximize, close) - Make them highly visible
        window_controls = ttk.Frame(right_controls, style='WindowControls.TFrame')
        window_controls.pack(side=tk.RIGHT, padx=(20, 0))

        # Configure window controls style
        style.configure('WindowControls.TFrame', background='#e0e0e0', borderwidth=2, relief='raised')

        # Minimize button - Highly visible
        minimize_btn = ttk.Button(window_controls, text="🪟", command=self._minimize_window, width=5,
                                 style='WindowControl.TButton')
        minimize_btn.pack(side=tk.LEFT, padx=(5, 3))
        minimize_btn.bind("<Enter>", lambda e: self._show_tooltip(minimize_btn, "Minimize Window"))
        minimize_btn.bind("<Leave>", lambda e: self._hide_tooltip())

        # Maximize/Fullscreen button - Highly visible
        self.maximize_btn = ttk.Button(window_controls, text="⛶", command=self._toggle_fullscreen, width=5,
                                      style='WindowControl.TButton')
        self.maximize_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.maximize_btn.bind("<Enter>", lambda e: self._show_tooltip(self.maximize_btn, "Toggle Fullscreen"))
        self.maximize_btn.bind("<Leave>", lambda e: self._hide_tooltip())

        # Close button - Highly visible
        close_btn = ttk.Button(window_controls, text="✕", command=self._on_close, width=5,
                              style='WindowControl.TButton')
        close_btn.pack(side=tk.LEFT)
        close_btn.bind("<Enter>", lambda e: self._show_tooltip(close_btn, "Close Window"))
        close_btn.bind("<Leave>", lambda e: self._hide_tooltip())

        # Configure window control button style
        style.configure('WindowControl.TButton', font=('TkDefaultFont', 10, 'bold'), padding=5)

        # Separator
        ttk.Separator(right_controls, orient="vertical").pack(side=tk.RIGHT, padx=(15, 10), fill=tk.Y)

        # Action buttons
        action_controls = ttk.Frame(right_controls)
        action_controls.pack(side=tk.RIGHT)

        ttk.Button(action_controls, text="💾 Save Config",
                  command=self._save_chart_config, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_controls, text="📤 Export Chart",
                  command=self._export_chart, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_controls, text="🔄 Refresh",
                  command=self._refresh_data, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_controls, text="📊 Update",
                  command=self._update_chart, width=10).pack(side=tk.LEFT, padx=(0, 10))

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(toolbar_frame, textvariable=self.status_var,
                               font=('TkDefaultFont', 8), foreground='gray')
        status_label.pack(side=tk.RIGHT, padx=(0, 10))

    def _refresh_data(self):
        """Refresh data from parent Tree view with smart refresh detection."""
        try:
            if hasattr(self.parent, 'data_processor') and hasattr(self.parent.data_processor, 'filtered_data'):
                new_data = self.parent.data_processor.filtered_data
                if new_data is not None and not new_data.empty:
                    # Check if data has actually changed using more robust comparison
                    data_changed = self._has_data_changed(new_data)
                    if data_changed:
                        self.data = new_data.copy()
                        self._update_data_hash(new_data)  # Update hash for next comparison
                        self._filter_relevant_columns()  # Re-filter columns after data refresh
                        self._update_chart()
                        # Only log when data actually changes
                        self.status_var.set("Chart updated")
                        logger.info("Charts data refreshed from Tree view")
                    else:
                        # Data hasn't changed - completely silent operation
                        self.status_var.set("Ready")
                        # No logging, no messages - completely silent
                else:
                    messagebox.showinfo("No Data", "No data available in Tree view to refresh.")
            else:
                messagebox.showwarning("Refresh Failed", "Could not access Tree view data.")
        except Exception as e:
            logger.error(f"Error refreshing chart data: {e}")
            messagebox.showerror("Refresh Error", f"Failed to refresh data: {str(e)}")

    def _has_data_changed(self, new_data):
        """Check if data has actually changed using robust comparison."""
        try:
            # If no previous data, it's a change
            if self.last_data_hash is None:
                return True

            # Compare basic properties first (faster)
            if (len(new_data) != len(self.data) or
                set(new_data.columns) != set(self.data.columns)):
                return True

            # Try pandas equals first (most reliable)
            try:
                if new_data.equals(self.data):
                    return False
            except Exception:
                pass

            # If pandas equals fails, do more careful comparison
            try:
                # Reset index and sort both dataframes for consistent comparison
                new_reset = new_data.reset_index(drop=True)
                old_reset = self.data.reset_index(drop=True)

                # Sort columns to ensure consistent order
                new_sorted = new_reset.reindex(sorted(new_reset.columns), axis=1)
                old_sorted = old_reset.reindex(sorted(old_reset.columns), axis=1)

                # Compare dtypes first
                if not new_sorted.dtypes.equals(old_sorted.dtypes):
                    return True

                # Compare values - handle NaN values properly
                new_values = new_sorted.values
                old_values = old_sorted.values

                # Check if shapes match
                if new_values.shape != old_values.shape:
                    return True

                # Compare values, treating NaN as equal
                if new_values.shape[0] == 0:  # Both empty
                    return False

                # Use pandas isnull for proper NaN comparison
                new_nan_mask = pd.isna(new_values)
                old_nan_mask = pd.isna(old_values)

                if not (new_nan_mask == old_nan_mask).all():
                    return True

                # Compare non-NaN values
                new_non_nan = new_values[~new_nan_mask]
                old_non_nan = old_values[~old_nan_mask]

                if len(new_non_nan) != len(old_non_nan):
                    return True

                if len(new_non_nan) > 0 and not (new_non_nan == old_non_nan).all():
                    return True

                return False

            except Exception as e:
                logger.debug(f"Detailed comparison failed: {e}")
                # If detailed comparison fails, assume no change to be safe
                return False

        except Exception as e:
            logger.warning(f"Error in data change detection: {e}")
            # If we can't determine, assume no change to avoid unnecessary refreshes
            return False

    def _update_data_hash(self, data):
        """Update the data hash for comparison."""
        try:
            # Create a more stable hash based on actual data content
            if data is not None and not data.empty:
                # Use a combination of shape, columns, and a sample of values
                hash_data = f"{data.shape}_{sorted(data.columns.tolist())}"
                if len(data) > 0:
                    # Add first few and last few values for comparison
                    sample = data.head(3).values.tolist() + data.tail(3).values.tolist()
                    hash_data += f"_{sample}"
                self.last_data_hash = hash(hash_data)
            else:
                self.last_data_hash = None
        except Exception as e:
            logger.warning(f"Error updating data hash: {e}")
            self.last_data_hash = None

    def _update_chart_and_description(self):
        """Update chart and its description."""
        self._update_chart_description()
        self._update_chart()

    def _update_chart_description(self):
        """Update the chart description based on selected chart type."""
        chart_type = self.current_chart_type.get()

        descriptions = {
            "bar": "Bar Chart: Shows the frequency count of each category in the selected column",
            "pie": "Pie Chart: Shows the distribution of categories as percentages with absolute counts",
            "line": "Line Chart: Shows trends and patterns over time or across categories",
            "histogram": "Histogram: Shows the distribution of numeric values in the selected column",
            "scatter": "Scatter Plot: Shows relationship between the selected column and other numeric columns"
        }

        self.chart_description_var.set(descriptions.get(chart_type, "Chart visualization"))

    def _update_chart(self):
        """Update the chart based on current settings."""
        if self.data is None or self.data.empty:
            self._show_no_data_message()
            return

        try:
            # Clear previous chart
            self.ax.clear()

            chart_type = self.current_chart_type.get()
            column = self.selected_column.get()

            if not column or column not in self.data.columns:
                self._show_no_data_message()
                return

            # Prepare data for charting
            chart_data = self._prepare_chart_data(column)

            if chart_data is None or chart_data.empty:
                self._show_no_data_message()
                return

            # Create appropriate chart type
            if chart_type == "bar":
                self._create_bar_chart(chart_data, column)
            elif chart_type == "pie":
                self._create_pie_chart(chart_data, column)
            elif chart_type == "line":
                self._create_line_chart(chart_data, column)
            elif chart_type == "histogram":
                self._create_histogram(chart_data, column)
            elif chart_type == "scatter":
                self._create_scatter_chart(chart_data, column)

            # Update the canvas
            self.canvas.draw()

        except Exception as e:
            logger.error(f"Error updating chart: {e}")
            self._show_error_message(str(e))

    def _prepare_chart_data(self, column):
        """Prepare data for charting by aggregating values."""
        try:
            # Check if this is a date-related column that might be stored as string
            col_lower = str(column).lower()
            is_date_column = any(kw in col_lower for kw in ['date', 'time', 'closing', 'close', 'due', 'deadline', 'end', 'publish', 'created', 'opening'])

            # Get current chart type to determine how to handle date columns
            chart_type = self.current_chart_type.get()

            # Handle different data types
            if pd.api.types.is_numeric_dtype(self.data[column]):
                # For numeric columns, create value distribution
                return self._prepare_numeric_data(column)
            elif pd.api.types.is_datetime64_dtype(self.data[column]):
                # For datetime columns, handle based on chart type
                if chart_type == "line":
                    # Line charts work well with time series
                    return self._prepare_datetime_data(column)
                else:
                    # For pie/bar/histogram, convert datetime to categorical periods
                    return self._prepare_datetime_as_categorical(column)
            elif is_date_column:
                # Try to convert date-like columns to datetime
                try:
                    # Attempt to convert to datetime
                    temp_data = pd.to_datetime(self.data[column], errors='coerce')
                    if temp_data.notna().any():
                        # Successfully converted some dates
                        if chart_type == "line":
                            # Line charts work well with time series
                            self.data = self.data.copy()  # Avoid modifying original
                            self.data[column] = temp_data
                            return self._prepare_datetime_data(column)
                        else:
                            # For pie/bar/histogram, convert to categorical periods
                            return self._prepare_datetime_as_categorical_from_series(temp_data)
                except Exception:
                    pass
                # Fall back to categorical if conversion fails
                return self._prepare_categorical_data(column)
            else:
                # For categorical/text columns, create frequency counts
                return self._prepare_categorical_data(column)
        except Exception as e:
            logger.error(f"Error preparing chart data: {e}")
            return None

    def _prepare_numeric_data(self, column):
        """Prepare numeric data for charting."""
        try:
            # Create bins for numeric data
            data_clean = self.data[column].dropna()

            if len(data_clean) == 0:
                return None

            # Create reasonable bins
            min_val, max_val = data_clean.min(), data_clean.max()
            if min_val == max_val:
                # All values are the same
                return pd.DataFrame({'Value': [min_val], 'Count': [len(data_clean)]})

            # Create bins
            bins = min(20, max(5, len(data_clean) // 10))  # Adaptive bin count
            bin_edges = np.linspace(min_val, max_val, bins + 1)

            # Create histogram data
            counts, bin_edges = np.histogram(data_clean, bins=bin_edges)
            bin_labels = [f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}" for i in range(len(counts))]

            return pd.DataFrame({
                'Range': bin_labels,
                'Count': counts
            })
        except Exception as e:
            logger.error(f"Error preparing numeric data: {e}")
            return None

    def _prepare_categorical_data(self, column):
        """Prepare categorical/text data for charting."""
        try:
            # Get value counts
            value_counts = self.data[column].value_counts().head(10)  # Top 10 categories

            return pd.DataFrame({
                'Category': value_counts.index,
                'Count': value_counts.values
            })
        except Exception as e:
            logger.error(f"Error preparing categorical data: {e}")
            return None

    def _prepare_datetime_data(self, column):
        """Prepare datetime data for charting."""
        try:
            # Group by date and count occurrences
            date_counts = self.data[column].dt.date.value_counts().sort_index()

            return pd.DataFrame({
                'Date': date_counts.index,
                'Count': date_counts.values
            })
        except Exception as e:
            logger.error(f"Error preparing datetime data: {e}")
            return None

    def _prepare_datetime_as_categorical(self, column):
        """Prepare datetime data as categorical periods for pie/bar/histogram charts."""
        try:
            # Convert datetime to categorical periods based on selected period
            dt_series = self.data[column].dropna()

            if len(dt_series) == 0:
                return None

            # Get selected period and map to pandas period frequency
            period = self.selected_period.get()
            period_freq = {
                'days': 'D',
                'weeks': 'W',
                'months': 'M',
                'years': 'Y'
            }.get(period, 'M')  # Default to months

            # Group by selected period for categorization
            period_counts = dt_series.dt.to_period(period_freq).value_counts().sort_index()

            # Convert periods to readable strings
            categories = [str(period) for period in period_counts.index]
            counts = period_counts.values

            return pd.DataFrame({
                'Category': categories,
                'Count': counts
            })
        except Exception as e:
            logger.error(f"Error preparing datetime as categorical: {e}")
            return None

    def _prepare_datetime_as_categorical_from_series(self, dt_series):
        """Prepare datetime series as categorical periods for pie/bar/histogram charts."""
        try:
            # Convert datetime to categorical periods based on selected period
            dt_series = dt_series.dropna()

            if len(dt_series) == 0:
                return None

            # Get selected period and map to pandas period frequency
            period = self.selected_period.get()
            period_freq = {
                'days': 'D',
                'weeks': 'W',
                'months': 'M',
                'years': 'Y'
            }.get(period, 'M')  # Default to months

            # Group by selected period for categorization
            period_counts = dt_series.dt.to_period(period_freq).value_counts().sort_index()

            # Convert periods to readable strings
            categories = [str(period) for period in period_counts.index]
            counts = period_counts.values

            return pd.DataFrame({
                'Category': categories,
                'Count': counts
            })
        except Exception as e:
            logger.error(f"Error preparing datetime series as categorical: {e}")
            return None

    def _create_bar_chart(self, chart_data, column):
        """Create a bar chart."""
        try:
            # Validate chart_data
            if chart_data is None or chart_data.empty:
                self._show_error_message("No data available for bar chart")
                return

            if 'Range' in chart_data.columns and 'Count' in chart_data.columns:
                # Numeric histogram
                self.ax.bar(range(len(chart_data)), chart_data['Count'])
                self.ax.set_xlabel('Value Ranges')
                self.ax.set_title(f'Distribution of {column}')
            elif 'Category' in chart_data.columns and 'Count' in chart_data.columns:
                # Categorical data
                categories = chart_data['Category'].astype(str)
                counts = chart_data['Count']

                bars = self.ax.bar(range(len(categories)), counts)
                self.ax.set_xlabel('Categories')
                self.ax.set_title(f'Frequency of {column}')

                # Add value labels on bars
                for i, (bar, count) in enumerate(zip(bars, counts)):
                    self.ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                               str(count), ha='center', va='bottom', fontweight='bold')

                # Set x-axis labels
                self.ax.set_xticks(range(len(categories)))
                self.ax.set_xticklabels(categories, rotation=45, ha='right')
            else:
                self._show_error_message("Invalid data format for bar chart")
                return

            self.ax.set_ylabel('Count')
            self.ax.grid(True, alpha=0.3)

        except Exception as e:
            logger.error(f"Error creating bar chart: {e}")
            self._show_error_message("Failed to create bar chart")

    def _create_pie_chart(self, chart_data, column):
        """Create a pie chart with both percentages and absolute numbers."""
        try:
            # Validate chart_data
            if chart_data is None or chart_data.empty:
                self._show_error_message("No data available for pie chart")
                return

            # Ensure chart_data has the required columns
            if 'Category' not in chart_data.columns or 'Count' not in chart_data.columns:
                self._show_error_message("Invalid data format for pie chart")
                return

            # Filter out zero or negative counts
            chart_data = chart_data[chart_data['Count'] > 0]
            if chart_data.empty:
                self._show_error_message("No valid data for pie chart")
                return

            if len(chart_data) > 10:
                # Show only top 10 and group others
                top_10 = chart_data.head(10)
                others_sum = chart_data.iloc[10:]['Count'].sum()

                if others_sum > 0:
                    others_row = pd.DataFrame({'Category': ['Others'], 'Count': [others_sum]})
                    chart_data = pd.concat([top_10, others_row], ignore_index=True)

            labels = chart_data['Category'].astype(str).tolist()  # Convert Series to list
            sizes = chart_data['Count'].tolist()  # Convert Series to list
            total = sum(sizes)

            # Custom autopct function to show both percentage and absolute number
            def autopct_format(pct):
                count = int(round(pct * total / 100.0))
                return f'{pct:.1f}%\n({count})'

            # Create pie chart - handle both 2-tuple and 3-tuple return values
            pie_result = self.ax.pie(sizes, labels=labels, autopct=autopct_format,
                                   startangle=90, textprops={'fontsize': 7})

            # Handle different return value formats
            if len(pie_result) == 2:
                wedges, texts = pie_result
                autotexts = []  # No autotexts in this case
            else:
                wedges, texts, autotexts = pie_result

            self.ax.set_title(f'Distribution of {column}\n(Total: {total:,})')
            self.ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle

            # Make labels more readable
            for text in texts + autotexts:
                text.set_fontsize(7)

        except Exception as e:
            logger.error(f"Error creating pie chart: {e}")
            self._show_error_message("Failed to create pie chart")

    def _create_line_chart(self, chart_data, column):
        """Create a line chart."""
        try:
            # Validate chart_data
            if chart_data is None or chart_data.empty:
                self._show_error_message("No data available for line chart")
                return

            if 'Date' in chart_data.columns and 'Count' in chart_data.columns:
                # Time series data
                dates = chart_data['Date']
                values = chart_data['Count']

                self.ax.plot(dates, values, marker='o', linewidth=2, markersize=4)
                self.ax.set_xlabel('Date')
                self.ax.set_title(f'Time Series of {column}')
            elif 'Count' in chart_data.columns:
                # Regular line chart
                x = range(len(chart_data))
                y = chart_data['Count']

                self.ax.plot(x, y, marker='o', linewidth=2, markersize=4)
                self.ax.set_xlabel('Categories')
                self.ax.set_title(f'Trend of {column}')

                # Set x-axis labels if categorical
                if 'Category' in chart_data.columns:
                    categories = chart_data['Category'].astype(str)
                    self.ax.set_xticks(x)
                    self.ax.set_xticklabels(categories, rotation=45, ha='right')
            else:
                self._show_error_message("Invalid data format for line chart")
                return

            self.ax.set_ylabel('Count')
            self.ax.grid(True, alpha=0.3)

        except Exception as e:
            logger.error(f"Error creating line chart: {e}")
            self._show_error_message("Failed to create line chart")

    def _create_histogram(self, chart_data, column):
        """Create a histogram."""
        try:
            # Validate chart_data
            if chart_data is None or chart_data.empty:
                self._show_error_message("No data available for histogram")
                return

            if 'Count' in chart_data.columns:
                # Use the prepared histogram data
                counts = chart_data['Count']
                if 'Range' in chart_data.columns:
                    # Numeric histogram
                    self.ax.hist(counts, bins=20, alpha=0.7, edgecolor='black')
                    self.ax.set_xlabel('Frequency')
                    self.ax.set_title(f'Histogram of {column} Distribution')
                elif 'Category' in chart_data.columns:
                    # Categorical histogram
                    categories = chart_data['Category']
                    self.ax.hist(categories, alpha=0.7, edgecolor='black')
                    self.ax.set_xlabel('Categories')
                    self.ax.set_title(f'Histogram of {column}')
                else:
                    self._show_error_message("Invalid data format for histogram")
                    return
            else:
                # Direct histogram from data
                data_clean = self.data[column].dropna()
                if len(data_clean) == 0:
                    self._show_error_message("No data available for histogram")
                    return
                self.ax.hist(data_clean, bins=20, alpha=0.7, edgecolor='black')
                self.ax.set_xlabel(column)
                self.ax.set_title(f'Histogram of {column}')

            self.ax.set_ylabel('Frequency')
            self.ax.grid(True, alpha=0.3)

        except Exception as e:
            logger.error(f"Error creating histogram: {e}")
            self._show_error_message("Failed to create histogram")

    def _create_scatter_chart(self, chart_data, column):
        """Create a scatter plot."""
        try:
            # For scatter plot, we need at least two numeric columns
            numeric_cols = [col for col in self.data.columns
                          if pd.api.types.is_numeric_dtype(self.data[col]) and col != column]

            if not numeric_cols:
                self._show_error_message("No numeric columns available for scatter plot")
                return

            # Use the first numeric column as X-axis
            x_col = numeric_cols[0]
            x_data = self.data[x_col].dropna()
            y_data = self.data[column].dropna()

            # Align the data
            common_index = x_data.index.intersection(y_data.index)
            x_data = x_data.loc[common_index]
            y_data = y_data.loc[common_index]

            if len(x_data) == 0 or len(y_data) == 0:
                self._show_error_message("No valid data points for scatter plot")
                return

            self.ax.scatter(x_data, y_data, alpha=0.6, s=50)
            self.ax.set_xlabel(x_col)
            self.ax.set_ylabel(column)
            self.ax.set_title(f'Scatter Plot: {x_col} vs {column}')
            self.ax.grid(True, alpha=0.3)

        except Exception as e:
            logger.error(f"Error creating scatter chart: {e}")
            self._show_error_message("Failed to create scatter plot")

    def _show_no_data_message(self):
        """Show a message when no data is available."""
        self.ax.clear()
        self.ax.text(0.5, 0.5, 'No data available\nfor visualization',
                    ha='center', va='center', fontsize=14,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.canvas.draw()

    def _show_error_message(self, error_msg):
        """Show an error message on the chart."""
        self.ax.clear()
        self.ax.text(0.5, 0.5, f'Error: {error_msg}',
                    ha='center', va='center', fontsize=12, color='red',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightcoral", alpha=0.5))
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.canvas.draw()

    def _filter_relevant_columns(self):
        """Filter to only show relevant columns (Date, Department, Source File)."""
        if not hasattr(self.data, 'columns') or self.data.columns is None:
            return

        # Define relevant column patterns
        date_patterns = ['date', 'time', 'closing', 'close', 'due', 'deadline', 'end', 'publish', 'created']
        dept_patterns = ['department', 'dept', 'agency', 'organisation', 'ministry', 'authority', 'organization']
        source_patterns = ['source', 'file', 'filename', 'path', 'origin']

        # Define columns to exclude
        exclude_patterns = ['url', 'link', 'id', 'sr', 'serial', 'number', 'tender_id', 'reference']

        relevant_columns = []

        for col in self.data.columns:
            col_lower = str(col).lower()

            # Skip columns that match exclude patterns
            if any(pattern in col_lower for pattern in exclude_patterns):
                continue

            # Check if column matches relevant patterns
            is_date = any(pattern in col_lower for pattern in date_patterns)
            is_dept = any(pattern in col_lower for pattern in dept_patterns)
            is_source = any(pattern in col_lower for pattern in source_patterns)

            # Also include columns that are likely to be these types
            if (is_date or is_dept or is_source or
                'date' in col_lower or 'dept' in col_lower or 'source' in col_lower):
                relevant_columns.append(col)

        # Update the column combo with filtered columns
        if relevant_columns:
            self.column_combo['values'] = relevant_columns
            if not self.selected_column.get() or self.selected_column.get() not in relevant_columns:
                self.selected_column.set(relevant_columns[0])

    def _set_smart_defaults(self):
        """Set smart default column and chart type based on data."""
        if not hasattr(self.data, 'columns') or self.data.columns is None:
            return

        # Find the best column to visualize - prioritize closing date columns
        closing_date_columns = [col for col in self.data.columns
                               if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end'])]

        other_date_columns = [col for col in self.data.columns
                             if any(kw in col.lower() for kw in ['date', 'time']) and col not in closing_date_columns]

        dept_columns = [col for col in self.data.columns
                       if any(kw in col.lower() for kw in ['department', 'dept', 'agency', 'organisation', 'ministry'])]

        # Prioritize: Closing date columns > Other date columns > Department columns > First column
        if closing_date_columns:
            self.selected_column.set(closing_date_columns[0])
            # For date columns, line chart is often most useful
            if pd.api.types.is_datetime64_dtype(self.data[closing_date_columns[0]]):
                self.current_chart_type.set("line")
            else:
                self.current_chart_type.set("bar")
        elif other_date_columns:
            self.selected_column.set(other_date_columns[0])
            # For date columns, line chart is often most useful
            if pd.api.types.is_datetime64_dtype(self.data[other_date_columns[0]]):
                self.current_chart_type.set("line")
            else:
                self.current_chart_type.set("bar")
        elif dept_columns:
            self.selected_column.set(dept_columns[0])
            # For department columns, pie chart shows distribution well
            self.current_chart_type.set("pie")
        else:
            # Default to first column
            if len(self.data.columns) > 0:
                self.selected_column.set(self.data.columns[0])

    def _start_auto_refresh(self):
        """Start the auto-refresh timer."""
        if self.auto_refresh_enabled and self.window:
            self.refresh_timer = self.window.after(self.refresh_interval, self._auto_refresh)

    def _auto_refresh(self):
        """Automatically refresh chart data."""
        if self.window and self.auto_refresh_enabled:
            try:
                self._refresh_data()
            except Exception as e:
                logger.error(f"Error in auto-refresh: {e}")

            # Schedule next refresh
            self._start_auto_refresh()

    def _add_touchpad_support(self):
        """Add touch pad and mouse wheel support for zooming and panning."""
        try:
            # Initialize pan state variables
            self._pan_start = None
            self._pan_prev = None

            # Bind mouse wheel events for zooming
            def on_mousewheel(event):
                if event.widget is not self.canvas.get_tk_widget():
                    return

                # Get the current axis limits
                xlim = self.ax.get_xlim()
                ylim = self.ax.get_ylim()

                # Calculate zoom factor (Ctrl+scroll for horizontal, Shift+scroll for vertical)
                if event.state & 0x4:  # Ctrl key pressed
                    # Horizontal zoom
                    zoom_factor = 1.2 if event.delta > 0 else 0.8
                    center_x = (xlim[0] + xlim[1]) / 2
                    new_width = (xlim[1] - xlim[0]) * zoom_factor
                    self.ax.set_xlim(center_x - new_width/2, center_x + new_width/2)
                elif event.state & 0x1:  # Shift key pressed
                    # Vertical zoom
                    zoom_factor = 1.2 if event.delta > 0 else 0.8
                    center_y = (ylim[0] + ylim[1]) / 2
                    new_height = (ylim[1] - ylim[0]) * zoom_factor
                    self.ax.set_ylim(center_y - new_height/2, center_y + new_height/2)
                else:
                    # Both axes zoom
                    zoom_factor = 1.2 if event.delta > 0 else 0.8
                    center_x = (xlim[0] + xlim[1]) / 2
                    center_y = (ylim[0] + ylim[1]) / 2
                    new_width = (xlim[1] - xlim[0]) * zoom_factor
                    new_height = (ylim[1] - ylim[0]) * zoom_factor
                    self.ax.set_xlim(center_x - new_width/2, center_x + new_width/2)
                    self.ax.set_ylim(center_y - new_height/2, center_y + new_height/2)

                self.canvas.draw()

            # Bind to the canvas widget
            canvas_widget = self.canvas.get_tk_widget()
            canvas_widget.bind("<MouseWheel>", on_mousewheel)  # Windows
            canvas_widget.bind("<Button-4>", lambda e: on_mousewheel(type('Event', (), {'delta': 120, 'state': e.state, 'widget': e.widget})()))  # Linux scroll up
            canvas_widget.bind("<Button-5>", lambda e: on_mousewheel(type('Event', (), {'delta': -120, 'state': e.state, 'widget': e.widget})()))  # Linux scroll down

            # Add pan support with mouse drag
            def on_mouse_press(event):
                if event.widget is not canvas_widget:
                    return
                self._pan_start = (event.x, event.y)
                self._pan_prev = self.ax.transData.transform([(event.x, event.y)])

            def on_mouse_drag(event):
                if self._pan_start is None or self._pan_prev is None:
                    return
                if event.widget is not canvas_widget:
                    return

                try:
                    # Calculate pan distance
                    curr = self.ax.transData.transform([(event.x, event.y)])
                    if curr is not None and len(curr) > 0 and len(curr[0]) >= 2:
                        dx = curr[0][0] - self._pan_prev[0][0]
                        dy = curr[0][1] - self._pan_prev[0][1]

                        # Validate dx and dy are not NaN or Inf
                        if not (np.isfinite(dx) and np.isfinite(dy)):
                            return

                        # Apply pan
                        xlim = self.ax.get_xlim()
                        ylim = self.ax.get_ylim()

                        # Calculate new limits and validate they are finite
                        new_xlim_left = xlim[0] - dx
                        new_xlim_right = xlim[1] - dx
                        new_ylim_bottom = ylim[0] - dy
                        new_ylim_top = ylim[1] - dy

                        if all(np.isfinite([new_xlim_left, new_xlim_right, new_ylim_bottom, new_ylim_top])):
                            self.ax.set_xlim(new_xlim_left, new_xlim_right)
                            self.ax.set_ylim(new_ylim_bottom, new_ylim_top)
                            self.canvas.draw()
                            self._pan_prev = curr
                except Exception as e:
                    # Silently handle pan errors to prevent crashes
                    logger.debug(f"Pan error: {e}")
                    pass

            def on_mouse_release(event):
                self._pan_start = None
                self._pan_prev = None

            canvas_widget.bind("<ButtonPress-1>", on_mouse_press)
            canvas_widget.bind("<B1-Motion>", on_mouse_drag)
            canvas_widget.bind("<ButtonRelease-1>", on_mouse_release)

        except Exception as e:
            logger.warning(f"Could not add touchpad support: {e}")

    def _minimize_window(self):
        """Minimize the window."""
        try:
            if self.window:
                self.window.iconify()  # Minimize the window
                self.status_var.set("Window minimized")
        except Exception as e:
            logger.warning(f"Could not minimize window: {e}")

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        try:
            if self.window:
                # Toggle fullscreen state
                self.is_fullscreen = not getattr(self, 'is_fullscreen', False)

                if self.is_fullscreen:
                    # Go fullscreen
                    self.window.attributes('-fullscreen', True)
                    self.maximize_btn.config(text="⛶")  # Restore icon
                    self.status_var.set("Fullscreen mode")
                else:
                    # Exit fullscreen
                    self.window.attributes('-fullscreen', False)
                    self.maximize_btn.config(text="⛶")  # Maximize icon
                    self.status_var.set("Window mode")

                # Update button tooltip
                if self.is_fullscreen:
                    self.maximize_btn.bind("<Enter>", lambda e: self._show_tooltip(self.maximize_btn, "Exit Fullscreen"))
                else:
                    self.maximize_btn.bind("<Enter>", lambda e: self._show_tooltip(self.maximize_btn, "Enter Fullscreen"))

        except Exception as e:
            logger.warning(f"Could not toggle fullscreen: {e}")

    def _show_tooltip(self, widget, text):
        """Show tooltip for a widget."""
        try:
            # Create tooltip if it doesn't exist
            if not hasattr(self, 'tooltip'):
                self.tooltip = tk.Toplevel(self.window)
                self.tooltip.wm_overrideredirect(True)
                self.tooltip.wm_geometry("+%d+%d" % (widget.winfo_rootx(), widget.winfo_rooty() + 20))
                self.tooltip_label = tk.Label(self.tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
                self.tooltip_label.pack()
            else:
                # Update tooltip position and text
                self.tooltip.wm_geometry("+%d+%d" % (widget.winfo_rootx(), widget.winfo_rooty() + 20))
                self.tooltip_label.config(text=text)
                self.tooltip.deiconify()
        except Exception as e:
            logger.warning(f"Could not show tooltip: {e}")

    def _hide_tooltip(self):
        """Hide tooltip."""
        try:
            if hasattr(self, 'tooltip'):
                self.tooltip.withdraw()
        except Exception as e:
            logger.warning(f"Could not hide tooltip: {e}")

    def show(self):
        """Show the charts window."""
        if self.window:
            self.window.deiconify()
            self.window.focus_force()

    def _on_close(self):
        """Handle window close event."""
        try:
            if self.window:
                self.window.destroy()
        except Exception as e:
            logger.warning(f"Could not close window: {e}")

    def _create_charts_tab(self):
        """Create the charts tab with matplotlib display."""
        # Charts Tab Frame
        charts_frame = ttk.Frame(self.notebook)
        self.notebook.add(charts_frame, text="📊 Charts")

        # Chart display area - takes up most space
        chart_frame = ttk.LabelFrame(charts_frame, text="Chart Display", padding=10)
        chart_frame.pack(fill=tk.BOTH, expand=True)

        # Create matplotlib figure and canvas with proper configuration for zooming/scrolling
        self.figure, self.ax = plt.subplots(figsize=(12, 8), dpi=100)

        # Configure matplotlib for proper zooming and scrolling
        self.ax.set_adjustable('box')  # Allow independent x/y axis scaling
        self.ax.set_aspect('auto')  # Allow automatic aspect ratio adjustment

        # Configure subplot parameters for better layout
        self.figure.subplots_adjust(left=0.1, bottom=0.1, right=0.95, top=0.9, wspace=0.2, hspace=0.2)

        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add touch pad and mouse wheel support for zooming and panning
        self._add_touchpad_support()

        # Add matplotlib navigation toolbar to the center section of top toolbar
        if hasattr(self, 'matplotlib_toolbar_frame'):
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.matplotlib_toolbar_frame)

    def _create_calendar_tab(self):
        """Create the calendar tab with tender calendar view."""
        # Calendar Tab Frame
        calendar_frame = ttk.Frame(self.notebook)
        self.notebook.add(calendar_frame, text="📅 Calendar")

        # Calendar controls
        controls_frame = ttk.Frame(calendar_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        # Left section - Navigation and search
        left_controls = ttk.Frame(controls_frame)
        left_controls.pack(side=tk.LEFT)

        # Month/Year navigation
        nav_frame = ttk.Frame(left_controls)
        nav_frame.pack(side=tk.TOP, pady=(0, 5))

        ttk.Button(nav_frame, text="◀", command=self._prev_month, width=3).pack(side=tk.LEFT, padx=(0, 5))
        self.calendar_title_var = tk.StringVar(value="September 2025")
        ttk.Label(nav_frame, textvariable=self.calendar_title_var, font=('TkDefaultFont', 12, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(nav_frame, text="▶", command=self._next_month, width=3).pack(side=tk.LEFT)

        # Search functionality
        search_frame = ttk.Frame(left_controls)
        search_frame.pack(side=tk.TOP, pady=(5, 0))

        ttk.Label(search_frame, text="Search:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.calendar_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.calendar_search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        search_entry.bind("<KeyRelease>", lambda e: self._debounced_calendar_search())
        ttk.Button(search_frame, text="Clear", command=self._clear_calendar_search, width=6).pack(side=tk.LEFT)

        # Right section - Action buttons
        right_controls = ttk.Frame(controls_frame)
        right_controls.pack(side=tk.RIGHT)

        # Today button and export/print buttons
        ttk.Button(right_controls, text="Today", command=self._goto_today).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_controls, text="📄 Print", command=self._print_calendar).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_controls, text="📊 Export CSV", command=self._export_calendar_csv).pack(side=tk.LEFT)

        # Calendar display area
        calendar_display_frame = ttk.Frame(calendar_frame)
        calendar_display_frame.pack(fill=tk.BOTH, expand=True)

        # Create calendar grid
        self._create_calendar_grid(calendar_display_frame)

        # Legend
        legend_frame = ttk.Frame(calendar_frame)
        legend_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(legend_frame, text="Legend:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT)
        ttk.Label(legend_frame, text="• Number = Tender count for that day", foreground='blue').pack(side=tk.LEFT, padx=(10, 0))

        # Initial calendar update
        self._update_calendar()

    def _create_calendar_grid(self, parent):
        """Create the calendar grid display."""
        # Calendar grid container
        self.calendar_grid_frame = ttk.Frame(parent)
        self.calendar_grid_frame.pack(fill=tk.BOTH, expand=True)

        # Days of week header
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day in enumerate(days):
            ttk.Label(self.calendar_grid_frame, text=day, font=('TkDefaultFont', 10, 'bold'),
                     anchor='center').grid(row=0, column=i, sticky='nsew', padx=1, pady=1)

        # Configure grid weights
        for i in range(7):
            self.calendar_grid_frame.grid_columnconfigure(i, weight=1)

        # Create day cells (6 rows max for any month)
        self.day_buttons = []
        for week in range(6):
            for day in range(7):
                btn = tk.Button(self.calendar_grid_frame, text="", width=4, height=2,
                              font=('TkDefaultFont', 9), relief='flat', bg='white',
                              command=lambda w=week, d=day: self._on_day_click(w, d))
                btn.grid(row=week+1, column=day, sticky='nsew', padx=1, pady=1)
                self.day_buttons.append(btn)

    def _update_calendar(self):
        """Update the calendar display with current data."""
        try:
            # Get current calendar date
            if not hasattr(self, 'current_calendar_date'):
                self.current_calendar_date = datetime.now()

            year = self.current_calendar_date.year
            month = self.current_calendar_date.month

            # Update title
            month_name = self.current_calendar_date.strftime("%B %Y")
            self.calendar_title_var.set(month_name)

            # Calculate calendar layout
            import calendar as cal
            cal.setfirstweekday(0)  # Monday first

            # Get month data
            month_days = cal.monthcalendar(year, month)

            # Get tender counts for this month
            tender_counts = self._get_tender_counts_for_month(year, month)

            # Update day buttons
            day_num = 1
            for week in range(6):
                for day in range(7):
                    btn = self.day_buttons[week * 7 + day]

                    if week < len(month_days) and day < len(month_days[week]) and month_days[week][day] != 0:
                        day_of_month = month_days[week][day]
                        count = tender_counts.get(day_of_month, 0)

                        if count > 0:
                            btn.config(text=f"{day_of_month}\n{count}T",
                                     bg='#e3f2fd', fg='blue', font=('TkDefaultFont', 10, 'bold'))
                        else:
                            btn.config(text=str(day_of_month), bg='white', fg='black',
                                     font=('TkDefaultFont', 11, 'bold'))
                    else:
                        btn.config(text="", bg='#f5f5f5', state='disabled')

        except Exception as e:
            logger.error(f"Error updating calendar: {e}")

    def _get_tender_counts_for_month(self, year, month):
        """Get tender counts by day for the specified month."""
        try:
            counts = {}

            if self.data is None or self.data.empty:
                return counts

            # Find date columns
            date_cols = [col for col in self.data.columns
                        if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end', 'date', 'time'])]

            if not date_cols:
                return counts

            date_col = date_cols[0]

            # Convert to datetime if needed
            if not pd.api.types.is_datetime64_dtype(self.data[date_col]):
                try:
                    # Try to convert with common formats first, then fall back to infer
                    dates = pd.to_datetime(self.data[date_col], errors='coerce', format='%Y-%m-%d')
                    if dates.isna().all():
                        # Try another common format
                        dates = pd.to_datetime(self.data[date_col], errors='coerce', format='%d/%m/%Y')
                    if dates.isna().all():
                        # Fall back to inferring format
                        dates = pd.to_datetime(self.data[date_col], errors='coerce')
                except Exception:
                    return counts
            else:
                dates = self.data[date_col]

            # Check if we have any valid datetime values
            if dates.isna().all() or not pd.api.types.is_datetime64_dtype(dates):
                return counts

            # Filter for the specified month and count by day
            month_start = pd.Timestamp(year, month, 1)
            if month == 12:
                month_end = pd.Timestamp(year + 1, 1, 1) - pd.Timedelta(days=1)
            else:
                month_end = pd.Timestamp(year, month + 1, 1) - pd.Timedelta(days=1)

            # Filter valid datetime values within the month range
            valid_dates = dates.dropna()
            month_data = valid_dates[(valid_dates >= month_start) & (valid_dates <= month_end)]

            # Ensure month_data is still datetime-like before using .dt accessor
            if len(month_data) > 0 and pd.api.types.is_datetime64_dtype(month_data):
                day_counts = month_data.dt.day.value_counts()
                return day_counts.to_dict()
            else:
                return counts

        except Exception as e:
            logger.error(f"Error getting tender counts for month: {e}")
            return {}

    def _prev_month(self):
        """Go to previous month."""
        if hasattr(self, 'current_calendar_date'):
            year = self.current_calendar_date.year
            month = self.current_calendar_date.month

            if month == 1:
                self.current_calendar_date = datetime(year - 1, 12, 1)
            else:
                self.current_calendar_date = datetime(year, month - 1, 1)

            self._update_calendar()

    def _next_month(self):
        """Go to next month."""
        if hasattr(self, 'current_calendar_date'):
            year = self.current_calendar_date.year
            month = self.current_calendar_date.month

            if month == 12:
                self.current_calendar_date = datetime(year + 1, 1, 1)
            else:
                self.current_calendar_date = datetime(year, month + 1, 1)

            self._update_calendar()

    def _goto_today(self):
        """Go to current month."""
        self.current_calendar_date = datetime.now()
        self._update_calendar()

    def _on_day_click(self, week, day):
        """Handle day click in calendar."""
        try:
            # Calculate the actual date
            if not hasattr(self, 'current_calendar_date'):
                return

            year = self.current_calendar_date.year
            month = self.current_calendar_date.month

            import calendar as cal
            month_days = cal.monthcalendar(year, month)

            if week < len(month_days) and day < len(month_days[week]):
                day_of_month = month_days[week][day]
                if day_of_month != 0:
                    selected_date = datetime(year, month, day_of_month)

                    # Show details for this date
                    self._show_date_details(selected_date)

        except Exception as e:
            logger.error(f"Error handling day click: {e}")

    def _show_date_details(self, date):
        """Show detailed information for tenders on the selected date with filtering and export."""
        try:
            # Find tenders for this date
            date_str = date.strftime("%Y-%m-%d")

            # Find date columns
            date_cols = [col for col in self.data.columns
                        if any(kw in col.lower() for kw in ['closing', 'close', 'due', 'deadline', 'end', 'date', 'time'])]

            if not date_cols or self.data is None or self.data.empty:
                messagebox.showinfo("No Data", f"No tender data available for {date_str}")
                return

            date_col = date_cols[0]

            # Filter data for this date
            if pd.api.types.is_datetime64_dtype(self.data[date_col]):
                date_filter = self.data[date_col].dt.date == date.date()
            else:
                try:
                    dt_series = pd.to_datetime(self.data[date_col], errors='coerce')
                    date_filter = dt_series.dt.date == date.date()
                except:
                    messagebox.showinfo("Date Error", f"Could not process dates for {date_str}")
                    return

            day_tenders = self.data[date_filter]

            if day_tenders.empty:
                messagebox.showinfo("No Tenders", f"No tenders found for {date_str}")
                return

            # Create details window
            details_window = tk.Toplevel(self.window)
            details_window.title(f"Tenders for {date_str}")
            details_window.geometry("1000x700")

            # Create a class to manage the details window
            DateDetailsWindow(details_window, day_tenders, date_str)

        except Exception as e:
            logger.error(f"Error showing date details: {e}")
            messagebox.showerror("Error", f"Could not show details: {str(e)}")

    def _debounced_calendar_search(self):
        """Debounced search for calendar."""
        try:
            if self.window and self.calendar_search_after_id:
                self.window.after_cancel(self.calendar_search_after_id)
            if self.window:
                self.calendar_search_after_id = self.window.after(self.calendar_search_delay_ms, self._perform_calendar_search)
        except Exception as e:
            logger.warning(f"Could not debounce calendar search: {e}")

    def _perform_calendar_search(self):
        """Perform the actual calendar search."""
        try:
            # Implement search logic here - for now just update calendar
            search_term = self.calendar_search_var.get().strip().lower()
            # Could filter calendar display based on search term
            self._update_calendar()
        except Exception as e:
            logger.warning(f"Could not perform calendar search: {e}")

    def _clear_calendar_search(self):
        """Clear the calendar search."""
        try:
            self.calendar_search_var.set("")
            self._update_calendar()
        except Exception as e:
            logger.warning(f"Could not clear calendar search: {e}")

    def _print_calendar(self):
        """Print the calendar."""
        try:
            import calendar as cal
            if hasattr(self, 'current_calendar_date'):
                year = self.current_calendar_date.year
                month = self.current_calendar_date.month
                month_name = self.current_calendar_date.strftime("%B %Y")
                print(f"\n{month_name}")
                print(cal.month(year, month))
            else:
                print("No calendar date available")
        except Exception as e:
            logger.warning(f"Could not print calendar: {e}")

    def _export_calendar_csv(self):
        """Export calendar data to CSV."""
        try:
            from tkinter import filedialog
            if not hasattr(self, 'current_calendar_date'):
                return

            year = self.current_calendar_date.year
            month = self.current_calendar_date.month

            # Get tender counts
            tender_counts = self._get_tender_counts_for_month(year, month)

            # Create DataFrame
            days = list(range(1, 32))
            data = {'Day': days, 'Tender_Count': [tender_counts.get(day, 0) for day in days]}
            df = pd.DataFrame(data)

            file_path = filedialog.asksaveasfilename(
                title="Export Calendar to CSV",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                initialfile=f"calendar_{year}_{month:02d}.csv"
            )

            if file_path:
                df.to_csv(file_path, index=False)
                messagebox.showinfo("Export Successful", f"Calendar exported to:\n{file_path}")
        except Exception as e:
            logger.warning(f"Could not export calendar: {e}")
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")

    def _save_chart_config(self):
        """Save the current chart configuration to a JSON file."""
        try:
            # Get current chart settings
            config = {
                "chart_type": self.current_chart_type.get(),
                "selected_column": self.selected_column.get(),
                "selected_period": self.selected_period.get(),
                "timestamp": datetime.now().isoformat()
            }

            # Open file dialog to choose save location
            file_path = filedialog.asksaveasfilename(
                title="Save Chart Configuration",
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                initialfile=f"chart_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

            if not file_path:
                return

            # Save configuration to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.status_var.set(f"Configuration saved to {os.path.basename(file_path)}")
            messagebox.showinfo("Save Successful", f"Chart configuration saved to:\n{file_path}")

        except Exception as e:
            logger.error(f"Error saving chart config: {e}")
            messagebox.showerror("Save Error", f"Failed to save configuration: {str(e)}")

    def _export_chart(self):
        """Export the current chart as an image file."""
        try:
            # Check if we have a chart to export
            if not hasattr(self, 'figure') or self.figure is None:
                messagebox.showwarning("No Chart", "No chart available to export")
                return

            # Open file dialog to choose save location
            file_path = filedialog.asksaveasfilename(
                title="Export Chart as Image",
                defaultextension=".png",
                filetypes=[
                    ("PNG Files", "*.png"),
                    ("JPEG Files", "*.jpg"),
                    ("SVG Files", "*.svg"),
                    ("PDF Files", "*.pdf"),
                    ("All Files", "*.*")
                ],
                initialfile=f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )

            if not file_path:
                return

            # Determine format from file extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()

            format_map = {
                '.png': 'png',
                '.jpg': 'jpg',
                '.jpeg': 'jpg',
                '.svg': 'svg',
                '.pdf': 'pdf'
            }

            format_type = format_map.get(ext, 'png')

            # Save the figure
            self.figure.savefig(file_path, format=format_type, dpi=300, bbox_inches='tight')

            self.status_var.set(f"Chart exported to {os.path.basename(file_path)}")
            messagebox.showinfo("Export Successful", f"Chart exported to:\n{file_path}")

        except Exception as e:
            logger.error(f"Error exporting chart: {e}")
            messagebox.showerror("Export Error", f"Failed to export chart: {str(e)}")


class DateDetailsWindow:
    """Window for displaying and managing date-specific tender details."""

    def __init__(self, parent, data, date_str):
        self.parent = parent
        self.original_data = data.copy()
        self.filtered_data = data.copy()
        self.date_str = date_str
        self.search_var = tk.StringVar()

        self._create_widgets()
        self._populate_treeview()

    def _create_widgets(self):
        """Create the widgets for the date details window."""
        # Top controls frame
        controls_frame = ttk.Frame(self.parent)
        controls_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Left side - search
        search_frame = ttk.Frame(controls_frame)
        search_frame.pack(side=tk.LEFT)

        ttk.Label(search_frame, text="Filter:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        search_entry.bind("<KeyRelease>", lambda e: self._filter_tenders())
        ttk.Button(search_frame, text="Clear", command=self._clear_filter, width=8).pack(side=tk.LEFT)

        # Right side - export buttons
        export_frame = ttk.Frame(controls_frame)
        export_frame.pack(side=tk.RIGHT)

        ttk.Button(export_frame, text="📄 Export Excel", command=self._export_excel, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(export_frame, text="📊 Export CSV", command=self._export_csv, width=12).pack(side=tk.LEFT)

        # Treeview frame
        tree_frame = ttk.Frame(self.parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Create treeview
        self.tree = ttk.Treeview(tree_frame, show='headings', height=25)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Status label
        self.status_var = tk.StringVar(value=f"Showing {len(self.filtered_data)} tenders for {self.date_str}")
        status_label = ttk.Label(self.parent, textvariable=self.status_var, font=('TkDefaultFont', 9, 'bold'))
        status_label.pack(pady=(0, 10))

    def _populate_treeview(self):
        """Populate the treeview with tender data."""
        # Configure columns
        columns = list(self.filtered_data.columns)
        self.tree["columns"] = columns

        for col in columns:
            width = 120  # Default width
            if any(kw in col.lower() for kw in ['title', 'description', 'summary']):
                width = 250
            elif any(kw in col.lower() for kw in ['department', 'ministry', 'agency']):
                width = 150
            elif any(kw in col.lower() for kw in ['date', 'time', 'closing', 'close', 'due', 'deadline', 'end']):
                width = 100

            self.tree.column(col, width=width, minwidth=80)
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))

        # Add data
        for _, row in self.filtered_data.iterrows():
            values = [str(row[col]) if pd.notna(row[col]) else "" for col in columns]
            self.tree.insert("", "end", values=values)

    def _filter_tenders(self):
        """Filter tenders based on search term."""
        search_term = self.search_var.get().strip().lower()

        if not search_term:
            self.filtered_data = self.original_data.copy()
        else:
            # Apply filter across all columns
            mask = None
            for col in self.original_data.columns:
                try:
                    col_mask = self.original_data[col].astype(str).str.lower().str.contains(search_term, na=False, regex=False)
                    if mask is None:
                        mask = col_mask
                    else:
                        mask = mask | col_mask
                except Exception:
                    continue

            if mask is not None:
                self.filtered_data = self.original_data[mask]
            else:
                self.filtered_data = self.original_data.copy()

        # Update display
        self._refresh_treeview()
        self.status_var.set(f"Showing {len(self.filtered_data)} of {len(self.original_data)} tenders for {self.date_str}")

    def _clear_filter(self):
        """Clear the search filter."""
        self.search_var.set("")
        self._filter_tenders()

    def _refresh_treeview(self):
        """Refresh the treeview with current filtered data."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add filtered data
        for _, row in self.filtered_data.iterrows():
            values = [str(row[col]) if pd.notna(row[col]) else "" for col in self.filtered_data.columns]
            self.tree.insert("", "end", values=values)

    def _sort_by_column(self, col):
        """Sort the treeview by the specified column."""
        try:
            # Toggle sort direction
            if not hasattr(self, '_sort_reverse'):
                self._sort_reverse = {}

            if col not in self._sort_reverse:
                self._sort_reverse[col] = False

            self._sort_reverse[col] = not self._sort_reverse[col]
            reverse = self._sort_reverse[col]

            # Sort the data
            def sort_key(row):
                val = row[col]
                if pd.isna(val):
                    return "" if not reverse else "~~~"  # Handle NaN values
                return str(val).lower()

            sorted_data = sorted(self.filtered_data.iterrows(),
                               key=lambda x: sort_key(x[1]),
                               reverse=reverse)

            # Update treeview
            for item in self.tree.get_children():
                self.tree.delete(item)

            for _, row in sorted_data:
                values = [str(row[c]) if pd.notna(row[c]) else "" for c in self.filtered_data.columns]
                self.tree.insert("", "end", values=values)

        except Exception as e:
            logger.error(f"Error sorting by column {col}: {e}")

    def _export_excel(self):
        """Export filtered data to Excel."""
        try:
            from tkinter import filedialog

            file_path = filedialog.asksaveasfilename(
                title="Export Tenders to Excel",
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
                initialfile=f"tenders_{self.date_str.replace('-', '_')}.xlsx"
            )

            if not file_path:
                return

            self.filtered_data.to_excel(file_path, index=False)
            messagebox.showinfo("Export Successful", f"Data exported to:\n{file_path}")

        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")

    def _export_csv(self):
        """Export filtered data to CSV."""
        try:
            from tkinter import filedialog

            file_path = filedialog.asksaveasfilename(
                title="Export Tenders to CSV",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                initialfile=f"tenders_{self.date_str.replace('-', '_')}.csv"
            )

            if not file_path:
                return

            self.filtered_data.to_csv(file_path, index=False, encoding='utf-8')
            messagebox.showinfo("Export Successful", f"Data exported to:\n{file_path}")

        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
