# Tender Management Utility (v3)

## Overview
Desktop application (Tkinter) to load, search, filter, visualize, merge and manage tender data with calendar & task integration.

## Recent Updates
(NEW) Visual active date filter buttons (dark green highlight)  
(NEW) Reset All Filters restores original button colors  
(NEW) Treeview column sorting (chronological for dates, numeric & text fallback)  
(NEW) Export (Excel / CSV) retained  
(NEW) Build script (PyInstaller) with optional UPX compression  
(NEW) Settings Tab improvements & propagation of configuration changes  

## Key Features
- Multi-folder data load (Excel / CSV)
- Live search (department + global, AND/OR logic)
- Date presets: All, Live, Today, Next 3/7/30 Days, Expired, plus custom range
- Quick filters (live, expired, due, high value) framework
- Dashboard KPIs (live, expired, totals, due windows, etc.)
- Saved search profiles (load/save/delete)
- Calendar integration (single/multi row add with notes)
- Column configuration (order, visibility, width)
- Data visualization (departments & monthly distribution)
- Export visible filtered dataset
- Settings-driven merger + paths
- Executable build script

## Treeview Column Sorting (NEW)
Click any column header to sort.
- First click: Ascending (adds ↑)
- Second click: Descending (adds ↓)
- Date columns: Parsed to real datetime (even if original dtype is object)
- Numeric detection fallback
- Otherwise case-insensitive text sort
- Stable sort (mergesort) so relative order of equal rows persists
- Sort reapplied automatically after filtering

## Date Filter Visual Feedback (NEW)
- Active preset button turns dark green (#2E7D32)
- Reset All Filters restores original palette:
  - All: gray
  - Live: green
  - Expired: red
  - Others: blue
- Custom range selection still works alongside presets

## Building Executable
Run:
```
python build_exe.py
```
Requirements:
- pyinstaller installed
- (Optional) UPX in PATH for compression
Outputs to: dist/TenderManagementUtility/

## Settings Tab
Configurable:
- Default data folder
- Merged data folder
- Preferred unique keys (ordered) for merge logic
- Critical fields for change detection
- Max backups per portal
Propagates changes to active tabs (Search & Portal Merger).

## Calendar Integration
Right-click row(s) → Add to Calendar / Add multiple  
Prompts for notes & (if missing) closing date.

## Column Configuration
Column Settings → reorder (▲/▼), toggle visibility, adjust widths, reset defaults.

## Saved Searches
Name + persist filters (dept/global/date). Stored in config JSON.

## Export
Exports only visible columns in current order.

## Visualization
Bar: Top 15 departments  
Line: Monthly distribution (if a datetime closing/date column detected)

## Build Script Notes
- Cleans previous build
- Adds required folders as data (utils, ui, core, config, resources)
- Copies default config post-build
- Reports size & timing

## Error Handling & Logging
Central logging configuration.
Graceful warnings (missing folders, no data, dependency absence).

## Roadmap / Ideas
- Persist column config across sessions
- Multi-key sorting (Shift+Click)
- Inline cell search highlighting with colored spans (current row-level tag)
- Task tab expansion
- Theming toggle (light/dark)

## Changelog (Excerpt)
v3.0  
- Added sortable Treeview headers  
- Added active date filter visual state + reset restoration  
- Added build_exe.py automation  
- Enhanced settings propagation  
- Improved calendar dialogs (notes & date picker)  

## Quick Start
1. Set default folders in Settings.
2. Add data folders in Search & Dashboard.
3. Use live filters + date presets.
4. Click column headers to sort.
5. Save frequent filter sets.
6. Add critical tenders to Calendar.
7. Export or visualize as needed.

## Support
Ensure required packages installed:
```
pip install pandas tkcalendar openpyxl matplotlib
```
(Visualization optional if matplotlib absent.)

---
