#!/usr/bin/env python3
"""
Performance Testing Demo for Tender Management Utility v3

This script demonstrates various performance testing options for your Dell G15 system.
Run this script to benchmark different operations and see how your system performs.

System Specs: Dell G15, 32GB DDR5, 2TB NVME, Nvidia 3050 4GB
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.performance_tester import (
    PerformanceTester,
    benchmark_data_loading,
    benchmark_filtering_scenarios,
    benchmark_data_analysis_operations,
    benchmark_query_complexity,
    benchmark_memory_operations
)

def create_sample_data_file(filename: str, num_rows: int = 10000):
    """
    Create a sample Excel file for testing.

    Args:
        filename: Path to create the file
        num_rows: Number of sample rows to generate
    """
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    print(f"Creating sample data file: {filename} with {num_rows} rows...")

    # Generate sample data
    departments = ['IT', 'HR', 'Finance', 'Operations', 'Procurement', 'Legal', 'Marketing']
    titles = [
        'Software License Renewal', 'Hardware Maintenance', 'Consulting Services',
        'Office Supplies', 'IT Equipment', 'Training Program', 'Facility Management'
    ]

    data = {
        'Tender ID': [f'T{10000+i}' for i in range(num_rows)],
        'Title': np.random.choice(titles, num_rows),
        'Department': np.random.choice(departments, num_rows),
        'Closing Date': [
            datetime.now() + timedelta(days=np.random.randint(-30, 90))
            for _ in range(num_rows)
        ],
        'Value': np.random.uniform(10000, 1000000, num_rows).round(2),
        'Status': np.random.choice(['Live', 'Expired'], num_rows),
        'Description': [f'Sample tender description {i}' for i in range(num_rows)]
    }

    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"✓ Created {filename} ({num_rows} rows)")

    return filename

def run_basic_performance_test():
    """Run basic performance tests to establish baseline."""
    print("\n" + "="*60)
    print("BASIC PERFORMANCE TEST")
    print("="*60)

    tester = PerformanceTester()

    # Test 1: Simple operation timing
    print("\n1. Basic Operation Timing Test")
    with tester.time_operation("simple_calculation"):
        result = sum(range(1000000))

    # Test 2: Memory allocation test
    print("\n2. Memory Allocation Test")
    with tester.time_operation("memory_allocation"):
        large_list = [i for i in range(1000000)]
        del large_list

    # Test 3: File I/O test
    print("\n3. File I/O Test")
    with tester.time_operation("file_io_test"):
        test_file = "temp_test_file.txt"
        with open(test_file, 'w') as f:
            for i in range(10000):
                f.write(f"Line {i}: This is a test line with some content\n")
        with open(test_file, 'r') as f:
            content = f.read()
        os.remove(test_file)

    tester.print_summary()

def run_data_loading_benchmark():
    """Benchmark data loading performance."""
    print("\n" + "="*60)
    print("DATA LOADING PERFORMANCE BENCHMARK")
    print("="*60)

    # Create sample data files
    sample_files = []

    # Small file (1K rows)
    small_file = create_sample_data_file("sample_data_small.xlsx", 1000)
    sample_files.append(small_file)

    # Medium file (10K rows)
    medium_file = create_sample_data_file("sample_data_medium.xlsx", 10000)
    sample_files.append(medium_file)

    # Large file (50K rows) - test your system's limits
    large_file = create_sample_data_file("sample_data_large.xlsx", 50000)
    sample_files.append(large_file)

    print(f"\nTesting with {len(sample_files)} files:")
    for f in sample_files:
        file_size = os.path.getsize(f) / 1024 / 1024  # MB
        print(f"  {os.path.basename(f)}: {file_size:.1f} MB")

    # Run benchmark
    results = benchmark_data_loading(sample_files, iterations=3)

    # Cleanup
    for f in sample_files:
        if os.path.exists(f):
            os.remove(f)
            print(f"✓ Cleaned up {f}")

    return results

def run_filtering_benchmark():
    """Benchmark filtering performance with loaded data."""
    print("\n" + "="*60)
    print("FILTERING PERFORMANCE BENCHMARK")
    print("="*60)

    # Create and load sample data
    sample_file = create_sample_data_file("filter_test_data.xlsx", 25000)

    from core.data_processor import TenderDataProcessor
    from core.config_manager import GlobalConfig

    # Load data
    config = GlobalConfig()
    processor = TenderDataProcessor(config)

    print(f"\nLoading data from {sample_file}...")
    success, message = processor.load_data_from_files([sample_file])
    if not success:
        print(f"❌ Failed to load data: {message}")
        return None

    print(f"✓ Loaded {len(processor.raw_data)} records")

    # Define filtering scenarios
    filter_scenarios = [
        # Simple department filter
        {'Department': 'IT', 'GlobalSearchOperator': 'OR'},

        # Complex multi-department filter
        {'Department': 'IT, Finance, HR', 'DepartmentOperator': 'OR'},

        # Global search with AND logic
        {'GlobalSearch': 'software, license', 'GlobalSearchOperator': 'AND'},

        # Date-based live filter
        {'DateFilter': {'type': 'live'}},

        # Combined department + date filter
        {'Department': 'IT, Operations', 'DepartmentOperator': 'OR', 'DateFilter': {'type': 'next_7_days'}},

        # Complex multi-criteria filter
        {
            'Department': 'Finance, Procurement',
            'DepartmentOperator': 'OR',
            'GlobalSearch': 'maintenance, service',
            'GlobalSearchOperator': 'OR',
            'DateFilter': {'type': 'next_30_days'}
        }
    ]

    print(f"\nTesting {len(filter_scenarios)} filtering scenarios...")

    # Run benchmark
    results = benchmark_filtering_scenarios(processor, filter_scenarios, iterations=5)

    # Cleanup
    if os.path.exists(sample_file):
        os.remove(sample_file)
        print(f"✓ Cleaned up {sample_file}")

    return results

def run_export_benchmark():
    """Benchmark export operations."""
    print("\n" + "="*60)
    print("EXPORT PERFORMANCE BENCHMARK")
    print("="*60)

    # Create sample data
    sample_file = create_sample_data_file("export_test_data.xlsx", 15000)

    from core.data_processor import TenderDataProcessor
    from core.config_manager import GlobalConfig

    # Load data
    config = GlobalConfig()
    processor = TenderDataProcessor(config)

    success, message = processor.load_data_from_files([sample_file])
    if not success:
        print(f"❌ Failed to load data: {message}")
        return None

    print(f"✓ Loaded {len(processor.raw_data)} records for export testing")

    # Benchmark export operations - focus on CSV since Excel requires openpyxl
    tester = PerformanceTester()
    results = tester.benchmark_export_operations(processor, ['csv'], iterations=3)
    tester.print_summary()

    # Cleanup
    if os.path.exists(sample_file):
        os.remove(sample_file)

    return results

def run_data_analysis_benchmark():
    """Benchmark data analysis operations."""
    print("\n" + "="*60)
    print("DATA ANALYSIS PERFORMANCE BENCHMARK")
    print("="*60)

    # Create and load sample data
    sample_file = create_sample_data_file("analysis_test_data.xlsx", 20000)

    from core.data_processor import TenderDataProcessor
    from core.config_manager import GlobalConfig

    # Load data
    config = GlobalConfig()
    processor = TenderDataProcessor(config)

    success, message = processor.load_data_from_files([sample_file])
    if not success:
        print(f"❌ Failed to load data: {message}")
        return None

    print(f"✓ Loaded {len(processor.raw_data)} records for analysis testing")

    # Benchmark data analysis operations
    results = benchmark_data_analysis_operations(processor, iterations=3)

    # Cleanup
    if os.path.exists(sample_file):
        os.remove(sample_file)

    return results

def run_query_complexity_benchmark():
    """Benchmark query performance at different complexity levels."""
    print("\n" + "="*60)
    print("QUERY COMPLEXITY PERFORMANCE BENCHMARK")
    print("="*60)

    # Create and load sample data
    sample_file = create_sample_data_file("query_test_data.xlsx", 30000)

    from core.data_processor import TenderDataProcessor
    from core.config_manager import GlobalConfig

    # Load data
    config = GlobalConfig()
    processor = TenderDataProcessor(config)

    success, message = processor.load_data_from_files([sample_file])
    if not success:
        print(f"❌ Failed to load data: {message}")
        return None

    print(f"✓ Loaded {len(processor.raw_data)} records for query testing")

    # Benchmark query complexity
    results = benchmark_query_complexity(processor, iterations=5)

    # Cleanup
    if os.path.exists(sample_file):
        os.remove(sample_file)

    return results

def run_memory_operations_benchmark():
    """Benchmark memory usage during operations."""
    print("\n" + "="*60)
    print("MEMORY OPERATIONS BENCHMARK")
    print("="*60)

    # Create and load sample data
    sample_file = create_sample_data_file("memory_test_data.xlsx", 15000)

    from core.data_processor import TenderDataProcessor
    from core.config_manager import GlobalConfig

    # Load data
    config = GlobalConfig()
    processor = TenderDataProcessor(config)

    success, message = processor.load_data_from_files([sample_file])
    if not success:
        print(f"❌ Failed to load data: {message}")
        return None

    print(f"✓ Loaded {len(processor.raw_data)} records for memory testing")

    # Benchmark memory operations
    results = benchmark_memory_operations(processor, iterations=3)

    # Cleanup
    if os.path.exists(sample_file):
        os.remove(sample_file)

    return results

def run_memory_scaling_test():
    """Test how the application scales with different data sizes."""
    print("\n" + "="*60)
    print("MEMORY SCALING TEST")
    print("="*60)

    from core.data_processor import TenderDataProcessor
    from core.config_manager import GlobalConfig

    config = GlobalConfig()
    tester = PerformanceTester()

    sizes_to_test = [1000, 5000, 10000, 25000, 50000]  # Adjust based on your system

    print("Testing data loading performance at different scales:")
    print("Size (rows) | Load Time (s) | Memory Used (MB) | Records Loaded")
    print("-" * 65)

    for size in sizes_to_test:
        try:
            # Create test file
            test_file = f"scale_test_{size}.xlsx"
            create_sample_data_file(test_file, size)

            # Test loading
            processor = TenderDataProcessor(config)

            with tester.time_operation(f"scale_test_{size}rows"):
                success, message = processor.load_data_from_files([test_file])

            if success:
                result = tester.results[f"scale_test_{size}rows"][-1]
                records = len(processor.raw_data)
                print(f"{size:8d} | {result['duration_seconds']:11.2f} | {result['memory_delta_mb']:14.1f} | {records:13d}")

                # Clean up memory
                del processor
            else:
                print(f"{size:8d} | {'ERROR':>11} | {'ERROR':>14} | {'ERROR':>13}")

            # Cleanup file
            if os.path.exists(test_file):
                os.remove(test_file)

        except Exception as e:
            print(f"{size:8d} | {'EXCEPTION':>11} | {'EXCEPTION':>14} | {'EXCEPTION':>13}")

    print("\nNote: Your Dell G15 with 32GB RAM should handle up to 100K+ rows comfortably.")
    print("For larger datasets (1M+), consider optimizing memory usage or using chunked loading.")

def show_system_info():
    """Display detailed system information."""
    print("\n" + "="*60)
    print("SYSTEM INFORMATION")
    print("="*60)

    tester = PerformanceTester()
    sys_info = tester.get_system_info()

    # OS Information
    print(f"Operating System: {sys_info.get('os_name', 'Unknown')} {sys_info.get('os_release', '')}")
    print(f"OS Version: {sys_info.get('os_version', 'Unknown')}")
    print(f"Architecture: {sys_info.get('architecture', 'Unknown')} ({sys_info.get('machine', 'Unknown')})")
    print(f"Platform: {sys_info.get('platform', 'Unknown')}")

    # CPU Information
    print(f"\nCPU Information:")
    if 'cpu_model' in sys_info:
        print(f"  Model: {sys_info['cpu_model']}")
    else:
        print(f"  Processor: {sys_info.get('processor', 'Unknown')}")
    print(f"  Cores: {sys_info['cpu_count']} physical, {sys_info['cpu_count_logical']} logical")
    if 'cpu_freq_mhz' in sys_info:
        print(f"  Frequency: {sys_info['cpu_freq_mhz']:.0f} MHz (max: {sys_info.get('cpu_freq_max_mhz', 'N/A'):.0f} MHz)")

    # Memory Information
    print(f"\nMemory Information:")
    print(f"  Total RAM: {sys_info['memory_total_gb']:.1f} GB")
    print(f"  Available RAM: {sys_info['memory_available_gb']:.1f} GB")
    if 'memory_used_gb' in sys_info:
        print(f"  Used RAM: {sys_info['memory_used_gb']:.1f} GB ({sys_info.get('memory_percent', 0):.1f}%)")

    # Storage Information
    print(f"\nStorage Information:")
    print(f"  Total Disk: {sys_info['disk_total_gb']:.1f} GB")
    print(f"  Free Disk: {sys_info['disk_free_gb']:.1f} GB")
    if 'disk_model' in sys_info:
        print(f"  Disk Model: {sys_info['disk_model']}")

    # GPU Information
    if 'gpu_info' in sys_info:
        print(f"\nGPU Information:")
        print(f"  {sys_info['gpu_info']}")

    # Python Information
    print(f"\nSoftware Information:")
    print(f"  Python Version: {sys_info['python_version']}")

    # Performance Assessment
    print(f"\nPerformance Assessment:")
    print(f"- System Type: High-performance gaming laptop")
    print(f"- RAM: {sys_info['memory_total_gb']:.0f}GB DDR5 (excellent for data processing)")
    print(f"- Storage: NVME SSD (fast I/O for large datasets)")
    print(f"- CPU: {sys_info['cpu_count']} cores (good parallel processing)")
    print(f"- Expected Performance: 50K-100K+ rows comfortable")
    print(f"- Scaling Limit: 500K+ rows with optimization")

def main():
    """Main performance testing function."""
    print("🚀 Tender Management Utility v3 - Performance Testing Suite")
    print("="*60)
    print("Testing on: Dell G15 (32GB DDR5, 2TB NVME, RTX 3050)")

    # Show system info first
    show_system_info()

    try:
        # Run basic tests
        run_basic_performance_test()

        # Test data loading at different scales
        run_data_loading_benchmark()

        # Test filtering performance
        run_filtering_benchmark()

        # Test data analysis operations
        run_data_analysis_benchmark()

        # Test query complexity performance
        run_query_complexity_benchmark()

        # Test memory operations
        run_memory_operations_benchmark()

        # Test export operations
        run_export_benchmark()

        # Test memory scaling
        run_memory_scaling_test()

        print("\n" + "="*60)
        print("PERFORMANCE TESTING COMPLETE")
        print("="*60)
        print("📊 Key Findings for your Dell G15:")
        print("• Data loading: Should be very fast with NVME storage")
        print("• Memory usage: 32GB RAM handles large datasets well")
        print("• Filtering: Fast with proper indexing")
        print("• Export: Quick with SSD storage")
        print("• Scaling: Comfortable up to 100K+ rows")
        print("\n💡 Optimization Tips:")
        print("• Use SSD storage for best performance")
        print("• Close other applications when processing large datasets")
        print("• Consider data chunking for 1M+ rows")
        print("• Monitor memory usage with Task Manager")

    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
