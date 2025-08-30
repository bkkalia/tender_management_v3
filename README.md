# Tender Management Utility (v3.1)

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
v3.1  
- Version bump: UI now reflects 3.1 (minor maintenance update)  

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

## Suggested Improvements & New Features

### High Impact / Quick Wins
- Persist column configuration: save visible columns, order, widths, last sort column/direction in config.
- Multi-column sort: Shift+Click additional headers to create sort priority list.
- Column header filter row: optional mini entries or dropdowns per column (exact / contains).
- Auto reapply last session: restore last loaded folders, filters, and sort state.
- Keyboard shortcuts: e.g. Ctrl+F (focus global search), F5 (refresh data), Ctrl+S (save search), Alt+R (reset filters).
- Status bar enhancements: show active sort + filter count.
- Dark mode toggle (store in config).

### UX / Visualization
- Conditional cell coloring (e.g., deadlines approaching: today = red, 3 days = orange, 7 days = yellow).
- Inline badge for Expired / Live in a dedicated Status column.
- Tooltip previews for truncated Title / Department.
- Mini sparkline widget in dashboard for last 30‑day tender counts.
- Export profiles: predefined column sets (Minimal / Full / Reporting).

### Search & Filtering Enhancements
- Fuzzy search (rapidfuzz) with adjustable threshold.
- Saved search tagging + grouping.
- Advanced query syntax: dept:"Roads" AND ("bridge" OR "culvert") NOT test.
- Date range sliders (optional alt UI).
- Filter history (undo last N filter changes).

### Performance / Scalability
- Background thread pool for file loading & parsing (non-blocking UI).
- Incremental data index for faster repeated searches (e.g. whoosh or in-memory inverted index).
- Virtualized table rendering (replace Treeview with a Canvas-based virtual list for >50k rows).
- Cached dashboard metrics (invalidate only on data change).

### Data Quality / Integrity
- Data validation report: missing critical fields, malformed dates, duplicate IDs.
- Change tracker: highlight rows whose critical fields changed since last load.
- Hash-based duplication detection across folders.

### Calendar & Notifications
- Auto reminders: optional notification popup X days before closing.
- iCal (.ics) export for selected tenders.
- Batch rule: auto-add to calendar when Closing Date within N days and value > threshold.

### Automation / Integration
- Scheduled folder rescan (interval-based) with delta detection.
- Webhook / email export of daily expiring tenders.
- Plugin architecture for portal scrapers (standard interface: fetch(), normalize()).

### Collaboration / Persistence
- Profile switcher (different configs per user).
- Optional cloud sync (OneDrive/Google Drive) for saved searches & layouts.
- Audit log view (who added calendar events, edits, exports).

### Advanced Analytics
- Pivot summary (by department, month, status).
- Value aggregation (sum, median if numeric value column present).
- Trend anomaly detection (sudden spike/decline warnings).

### Reliability / Diagnostics
- In-app log viewer filters (level, source module).
- Self-test utility: verify dependencies, writable dirs, config schema.
- Crash recovery: autosave session state snapshot every X minutes.

### Extensibility Roadmap
| Tier | Feature | Notes |
|------|---------|-------|
| 1 | Persist columns + sort | Low effort, high usability |
| 1 | Multi-column sorting | Build upon existing sort handler |
| 2 | Fuzzy search | Rapidfuzz integration |
| 2 | Virtualized table | Biggest performance uplift |
| 3 | Plugin scrapers | Requires interface spec |
| 3 | Cloud sync | Add abstraction layer for storage |

### Possible Internal Refactors
- Separate Treeview adapter class (sorting, highlighting, URL tagging).
- Event bus (pub/sub) for filters, data reload, and dashboard updates.
- Unified dialog factory (calendar, notes, date picker).
- Wrap config access with schema validation (pydantic or manual).

### Security / Safety (Future)
- Optional hashing of exported files for integrity.
- Sanitization layer for user-entered notes (avoid injection in future HTML exports).

---

Feel free to prune or re-order based on priority.
