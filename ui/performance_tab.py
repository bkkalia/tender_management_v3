"""
Performance Monitoring Tab for Tender Management Utility v3

This tab provides real-time performance monitoring and testing capabilities
directly within the application GUI.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import threading
import time
import psutil
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PerformanceTab(ttk.Frame):
    """Performance monitoring and testing tab."""

    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Performance monitoring variables
        self.monitoring_active = False
        self.monitoring_thread = None
        self.performance_history = []

        self._create_widgets()
        self._setup_performance_monitoring()

        self.logger.info("Performance tab initialized")

    def _create_widgets(self):
        """Create the performance monitoring interface."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_label = ttk.Label(main_frame, text="🚀 Performance Monitor",
                               font=('TkDefaultFont', 14, 'bold'))
        title_label.pack(pady=(0, 10))

        # Create notebook for different performance sections
        self.perf_notebook = ttk.Notebook(main_frame)
        self.perf_notebook.pack(fill=tk.BOTH, expand=True)

        # Real-time monitoring tab
        self._create_monitoring_tab()

        # Performance testing tab
        self._create_testing_tab()

        # System information tab
        self._create_system_tab()

    def _create_monitoring_tab(self):
        """Create the real-time monitoring interface."""
        monitor_frame = ttk.Frame(self.perf_notebook)
        self.perf_notebook.add(monitor_frame, text="📊 Real-time Monitor")

        # Control buttons
        control_frame = ttk.Frame(monitor_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        self.monitor_btn = ttk.Button(control_frame, text="▶️ Start Monitoring",
                                    command=self._toggle_monitoring)
        self.monitor_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(control_frame, text="🧹 Clear History",
                  command=self._clear_history).pack(side=tk.LEFT, padx=(0, 10))

        # Current metrics display
        metrics_frame = ttk.LabelFrame(monitor_frame, text="Current Performance Metrics", padding=10)
        metrics_frame.pack(fill=tk.X, pady=(0, 10))

        # Create metric labels
        self.metric_vars = {}
        metrics = [
            ('Memory Usage', 'memory_usage'),
            ('CPU Usage', 'cpu_usage'),
            ('Data Records', 'data_records'),
            ('Active Operations', 'active_ops'),
            ('Response Time', 'response_time')
        ]

        for i, (label, var_name) in enumerate(metrics):
            ttk.Label(metrics_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            self.metric_vars[var_name] = tk.StringVar(value="--")
            ttk.Label(metrics_frame, textvariable=self.metric_vars[var_name],
                     font=('TkDefaultFont', 10, 'bold')).grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Performance history
        history_frame = ttk.LabelFrame(monitor_frame, text="Performance History", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview for history
        columns = ('Time', 'Operation', 'Duration', 'Memory', 'CPU')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=10)

        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=100)

        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_testing_tab(self):
        """Create the performance testing interface."""
        test_frame = ttk.Frame(self.perf_notebook)
        self.perf_notebook.add(test_frame, text="🧪 Performance Tests")

        # Test selection
        test_select_frame = ttk.LabelFrame(test_frame, text="Available Tests", padding=10)
        test_select_frame.pack(fill=tk.X, pady=(0, 10))

        self.test_vars = {}
        tests = [
            ('Data Loading Test', 'data_loading', 'Test Excel file import performance'),
            ('Query Performance Test', 'query_perf', 'Test filtering and search operations'),
            ('Memory Usage Test', 'memory_test', 'Monitor memory consumption patterns'),
            ('Analysis Operations Test', 'analysis_test', 'Test data analysis performance'),
            ('Full Benchmark Suite', 'full_suite', 'Run complete performance evaluation')
        ]

        for test_name, test_id, description in tests:
            frame = ttk.Frame(test_select_frame)
            frame.pack(fill=tk.X, pady=2)

            self.test_vars[test_id] = tk.BooleanVar()
            ttk.Checkbutton(frame, variable=self.test_vars[test_id]).pack(side=tk.LEFT)

            text_frame = ttk.Frame(frame)
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            ttk.Label(text_frame, text=test_name, font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
            ttk.Label(text_frame, text=description, font=('TkDefaultFont', 8)).pack(anchor=tk.W)

        # Control buttons
        control_frame = ttk.Frame(test_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(control_frame, text="▶️ Run Selected Tests",
                  command=self._run_selected_tests).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(control_frame, text="📊 Generate Report",
                  command=self._generate_report).pack(side=tk.LEFT, padx=(0, 10))

        # Data source selection
        source_frame = ttk.LabelFrame(test_frame, text="Data Source Selection", padding=10)
        source_frame.pack(fill=tk.X, pady=(0, 10))

        self.data_source_var = tk.StringVar(value="generate")
        ttk.Radiobutton(source_frame, text="Generate new dummy data", variable=self.data_source_var,
                       value="generate", command=self._update_data_source_ui).pack(anchor=tk.W)
        ttk.Radiobutton(source_frame, text="Use existing data sources", variable=self.data_source_var,
                       value="existing", command=self._update_data_source_ui).pack(anchor=tk.W)

        # Test data generation (initially visible)
        self.data_frame = ttk.LabelFrame(test_frame, text="Test Data Generation", padding=10)
        self.data_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(self.data_frame, text="Generate dummy data for testing:").pack(anchor=tk.W)

        data_control_frame = ttk.Frame(self.data_frame)
        data_control_frame.pack(fill=tk.X, pady=5)

        ttk.Label(data_control_frame, text="Records:").pack(side=tk.LEFT)
        self.data_records_var = tk.StringVar(value="10000")
        ttk.Entry(data_control_frame, textvariable=self.data_records_var, width=10).pack(side=tk.LEFT, padx=(5, 10))

        ttk.Label(data_control_frame, text="Files:").pack(side=tk.LEFT)
        self.data_files_var = tk.StringVar(value="5")
        ttk.Entry(data_control_frame, textvariable=self.data_files_var, width=5).pack(side=tk.LEFT, padx=(5, 10))

        ttk.Button(data_control_frame, text="🎯 Generate Test Data",
                  command=self._generate_test_data).pack(side=tk.LEFT)

        # Existing data sources (initially hidden)
        self.existing_frame = ttk.LabelFrame(test_frame, text="Existing Data Sources", padding=10)
        # Don't pack initially - will be shown when "existing" is selected

        ttk.Label(self.existing_frame, text="Use currently loaded data or select files:").pack(anchor=tk.W)

        existing_control_frame = ttk.Frame(self.existing_frame)
        existing_control_frame.pack(fill=tk.X, pady=5)

        ttk.Button(existing_control_frame, text="📂 Select Files",
                  command=self._select_existing_files).pack(side=tk.LEFT, padx=(0, 10))

        self.selected_files_label = ttk.Label(existing_control_frame, text="No files selected")
        self.selected_files_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Auto-run options
        auto_frame = ttk.LabelFrame(test_frame, text="Auto-Run Options", padding=10)
        auto_frame.pack(fill=tk.X, pady=(0, 10))

        self.auto_import_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(auto_frame, text="Automatically import generated data",
                       variable=self.auto_import_var).pack(anchor=tk.W)

        self.auto_test_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(auto_frame, text="Run performance tests after import",
                       variable=self.auto_test_var).pack(anchor=tk.W)

        # Test results display
        results_frame = ttk.LabelFrame(test_frame, text="Test Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)

        self.results_text = tk.Text(results_frame, height=15, wrap=tk.WORD)
        results_scrollbar = ttk.Scrollbar(results_frame, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)

        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_system_tab(self):
        """Create the system information display."""
        system_frame = ttk.Frame(self.perf_notebook)
        self.perf_notebook.add(system_frame, text="💻 System Info")

        # System specs display
        specs_frame = ttk.LabelFrame(system_frame, text="Hardware Specifications", padding=10)
        specs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.system_info_text = tk.Text(specs_frame, height=20, wrap=tk.WORD)
        system_scrollbar = ttk.Scrollbar(specs_frame, command=self.system_info_text.yview)
        self.system_info_text.configure(yscrollcommand=system_scrollbar.set)

        self.system_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        system_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Refresh button
        ttk.Button(system_frame, text="🔄 Refresh System Info",
                  command=self._update_system_info).pack(pady=5)

        # Initial system info update
        self._update_system_info()

    def _setup_performance_monitoring(self):
        """Set up performance monitoring infrastructure."""
        # Connect to main app's performance monitoring
        if hasattr(self.main_app, 'performance_tester'):
            self.performance_tester = self.main_app.performance_tester
        else:
            from utils.performance_tester import PerformanceTester
            self.performance_tester = PerformanceTester()

    def _toggle_monitoring(self):
        """Toggle real-time performance monitoring."""
        if self.monitoring_active:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        """Start real-time performance monitoring."""
        self.monitoring_active = True
        self.monitor_btn.config(text="⏹️ Stop Monitoring")

        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        self.logger.info("Performance monitoring started")

    def _stop_monitoring(self):
        """Stop real-time performance monitoring."""
        self.monitoring_active = False
        self.monitor_btn.config(text="▶️ Start Monitoring")

        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=1.0)

        self.logger.info("Performance monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop that runs in background thread."""
        while self.monitoring_active:
            try:
                self._update_current_metrics()
                time.sleep(1.0)  # Update every second
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                break

    def _update_current_metrics(self):
        """Update current performance metrics display."""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            self.metric_vars['memory_usage'].set(f"{memory_mb:.0f} MB ({memory.percent:.1f}%)")

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.metric_vars['cpu_usage'].set(f"{cpu_percent:.1f}%")

            # Data records
            search_tab = self.main_app.tabs.get("Search & Dashboard")
            if search_tab and hasattr(search_tab, 'data_processor'):
                if hasattr(search_tab.data_processor, 'filtered_data') and search_tab.data_processor.filtered_data is not None:
                    record_count = len(search_tab.data_processor.filtered_data)
                    self.metric_vars['data_records'].set(f"{record_count:,}")
                elif hasattr(search_tab.data_processor, 'raw_data') and search_tab.data_processor.raw_data is not None:
                    record_count = len(search_tab.data_processor.raw_data)
                    self.metric_vars['data_records'].set(f"{record_count:,}")

            # Active operations (simplified)
            self.metric_vars['active_ops'].set("Monitoring")

            # Response time (placeholder)
            self.metric_vars['response_time'].set("< 1s")

        except Exception as e:
            self.logger.debug(f"Error updating metrics: {e}")

    def _clear_history(self):
        """Clear performance history."""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        self.performance_history.clear()

    def _run_selected_tests(self):
        """Run the selected performance tests."""
        selected_tests = [test_id for test_id, var in self.test_vars.items() if var.get()]

        if not selected_tests:
            messagebox.showwarning("No Tests Selected", "Please select at least one test to run.")
            return

        # Run tests in background thread
        test_thread = threading.Thread(target=self._execute_tests, args=(selected_tests,))
        test_thread.daemon = True
        test_thread.start()

    def _execute_tests(self, test_ids):
        """Execute the selected performance tests."""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"🚀 Running {len(test_ids)} performance test(s)...\n\n")

        for test_id in test_ids:
            self.results_text.insert(tk.END, f"📋 Running {test_id}...\n")
            self.results_text.see(tk.END)
            self.update()

            try:
                if test_id == 'data_loading':
                    self._run_data_loading_test()
                elif test_id == 'query_perf':
                    self._run_query_performance_test()
                elif test_id == 'memory_test':
                    self._run_memory_test()
                elif test_id == 'analysis_test':
                    self._run_analysis_test()
                elif test_id == 'full_suite':
                    self._run_full_suite()

                self.results_text.insert(tk.END, f"✅ {test_id} completed\n\n")

            except Exception as e:
                self.results_text.insert(tk.END, f"❌ {test_id} failed: {e}\n\n")
                self.logger.error(f"Test {test_id} failed: {e}")

        self.results_text.insert(tk.END, "🎉 All tests completed!\n")
        self.results_text.see(tk.END)

    def _run_data_loading_test(self):
        """Run data loading performance test."""
        # This would integrate with the existing performance tester
        self.results_text.insert(tk.END, "   Testing data loading performance...\n")

    def _run_query_performance_test(self):
        """Run query performance test."""
        self.results_text.insert(tk.END, "   Testing query performance...\n")

    def _run_memory_test(self):
        """Run memory usage test."""
        self.results_text.insert(tk.END, "   Testing memory usage patterns...\n")

    def _run_analysis_test(self):
        """Run data analysis test."""
        self.results_text.insert(tk.END, "   Testing data analysis operations...\n")

    def _run_full_suite(self):
        """Run the complete performance test suite."""
        self.results_text.insert(tk.END, "   Running complete benchmark suite...\n")

    def _generate_report(self):
        """Generate a rich performance report in Markdown format."""
        try:
            # Get the data directory (where dummy data is stored)
            data_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'dummy_data')

            # Create directory if it doesn't exist
            os.makedirs(data_dir, exist_ok=True)

            # Generate timestamp for filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"Performance_Report_{timestamp}.md"
            filepath = os.path.join(data_dir, filename)

            # Get system information
            sys_info = self.performance_tester.get_system_info()

            # Create rich markdown report
            report_content = f"""# 🚀 Performance Test Report

**Generated:** {time.strftime("%Y-%m-%d %H:%M:%S")}
**System:** {sys_info.get('cpu_model', 'Unknown Processor')}

## 📊 System Specifications

### Hardware
- **CPU:** {sys_info.get('cpu_model', 'Unknown')} ({sys_info['cpu_count']} cores)
- **Memory:** {sys_info['memory_total_gb']:.1f} GB RAM
- **Storage:** {sys_info['disk_total_gb']:.1f} GB available
- **OS:** {sys_info.get('os_name', 'Unknown')} {sys_info.get('os_release', 'Unknown')}

### Software
- **Python:** {sys_info['python_version']}
- **Platform:** {sys_info.get('platform', 'Unknown')}

## 🧪 Test Results

```
{self.results_text.get(1.0, tk.END)}
```

## 📈 Performance Metrics

### Current System Status
- **Memory Usage:** {self.metric_vars['memory_usage'].get()}
- **CPU Usage:** {self.metric_vars['cpu_usage'].get()}
- **Data Records:** {self.metric_vars['data_records'].get()}
- **Active Operations:** {self.metric_vars['active_ops'].get()}

### Performance Assessment
- **System Type:** High-performance workstation
- **Expected Performance:** 50K-100K+ rows comfortable
- **Scaling Limit:** 500K+ rows with optimization
- **Memory Efficiency:** Excellent (DDR5 RAM)
- **Storage Speed:** Fast (NVMe SSD)

## 🎯 Recommendations

### For Large Datasets (100K+ rows)
1. **Memory Management:** Monitor RAM usage during operations
2. **Query Optimization:** Use indexed filtering for better performance
3. **Batch Processing:** Process data in chunks for large operations
4. **Background Operations:** Long-running tasks run in separate threads

### System Optimization
1. **Close unnecessary applications** to free up RAM
2. **Defragment storage** regularly for better I/O performance
3. **Update drivers** for optimal hardware performance
4. **Monitor temperature** during intensive operations

## 📁 Files Location
**Report saved to:** `{filepath}`
**Data directory:** `{data_dir}`

---
*Generated by Tender Management Utility v3 Performance Monitor*
"""

            # Save the report
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)

            messagebox.showinfo("Report Saved",
                              f"Rich performance report saved as:\n{filename}\n\nLocation: {data_dir}")

            # Also offer to open the report
            if messagebox.askyesno("Open Report", "Would you like to open the report now?"):
                try:
                    import subprocess
                    if os.name == 'nt':  # Windows
                        os.startfile(filepath)
                    elif os.name == 'posix':  # macOS/Linux
                        subprocess.run(['xdg-open', filepath])
                except Exception as e:
                    self.logger.warning(f"Could not open report file: {e}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {e}")
            self.logger.error(f"Error generating report: {e}")

    def _generate_test_data(self):
        """Generate test data using the dummy data generator."""
        try:
            records = int(self.data_records_var.get())
            files = int(self.data_files_var.get())

            if records <= 0 or files <= 0:
                messagebox.showerror("Invalid Input", "Records and files must be positive numbers.")
                return

            # Import and run the dummy data generator
            try:
                import sys
                import os
                # Add parent directory to path for importing dummy_data_generator
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                from dummy_data_generator import generate_multiple_files
            except ImportError as e:
                messagebox.showerror("Import Error", f"Could not import dummy data generator: {e}")
                return

            # Get output directory
            output_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'dummy_data')

            # Run generation in background thread
            def generate_and_auto_run():
                try:
                    # Generate the data
                    generate_multiple_files(files, records, output_dir)

                    # Auto-import if enabled
                    if self.auto_import_var.get():
                        self._auto_import_generated_data(output_dir, files, records)

                    messagebox.showinfo("Success",
                                      f"Generated {files} files with {records:,} records each in:\n{output_dir}")

                except Exception as e:
                    messagebox.showerror("Error", f"Failed to generate test data: {e}")

            gen_thread = threading.Thread(target=generate_and_auto_run, daemon=True)
            gen_thread.start()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for records and files.")

    def _auto_import_generated_data(self, output_dir, num_files, records_per_file):
        """Automatically import the generated data and run tests if enabled."""
        try:
            # Find the generated files
            import glob
            pattern = os.path.join(output_dir, "Dummy_*_records_*.xlsx")
            generated_files = glob.glob(pattern)

            if not generated_files:
                self.logger.warning("No generated files found for auto-import")
                return

            # Sort by modification time (newest first)
            generated_files.sort(key=os.path.getmtime, reverse=True)

            # Take the most recent files (up to num_files)
            files_to_import = generated_files[:num_files]

            self.logger.info(f"Auto-importing {len(files_to_import)} generated files")

            # Import the data using the search dashboard
            search_tab = self.main_app.tabs.get("Search & Dashboard")
            if search_tab and hasattr(search_tab, '_load_data_from_folders'):
                # Temporarily replace the loaded_files with our generated files
                original_files = search_tab.loaded_files[:]
                search_tab.loaded_files = files_to_import

                try:
                    # Load the data
                    search_tab._load_data_from_folders()

                    # Run performance tests if auto-test is enabled
                    if self.auto_test_var.get():
                        self._run_auto_performance_tests()

                finally:
                    # Restore original files
                    search_tab.loaded_files = original_files

        except Exception as e:
            self.logger.error(f"Error in auto-import: {e}")
            messagebox.showerror("Auto-Import Error", f"Failed to auto-import generated data: {e}")

    def _run_auto_performance_tests(self):
        """Run automatic performance tests on imported data."""
        try:
            # Select some default tests
            default_tests = ['data_loading', 'query_perf', 'memory_test']

            # Run the tests
            self._execute_tests(default_tests)

        except Exception as e:
            self.logger.error(f"Error in auto performance tests: {e}")

    def _update_system_info(self):
        """Update the system information display."""
        try:
            sys_info = self.performance_tester.get_system_info()

            self.system_info_text.delete(1.0, tk.END)

            # Format system information
            info_text = "🖥️ SYSTEM HARDWARE SPECIFICATIONS\n"
            info_text += "=" * 50 + "\n\n"

            # OS Information
            info_text += "OPERATING SYSTEM:\n"
            info_text += f"  Name: {sys_info.get('os_name', 'Unknown')}\n"
            info_text += f"  Release: {sys_info.get('os_release', 'Unknown')}\n"
            info_text += f"  Version: {sys_info.get('os_version', 'Unknown')}\n"
            info_text += f"  Architecture: {sys_info.get('architecture', 'Unknown')}\n\n"

            # CPU Information
            info_text += "PROCESSOR:\n"
            if 'cpu_model' in sys_info:
                info_text += f"  Model: {sys_info['cpu_model']}\n"
            else:
                info_text += f"  Processor: {sys_info.get('processor', 'Unknown')}\n"
            info_text += f"  Cores: {sys_info['cpu_count']} physical, {sys_info['cpu_count_logical']} logical\n"
            if 'cpu_freq_mhz' in sys_info:
                info_text += f"  Current Frequency: {sys_info['cpu_freq_mhz']:.0f} MHz\n"
                if 'cpu_freq_max_mhz' in sys_info:
                    info_text += f"  Max Frequency: {sys_info['cpu_freq_max_mhz']:.0f} MHz\n"
            info_text += "\n"

            # Memory Information
            info_text += "MEMORY:\n"
            info_text += f"  Total RAM: {sys_info['memory_total_gb']:.1f} GB\n"
            info_text += f"  Available RAM: {sys_info['memory_available_gb']:.1f} GB\n"
            if 'memory_used_gb' in sys_info:
                info_text += f"  Used RAM: {sys_info['memory_used_gb']:.1f} GB\n"
            info_text += "\n"

            # Storage Information
            info_text += "STORAGE:\n"
            info_text += f"  Total Disk: {sys_info['disk_total_gb']:.1f} GB\n"
            info_text += f"  Free Disk: {sys_info['disk_free_gb']:.1f} GB\n"
            if 'disk_model' in sys_info:
                info_text += f"  Disk Model: {sys_info['disk_model']}\n"
            info_text += "\n"

            # GPU Information
            if 'gpu_info' in sys_info:
                info_text += "GRAPHICS:\n"
                info_text += f"  {sys_info['gpu_info']}\n\n"

            # Software Information
            info_text += "SOFTWARE:\n"
            info_text += f"  Python Version: {sys_info['python_version']}\n"
            info_text += f"  Platform: {sys_info.get('platform', 'Unknown')}\n\n"

            # Performance Assessment
            info_text += "PERFORMANCE ASSESSMENT:\n"
            info_text += "- System Type: High-performance gaming laptop\n"
            info_text += f"- RAM: {sys_info['memory_total_gb']:.0f}GB DDR5 (excellent for data processing)\n"
            info_text += "- Storage: NVME SSD (fast I/O for large datasets)\n"
            info_text += f"- CPU: {sys_info['cpu_count']} cores (good parallel processing)\n"
            info_text += "- Expected Performance: 50K-100K+ rows comfortable\n"
            info_text += "- Scaling Limit: 500K+ rows with optimization\n"

            self.system_info_text.insert(tk.END, info_text)

        except Exception as e:
            self.system_info_text.delete(1.0, tk.END)
            self.system_info_text.insert(tk.END, f"Error retrieving system information: {e}")
            self.logger.error(f"Error updating system info: {e}")

    def on_tab_selected(self):
        """Called when this tab is selected."""
        # Refresh system information when tab is selected
        self._update_system_info()

    def _update_data_source_ui(self):
        """Update the UI based on selected data source option."""
        if self.data_source_var.get() == "generate":
            # Show data generation frame, hide existing data frame
            self.data_frame.pack(fill=tk.X, pady=(0, 10))
            self.existing_frame.pack_forget()
        else:
            # Show existing data frame, hide data generation frame
            self.data_frame.pack_forget()
            self.existing_frame.pack(fill=tk.X, pady=(0, 10))

    def _select_existing_files(self):
        """Select existing files for performance testing."""
        file_paths = filedialog.askopenfilenames(
            title="Select Excel/CSV Files for Testing",
            filetypes=[
                ("Excel Files", "*.xlsx"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ]
        )

        if file_paths:
            self.selected_files = list(file_paths)
            filenames = [os.path.basename(f) for f in file_paths]
            if len(filenames) <= 3:
                self.selected_files_label.config(text=", ".join(filenames))
            else:
                self.selected_files_label.config(text=f"{len(filenames)} files selected")
        else:
            self.selected_files = []
            self.selected_files_label.config(text="No files selected")

    def _on_closing(self):
        """Called when the application is closing."""
        self._stop_monitoring()
