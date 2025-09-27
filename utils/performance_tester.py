"""
Performance Testing Utilities for Tender Management Utility v3

This module provides comprehensive performance testing capabilities to benchmark
various operations in the application, including data loading, filtering, chart
generation, and export operations.

Usage:
    from utils.performance_tester import PerformanceTester

    tester = PerformanceTester()
    with tester.time_operation("data_loading"):
        # Your code here
        pass

    # Get results
    results = tester.get_results()
    print(results)
"""

import time
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable
from contextlib import contextmanager
import logging
import pandas as pd
from functools import wraps

logger = logging.getLogger(__name__)

class PerformanceTester:
    """
    Comprehensive performance testing utility for benchmarking application operations.

    Features:
    - Time measurement with high precision
    - Memory usage tracking
    - CPU usage monitoring
    - Operation statistics
    - Thread-safe operation
    """

    def __init__(self):
        self.results = {}
        self.current_operations = {}
        self._lock = threading.Lock()

    @contextmanager
    def time_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to time an operation and track performance metrics.

        Args:
            operation_name: Name of the operation being timed
            metadata: Additional metadata to store with the operation
        """
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent(interval=None)

        operation_data = {
            'start_time': start_time,
            'start_memory': start_memory,
            'start_cpu': start_cpu,
            'metadata': metadata or {},
            'thread_id': threading.get_ident()
        }

        with self._lock:
            self.current_operations[operation_name] = operation_data

        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            end_cpu = psutil.cpu_percent(interval=None)

            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            cpu_delta = end_cpu - start_cpu

            result = {
                'duration_seconds': duration,
                'duration_ms': duration * 1000,
                'memory_start_mb': start_memory,
                'memory_end_mb': end_memory,
                'memory_delta_mb': memory_delta,
                'cpu_start_percent': start_cpu,
                'cpu_end_percent': end_cpu,
                'cpu_delta_percent': cpu_delta,
                'timestamp': time.time(),
                'metadata': metadata or {}
            }

            with self._lock:
                if operation_name in self.results:
                    self.results[operation_name].append(result)
                else:
                    self.results[operation_name] = [result]

                if operation_name in self.current_operations:
                    del self.current_operations[operation_name]

            logger.info(f"Operation '{operation_name}' completed: {duration:.2f}s, "
                       f"Memory: {memory_delta:+.1f}MB, CPU: {cpu_delta:+.1f}%")

    def time_function(self, operation_name: Optional[str] = None):
        """
        Decorator to time a function automatically.

        Args:
            operation_name: Name for the operation (defaults to function name)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                name = operation_name or f"{func.__module__}.{func.__name__}"
                with self.time_operation(name, {'function': func.__name__, 'args_count': len(args), 'kwargs_count': len(kwargs)}):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def benchmark_data_loading(self, file_paths: List[str], iterations: int = 3) -> Dict[str, Any]:
        """
        Benchmark data loading performance with multiple iterations.

        Args:
            file_paths: List of file paths to load
            iterations: Number of times to run the benchmark

        Returns:
            Dictionary with benchmark results
        """
        from core.data_processor import TenderDataProcessor
        from core.config_manager import GlobalConfig

        results = {
            'operation': 'data_loading_benchmark',
            'iterations': iterations,
            'file_paths': file_paths,
            'runs': []
        }

        config = GlobalConfig()

        for i in range(iterations):
            processor = TenderDataProcessor(config)

            with self.time_operation(f"data_loading_run_{i+1}",
                                   {'run': i+1, 'file_count': len(file_paths)}):
                success, message = processor.load_data_from_files(file_paths)

            run_result = self.results[f"data_loading_run_{i+1}"][-1].copy()
            run_result['success'] = success
            run_result['message'] = message
            run_result['records_loaded'] = len(processor.raw_data) if success else 0
            results['runs'].append(run_result)

        # Calculate averages
        durations = [run['duration_seconds'] for run in results['runs']]
        memory_deltas = [run['memory_delta_mb'] for run in results['runs']]

        results['average_duration'] = sum(durations) / len(durations)
        results['average_memory_delta'] = sum(memory_deltas) / len(memory_deltas)
        results['min_duration'] = min(durations)
        results['max_duration'] = max(durations)

        return results

    def benchmark_filtering(self, data_processor, filter_configs: List[Dict[str, Any]], iterations: int = 5) -> Dict[str, Any]:
        """
        Benchmark filtering performance with different filter configurations.

        Args:
            data_processor: TenderDataProcessor instance with loaded data
            filter_configs: List of filter configurations to test
            iterations: Number of iterations per filter config

        Returns:
            Dictionary with benchmark results
        """
        results = {
            'operation': 'filtering_benchmark',
            'iterations': iterations,
            'filter_configs': filter_configs,
            'runs': []
        }

        for i, filter_config in enumerate(filter_configs):
            for j in range(iterations):
                with self.time_operation(f"filtering_config_{i+1}_run_{j+1}",
                                       {'config': filter_config, 'run': j+1}):
                    data_processor.apply_filters(filter_config)

                run_result = self.results[f"filtering_config_{i+1}_run_{j+1}"][-1].copy()
                run_result['config_index'] = i
                run_result['filter_config'] = filter_config
                run_result['results_count'] = len(data_processor.filtered_data)
                results['runs'].append(run_result)

        return results

    def benchmark_chart_generation(self, chart_types: Optional[List[str]] = None, iterations: int = 3) -> Dict[str, Any]:
        """
        Benchmark chart generation performance.

        Args:
            chart_types: List of chart types to test (department, monthly, etc.)
            iterations: Number of iterations per chart type

        Returns:
            Dictionary with benchmark results
        """
        if chart_types is None:
            chart_types = ['department_distribution', 'monthly_trends']

        results = {
            'operation': 'chart_generation_benchmark',
            'iterations': iterations,
            'chart_types': chart_types,
            'runs': []
        }

        # Import here to avoid circular imports
        try:
            from ui.charts_window import ChartsWindow
            import tkinter as tk

            # Create a minimal Tkinter root for testing
            root = tk.Tk()
            root.withdraw()  # Hide the window

            for chart_type in chart_types:
                for i in range(iterations):
                    with self.time_operation(f"chart_{chart_type}_run_{i+1}",
                                           {'chart_type': chart_type, 'run': i+1}):
                        # Simulate chart generation - this would need actual implementation
                        # For now, just simulate the time it takes
                        time.sleep(0.1)  # Placeholder

                    run_result = self.results[f"chart_{chart_type}_run_{i+1}"][-1].copy()
                    run_result['chart_type'] = chart_type
                    results['runs'].append(run_result)

            root.destroy()

        except ImportError as e:
            logger.warning(f"Chart benchmarking not available: {e}")
            results['error'] = str(e)

        return results

    def benchmark_export_operations(self, data_processor, export_formats: Optional[List[str]] = None, iterations: int = 3) -> Dict[str, Any]:
        """
        Benchmark export operations performance.

        Args:
            data_processor: TenderDataProcessor with data to export
            export_formats: List of export formats to test
            iterations: Number of iterations per format

        Returns:
            Dictionary with benchmark results
        """
        if export_formats is None:
            export_formats = ['excel', 'csv']

        results = {
            'operation': 'export_benchmark',
            'iterations': iterations,
            'export_formats': export_formats,
            'runs': []
        }

        import tempfile
        import os

        for export_format in export_formats:
            for i in range(iterations):
                with tempfile.NamedTemporaryFile(suffix=f'.{export_format}', delete=False) as tmp_file:
                    temp_path = tmp_file.name

                try:
                    with self.time_operation(f"export_{export_format}_run_{i+1}",
                                           {'format': export_format, 'run': i+1}):
                        # Simulate export operation
                        if export_format == 'excel':
                            try:
                                data_processor.filtered_data.to_excel(temp_path, index=False, engine='openpyxl')
                            except ImportError:
                                logger.warning("openpyxl not installed, skipping Excel export test")
                                continue
                        elif export_format == 'csv':
                            data_processor.filtered_data.to_csv(temp_path, index=False)

                    run_result = self.results[f"export_{export_format}_run_{i+1}"][-1].copy()
                    run_result['format'] = export_format
                    run_result['file_size_kb'] = os.path.getsize(temp_path) / 1024
                    run_result['records_exported'] = len(data_processor.filtered_data)
                    results['runs'].append(run_result)

                finally:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)

        return results

    def benchmark_data_analysis(self, data_processor, analysis_types: Optional[List[str]] = None, iterations: int = 3) -> Dict[str, Any]:
        """
        Benchmark data analysis operations performance.

        Args:
            data_processor: TenderDataProcessor with loaded data
            analysis_types: List of analysis types to test
            iterations: Number of iterations per analysis type

        Returns:
            Dictionary with benchmark results
        """
        if analysis_types is None:
            analysis_types = ['department_summary', 'value_analysis', 'date_analysis', 'status_summary']

        results = {
            'operation': 'data_analysis_benchmark',
            'iterations': iterations,
            'analysis_types': analysis_types,
            'runs': []
        }

        for analysis_type in analysis_types:
            for i in range(iterations):
                with self.time_operation(f"analysis_{analysis_type}_run_{i+1}",
                                       {'analysis_type': analysis_type, 'run': i+1}):
                    if analysis_type == 'department_summary':
                        # Group by department and count
                        if hasattr(data_processor, 'filtered_data') and not data_processor.filtered_data.empty:
                            dept_counts = data_processor.filtered_data.groupby('Department').size()
                        else:
                            dept_counts = data_processor.raw_data.groupby('Department').size()

                    elif analysis_type == 'value_analysis':
                        # Value statistics
                        if hasattr(data_processor, 'filtered_data') and not data_processor.filtered_data.empty:
                            value_stats = data_processor.filtered_data['Value'].describe()
                        else:
                            value_stats = data_processor.raw_data['Value'].describe()

                    elif analysis_type == 'date_analysis':
                        # Date-based analysis
                        if hasattr(data_processor, 'filtered_data') and not data_processor.filtered_data.empty:
                            date_analysis = data_processor.filtered_data.groupby(
                                data_processor.filtered_data['Closing Date'].dt.month
                            ).size()
                        else:
                            date_analysis = data_processor.raw_data.groupby(
                                data_processor.raw_data['Closing Date'].dt.month
                            ).size()

                    elif analysis_type == 'status_summary':
                        # Status distribution
                        if hasattr(data_processor, 'filtered_data') and not data_processor.filtered_data.empty:
                            status_counts = data_processor.filtered_data.groupby('Status').size()
                        else:
                            status_counts = data_processor.raw_data.groupby('Status').size()

                run_result = self.results[f"analysis_{analysis_type}_run_{i+1}"][-1].copy()
                run_result['analysis_type'] = analysis_type
                run_result['records_analyzed'] = len(data_processor.filtered_data) if hasattr(data_processor, 'filtered_data') else len(data_processor.raw_data)
                results['runs'].append(run_result)

        return results

    def benchmark_query_performance(self, data_processor, query_complexity: str = 'mixed', iterations: int = 5) -> Dict[str, Any]:
        """
        Benchmark query performance with different complexity levels.

        Args:
            data_processor: TenderDataProcessor with loaded data
            query_complexity: Complexity level ('simple', 'medium', 'complex', 'mixed')
            iterations: Number of iterations per query type

        Returns:
            Dictionary with benchmark results
        """
        results = {
            'operation': 'query_performance_benchmark',
            'query_complexity': query_complexity,
            'iterations': iterations,
            'runs': []
        }

        # Define query scenarios based on complexity
        if query_complexity == 'simple':
            queries = [
                {'Department': 'IT'},
                {'Status': 'Live'},
                {'GlobalSearch': 'software'}
            ]
        elif query_complexity == 'medium':
            queries = [
                {'Department': 'IT, Finance', 'DepartmentOperator': 'OR'},
                {'GlobalSearch': 'software, license', 'GlobalSearchOperator': 'AND'},
                {'DateFilter': {'type': 'next_7_days'}}
            ]
        elif query_complexity == 'complex':
            queries = [
                {
                    'Department': 'IT, Finance, Operations',
                    'DepartmentOperator': 'OR',
                    'GlobalSearch': 'maintenance, service',
                    'GlobalSearchOperator': 'OR',
                    'DateFilter': {'type': 'next_30_days'}
                }
            ]
        else:  # mixed
            queries = [
                {'Department': 'IT'},
                {'Department': 'IT, Finance', 'DepartmentOperator': 'OR', 'DateFilter': {'type': 'live'}},
                {'GlobalSearch': 'software, license', 'GlobalSearchOperator': 'AND'},
                {
                    'Department': 'Finance, Procurement',
                    'GlobalSearch': 'maintenance, service',
                    'DateFilter': {'type': 'next_30_days'}
                }
            ]

        for i, query in enumerate(queries):
            for j in range(iterations):
                with self.time_operation(f"query_complexity_{query_complexity}_q{i+1}_run_{j+1}",
                                       {'query': query, 'complexity': query_complexity, 'run': j+1}):
                    data_processor.apply_filters(query)

                run_result = self.results[f"query_complexity_{query_complexity}_q{i+1}_run_{j+1}"][-1].copy()
                run_result['query_config'] = query
                run_result['results_count'] = len(data_processor.filtered_data)
                run_result['query_complexity'] = query_complexity
                results['runs'].append(run_result)

        return results

    def benchmark_memory_usage_analysis(self, data_processor, operations: Optional[List[str]] = None, iterations: int = 3) -> Dict[str, Any]:
        """
        Benchmark memory usage during analysis operations.

        Args:
            data_processor: TenderDataProcessor with loaded data
            operations: List of operations to test memory usage for
            iterations: Number of iterations per operation

        Returns:
            Dictionary with benchmark results
        """
        if operations is None:
            operations = ['load_data', 'apply_filters', 'group_analysis', 'sort_data']

        results = {
            'operation': 'memory_usage_analysis_benchmark',
            'iterations': iterations,
            'operations': operations,
            'runs': []
        }

        for operation in operations:
            for i in range(iterations):
                with self.time_operation(f"memory_{operation}_run_{i+1}",
                                       {'operation': operation, 'run': i+1}):
                    if operation == 'load_data':
                        # Memory usage during data loading (already loaded, but simulate)
                        _ = len(data_processor.raw_data)

                    elif operation == 'apply_filters':
                        # Apply a complex filter
                        data_processor.apply_filters({
                            'Department': 'IT, Finance',
                            'GlobalSearch': 'software',
                            'DateFilter': {'type': 'live'}
                        })

                    elif operation == 'group_analysis':
                        # Perform grouping analysis
                        if not data_processor.filtered_data.empty:
                            grouped = data_processor.filtered_data.groupby(['Department', 'Status']).size()
                        else:
                            grouped = data_processor.raw_data.groupby(['Department', 'Status']).size()

                    elif operation == 'sort_data':
                        # Sort by value
                        if not data_processor.filtered_data.empty:
                            sorted_data = data_processor.filtered_data.sort_values('Value', ascending=False)
                        else:
                            sorted_data = data_processor.raw_data.sort_values('Value', ascending=False)

                run_result = self.results[f"memory_{operation}_run_{i+1}"][-1].copy()
                run_result['operation'] = operation
                run_result['data_size'] = len(data_processor.filtered_data) if hasattr(data_processor, 'filtered_data') else len(data_processor.raw_data)
                results['runs'].append(run_result)

        return results

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get detailed system information for performance context.

        Returns:
            Dictionary with detailed system information
        """
        import platform
        import subprocess

        # Basic system info
        info = {
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
            'disk_total_gb': psutil.disk_usage('/').total / 1024 / 1024 / 1024,
            'disk_free_gb': psutil.disk_usage('/').free / 1024 / 1024 / 1024,
            'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
            'platform': platform.platform(),
            'os_name': platform.system(),
            'os_version': platform.version(),
            'os_release': platform.release(),
            'architecture': platform.architecture()[0],
            'machine': platform.machine(),
            'processor': platform.processor() or 'Unknown'
        }

        # Try to get detailed CPU info
        try:
            if platform.system() == 'Windows':
                # Try PowerShell as alternative to wmic
                try:
                    result = subprocess.run(['powershell', '-Command', 'Get-WmiObject Win32_Processor | Select-Object -ExpandProperty Name'],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        info['cpu_model'] = result.stdout.strip()
                except:
                    # Fallback to registry query
                    try:
                        result = subprocess.run(['reg', 'query', 'HKEY_LOCAL_MACHINE\\HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0', '/v', 'ProcessorNameString'],
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            for line in result.stdout.split('\n'):
                                if 'ProcessorNameString' in line:
                                    parts = line.split('    ')
                                    if len(parts) > 1:
                                        info['cpu_model'] = parts[-1].strip()
                                    break
                    except:
                        pass
            else:
                # For other systems, try to get from /proc/cpuinfo or similar
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
                            if line.startswith('model name'):
                                info['cpu_model'] = line.split(':')[1].strip()
                                break
                except:
                    pass
        except:
            pass

        # Try to get GPU information
        try:
            if platform.system() == 'Windows':
                # Try PowerShell for GPU info
                try:
                    result = subprocess.run(['powershell', '-Command', 'Get-WmiObject Win32_VideoController | Select-Object -ExpandProperty Name'],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        gpu_names = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                        if gpu_names:
                            info['gpu_info'] = ', '.join(gpu_names)
                except:
                    pass
        except:
            pass

        # Try to get disk information
        try:
            if platform.system() == 'Windows':
                # Try PowerShell for disk info
                try:
                    result = subprocess.run(['powershell', '-Command', 'Get-PhysicalDisk | Select-Object -ExpandProperty Model'],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        disk_models = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                        if disk_models:
                            info['disk_model'] = ', '.join(disk_models)
                except:
                    pass
        except:
            pass

        # Get additional memory info
        try:
            vm = psutil.virtual_memory()
            info['memory_used_gb'] = vm.used / 1024 / 1024 / 1024
            info['memory_percent'] = vm.percent
        except:
            pass

        # Get CPU frequency if available
        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                info['cpu_freq_mhz'] = cpu_freq.current
                info['cpu_freq_max_mhz'] = cpu_freq.max
        except:
            pass

        return info

    def get_results(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance results for all operations or a specific operation.

        Args:
            operation_name: Specific operation to get results for (optional)

        Returns:
            Dictionary with performance results
        """
        with self._lock:
            if operation_name:
                return {
                    'operation': operation_name,
                    'results': self.results.get(operation_name, []),
                    'count': len(self.results.get(operation_name, [])),
                    'system_info': self.get_system_info()
                }
            else:
                return {
                    'all_operations': self.results,
                    'total_operations': len(self.results),
                    'system_info': self.get_system_info()
                }

    def clear_results(self):
        """Clear all stored performance results."""
        with self._lock:
            self.results.clear()
            self.current_operations.clear()

    def save_results_to_file(self, filename: str, operation_name: Optional[str] = None):
        """
        Save performance results to a JSON file.

        Args:
            filename: Path to save the results
            operation_name: Specific operation to save (optional)
        """
        import json
        results = self.get_results(operation_name)

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Performance results saved to {filename}")

    def print_summary(self, operation_name: Optional[str] = None):
        """
        Print a summary of performance results.

        Args:
            operation_name: Specific operation to summarize (optional)
        """
        results = self.get_results(operation_name)

        print("\n" + "="*60)
        print("PERFORMANCE TEST SUMMARY")
        print("="*60)

        if operation_name:
            print(f"Operation: {operation_name}")
            ops = results.get('results', [])
            if ops:
                durations = [op['duration_ms'] for op in ops]
                memory_deltas = [op['memory_delta_mb'] for op in ops]

                avg_duration = sum(durations) / len(durations)
                avg_memory = sum(memory_deltas) / len(memory_deltas)
                min_duration = min(durations)
                max_duration = max(durations)

                print(f"  Average Duration: {avg_duration:.2f}ms")
                print(f"  Average Memory Delta: {avg_memory:.1f}MB")
                print(f"  Min Duration: {min_duration:.1f}ms")
                print(f"  Max Duration: {max_duration:.1f}ms")
                print(f"  Total Runs: {len(ops)}")
        else:
            print(f"Total Operations Tested: {results['total_operations']}")
            for op_name, op_results in results['all_operations'].items():
                if op_results:
                    avg_duration = sum(r['duration_ms'] for r in op_results) / len(op_results)
                    print(f"  {op_name}: {avg_duration:.2f}ms avg")

        print("\nSystem Information:")
        sys_info = results['system_info']
        print(f"  CPU Cores: {sys_info['cpu_count']} physical, {sys_info['cpu_count_logical']} logical")
        print(f"  Memory: {sys_info['memory_total_gb']:.1f}GB total, {sys_info['memory_available_gb']:.1f}GB available")
        print(f"  Disk: {sys_info['disk_total_gb']:.1f}GB total, {sys_info['disk_free_gb']:.1f}GB free")
        print(f"  Python Version: {sys_info['python_version']}")
        print("="*60)


