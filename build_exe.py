"""
Executable builder script for Tender Management Utility application.
Builds a standalone executable using PyInstaller.
"""
import os
import shutil
import sys
import time
import importlib

def check_package(package_name: str) -> bool:
    """Check if a package is installed."""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def get_folder_size(folder_path):
    """Calculate the total size of a folder in MB."""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # Convert to MB
    except Exception:
        return 0

def build_exe():
    """Build executable using PyInstaller"""
    # Check for PyInstaller dependency first
    if not check_package("PyInstaller"):
        print("\nError: PyInstaller is not installed.")
        print("Please install it by running: pip install pyinstaller")
        sys.exit(1)

    # Import PyInstaller's main function now that we know it exists
    import PyInstaller.__main__

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
    
    # Check for UPX
    upx_path = shutil.which('upx') or (os.path.exists('upx.exe') and 'upx.exe')
    if upx_path:
        print(f"\nFound UPX at: {upx_path}. Compression will be enabled.")
    else:
        print("\nWarning: UPX not found. Executable will not be compressed. Download from upx.github.io")

    # Define PyInstaller command with optimized settings for a directory build
    print("\nBuilding executable (this may take several minutes)...")
    start_time = time.time()
    
    app_name = "TenderManagementUtility"
    
    # Arguments for PyInstaller's run function
    pyinstaller_args = [
        f"--name={app_name}",
        "--windowed",
        "--clean",
        "--noconfirm",
        # Add icon to the executable
        "--icon=resources/app_icon.ico",
        # Use os.pathsep for cross-platform compatibility
        f"--add-data=utils{os.pathsep}utils",
        f"--add-data=ui{os.pathsep}ui",
        f"--add-data=core{os.pathsep}core",
        f"--add-data=config{os.pathsep}config",
        f"--add-data=resources{os.pathsep}resources",
        # Include critical hidden imports
        "--hidden-import=pandas",
        "--hidden-import=tkinter",
        "--hidden-import=tkcalendar",
        "--hidden-import=openpyxl", # Explicitly include for pandas Excel support
        "--hidden-import=requests",  # For HTTP downloads
        "--hidden-import=urllib.request",  # For basic URL handling
        "--hidden-import=ftplib",  # For FTP support
        "--hidden-import=paramiko",  # For SFTP support (optional)
        "--hidden-import=ssl",  # For secure connections
        "main.py"
    ]
    
    if upx_path:
        pyinstaller_args.append(f"--upx-dir={os.path.dirname(upx_path) if os.path.dirname(upx_path) else '.'}")

    # Run PyInstaller directly from the script
    try:
        print("Running PyInstaller (this may take a while)...")
        print("Please wait while files are being processed and compressed...")
        
        PyInstaller.__main__.run(pyinstaller_args)
        
        build_time = time.time() - start_time
        
        # Post-build: Copy the default config file into the distribution
        dist_path = os.path.join("dist", app_name)
        config_source = os.path.join("config", "app_config.json")
        config_dest_dir = os.path.join(dist_path, "config")
        
        if os.path.exists(config_source):
            os.makedirs(config_dest_dir, exist_ok=True)
            shutil.copy(config_source, config_dest_dir)
            print(f"Copied default config to {config_dest_dir}")

        # Calculate final size
        if os.path.exists(dist_path):
            folder_size = get_folder_size(dist_path)
            print(f"\n{'='*70}")
            print("BUILD COMPLETED SUCCESSFULLY!")
            print(f"{'='*70}")
            print(f"Build time: {build_time:.1f} seconds")
            print(f"Application size: {folder_size:.1f} MB")
            print(f"Application built at: {dist_path}")
            print(f"Main executable: {os.path.join(dist_path, app_name + '.exe')}")
            print(f"{'='*70}")
            
            # Check if executable exists
            exe_path = os.path.join(dist_path, app_name + '.exe')
            if os.path.exists(exe_path):
                exe_size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"Executable size: {exe_size:.1f} MB")
                print("✓ Build completed successfully!")
            else:
                print("⚠ Warning: Executable file not found!")
        else:
            print(f"\n⚠ Warning: Distribution folder not found at {dist_path}")
        
    except KeyboardInterrupt:
        print(f"\n\nBuild interrupted by user!")
        sys.exit(1)
    except Exception as e:
        print(f"\n{'='*70}")
        print("BUILD FAILED!")
        print(f"{'='*70}")
        print(f"Error during build: {e}")
        print(f"Build time before failure: {time.time() - start_time:.1f} seconds")
        sys.exit(1)

if __name__ == "__main__":
    build_exe()
