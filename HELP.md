# Tender Management Utility V3.2 - Help & Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start Guide](#quick-start-guide)
4. [User Guide](#user-guide)
5. [Developer Guide](#developer-guide)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)
9. [Contributing](#contributing)

---

## 🎯 Overview

The **Tender Management Utility V3** is a comprehensive desktop application for managing, searching, and analyzing tender data from multiple sources. It provides advanced filtering, search capabilities, and data visualization features.

### Key Features

- **Multi-Source Data Loading**: Load data from local folders and remote URLs
- **Advanced Search & Filtering**: Department search, global search, date filtering
- **Saved Searches**: Save and reuse search configurations
- **Data Export**: Export filtered data to Excel/CSV formats
- **Real-time Dashboard**: Live metrics and statistics
- **Data Visualization**: Charts and visual representations
- **Remote Data Integration**: Support for cloud-based data sources
- **Performance Monitoring**: Real-time system metrics and performance tracking
- **Advanced Dummy Data Generator**: Generate test data with 50K+ records
- **GUI Performance Testing**: Built-in benchmark testing suite
- **Rich Performance Reports**: Professional markdown reports with system specs

### System Requirements

- **Operating System**: Windows 10/11, macOS 10.14+, Linux
- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 500MB free space
- **Display**: 1024x768 minimum resolution

---

## 🚀 Installation

### Method 1: Using the Installer (Recommended)

1. Download the latest installer from the releases page
2. Run the installer executable
3. Follow the on-screen instructions
4. Launch the application from the desktop shortcut or start menu

### Method 2: Manual Installation

#### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install additional system dependencies (Windows)
# - Microsoft Visual C++ 14.0 or greater (for some packages)
# - Excel support requires: pywin32 (Windows only)
```

#### Setup Steps

1. **Clone or download** the project files
2. **Navigate** to the project directory:
   ```bash
   cd tender_management_v3
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

### First Run Setup

1. The application will create necessary directories:
   - `data/input_excel_files/` - for input data
   - `data/merged_data/` - for processed data
   - `logs/` - for application logs
   - `config/` - for configuration files

2. Configure your data sources in the **Data Folders** section

---

## 📖 Quick Start Guide

### Loading Your First Data

1. **Add Data Sources**:
   - Click **"Add Folder"** to select folders containing Excel/CSV files
   - Or click **"Add Cloud URL"** for remote data sources

2. **Load Data**:
   - Click **"Refresh Data"** to load files from selected sources
   - Wait for the loading process to complete

3. **View Results**:
   - Data will appear in the main table
   - Dashboard shows key metrics and statistics

### Basic Search

1. **Department Search**:
   - Enter keywords in the "Department Search" field
   - Use commas to separate multiple terms
   - Choose AND/OR logic for multiple terms

2. **Global Search**:
   - Enter keywords in the "Global Search" field
   - Searches across all columns
   - Use AND/OR logic for multiple terms

3. **Apply Filters**:
   - Click search or press Enter to apply filters
   - Results update automatically as you type

### Saving and Loading Searches

1. **Save Current Search**:
   - Enter a name in the "Save Current Search" field
   - Click **"Save"** button
   - Search configuration is saved for later use

2. **Load Saved Search**:
   - Select from the dropdown in "Load Search"
   - Click **"Load"** to apply the saved search

---

## 👥 User Guide

### Data Management

#### Loading Data Sources

**Local Folders**:
- Click **"Add Folder"** to browse and select folders
- Supports Excel (.xlsx, .xls) and CSV files
- Files are automatically detected and loaded

**Remote URLs**:
- Click **"Add Cloud URL"** to add remote data sources
- Supports HTTP/HTTPS URLs
- Optional authentication (username/password)

#### Data Refresh
- Click **"Refresh Data"** to reload all data sources
- Useful when source files have been updated
- Shows progress and loading status

### Search and Filtering

#### Search Types

**Department Search**:
- Searches within department/agency columns
- Example: "IT Department, Finance"
- Supports AND/OR logic

**Global Search**:
- Searches across all columns
- Example: "software, license, maintenance"
- Supports AND/OR logic

#### Filter Options

**Status Filters**:
- **All Records**: Show all tenders
- **Live Tenders**: Only tenders with future closing dates
- **Expired Tenders**: Only tenders with past closing dates

**Time Range Filters**:
- **Today**: Tenders closing today
- **3 Days**: Tenders closing in next 3 days
- **7 Days**: Tenders closing in next 7 days
- **30 Days**: Tenders closing in next 30 days

**Custom Date Range**:
- Use date pickers to set custom start/end dates
- Supports time-based filtering
- Useful for specific date ranges

### Saved Searches

#### Creating Saved Searches
1. Set up your desired search criteria
2. Enter a descriptive name in the save field
3. Click **"Save"** to store the configuration

#### Managing Saved Searches
- **Load**: Apply a saved search configuration
- **Delete**: Remove unwanted saved searches
- **Export**: Save all searches to JSON/CSV file
- **Import**: Load searches from exported file
- **Clean**: Remove corrupted search entries

### Data Export

#### Export Options
- **Export Excel**: Save filtered data as Excel file
- **Export CSV**: Save filtered data as CSV file

#### Export Process
1. Apply desired filters to get target data
2. Click **"Export Excel"** or **"Export CSV"**
3. Choose save location and filename
4. Data is exported with current filters applied

### Dashboard

#### Key Metrics
- **Total Tenders**: Total number of loaded records
- **Live Tenders**: Tenders with future closing dates
- **Expired Tenders**: Tenders with past closing dates
- **Filtered Results**: Number of records matching current filters
- **Filter Match %**: Percentage of data matching filters
- **Departments**: Number of unique departments
- **Due Today**: Tenders closing today
- **Due in 3/7 Days**: Upcoming tender deadlines

#### Real-time Updates
- Dashboard updates automatically when data changes
- Metrics reflect current filtered data
- Live clock and date display

### Advanced Features

#### Data Visualization
- Click **"Charts"** button for visual representations
- View data distributions and trends
- Interactive charts and graphs

#### Calendar Integration
- Add tender deadlines to calendar applications
- Right-click on tender rows for calendar options
- Supports various calendar formats

#### URL Handling
- Automatic detection of URL columns
- Click on URLs to open in browser
- Visual indicators for URL fields

---

## 🛠️ Developer Guide

### Project Structure

```
tender_management_v3/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── config/                 # Configuration files
│   ├── config.json        # Main configuration
│   └── app_config.json    # Application settings
├── core/                   # Core business logic
│   ├── config_manager.py  # Configuration management
│   ├── data_processor.py  # Data processing engine
│   ├── file_merger.py     # File merging utilities
│   ├── remote_data_loader.py # Remote data loading
│   └── tender_models.py   # Data models
├── ui/                     # User interface components
│   ├── main_window.py     # Main window
│   ├── search_dashboard_tab.py # Search and dashboard
│   ├── calendar_tab.py    # Calendar integration
│   ├── logs_tab.py        # Log viewer
│   ├── settings_tab.py    # Settings panel
│   ├── common_widgets.py  # Reusable UI components
│   └── assets/            # Images and resources
├── data/                   # Data storage
│   ├── input_excel_files/ # Input data files
│   ├── merged_data/       # Processed data
│   ├── calendar_events.json # Calendar data
│   └── users.json         # User data
├── logs/                   # Application logs
├── utils/                  # Utility functions
│   ├── constants.py       # Application constants
│   ├── logger_setup.py    # Logging configuration
│   └── common_imports.py  # Common imports
└── docs/                   # Documentation
    ├── CHANGELOG.md       # Version history
    └── HELP.md            # This file
```

### Core Components

#### Configuration Manager (`core/config_manager.py`)
```python
from core.config_manager import GlobalConfig

# Initialize configuration
config = GlobalConfig()

# Get configuration value
value = config.get("key", default_value)

# Set configuration value
config.set("key", value)

# Save configuration
config.save_config()
```

#### Data Processor (`core/data_processor.py`)
```python
from core.data_processor import TenderDataProcessor

# Initialize processor
processor = TenderDataProcessor(config)

# Load data
processor.load_data(file_paths)

# Apply filters
processor.apply_filters(filters)

# Get filtered data
filtered_data = processor.filtered_data
```

#### Remote Data Loader (`core/remote_data_loader.py`)
```python
from core.remote_data_loader import RemoteDataLoader

# Initialize loader
loader = RemoteDataLoader()

# Load from remote source
success, message, local_file = loader.load_from_remote_source(
    url, username=None, password=None
)
```

### UI Components

#### Creating Custom Widgets
```python
from ui.common_widgets import create_action_button, create_labeled_frame

# Create a labeled frame
frame = create_labeled_frame(parent, "Section Title")

# Create an action button
button = create_action_button(
    parent,
    "Button Text",
    command_function,
    button_type='primary',  # primary, success, danger, info, warning, secondary
    width=12
)
```

#### Extending the Main Window
```python
from ui.main_window import MainApplication

class CustomTab(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self._create_widgets()

    def _create_widgets(self):
        # Create your custom widgets here
        pass

# Add to main application
app = MainApplication()
app.add_tab("Custom Tab", CustomTab)
```

### Configuration Options

#### Main Configuration (`config/config.json`)
```json
{
  "app_title": "Tender Search Utility V3",
  "default_data_folder": "./data/input_excel_files/",
  "merged_data_folder": "./data/merged_data/",
  "log_level": "INFO",
  "last_used_folders": [],
  "merger_unique_key": "Tender ID",
  "merger_critical_fields": ["Closing Date", "Status", "Value"],
  "saved_searches": {},
  "saved_searches_data": {}
}
```

#### Application Settings (`config/app_config.json`)
```json
{
  "window_geometry": "1200x800+100+100",
  "default_theme": "default",
  "auto_save": true,
  "export_format": "excel",
  "max_recent_files": 10
}
```

### Extending Functionality

#### Adding New Data Sources
1. Create a new loader class in `core/`
2. Implement the data loading interface
3. Add UI components for configuration
4. Register the new source type

#### Creating Custom Filters
1. Extend the `TenderDataProcessor` class
2. Add new filter methods
3. Update the UI to include new filter options
4. Test with various data formats

#### Adding Export Formats
1. Create export utility functions
2. Add format-specific handling
3. Update export UI components
4. Add configuration options

### Testing

#### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_data_processor.py

# Run with verbose output
python -m pytest -v tests/
```

#### Writing Tests
```python
import unittest
from core.data_processor import TenderDataProcessor

class TestDataProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = TenderDataProcessor()

    def test_load_data(self):
        # Test data loading functionality
        pass

    def test_apply_filters(self):
        # Test filtering functionality
        pass
```

### Debugging

#### Common Issues

**Application won't start**:
- Check Python version (requires 3.8+)
- Verify all dependencies are installed
- Check for missing system libraries

**Data loading fails**:
- Verify file paths and permissions
- Check file formats (Excel/CSV only)
- Review error logs in `logs/` directory

**Search not working**:
- Check data is loaded properly
- Verify column names match search criteria
- Review filter configurations

#### Debug Mode
```python
import logging

# Enable debug logging
logging.getLogger().setLevel(logging.DEBUG)

# Run application
python main.py
```

### Performance Optimization

#### Memory Management
- Process large datasets in chunks
- Use pandas `read_excel` with `chunksize` parameter
- Implement data caching for frequently accessed data

#### UI Responsiveness
- Use threading for long-running operations
- Implement progress indicators
- Add cancellation options for operations

#### Database Optimization
- Index frequently searched columns
- Use appropriate data types
- Implement connection pooling

---

## ⚙️ Configuration

### Configuration Files

#### Main Configuration
**Location**: `config/config.json`

| Setting | Description | Default Value |
|---------|-------------|---------------|
| `app_title` | Application window title | "Tender Search Utility V3" |
| `default_data_folder` | Default folder for input files | "./data/input_excel_files/" |
| `merged_data_folder` | Folder for processed data | "./data/merged_data/" |
| `log_level` | Logging level (DEBUG, INFO, WARNING, ERROR) | "INFO" |
| `last_used_folders` | Recently used data folders | [] |
| `merger_unique_key` | Column used as unique identifier | "Tender ID" |
| `merger_critical_fields` | Fields required for merging | ["Closing Date", "Status", "Value"] |

#### Application Settings
**Location**: `config/app_config.json`

| Setting | Description | Default Value |
|---------|-------------|---------------|
| `window_geometry` | Window size and position | "1200x800+100+100" |
| `default_theme` | UI theme | "default" |
| `auto_save` | Auto-save configuration | true |
| `export_format` | Default export format | "excel" |
| `max_recent_files` | Maximum recent files to track | 10 |

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TENDER_CONFIG_PATH` | Custom config file path | "/path/to/config.json" |
| `TENDER_LOG_LEVEL` | Override log level | "DEBUG" |
| `TENDER_DATA_PATH` | Custom data directory | "/path/to/data/" |

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms**: Application fails to launch or crashes immediately

**Solutions**:
- Verify Python 3.8+ is installed
- Check all dependencies: `pip install -r requirements.txt`
- Review error logs in `logs/` directory
- Try running in debug mode

#### 2. Data Loading Problems

**Symptoms**: Files not loading or showing empty results

**Solutions**:
- Check file permissions and paths
- Verify file formats (Excel .xlsx/.xls or CSV)
- Ensure files are not corrupted
- Check available disk space
- Review data format compatibility

#### 3. Search Not Working

**Symptoms**: Search returns no results or incorrect matches

**Solutions**:
- Verify data is loaded successfully
- Check column names and data types
- Test with simple search terms
- Review filter configurations
- Check for special characters in search terms

#### 4. Performance Issues

**Symptoms**: Slow response, high memory usage, freezing

**Solutions**:
- Process large files in smaller chunks
- Increase system memory
- Close other applications
- Check for memory leaks in custom code
- Optimize data processing algorithms

#### 5. Export Problems

**Symptoms**: Export fails or produces incorrect files

**Solutions**:
- Check disk space and permissions
- Verify data is loaded and filtered correctly
- Try different export formats
- Check for special characters in data
- Review export configuration settings

### Error Messages

#### Common Error Messages and Solutions

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "No data loaded" | No data sources configured | Add data folders or files |
| "File not found" | Missing or moved files | Check file paths and permissions |
| "Permission denied" | Insufficient file permissions | Check file/folder permissions |
| "Out of memory" | Dataset too large | Process data in chunks or increase RAM |
| "Invalid file format" | Unsupported file type | Use Excel (.xlsx/.xls) or CSV files |
| "Database connection failed" | Database connectivity issues | Check network and credentials |

### Getting Help

1. **Check the logs**: Review `logs/` directory for detailed error information
2. **Review documentation**: Check this help file for solutions
3. **Search existing issues**: Look for similar problems in the issue tracker
4. **Create bug report**: Provide detailed information about the issue

### Performance Tips

- **Large datasets**: Process in chunks of 10,000-50,000 rows
- **Memory usage**: Monitor with system tools, restart if needed
- **Search optimization**: Use specific terms rather than broad searches
- **UI responsiveness**: Avoid loading very large datasets in UI
- **Caching**: Implement data caching for frequently accessed information

---

## 📚 API Reference

### Core Classes

#### TenderDataProcessor
Main data processing engine for tender data.

**Methods**:
- `load_data(file_paths)`: Load data from multiple files
- `apply_filters(filters)`: Apply search and filter criteria
- `export_data(format, path)`: Export data in specified format
- `get_statistics()`: Get data statistics and metrics

#### GlobalConfig
Configuration management system.

**Methods**:
- `get(key, default)`: Get configuration value
- `set(key, value)`: Set configuration value
- `save_config()`: Save configuration to file
- `load_config()`: Load configuration from file

#### RemoteDataLoader
Handles loading data from remote sources.

**Methods**:
- `load_from_remote_source(url, username, password)`: Load from remote URL
- `cleanup_temp_files()`: Clean up temporary downloaded files

### UI Classes

#### MainApplication
Main application window and controller.

**Methods**:
- `add_tab(name, tab_class)`: Add new tab to interface
- `show_message(message, type)`: Show message to user
- `get_active_tab()`: Get currently active tab

#### SearchDashboardTab
Search and dashboard functionality.

**Methods**:
- `load_data_from_folders()`: Load data from configured sources
- `apply_filters()`: Apply current search filters
- `export_results()`: Export filtered results

### Utility Functions

#### Data Processing Utilities
```python
from utils.data_utils import (
    clean_column_names,
    standardize_dates,
    validate_tender_data
)
```

#### UI Utilities
```python
from ui.common_widgets import (
    create_action_button,
    create_labeled_frame,
    create_info_label
)
```

---

## 🤝 Contributing

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/tender-management-v3.git
   cd tender-management-v3
   ```

3. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

5. **Run tests**:
   ```bash
   python -m pytest tests/
   ```

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Add docstrings to all public functions and classes
- Keep line length under 88 characters

### Commit Guidelines

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Reference issue numbers when applicable
- Keep commits focused on single changes

### Pull Request Process

1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** and test thoroughly

3. **Update documentation** if needed

4. **Run tests**:
   ```bash
   python -m pytest tests/
   ```

5. **Create pull request** with:
   - Clear description of changes
   - Screenshots if UI changes
   - Test results
   - Reference to related issues

### Testing

#### Writing Tests
```python
import unittest
from core.data_processor import TenderDataProcessor

class TestDataProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = TenderDataProcessor()

    def test_data_loading(self):
        # Test implementation
        pass

    def test_filtering(self):
        # Test implementation
        pass
```

#### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_data_processor.py

# Run with coverage
python -m pytest --cov=core tests/

# Run with verbose output
python -m pytest -v
```

### Documentation

- Update this help file for user-facing changes
- Add docstrings to new functions and classes
- Update API documentation for new features
- Include examples and usage instructions

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: [GitHub Pages](https://your-username.github.io/tender-management-v3/)
- **Issues**: [GitHub Issues](https://github.com/your-username/tender-management-v3/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/tender-management-v3/discussions)
- **Email**: support@tendermanagement.com

---

## 📈 Version History

- **v3.2** (Current): Enhanced saved searches, improved UI, better performance
- **v3.0**: Complete redesign, new architecture, advanced features
- **v2.0**: Enhanced functionality, improved stability
- **v1.0**: Initial release

---

*Last updated: September 30, 2025*
