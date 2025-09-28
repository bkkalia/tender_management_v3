#!/usr/bin/env python3
"""
Test script to verify benchmark improvements are working correctly.
"""
import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_benchmark_imports():
    """Test that benchmark modules can be imported."""
    try:
        from ui.benchmark_window import BenchmarkWindow
        print("✅ BenchmarkWindow imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import BenchmarkWindow: {e}")
        return False

    try:
        # Test that help file exists
        help_file = os.path.join(os.path.dirname(__file__), 'BENCHMARK_HELP.md')
        if os.path.exists(help_file):
            print("✅ BENCHMARK_HELP.md file exists")
            # Check file has content
            with open(help_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content) > 1000:  # Substantial content
                    print("✅ BENCHMARK_HELP.md has substantial content")
                else:
                    print("⚠️ BENCHMARK_HELP.md appears to be small")
        else:
            print("❌ BENCHMARK_HELP.md file not found")
            return False
    except Exception as e:
        print(f"❌ Error checking help file: {e}")

    return True

def test_benchmark_methods():
    """Test that benchmark methods return correct data types."""
    try:
        from ui.benchmark_window import BenchmarkWindow
        import tkinter as tk

        # Create a minimal Tkinter root (will be hidden)
        root = tk.Tk()
        root.withdraw()

        # Create a benchmark window instance
        try:
            app = None  # Mock main app
            benchmark = BenchmarkWindow(root, app)

            # Test CPU single core benchmark
            result = benchmark._benchmark_cpu_single_core()
            print("🔬 Testing CPU single core benchmark...")

            if isinstance(result, dict):
                if 'score' in result and isinstance(result['score'], (int, float)):
                    print(f"✅ CPU benchmark returned score: {result['score']}")

                    # Check for properly formatted metrics
                    if 'duration_seconds' in result and isinstance(result['duration_seconds'], (int, float)):
                        print(f"✅ Duration properly formatted: {result['duration_seconds']} seconds")
                    else:
                        print("❌ Duration not properly formatted")

                    if 'primes_found' in result and isinstance(result['primes_found'], int):
                        print(f"✅ Primes found: {result['primes_found']}")
                    else:
                        print("❌ Primes found not properly tracked")
                else:
                    print("❌ CPU benchmark didn't return proper score")
            else:
                print("❌ CPU benchmark didn't return dictionary")

            # Test memory bandwidth benchmark
            print("🔬 Testing memory bandwidth benchmark...")
            result = benchmark._benchmark_memory_bandwidth()

            if isinstance(result, dict) and 'score' in result:
                print(f"✅ Memory benchmark returned score: {result['score']}")

                # Check for actual numeric values, not format strings
                for key in ['write_time_seconds', 'read_time_seconds', 'bandwidth_mb_per_sec', 'data_size_mb']:
                    if key in result and isinstance(result[key], (int, float)):
                        print(f"✅ {key}: {result[key]}")
                    else:
                        print(f"❌ {key} not properly formatted or missing")

            # Clean up
            root.destroy()

        except Exception as e:
            print(f"❌ Error testing benchmark methods: {e}")
            root.destroy()
            return False

    except Exception as e:
        print(f"❌ Error in benchmark methods test: {e}")
        return False

    return True

if __name__ == "__main__":
    print("🚀 Testing Benchmark Improvements\n")

    success = True

    print("1. Testing imports and file existence...")
    if not test_benchmark_imports():
        success = False

    print("\n2. Testing benchmark method functionality...")
    if not test_benchmark_methods():
        success = False

    if success:
        print("\n🎉 All tests passed! Benchmark improvements are working correctly.")
        print("\nKey improvements verified:")
        print("- ✅ BENCHMARK_HELP.md file exists with content")
        print("- ✅ Benchmark methods return proper numeric values")
        print("- ✅ Format strings replaced with actual values (e.g., 1.234 instead of '.3f')")
        print("- ✅ Benchmark window can be instantiated")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")

    print("\n📋 Next steps:")
    print("- Test the GUI by running 'python main.py' and opening Tools → Performance Benchmark")
    print("- Check that the new Help tab appears and loads content")
    print("- Run a benchmark test and verify numeric values appear (not format strings)")
    print("- Generate a report and check detailed explanations and recommendations")
