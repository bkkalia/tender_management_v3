#!/usr/bin/env python3
"""
Script to regenerate PNG visualizations from saved benchmark data
"""

import json
import os
from comprehensive_benchmark_suite import ComprehensiveBenchmarkSuite

def main():
    # Load the saved benchmark report
    report_file = 'comprehensive_benchmark_report_20250930_112151.json'

    if not os.path.exists(report_file):
        print(f"Error: {report_file} not found")
        return

    print(f"Loading benchmark data from {report_file}...")

    with open(report_file, 'r') as f:
        report_data = json.load(f)

    # Extract benchmark results
    benchmark_results = report_data.get('results', {}).get('benchmark_results', {})

    if not benchmark_results:
        print("Error: No benchmark results found in the report")
        return

    print("Regenerating PNG visualizations...")

    # Create a benchmark suite instance (without running benchmarks)
    suite = ComprehensiveBenchmarkSuite()

    # Create visualizations from the loaded data
    viz_files = suite.create_performance_visualizations(benchmark_results)

    print("PNG files regenerated:")
    for viz_name, viz_path in viz_files.items():
        if os.path.exists(viz_path):
            print(f"  ✓ {viz_name}: {viz_path}")
        else:
            print(f"  ✗ {viz_name}: {viz_path} (failed)")

if __name__ == "__main__":
    main()
