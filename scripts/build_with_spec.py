"""
Build the executable using the spec file for better control.
"""
import subprocess
import sys
import os
import time

print("=" * 70)
print("Building Tender Management Utility with Spec File")
print("=" * 70)

start_time = time.time()

try:
    # Use the current Python interpreter to run PyInstaller with the spec file
    subprocess.run([
        sys.executable, 
        "-m", 
        "pyinstaller", 
        "TenderManagementUtility.spec", 
        "--clean"
    ], check=True)
    
    build_time = time.time() - start_time
    print(f"\nBuild completed in {build_time:.1f} seconds!")
    print("\nExecutable created at: dist/TenderManagementUtility.exe")
    
except subprocess.CalledProcessError as e:
    print(f"Error during build: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)

print("=" * 70)
