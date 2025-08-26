"""
Executable builder script for Tender Management Utility application.
Builds a standalone executable using PyInstaller.
"""
import os
import subprocess
import shutil
import sys
import time

def build_exe():
    """Build executable using PyInstaller"""
    print("=" * 70)
    print("Building Tender Management Utility Executable")
    print("=" * 70)
    
    # Ensure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Create required directories
    os.makedirs('dist', exist_ok=True)
    os.makedirs('resources', exist_ok=True)
    
    # Clean previous builds
    print("\nCleaning previous builds...")
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('TenderManagementUtility.spec'):
        os.remove('TenderManagementUtility.spec')
    
    # Skip virtual environment creation - use system Python instead
    print("\nUsing system Python for build...")
    python_executable = sys.executable
    
    # Define PyInstaller command with optimized settings
    print("\nBuilding executable (this may take several minutes)...")
    start_time = time.time()
    
    # Basic command with essential imports only
    pyinstaller_command = [
        python_executable, "-m", "pyinstaller",
        "--name=TenderManagementUtility",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        # Path handling is crucial - use correct separators for your OS
        "--add-data=utils;utils",
        "--add-data=ui;ui",
        "--add-data=core;core",
        "--add-data=config;config",
        "--add-data=resources;resources",
        # Include only critical hidden imports
        "--hidden-import=pandas",
        "--hidden-import=tkinter",
        "--hidden-import=tkcalendar",
        "main.py"
    ]
    
    # Run PyInstaller
    try:
        print("Running PyInstaller (this may take a while)...")
        subprocess.run(pyinstaller_command, check=True)
        
        build_time = time.time() - start_time
        print(f"\nBuild completed successfully in {build_time:.1f} seconds!")
        
        # Create config directory
        config_dir = os.path.join("dist", "config")
        os.makedirs(config_dir, exist_ok=True)
        
        print("\nExecutable created at: dist/TenderManagementUtility.exe")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError during build: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Build process completed!")
    print("=" * 70)

if __name__ == "__main__":
    build_exe()
