# Installation Guide - Tender Management Utility V3

This guide explains how to set up the Tender Management Utility V3 and install all required dependencies.

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation Steps

### 1. Clone or download the repository

Download the project files to your local machine.

### 2. Install required packages

Open a command prompt or terminal in the project directory and run:

```
pip install -r requirements.txt
```

This will install the following packages:
- **pandas**: For data processing and analysis
- **tkcalendar**: For calendar widgets in the UI
- **openpyxl**: For Excel file reading/writing
- **matplotlib**: For data visualization charts (optional)
- **filelock**: For safe file operations across network drives
- **icalendar**: For calendar import/export functionality

### 3. Run the application

From the project directory, run:

```
python main.py
```

## Optional Features

Some features require additional packages:

- **Calendar Import/Export**: Requires the `icalendar` package
- **Data Visualization**: Requires the `matplotlib` package

## Troubleshooting

If you encounter import errors:

1. Make sure you've installed all the required packages with `pip install -r requirements.txt`
2. Check your Python version (run `python --version`) - we require Python 3.7+
3. If using a virtual environment, ensure it's activated before installing and running

## Usage on Google Drive

When using this application with files stored on Google Drive:

1. The application will try to use file locking for safety, which requires the `filelock` package
2. If multiple users are working with the same data files, ensure all users have all the required dependencies installed