# Convenience functions for quick testing
def time_function(func_name: Optional[str] = None):
    """
    Decorator to easily time any function.

    Usage:
        @time_function()
        def my_function():
            pass
    """
    tester = PerformanceTester()
    return tester.time_function(func_name)

def benchmark_data_loading(file_paths: List[str], iterations: int = 3) -> Dict[str, Any]:
    """
    Quick function to benchmark data loading.

    Args:
        file_paths: List of file paths to test
        iterations: Number of benchmark iterations

    Returns:
        Benchmark results dictionary
    """
    tester = PerformanceTester()
    results = tester.benchmark_data_loading(file_paths, iterations)
    tester.print_summary()
    return results

def benchmark_filtering_scenarios(data_processor, scenarios: Optional[List[Dict[str, Any]]] = None, iterations: int = 5) -> Dict[str, Any]:
    """
    Quick function to benchmark common filtering scenarios.

    Args:
        data_processor: TenderDataProcessor with loaded data
        scenarios: List of filter scenarios to test
        iterations: Number of iterations per scenario

    Returns:
        Benchmark results dictionary
    """
    if scenarios is None:
        scenarios = [
            {'Department': 'IT', 'GlobalSearchOperator': 'OR'},
            {'GlobalSearch': 'software, license', 'GlobalSearchOperator': 'AND'},
            {'DateFilter': {'type': 'live'}},
            {'Department': 'HR, Finance', 'DepartmentOperator': 'OR', 'DateFilter': {'type': 'next_7_days'}}
        ]

    tester = PerformanceTester()
    results = tester.benchmark_filtering(data_processor, scenarios, iterations)
    tester.print_summary()
    return results

