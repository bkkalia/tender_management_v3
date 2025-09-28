"""
Benchmark Window module - Separate window for performance benchmarking.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import threading
import time
import psutil
import os
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BenchmarkWindow:
    """Separate window for displaying performance benchmarks and system tests."""

    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Window reference
        self.window: Optional[tk.Toplevel] = None

        # Benchmark state
        self.benchmark_running = False
        self.benchmark_thread = None
        self.benchmark_results = {}

        # Performance tester
        try:
            from utils.performance_tester import PerformanceTester
            self.performance_tester = PerformanceTester()
        except ImportError:
            self.performance_tester = None
            self.logger.warning("PerformanceTester not available")

        # Create the window
        self._create_window()
        self._create_widgets()

        self.logger.info("Benchmark window initialized")

    def _create_window(self):
        """Create the main benchmark window."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("🚀 Performance Benchmark Monitor")
        self.window.geometry("900x700")

        # Make window resizable
        self.window.resizable(True, True)
        self.window.minsize(700, 500)

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        """Create all widgets for the benchmark window."""
        if not self.window:
            return

        # Main container
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_label = ttk.Label(main_frame, text="🚀 Performance Benchmark Monitor",
                               font=('TkDefaultFont', 16, 'bold'))
        title_label.pack(pady=(0, 10))

        # Create notebook for different benchmark sections
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Benchmark Tests tab
        self._create_benchmark_tab()

        # System Information tab
        self._create_system_tab()

        # Results tab
        self._create_results_tab()

    def _create_benchmark_tab(self):
        """Create the benchmark tests interface."""
        benchmark_frame = ttk.Frame(self.notebook)
        self.notebook.add(benchmark_frame, text="🔬 Benchmark Tests")

        # Control buttons
        control_frame = ttk.Frame(benchmark_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        self.run_benchmark_btn = ttk.Button(control_frame, text="▶️ Run Benchmark Suite",
                                          command=self._run_benchmark)
        self.run_benchmark_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(control_frame, text="⏹️ Stop",
                  command=self._stop_benchmark).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(control_frame, text="💾 Save Results",
                  command=self._save_results).pack(side=tk.LEFT, padx=(0, 10))

        # Benchmark tests selection
        tests_frame = ttk.LabelFrame(benchmark_frame, text="Available Benchmark Tests", padding=10)
        tests_frame.pack(fill=tk.X, pady=(0, 10))

        # Create scrollable frame for tests
        tests_canvas = tk.Canvas(tests_frame, height=150)
        tests_scrollbar = ttk.Scrollbar(tests_frame, orient="vertical", command=tests_canvas.yview)
        tests_inner_frame = ttk.Frame(tests_canvas)

        tests_inner_frame.bind(
            "<Configure>",
            lambda e: tests_canvas.configure(scrollregion=tests_canvas.bbox("all"))
        )

        tests_canvas.create_window((0, 0), window=tests_inner_frame, anchor="nw")
        tests_canvas.configure(yscrollcommand=tests_scrollbar.set)

        # Pack canvas and scrollbar
        tests_canvas.pack(side="left", fill="both", expand=True)
        tests_scrollbar.pack(side="right", fill="y")

        # Benchmark test checkboxes
        self.benchmark_vars = {}
        benchmark_tests = [
            ('cpu_single_core', 'CPU Single-Core Performance', 'Test single-threaded CPU performance'),
            ('cpu_multi_core', 'CPU Multi-Core Performance', 'Test multi-threaded CPU performance'),
            ('memory_bandwidth', 'Memory Bandwidth', 'Test memory read/write bandwidth'),
            ('disk_speed', 'Disk I/O Speed', 'Test disk read/write performance'),
            ('data_processing', 'Data Processing Speed', 'Test data processing performance'),
            ('ui_responsiveness', 'UI Responsiveness', 'Test interface response times'),
        ]

        for test_id, test_name, description in benchmark_tests:
            test_frame = ttk.Frame(tests_inner_frame)
            test_frame.pack(fill=tk.X, pady=2)

            self.benchmark_vars[test_id] = tk.BooleanVar(value=True)  # Default all selected
            ttk.Checkbutton(test_frame, variable=self.benchmark_vars[test_id]).pack(side=tk.LEFT, padx=(0, 5))

            text_frame = ttk.Frame(test_frame)
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Label(text_frame, text=test_name, font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
            ttk.Label(text_frame, text=description, font=('TkDefaultFont', 8)).pack(anchor=tk.W)

        # Progress display
        progress_frame = ttk.LabelFrame(benchmark_frame, text="Benchmark Progress", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(anchor=tk.W)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))

        # Current results display
        results_frame = ttk.LabelFrame(benchmark_frame, text="Live Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Text area for live results
        self.results_text = tk.Text(results_frame, height=15, wrap=tk.WORD, font=('Courier New', 9))
        results_scrollbar = ttk.Scrollbar(results_frame, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)

        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_system_tab(self):
        """Create the system information display."""
        system_frame = ttk.Frame(self.notebook)
        self.notebook.add(system_frame, text="💻 System Information")

        # System specs display
        specs_frame = ttk.LabelFrame(system_frame, text="Hardware Specifications", padding=10)
        specs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.system_info_text = tk.Text(specs_frame, height=25, wrap=tk.WORD, font=('Courier New', 9))
        system_scrollbar = ttk.Scrollbar(specs_frame, command=self.system_info_text.yview)
        self.system_info_text.configure(yscrollcommand=system_scrollbar.set)

        self.system_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        system_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Refresh button
        ttk.Button(system_frame, text="🔄 Refresh System Info",
                  command=self._update_system_info).pack(pady=5)

        # Initial system info update
        self._update_system_info()

    def _create_results_tab(self):
        """Create the benchmark results display tab."""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="📊 Results Summary")

        # Results overview
        overview_frame = ttk.LabelFrame(results_frame, text="Benchmark Results Overview", padding=10)
        overview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Score display
        score_frame = ttk.Frame(overview_frame)
        score_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(score_frame, text="Overall Performance Score:", font=('TkDefaultFont', 12, 'bold')).pack(side=tk.LEFT)
        self.overall_score_var = tk.StringVar(value="--")
        ttk.Label(score_frame, textvariable=self.overall_score_var, font=('TkDefaultFont', 12, 'bold'),
                 foreground='blue').pack(side=tk.LEFT, padx=(10, 0))

        # Results text area
        results_text_frame = ttk.Frame(overview_frame)
        results_text_frame.pack(fill=tk.BOTH, expand=True)

        self.summary_text = tk.Text(results_text_frame, height=20, wrap=tk.WORD, font=('Courier New', 9))
        summary_scrollbar = ttk.Scrollbar(results_text_frame, command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)

        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons
        actions_frame = ttk.Frame(results_frame)
        actions_frame.pack(fill=tk.X)

        ttk.Button(actions_frame, text="📊 Generate Report",
                  command=self._generate_report).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(actions_frame, text="📋 Copy to Clipboard",
                  command=self._copy_to_clipboard).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(actions_frame, text="📤 Export JSON",
                  command=self._export_json).pack(side=tk.LEFT)

    def _run_benchmark(self):
        """Run the selected benchmark tests."""
        if self.benchmark_running:
            return

        selected_tests = [test_id for test_id, var in self.benchmark_vars.items() if var.get()]

        if not selected_tests:
            messagebox.showwarning("No Tests Selected", "Please select at least one benchmark test to run.")
            return

        # Clear previous results
        self.results_text.delete(1.0, tk.END)
        self.benchmark_results = {}
        self.progress_bar['value'] = 0
        self.progress_var.set("Starting benchmark...")

        # Disable button and start benchmark
        self.run_benchmark_btn.config(state='disabled')

        self.benchmark_thread = threading.Thread(target=self._execute_benchmarks, args=(selected_tests,))
        self.benchmark_thread.daemon = True
        self.benchmark_thread.start()

    def _stop_benchmark(self):
        """Stop the running benchmark."""
        self.benchmark_running = False
        self.progress_var.set("Stopping benchmark...")
        self.run_benchmark_btn.config(state='normal')

    def _execute_benchmarks(self, test_ids):
        """Execute the selected benchmark tests."""
        self.benchmark_running = True

        try:
            total_tests = len(test_ids)
            completed_tests = 0

            for test_id in test_ids:
                if not self.benchmark_running:
                    break

                self.progress_var.set(f"Running {test_id}...")
                self.results_text.insert(tk.END, f"\n🔬 Running {test_id}...\n")
                self.results_text.see(tk.END)

                try:
                    result = self._run_single_benchmark(test_id)
                    self.benchmark_results[test_id] = result

                    # Display result
                    if isinstance(result, dict):
                        self.results_text.insert(tk.END, f"✅ {test_id}: {result.get('score', 'N/A')} points\n")
                        for key, value in result.items():
                            if key != 'score':
                                self.results_text.insert(tk.END, f"   {key}: {value}\n")
                    else:
                        self.results_text.insert(tk.END, f"✅ {test_id}: {result}\n")

                except Exception as e:
                    self.results_text.insert(tk.END, f"❌ {test_id}: Failed - {e}\n")
                    self.logger.error(f"Benchmark {test_id} failed: {e}")

                completed_tests += 1
                progress = int((completed_tests / total_tests) * 100)
                self.progress_bar['value'] = progress

                self.results_text.see(tk.END)
                time.sleep(0.1)  # Small delay for UI responsiveness

            if self.benchmark_running:
                self.progress_var.set("Benchmark completed!")
                self._update_results_summary()
            else:
                self.progress_var.set("Benchmark stopped")

        except Exception as e:
            self.progress_var.set(f"Error: {e}")
            self.logger.error(f"Error during benchmarking: {e}")
        finally:
            self.benchmark_running = False
            if self.window:
                self.window.after(0, lambda: self.run_benchmark_btn.config(state='normal'))

    def _run_single_benchmark(self, test_id):
        """Run a single benchmark test."""
        if test_id == 'cpu_single_core':
            return self._benchmark_cpu_single_core()
        elif test_id == 'cpu_multi_core':
            return self._benchmark_cpu_multi_core()
        elif test_id == 'memory_bandwidth':
            return self._benchmark_memory_bandwidth()
        elif test_id == 'disk_speed':
            return self._benchmark_disk_speed()
        elif test_id == 'data_processing':
            return self._benchmark_data_processing()
        elif test_id == 'ui_responsiveness':
            return self._benchmark_ui_responsiveness()
        else:
            return {"score": 0, "error": "Unknown test"}

    def _benchmark_cpu_single_core(self):
        """Benchmark single-core CPU performance."""
        try:
            # Simple CPU benchmark using prime number calculation
            start_time = time.time()

            primes = []
            num = 2
            while len(primes) < 1000:  # Find first 1000 primes
                is_prime = True
                for prime in primes:
                    if prime * prime > num:
                        break
                    if num % prime == 0:
                        is_prime = False
                        break
                if is_prime:
                    primes.append(num)
                num += 1

            end_time = time.time()
            duration = end_time - start_time

            # Calculate score (lower time = higher score)
            score = max(0, int(1000 / duration))

            return {
                "score": score,
                "duration": ".2f",
                "primes_found": len(primes)
            }
        except Exception as e:
            return {"score": 0, "error": str(e)}

    def _benchmark_cpu_multi_core(self):
        """Benchmark multi-core CPU performance."""
        try:
            import multiprocessing
            from concurrent.futures import ThreadPoolExecutor

            def cpu_intensive_task(n):
                result = 0
                for i in range(n):
                    result += i * i
                return result

            start_time = time.time()

            # Use thread pool for CPU-bound tasks
            with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
                futures = [executor.submit(cpu_intensive_task, 100000) for _ in range(multiprocessing.cpu_count())]
                results = [future.result() for future in futures]

            end_time = time.time()
            duration = end_time - start_time

            score = max(0, int(1000 / duration))

            return {
                "score": score,
                "duration": ".2f",
                "cores_used": multiprocessing.cpu_count(),
                "total_calculations": sum(results)
            }
        except Exception as e:
            return {"score": 0, "error": str(e)}

    def _benchmark_memory_bandwidth(self):
        """Benchmark memory bandwidth."""
        try:
            # Simple memory bandwidth test
            size = 10000000  # 10 million elements

            # Write test
            start_time = time.time()
            data = [i for i in range(size)]
            write_time = time.time() - start_time

            # Read test
            start_time = time.time()
            total = sum(data)
            read_time = time.time() - start_time

            # Calculate bandwidth (rough estimate)
            data_size_mb = (size * 8) / (1024 * 1024)  # Assume 8 bytes per element
            total_time = write_time + read_time
            bandwidth_mbps = data_size_mb / total_time if total_time > 0 else 0

            score = max(0, int(bandwidth_mbps * 10))

            return {
                "score": score,
                "write_time": ".3f",
                "read_time": ".3f",
                "bandwidth": ".1f",
                "data_size_mb": ".1f"
            }
        except Exception as e:
            return {"score": 0, "error": str(e)}

    def _benchmark_disk_speed(self):
        """Benchmark disk I/O speed."""
        try:
            import tempfile
            import os

            # Test file operations
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_file = f.name
                data = b"x" * (1024 * 1024)  # 1MB of data

                # Write test
                start_time = time.time()
                for _ in range(10):  # Write 10MB
                    f.write(data)
                f.flush()
                write_time = time.time() - start_time

                # Read test
                f.seek(0)
                start_time = time.time()
                read_data = f.read()
                read_time = time.time() - start_time

            # Cleanup
            try:
                os.unlink(temp_file)
            except:
                pass

            # Calculate speeds
            data_size_mb = 10
            write_speed = data_size_mb / write_time if write_time > 0 else 0
            read_speed = data_size_mb / read_time if read_time > 0 else 0

            avg_speed = (write_speed + read_speed) / 2
            score = max(0, int(avg_speed * 50))

            return {
                "score": score,
                "write_speed": ".1f",
                "read_speed": ".1f",
                "avg_speed": ".1f",
                "test_file_size_mb": data_size_mb
            }
        except Exception as e:
            return {"score": 0, "error": str(e)}

    def _benchmark_data_processing(self):
        """Benchmark data processing performance."""
        try:
            import pandas as pd
            import numpy as np

            # Generate test data similar to the application
            start_time = time.time()
            data_size = 50000

            # Create sample data
            data = {
                'Tender ID': range(data_size),
                'Title': [f'Tender {i}' for i in range(data_size)],
                'Department': np.random.choice(['IT', 'Finance', 'HR', 'Operations'], data_size),
                'Value': np.random.uniform(1000, 1000000, data_size),
                'Closing Date': pd.date_range('2023-01-01', periods=data_size, freq='1H')[:data_size]
            }

            df = pd.DataFrame(data)

            # Perform typical operations
            operations_start = time.time()

            # Filter operations
            filtered = df[df['Value'] > 50000]

            # Group and aggregate
            grouped = df.groupby('Department')['Value'].agg(['sum', 'mean', 'count'])

            # Sort operations
            sorted_df = df.sort_values(['Value', 'Closing Date'], ascending=[False, True])

            operations_time = time.time() - operations_start
            total_time = time.time() - start_time

            operations_per_sec = len(df) / operations_time if operations_time > 0 else 0
            score = max(0, int(operations_per_sec / 10))

            return {
                "score": score,
                "total_time": ".2f",
                "operations_time": ".3f",
                "records_processed": len(df),
                "operations_per_sec": ".0f"
            }
        except Exception as e:
            return {"score": 0, "error": str(e)}

    def _benchmark_ui_responsiveness(self):
        """Benchmark UI responsiveness."""
        try:
            import psutil
            import os

            # Measure current system responsiveness
            start_time = time.time()

            # Quick system checks
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk_usage = psutil.disk_usage('/')

            # Simulate UI operations
            ui_operations = []
            for i in range(10):
                op_start = time.time()
                # Small computation
                result = sum(range(10000))
                ui_operations.append(time.time() - op_start)

            total_time = time.time() - start_time
            avg_ui_operation_time = sum(ui_operations) / len(ui_operations)

            # Calculate responsiveness score
            base_score = 100
            cpu_penalty = cpu_usage * 0.5
            memory_penalty = (memory.percent / 100) * 30
            ui_penalty = min(20, avg_ui_operation_time * 1000)  # Convert to milliseconds

            score = max(0, int(base_score - cpu_penalty - memory_penalty - ui_penalty))

            return {
                "score": score,
                "cpu_usage": ".1f",
                "memory_usage": ".1f",
                "disk_usage": ".1f",
                "avg_ui_operation_ms": ".2f"
            }
        except Exception as e:
            return {"score": 0, "error": str(e)}

    def _update_results_summary(self):
        """Update the results summary tab."""
        if not self.benchmark_results:
            return

        # Calculate overall score
        total_score = 0
        valid_tests = 0

        summary_text = "🏆 BENCHMARK RESULTS SUMMARY\n"
        summary_text += "=" * 50 + "\n\n"
        summary_text += "Test Results:\n"
        summary_text += "-" * 20 + "\n"

        for test_id, result in self.benchmark_results.items():
            if isinstance(result, dict) and 'score' in result:
                score = result['score']
                total_score += score
                valid_tests += 1
                summary_text += f"{test_id}: {score} points\n"

                # Add additional details
                for key, value in result.items():
                    if key != 'score':
                        summary_text += f"  {key}: {value}\n"
                summary_text += "\n"

        # Calculate average score
        avg_score = total_score / valid_tests if valid_tests > 0 else 0

        # Performance rating
        if avg_score >= 800:
            rating = "Excellent"
        elif avg_score >= 600:
            rating = "Good"
        elif avg_score >= 400:
            rating = "Average"
        elif avg_score >= 200:
            rating = "Below Average"
        else:
            rating = "Poor"

        summary_text += f"\nOverall Performance:\n"
        summary_text += f"Average Score: {avg_score:.1f} points\n"
        summary_text += f"Rating: {rating}\n"
        summary_text += f"Tests Completed: {valid_tests}\n"

        # Update the summary text widget
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, summary_text)

        # Update overall score display
        self.overall_score_var.set(f"{avg_score:.1f} ({rating})")

    def _update_system_info(self):
        """Update the system information display."""
        try:
            if not self.performance_tester:
                self.system_info_text.delete(1.0, tk.END)
                self.system_info_text.insert(tk.END, "Performance tester not available.")
                return

            sys_info = self.performance_tester.get_system_info()

            self.system_info_text.delete(1.0, tk.END)

            # Format system information
            info_text = "🖥️ SYSTEM HARDWARE SPECIFICATIONS\n"
            info_text += "=" * 50 + "\n\n"

            # Hardware Information
            info_text += "PROCESSOR:\n"
            info_text += f"  Model: {sys_info.get('cpu_model', 'Unknown')}\n"
            info_text += f"  Cores: {sys_info['cpu_count']} physical, {sys_info['cpu_count_logical']} logical\n"
            if 'cpu_freq_mhz' in sys_info:
                info_text += f"  Frequency: {sys_info['cpu_freq_mhz']:.0f} MHz\n"

            info_text += "\nMEMORY:\n"
            info_text += f"  Total RAM: {sys_info['memory_total_gb']:.1f} GB\n"
            info_text += f"  Available RAM: {sys_info['memory_available_gb']:.1f} GB\n"

            info_text += "\nSTORAGE:\n"
            info_text += f"  Total Disk: {sys_info['disk_total_gb']:.1f} GB\n"
            info_text += f"  Free Disk: {sys_info['disk_free_gb']:.1f} GB\n"

            # GPU Information
            if 'gpu_info' in sys_info:
                info_text += "\nGRAPHICS:\n"
                info_text += f"  {sys_info['gpu_info']}\n"

            # Software Information
            info_text += "\nSOFTWARE:\n"
            info_text += f"  Python: {sys_info['python_version']}\n"
            info_text += f"  OS: {sys_info.get('os_name', 'Unknown')} {sys_info.get('os_release', 'Unknown')}\n\n"

            # Performance Notes
            info_text += "PERFORMANCE NOTES:\n"
            if sys_info['cpu_count'] >= 4:
                info_text += "  ✅ Good CPU core count for data processing\n"
            else:
                info_text += "  ⚠️  Limited CPU cores may slow data processing\n"

            if sys_info['memory_total_gb'] >= 8:
                info_text += "  ✅ Sufficient RAM for typical datasets\n"
            else:
                info_text += "  ⚠️  Limited RAM may constrain dataset size\n"

            info_text += f"  💡 Expected performance: Good for datasets up to {sys_info['cpu_count'] * 50000:,} records\n"

            self.system_info_text.insert(tk.END, info_text)

        except Exception as e:
            self.system_info_text.delete(1.0, tk.END)
            self.system_info_text.insert(tk.END, f"Error retrieving system information: {e}")
            self.logger.error(f"Error updating system info in benchmark window: {e}")

    def _save_results(self):
        """Save benchmark results to a file."""
        try:
            import json
            from datetime import datetime

            if not self.benchmark_results:
                messagebox.showwarning("No Results", "No benchmark results to save.")
                return

            # Add metadata
            results_data = {
                "timestamp": datetime.now().isoformat(),
                "system_info": self.performance_tester.get_system_info() if self.performance_tester else {},
                "benchmark_results": self.benchmark_results
            }

            file_path = filedialog.asksaveasfilename(
                title="Save Benchmark Results",
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                initialfile=f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(results_data, f, indent=2, ensure_ascii=False)

                messagebox.showinfo("Results Saved", f"Benchmark results saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save results: {str(e)}")
            self.logger.error(f"Error saving benchmark results: {e}")

    def _generate_report(self):
        """Generate a comprehensive benchmark report."""
        try:
            from datetime import datetime

            if not self.benchmark_results:
                messagebox.showwarning("No Results", "No benchmark results to report.")
                return

            # Get system information
            system_info = self.performance_tester.get_system_info() if self.performance_tester else {}

            # Calculate scores
            total_score = sum(result.get('score', 0) for result in self.benchmark_results.values() if isinstance(result, dict))
            avg_score = total_score / len(self.benchmark_results) if self.benchmark_results else 0

            # Determine rating
            if avg_score >= 800:
                rating = "Excellent"
            elif avg_score >= 600:
                rating = "Good"
            elif avg_score >= 400:
                rating = "Average"
            elif avg_score >= 200:
                rating = "Below Average"
            else:
                rating = "Needs Improvement"

            # Generate report content
            report = f"""# 🚀 Performance Benchmark Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 System Overview
- **CPU:** {system_info.get('cpu_model', 'Unknown')}
- **Cores:** {system_info.get('cpu_count', 'Unknown')} physical
- **RAM:** {system_info.get('memory_total_gb', 'Unknown')} GB
- **Storage:** {system_info.get('disk_total_gb', 'Unknown')} GB total

## 🏆 Overall Performance Score
**{avg_score:.1f} points - {rating}**

## 📈 Benchmark Results

"""

            # Add individual test results
            for test_id, result in self.benchmark_results.items():
                if isinstance(result, dict):
                    report += f"### {test_id.replace('_', ' ').title()}\n"
                    report += f"**Score:** {result.get('score', 'N/A')} points\n\n"
                    for key, value in result.items():
                        if key != 'score':
                            report += f"- **{key.replace('_', ' ').title()}:** {value}\n"
                    report += "\n"

            # Add recommendations
            report += "## 💡 Recommendations\n\n"

            if avg_score >= 600:
                report += "**Excellent performance!** Your system handles data processing tasks very well.\n\n"
            elif avg_score >= 400:
                report += "**Good performance.** Your system performs adequately for typical data processing tasks.\n\n"
            else:
                report += "**Performance could be improved.** Consider the following:\n"
                report += "- Upgrade RAM for better data processing\n"
                report += "- Consider faster storage (SSD/NVMe)\n"
                report += "- More CPU cores would help with parallel processing\n\n"

            # Save report
            file_path = filedialog.asksaveasfilename(
                title="Save Benchmark Report",
                defaultextension=".md",
                filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")],
                initialfile=f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)

                messagebox.showinfo("Report Saved", f"Benchmark report saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Report Error", f"Failed to generate report: {str(e)}")
            self.logger.error(f"Error generating benchmark report: {e}")

    def _copy_to_clipboard(self):
        """Copy results summary to clipboard."""
        try:
            results_text = self.summary_text.get(1.0, tk.END).strip()
            if results_text and self.window:
                self.window.clipboard_clear()
                self.window.clipboard_append(results_text)
                messagebox.showinfo("Copied", "Results copied to clipboard!")
            else:
                messagebox.showwarning("No Content", "No results to copy.")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy to clipboard: {str(e)}")

    def _export_json(self):
        """Export results as JSON."""
        self._save_results()  # Reuse the save functionality

    def _on_close(self):
        """Handle window close event."""
        try:
            if self.window:
                # Stop any running benchmarks
                self._stop_benchmark()

                # Destroy the window
                self.window.destroy()
                self.window = None

            self.logger.info("Benchmark window closed")
        except Exception as e:
            self.logger.warning(f"Error closing benchmark window: {e}")
