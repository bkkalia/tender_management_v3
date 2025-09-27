# Tender Management Utility v3 - Frequently Asked Questions

## 📋 Table of Contents

1. [General Questions](#general-questions)
2. [Installation & Setup](#installation--setup)
3. [Features & Functionality](#features--functionality)
4. [Data Management](#data-management)
5. [Licensing & Pricing](#licensing--pricing)
6. [Technical Support](#technical-support)
7. [Troubleshooting](#troubleshooting)
8. [Custom Development](#custom-development)

---

## 🤔 General Questions

### What is Tender Management Utility v3?
Tender Management Utility v3 is a comprehensive desktop application built with Python and Tkinter that helps organizations efficiently manage, search, filter, visualize, and analyze tender data from multiple sources. It provides advanced data processing capabilities with calendar integration and real-time dashboard analytics.

### Who can benefit from using this application?
- **Government Agencies**: Streamline procurement processes and ensure compliance
- **Construction Companies**: Manage multiple tender opportunities and optimize bidding strategies
- **Procurement Teams**: Centralize data management and improve team collaboration
- **Consulting Firms**: Provide value-added services to clients
- **Any organization dealing with tender/procurement data**

### What makes v3 different from previous versions?
Version 3.1 includes significant performance enhancements:
- Debounced asynchronous filtering for large datasets (50K+ rows)
- Advanced search with inverted token indexing
- Improved memory management and multi-threaded processing
- Enhanced user interface with real-time dashboard updates
- Saved search profiles with export/import functionality

---

## 🚀 Installation & Setup

### What are the system requirements?
- **Operating System**: Windows 7 SP1 or later (64-bit)
- **Python**: Version 3.7 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended for large datasets
- **Storage**: 500MB free space
- **Display**: 1024x768 minimum resolution

### How do I install the application?
1. **Using Installer** (Recommended):
   - Download the latest installer from our website
   - Run the installer executable
   - Follow the on-screen instructions
   - Launch from desktop shortcut

2. **Manual Installation**:
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt

   # Run the application
   python main.py
   ```

### What dependencies are required?
The application requires these Python packages:
- `pandas` - Data processing and analysis
- `tkcalendar` - Calendar widgets
- `openpyxl` - Excel file support
- `matplotlib` - Data visualization (optional)
- `filelock` - Safe file operations

### Can I use it on Google Drive?
Yes, but ensure all users have the required dependencies installed. The application uses file locking for safety when working with shared files on network drives.

---

## ⚙️ Features & Functionality

### What file formats are supported?
- **Excel files**: .xlsx and .xls formats
- **CSV files**: All standard CSV formats with various delimiters
- **Remote URLs**: HTTP/HTTPS URLs for cloud-based data sources

### How does the search functionality work?
The application provides multiple search options:
- **Department Search**: Search within department/agency columns
- **Global Search**: Search across all columns
- **Date Filtering**: Live, expired, today, next 3/7/30 days, custom ranges
- **AND/OR Logic**: Combine multiple search terms
- **Live Search**: Real-time filtering as you type (debounced for performance)

### What dashboard metrics are available?
- Total tenders loaded
- Live vs expired tender counts
- Due date windows (today, next 3/7 days)
- Department distribution
- Filter match percentages
- Real-time updates as you apply filters

### How does calendar integration work?
- Right-click on tender rows to add to calendar
- Supports single or multiple row selection
- Add custom notes and closing dates
- Compatible with Outlook, Google Calendar, and other calendar applications
- Export in standard calendar formats

### Can I save my search configurations?
Yes! The application includes:
- **Saved Search Profiles**: Save and load frequently used filter combinations
- **Export/Import**: Share search configurations between team members
- **Persistent Settings**: Column configurations and preferences are saved automatically

---

## 📊 Data Management

### How large can my datasets be?
- **Current Testing**: Successfully handles 14,000+ rows
- **Hardware Dependent**: Can scale to 10M+ rows with adequate RAM and processing power
- **Performance**: Processes 10,000 rows in under 30 seconds on typical hardware
- **Optimization**: Uses asynchronous filtering and memory management for large datasets

### What data quality features are included?
- **Automatic Deduplication**: Identifies and removes duplicate entries
- **Data Cleaning**: Handles missing values and formatting issues
- **Date Validation**: Ensures proper date/time formatting
- **Type Detection**: Automatically identifies data types for proper processing

### How does data merging work?
The portal merger feature:
- **Unique Key Matching**: Uses configurable unique keys for merging
- **Intelligent Conflict Resolution**: Handles overlapping data gracefully
- **Backup System**: Automatic backups before merging operations
- **Change Detection**: Tracks modifications between data updates

### Is my data secure?
- **Local Processing**: All data processing happens on your local machine
- **No External Uploads**: Data never leaves your computer unless you explicitly export it
- **File Locking**: Safe concurrent access on network drives
- **No Telemetry**: No data collection or tracking

---

## 💰 Licensing & Pricing

### Is the software free?
Yes, for **non-commercial use**! The application is free for:
- Individual users
- Educational institutions
- Non-profit organizations
- Research and academic purposes

### When do I need a commercial license?
A commercial license is required for:
- Business operations
- Government agency deployments
- Any revenue-generating activities
- Commercial deployments and installations

### How much does a commercial license cost?
- **Starting Price**: $499 per year
- **Includes**: Unlimited commercial use, priority support, custom modifications
- **Volume Discounts**: Available for multiple licenses
- **Enterprise Options**: Custom deployment and support packages

### What support is included with commercial licenses?
- **Priority Technical Support**: Fast response times
- **Custom Modifications**: Tailored features and integrations
- **Professional Services**: Implementation assistance and training
- **Enterprise Deployment**: Large-scale deployment support

---

## 🆘 Technical Support

### How do I get help?
- **Documentation**: Comprehensive HELP.md and README.md files
- **Community Support**: Free for non-commercial users
- **Priority Support**: Included with commercial licenses
- **Contact**: licensing@cloud84.com for commercial inquiries

### What if I encounter a bug?
1. **Check Logs**: Review the `logs/` directory for error details
2. **Verify Requirements**: Ensure all dependencies are installed
3. **Check File Permissions**: Ensure read/write access to data directories
4. **Contact Support**: Provide detailed error information and steps to reproduce

### Are there any known limitations?
- **Memory Usage**: Large datasets (1M+ rows) require significant RAM
- **File Size Limits**: Limited by available system memory
- **Network Dependencies**: Remote URL loading requires internet connectivity
- **Platform**: Currently Windows-only (Python Tkinter limitation)

---

## 🔧 Troubleshooting

### The application won't start. What should I do?
1. **Check Python Version**: Ensure Python 3.7+ is installed
2. **Install Dependencies**: Run `pip install -r requirements.txt`
3. **Check File Paths**: Ensure the application directory structure is intact
4. **Review Logs**: Check `logs/` directory for startup errors
5. **Run from Source**: Try `python main.py` instead of the executable

### Data loading is slow or failing. What can I cause this?
- **File Permissions**: Ensure read access to data files
- **File Format**: Verify Excel/CSV files are not corrupted
- **Memory Issues**: Close other applications for large datasets
- **Network Issues**: For remote URLs, check internet connectivity
- **File Size**: Split very large files into smaller chunks

### Search results are not what I expected. Why?
- **Case Sensitivity**: Search is case-insensitive by default
- **Date Formats**: Ensure dates are in recognizable formats
- **Column Names**: Verify the columns you're searching contain the expected data
- **Filter Combination**: Check if multiple filters are conflicting

### The application is using too much memory. How can I optimize?
- **Process in Chunks**: Load data in smaller batches
- **Close Unused Tabs**: Free up memory by closing unnecessary interface elements
- **Clear Filters**: Reset filters to reduce active dataset size
- **Restart Application**: Clear memory leaks from extended use

---

## 🛠️ Custom Development

### Do you offer custom development services?
Yes! We specialize in creating tailored Python applications including:
- **Custom Data Processing Tools**
- **Integration Solutions**
- **Automation Scripts**
- **Desktop Applications**
- **Data Analysis Utilities**

### What technologies do you work with?
- **Primary**: Python, Tkinter, pandas, matplotlib
- **Databases**: SQLite, PostgreSQL, MongoDB
- **APIs**: RESTful APIs, web scraping, data integration
- **Cloud**: AWS, Google Cloud, Azure integration
- **Deployment**: Executable builds, containerization

### How do I request custom development?
1. **Contact Us**: Visit https://cloud84.in/contact/
2. **Describe Requirements**: Provide detailed specifications
3. **Project Scope**: Define timeline and deliverables
4. **Get Quote**: Receive customized pricing and timeline

### What is your development process?
1. **Requirements Gathering**: Detailed analysis of needs
2. **Solution Design**: Architecture and technology selection
3. **Development**: Iterative development with regular updates
4. **Testing**: Comprehensive testing and quality assurance
5. **Deployment**: Installation and training support
6. **Support**: Ongoing maintenance and updates

---

## 📞 Contact Information

- **Website**: https://cloud84.com
- **Contact Page**: https://cloud84.in/contact/
- **Commercial Licensing**: licensing@cloud84.com
- **Support**: Priority support included with commercial licenses

---

*This FAQ is regularly updated. Last updated: September 27, 2025*

---

## 🔗 Quick Links

- [Installation Guide](INSTALLATION.md)
- [User Documentation](HELP.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](ROADMAP.md)
- [License](resources/license.txt)
