"""
Main entry point for the Tender Management Utility application.
"""
import logging
import tkinter as tk
import sys
import os

# Determine if we're running as a script or frozen executable
if getattr(sys, 'frozen', False):
    # If the application is frozen (PyInstaller)
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)  # Change working directory to executable's directory
else:
    # If running as a script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Add the application path to sys.path to ensure imports work
if application_path not in sys.path:
    sys.path.insert(0, application_path)

# Only now import from the application modules
from utils.logging_config import setup_logging
from ui.main_window import MainApplication

# Set up logging
logger = setup_logging()

def main():
    """Main application entry point."""
    logger.info("Application starting...")
    
    try:
        root = MainApplication()
        logger.info("Main window initialized")
        root.mainloop()
        logger.info("Application closed")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()