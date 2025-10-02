# Tender Management Utility v3.2

[![Latest Version](https://img.shields.io/badge/version-3.2-blue.svg)](https://github.com/cloud84/tender-management-utility)
[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A powerful desktop application for loading, searching, filtering, visualizing, and managing large datasets of tender data with advanced performance monitoring and calendar integration.

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- pandas, tkinter, openpyxl, matplotlib, and other dependencies

### Installation
```bash
# Clone the repository
git clone https://github.com/cloud84/tender-management-utility.git
cd tender-management-utility

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Build Executable
```bash
# Run the build script
python scripts/build_exe.py
```

## 📊 Performance Highlights

- **700K+ rows processed in 0.6 seconds**
- **99% data accuracy rate**
- **2.1M records/second peak performance**
- **Memory efficient**: 414MB peak for 300K records

## 🎯 Key Features

- **Advanced Data Processing**: Multi-folder Excel/CSV loading with intelligent merging
- **Smart Search & Filtering**: Live search with department filters and date presets
- **Real-time Dashboard**: Dynamic KPIs with instant updates
- **Calendar Integration**: Export tender deadlines to calendar applications
- **Data Visualization**: Interactive charts for department distribution and trends
- **Performance Monitoring**: Real-time CPU, memory, and disk usage tracking
- **Advanced Testing Suite**: GUI-based performance testing with detailed reports

## 📁 Project Structure

```
tender-management-utility/
├── main.py                    # Main application entry point
├── requirements.txt           # Python dependencies
├── app_config.json           # Application configuration
├── pyrightconfig.json        # Python type checking config
├── scripts/                  # Build and utility scripts
│   ├── build_exe.py
│   ├── build_with_spec.py
│   └── compile_research_report.py
├── benchmark/                # Performance testing and reports
│   ├── comprehensive_benchmark_report_*.json
│   ├── *.png                 # Performance charts
│   └── *_benchmark.py        # Benchmark scripts
├── docs/                     # Documentation
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── FAQ.md
│   ├── HELP.md
│   └── INSTALLATION.md
├── tests/                    # Test files
│   ├── test_ocr_functionality.py
│   └── test_saved_searches.py
├── tools/                    # Utility tools
│   └── dummy_data_generator.py
├── data/                     # Data files and samples
│   ├── calendar_events.json
│   ├── categories.json
│   └── export_test_data.xlsx
├── config/                   # Configuration files
├── core/                     # Core application modules
├── ui/                       # User interface components
├── utils/                    # Utility functions
├── logs/                     # Application logs
└── resources/                # Static resources
```

## 📖 Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[User Manual](docs/HELP.md)** - Complete user guide
- **[FAQ](docs/FAQ.md)** - Frequently asked questions
- **[Changelog](docs/CHANGELOG.md)** - Version history and updates
- **[Performance Testing](docs/PERFORMANCE_TESTING_README.md)** - Benchmarking guide
- **[Contributing](docs/CONTRIBUTING.md)** - Development guidelines

## 🧪 Testing & Benchmarks

Run comprehensive performance tests:
```bash
# Run benchmark suite
python benchmark/comprehensive_benchmark_suite.py

# View detailed reports
python benchmark/comprehensive_benchmark_report_20250930_112151.json
```

## 🏗️ Architecture

Built with modern Python technologies:
- **Tkinter + Ttk**: Native Windows GUI framework
- **Pandas**: High-performance data processing
- **Matplotlib**: Data visualization and charting
- **Psutil**: System performance monitoring
- **OpenPyXL**: Excel file processing
- **TkCalendar**: Date picker widgets

## 📈 Performance Monitoring

Real-time system monitoring with:
- CPU usage tracking
- Memory consumption analysis
- Disk I/O monitoring
- Performance metrics logging
- Automated benchmark reporting

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details.

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run linting
python -m flake8
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [User Manual](docs/HELP.md)
- **Issues**: [GitHub Issues](https://github.com/cloud84/tender-management-utility/issues)
- **Discussions**: [GitHub Discussions](https://github.com/cloud84/tender-management-utility/discussions)

## 🙏 Acknowledgments

- Built with cutting-edge Python technologies
- Performance optimized for large datasets
- Designed for procurement professionals and organizations

---

**Tender Management Utility v3.2** - Professional tender data management with unparalleled performance and user experience.
