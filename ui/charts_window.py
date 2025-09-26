import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import numpy as np

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

        # Auto-refresh functionality
        self.auto_refresh_enabled = True
        self.refresh_timer = None
        self.refresh_interval = 5000  # 5 seconds

        # Set up matplotlib style
        plt.style.use('default')

        # Create the window
        self._create_window()
        self._create_widgets()

        # Set smart default column and chart type
        self._set_smart_defaults()

        # Initial chart
        self._update_chart()

        # Start auto-refresh
        self._start_auto_refresh()

    def _create_window(self):
        """Create the main charts window."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("📊 Data Charts & Visualizations")
        self.window.geometry("1000x700")

        # Center the window
        self.window.transient(self.parent)
        # Remove grab_set() to make window non-modal
        # self.window.grab_set()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        # Make window non-modal - don't force focus
        # self.window.focus_set()

    def _create_widgets(self):
        """Create all widgets for the charts window."""
        if not self.window:
            return

        # Main container
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Control panel at top
        control_frame = ttk.LabelFrame(main_frame, text="Chart Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Chart type selection
        chart_frame = ttk.Frame(control_frame)
        chart_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(chart_frame, text="Chart Type:").pack(side=tk.LEFT, padx=(0, 10))
        chart_combo = ttk.Combobox(chart_frame, textvariable=self.current_chart_type,
                                 values=["bar", "pie", "line", "histogram", "scatter"],
                                 state="readonly", width=15)
        chart_combo.pack(side=tk.LEFT, padx=(0, 20))
        chart_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

        # Column selection
        column_frame = ttk.Frame(control_frame)
        column_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(column_frame, text="Primary Column:").pack(side=tk.LEFT, padx=(0, 10))
        if hasattr(self.data, 'columns') and self.data.columns is not None:
            column_combo = ttk.Combobox(column_frame, textvariable=self.selected_column,
                                       values=list(self.data.columns), state="readonly", width=20)
            column_combo.pack(side=tk.LEFT, padx=(0, 20))
            column_combo.bind("<<ComboboxSelected>>", lambda e: self._update_chart())

            # Set default column
            if len(self.data.columns) > 0:
                self.selected_column.set(self.data.columns[0])

        # Action buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="🔄 Refresh Data",
                  command=self._refresh_data).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="📊 New Chart",
                  command=self._update_chart).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="❌ Close",
                  command=self._on_close).pack(side=tk.RIGHT)

        # Chart display area
        chart_frame = ttk.LabelFrame(main_frame, text="Chart Display", padding=10)
        chart_frame.pack(fill=tk.BOTH, expand=True)

        # Create matplotlib figure and canvas
        self.figure, self.ax = plt.subplots(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add navigation toolbar
        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.pack(fill=tk.X, pady=(5, 0))
        NavigationToolbar2Tk(self.canvas, toolbar_frame)

    def _refresh_data(self):
        """Refresh data from parent Tree view."""
        try:
            if hasattr(self.parent, 'data_processor') and hasattr(self.parent.data_processor, 'filtered_data'):
                new_data = self.parent.data_processor.filtered_data
                if new_data is not None and not new_data.empty:
                    self.data = new_data.copy()
                    self._update_chart()
                    logger.info("Charts data refreshed from Tree view")
                else:
                    messagebox.showinfo("No Data", "No data available in Tree view to refresh.")
            else:
                messagebox.showwarning("Refresh Failed", "Could not access Tree view data.")
        except Exception as e:
            logger.error(f"Error refreshing chart data: {e}")
            messagebox.showerror("Refresh Error", f"Failed to refresh data: {str(e)}")

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
            # Handle different data types
            if pd.api.types.is_numeric_dtype(self.data[column]):
                # For numeric columns, create value distribution
                return self._prepare_numeric_data(column)
            elif pd.api.types.is_datetime64_dtype(self.data[column]):
                # For datetime columns, create time series
                return self._prepare_datetime_data(column)
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

    def _create_bar_chart(self, chart_data, column):
        """Create a bar chart."""
        try:
            if 'Range' in chart_data.columns:
                # Numeric histogram
                self.ax.bar(range(len(chart_data)), chart_data['Count'])
                self.ax.set_xlabel('Value Ranges')
                self.ax.set_title(f'Distribution of {column}')
            else:
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

            self.ax.set_ylabel('Count')
            self.ax.grid(True, alpha=0.3)

        except Exception as e:
            logger.error(f"Error creating bar chart: {e}")
            self._show_error_message("Failed to create bar chart")

    def _create_pie_chart(self, chart_data, column):
        """Create a pie chart with both percentages and absolute numbers."""
        try:
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
            if 'Date' in chart_data.columns:
                # Time series data
                dates = chart_data['Date']
                values = chart_data['Count']

                self.ax.plot(dates, values, marker='o', linewidth=2, markersize=4)
                self.ax.set_xlabel('Date')
                self.ax.set_title(f'Time Series of {column}')
            else:
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

            self.ax.set_ylabel('Count')
            self.ax.grid(True, alpha=0.3)

        except Exception as e:
            logger.error(f"Error creating line chart: {e}")
            self._show_error_message("Failed to create line chart")

    def _create_histogram(self, chart_data, column):
        """Create a histogram."""
        try:
            if 'Count' in chart_data.columns:
                # Use the prepared histogram data
                counts = chart_data['Count']
                if 'Range' in chart_data.columns:
                    # Numeric histogram
                    self.ax.hist(counts, bins=20, alpha=0.7, edgecolor='black')
                    self.ax.set_xlabel('Frequency')
                    self.ax.set_title(f'Histogram of {column} Distribution')
                else:
                    # Categorical histogram
                    categories = chart_data['Category']
                    self.ax.hist(categories, alpha=0.7, edgecolor='black')
                    self.ax.set_xlabel('Categories')
                    self.ax.set_title(f'Histogram of {column}')
            else:
                # Direct histogram from data
                data_clean = self.data[column].dropna()
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

    def _set_smart_defaults(self):
        """Set smart default column and chart type based on data."""
        if not hasattr(self.data, 'columns') or self.data.columns is None:
            return

        # Find the best column to visualize
        date_columns = [col for col in self.data.columns
                       if any(kw in col.lower() for kw in ['date', 'time', 'closing', 'close', 'due', 'deadline', 'end'])]

        dept_columns = [col for col in self.data.columns
                       if any(kw in col.lower() for kw in ['department', 'dept', 'agency', 'organisation', 'ministry'])]

        # Prioritize: Date columns > Department columns > First column
        if date_columns:
            self.selected_column.set(date_columns[0])
            # For date columns, line chart is often most useful
            if pd.api.types.is_datetime64_dtype(self.data[date_columns[0]]):
                self.current_chart_type.set("line")
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

    def _on_close(self):
        """Handle window close event."""
        # Stop auto-refresh
        self.auto_refresh_enabled = False
        if self.refresh_timer:
            if self.window:
                self.window.after_cancel(self.refresh_timer)

        if self.window:
            self.window.destroy()
            self.window = None

    def show(self):
        """Show the charts window."""
        if self.window:
            self.window.mainloop()