def benchmark_data_analysis_operations(data_processor, analysis_types: Optional[List[str]] = None, iterations: int = 3) -> Dict[str, Any]:
    """
    Quick function to benchmark data analysis operations.

    Args:
        data_processor: TenderDataProcessor with loaded data
        analysis_types: List of analysis types to test
        iterations: Number of iterations per analysis type

    Returns:
        Benchmark results dictionary
    """
    tester = PerformanceTester()
    results = tester.benchmark_data_analysis(data_processor, analysis_types, iterations)
    tester.print_summary()
    return results

def benchmark_query_complexity(data_processor, complexity_levels: Optional[List[str]] = None, iterations: int = 5) -> Dict[str, Any]:
    """
    Quick function to benchmark query performance at different complexity levels.

    Args:
        data_processor: TenderDataProcessor with loaded data
        complexity_levels: List of complexity levels ('simple', 'medium', 'complex', 'mixed')
        iterations: Number of iterations per complexity level

    Returns:
        Benchmark results dictionary
    """
    if complexity_levels is None:
        complexity_levels = ['simple', 'medium', 'complex']

    tester = PerformanceTester()
    all_results = {}

    for complexity in complexity_levels:
        results = tester.benchmark_query_performance(data_processor, complexity, iterations)
        all_results[complexity] = results

    tester.print_summary()
    return all_results

def benchmark_memory_operations(data_processor, operations: Optional[List[str]] = None, iterations: int = 3) -> Dict[str, Any]:
    """
    Quick function to benchmark memory usage during operations.

    Args:
        data_processor: TenderDataProcessor with loaded data
        operations: List of operations to test memory usage for
        iterations: Number of iterations per operation

    Returns:
        Benchmark results dictionary
    """
    tester = PerformanceTester()
    results = tester.benchmark_memory_usage_analysis(data_processor, operations, iterations)
    tester.print_summary()
    return results


if __name__ == "__main__":
    # Example usage and self-test
    print("Performance Tester Self-Test")
    print("="*40)

    tester = PerformanceTester()

    # Test basic timing
    with tester.time_operation("test_operation", {"test": True}):
        time.sleep(0.1)

    # Test system info
    sys_info = tester.get_system_info()
    print(f"System: {sys_info['cpu_count']} CPU cores, {sys_info['memory_total_gb']:.1f} GB RAM")

    # Print results
    tester.print_summary()

    print("\nPerformance testing utilities are ready!")
    print("Use 'from utils.performance_tester import PerformanceTester' to get started.")
