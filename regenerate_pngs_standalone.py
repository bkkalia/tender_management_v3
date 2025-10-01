#!/usr/bin/env python3
"""
Standalone script to regenerate PNG visualizations from saved benchmark data
"""

import json
import os
import matplotlib.pyplot as plt
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
import numpy as np

def create_performance_scaling_chart(results, ax):
    """Create performance scaling visualization"""
    data_loading_results = results.get('data_loading', {}).get('results', [])

    if data_loading_results:
        sizes = [r['total_records'] for r in data_loading_results]
        times = [r['execution_time'] for r in data_loading_results]
        categories = [r['performance_category'] for r in data_loading_results]

        # Create scatter plot with performance categories
        colors = ['green' if cat == 'sub_second' else
                 'blue' if cat == 'fast' else
                 'orange' if cat == 'moderate' else
                 'red' if cat == 'slow' else 'gray'
                 for cat in categories]

        ax.scatter(sizes, times, c=colors, s=100, alpha=0.7)

        # Add trend line
        if len(sizes) > 1:
            z = np.polyfit(sizes, times, 1)
            p = np.poly1d(z)
            ax.plot(sizes, p(sizes), "r--", alpha=0.8, label=f'Trend: {z[0]:.2e}x + {z[1]:.2f}')

        ax.set_xlabel('Dataset Size (records)')
        ax.set_ylabel('Execution Time (seconds)')
        ax.set_title('Performance Scaling Analysis')
        ax.legend()
        ax.grid(True, alpha=0.3)

def create_memory_usage_chart(results, ax):
    """Create memory usage visualization"""
    memory_results = results.get('memory_usage', {}).get('results', [])

    if memory_results:
        sizes = [r['total_records'] for r in memory_results]
        memory_mb = [r['memory_delta_mb'] for r in memory_results]

        ax.bar(range(len(sizes)), memory_mb, alpha=0.7)
        ax.set_xlabel('Dataset Size Category')
        ax.set_ylabel('Memory Usage (MB)')
        ax.set_title('Memory Usage by Dataset Size')
        ax.set_xticks(range(len(sizes)))
        ax.set_xticklabels([r['dataset_size'] for r in memory_results])

def create_query_complexity_chart(results, ax):
    """Create query complexity visualization"""
    query_results = results.get('query_performance', {}).get('results', [])

    if query_results:
        # Group by complexity
        complexity_data = {}
        for result in query_results:
            complexity = result['query_complexity']
            if complexity not in complexity_data:
                complexity_data[complexity] = {'times': [], 'sizes': []}
            complexity_data[complexity]['times'].append(result['execution_time'])
            complexity_data[complexity]['sizes'].append(result['total_records'])

        # Create grouped bar chart
        complexities = list(complexity_data.keys())
        x_pos = range(len(complexities))

        for i, (complexity, data) in enumerate(complexity_data.items()):
            avg_time = sum(data['times']) / len(data['times'])
            ax.bar(i, avg_time, alpha=0.7, label=complexity)

        ax.set_xlabel('Query Complexity')
        ax.set_ylabel('Average Execution Time (seconds)')
        ax.set_title('Query Performance by Complexity')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(complexities)
        ax.legend()

def create_performance_distribution_chart(results, ax):
    """Create performance distribution visualization"""
    all_times = []

    # Collect all execution times
    for benchmark_type in ['data_loading', 'query_performance', 'memory_usage']:
        benchmark_results = results.get(benchmark_type, {}).get('results', [])
        for result in benchmark_results:
            all_times.append(result.get('execution_time', 0))

    if all_times:
        # Create histogram of performance distribution
        ax.hist(all_times, bins=20, alpha=0.7, edgecolor='black')

        # Add vertical lines for performance categories
        categories = [
            ('Sub-second (0-1s)', 1.0, 'green'),
            ('Fast (1-2s)', 2.0, 'blue'),
            ('Moderate (2-3s)', 3.0, 'orange'),
            ('Slow (3-5s)', 5.0, 'red')
        ]

        for label, threshold, color in categories:
            ax.axvline(x=threshold, color=color, linestyle='--', alpha=0.8, label=label)

        ax.set_xlabel('Execution Time (seconds)')
        ax.set_ylabel('Frequency')
        ax.set_title('Performance Distribution Analysis')
        ax.legend()
        ax.grid(True, alpha=0.3)

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

    print("Creating PNG visualizations...")

    # Set up the plotting style
    if HAS_SEABORN:
        plt.style.use('seaborn-v0_8')
    else:
        plt.style.use('default')

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Tender Management Utility v3.2 - Comprehensive Performance Analysis',
                fontsize=16, fontweight='bold')

    # Visualization file paths
    viz_files = {}

    try:
        # Create individual charts first
        # 1. Performance scaling chart
        fig1, ax1 = plt.subplots(figsize=(8, 6))
        create_performance_scaling_chart(benchmark_results, ax1)
        scaling_path = 'performance_scaling.png'
        fig1.savefig(scaling_path, dpi=300, bbox_inches='tight')
        plt.close(fig1)
        viz_files['performance_scaling'] = scaling_path

        # 2. Memory usage analysis
        fig2, ax2 = plt.subplots(figsize=(8, 6))
        create_memory_usage_chart(benchmark_results, ax2)
        memory_path = 'memory_usage_analysis.png'
        fig2.savefig(memory_path, dpi=300, bbox_inches='tight')
        plt.close(fig2)
        viz_files['memory_usage'] = memory_path

        # 3. Query complexity analysis
        fig3, ax3 = plt.subplots(figsize=(8, 6))
        create_query_complexity_chart(benchmark_results, ax3)
        query_path = 'query_complexity_analysis.png'
        fig3.savefig(query_path, dpi=300, bbox_inches='tight')
        plt.close(fig3)
        viz_files['query_complexity'] = query_path

        # 4. Performance distribution
        fig4, ax4 = plt.subplots(figsize=(8, 6))
        create_performance_distribution_chart(benchmark_results, ax4)
        dist_path = 'performance_distribution.png'
        fig4.savefig(dist_path, dpi=300, bbox_inches='tight')
        plt.close(fig4)
        viz_files['performance_distribution'] = dist_path

        # Now create the combined dashboard
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Tender Management Utility v3.2 - Comprehensive Performance Analysis',
                    fontsize=16, fontweight='bold')

        # Recreate charts on the dashboard
        create_performance_scaling_chart(benchmark_results, axes[0, 0])
        create_memory_usage_chart(benchmark_results, axes[0, 1])
        create_query_complexity_chart(benchmark_results, axes[1, 0])
        create_performance_distribution_chart(benchmark_results, axes[1, 1])

        plt.tight_layout()
        dashboard_path = 'comprehensive_performance_dashboard.png'
        fig.savefig(dashboard_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        viz_files['dashboard'] = dashboard_path

        print("PNG files created:")
        for viz_name, viz_path in viz_files.items():
            if os.path.exists(viz_path):
                print(f"  ✓ {viz_name}: {viz_path}")
            else:
                print(f"  ✗ {viz_name}: {viz_path} (failed)")

    except Exception as e:
        print(f"Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
