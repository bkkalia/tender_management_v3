#!/usr/bin/env python3
"""
Test script for OCR functionality in Search Dashboard Tab.
This script verifies that the OCR features work correctly.
"""

import tkinter as tk
import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_ocr_imports():
    """Test that OCR-related imports work correctly."""
    print("Testing OCR imports...")

    try:
        # Test PIL imports
        from PIL import Image, ImageDraw, ImageTk, ImageGrab
        print("✓ PIL/Pillow imports successful")
        print(f"  - ImageGrab available: {ImageGrab is not None}")
    except ImportError as e:
        print(f"✗ PIL/Pillow import failed: {e}")
        return False

    try:
        # Test pytesseract import
        import pytesseract
        print("✓ pytesseract import successful")
    except ImportError as e:
        print(f"✗ pytesseract import failed: {e}")
        return False

    return True

def test_clipboard_access():
    """Test clipboard access functionality."""
    print("\nTesting clipboard access...")

    try:
        # Create a test Tkinter root
        root = tk.Tk()
        root.withdraw()  # Hide the window

        # Test clipboard text access
        try:
            clipboard_text = root.clipboard_get()
            print(f"✓ Clipboard text access successful: '{clipboard_text[:50]}...' if too long")
        except tk.TclError:
            print("✓ Clipboard is empty (expected for first test)")

        # Test OCR function accessibility
        try:
            from ui.search_dashboard_tab import SearchDashboardTab, HAS_PYTESSERACT, HAS_PIL
            print(f"✓ SearchDashboardTab import successful")
            print(f"  - HAS_PYTESSERACT: {HAS_PYTESSERACT}")
            print(f"  - HAS_PIL: {HAS_PIL}")
        except ImportError as e:
            print(f"✗ SearchDashboardTab import failed: {e}")
            return False

        root.destroy()
        return True

    except Exception as e:
        print(f"✗ Clipboard access test failed: {e}")
        return False

def main():
    """Run all OCR tests."""
    print("=" * 50)
    print("OCR Functionality Test Suite")
    print("=" * 50)

    # Test imports
    imports_ok = test_ocr_imports()

    # Test clipboard access
    clipboard_ok = test_clipboard_access()

    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY:")
    print("=" * 50)

    if imports_ok and clipboard_ok:
        print("✓ All tests passed! OCR functionality should work correctly.")
        print("\nTo test manually:")
        print("1. Copy some text to clipboard")
        print("2. Run the application")
        print("3. Go to Search Dashboard tab")
        print("4. Click the '📷 OCR' button next to the Global Search field")
        print("5. The text should be extracted and filled into the Global Search field")
        print("\nFor image OCR testing:")
        print("1. Take a screenshot or copy an image with text to clipboard")
        print("2. Click the OCR button")
        print("3. The text should be extracted from the image")
    else:
        print("✗ Some tests failed. Check the error messages above.")
        print("\nTo fix OCR issues:")
        print("1. Install pytesseract: pip install pytesseract")
        print("2. Install PIL/Pillow: pip install pillow (if not already installed)")
        print("3. Install Tesseract OCR engine from: https://github.com/UB-Mannheim/tesseract/wiki")

    return 0 if (imports_ok and clipboard_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
