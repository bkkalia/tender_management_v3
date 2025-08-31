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
(NEW) Debounced & asynchronous filtering for large datasets (performance)  

## Implemented Performance Enhancements (v3.1)
- Debounced live search (250 ms) to prevent a full filter pass on every keystroke.
- Asynchronous filtering: for datasets >= 50K rows filtering runs in a background thread, UI stays responsive.
- Stable, type-aware sorting (datetime → numeric → text) with single pass key materialization.
- Guarded Treeview refresh: skips update when widget not yet created or no data.
- Ensured filtered_data DataFrame always exists (avoids attribute errors & conditional branches).
- Reduced redundant lower/regex passes by only transforming values during visible row materialization.
- Deferred heavy filter UI updates to main thread via after() for thread safety.
- Safe fallbacks for empty / non-scalar cell values preventing render-time exceptions.
- Prepared scaffolding for future indexing & virtualization (clean points for extension).
- NEW (experimental) In‑memory inverted token index (built for large datasets) speeds Global Search (AND/OR) by set intersections instead of full DataFrame scans.

## Notes on Search Architecture
Current baseline search operates fully in memory using pandas DataFrame boolean masks.  
When dataset size ≥ threshold (default 5,000 rows), an inverted index over selected text columns (e.g. Title, Department) is built:
- Tokenization: alphanumeric lowercased tokens length ≥ 2
- Global Search uses index (AND = set intersection, OR = set union)
- Falls back automatically if index not built or tokens absent
- Department + date filters layered after index narrowing
Future steps: multi-column indices, phrase search, fuzzy tokens, hybrid DuckDB / Polars backend, virtualization for 10M+ rows.

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

## Performance & Scalability Strategy (Toward 10M Rows)

### Current Bottlenecks
- Full DataFrame scan each keystroke (live search).
- Tkinter Treeview renders all rows (no virtualization).
- Repeated string lower/regex each filter pass.
- Single-threaded UI + compute on main thread.

### Implemented (v3.1 minor)
- Debounced filtering (reduces calls while typing).
- Async filter thread for large datasets (UI stays responsive).

### Short Term (≤100K rows)
- Cache lowercased columns for case-insensitive search.
- Precompile regex / token split once.
- Maintain filtered row index list instead of slicing whole DataFrame repeatedly.
- Only rebuild Treeview if result set actually changed (hash row ids).

### Mid Term (≤1M rows)
- Virtualized table (only render visible slice). Replace ttk.Treeview with:
  - ttk.Treeview + yview interception + recycle rows, or
  - Custom Canvas-based grid (row windowing).
- Inverted index for text fields (token -> row ids).
- Columnar storage (Parquet) + lazy load: keep only needed columns in memory.
- Background loading & incremental append (show partial results early).
- Persistent cache of parsed & normalized dataset (Arrow / Feather).

### Large Scale (1M–10M+)
- Query Engine Integration:
  - DuckDB: run SQL over Parquet directly (zero-copy Arrow).
  - Polars (lazy): vectorized, parallel query plans.
  - Optional fallback to pandas for small loads.
- Hybrid architecture:
  - Metadata / index layer in memory (row id, key fields, offsets).
  - On-demand fetch of full row detail when selected (master-detail pattern).
- Batched UI updates (chunk 1–2K rows into Treeview when scrolling).
- Pre-sorted projections (e.g., by Closing Date) for fast range queries.

### GPU Opportunities
- RAPIDS cuDF (if NVIDIA + suitable driver):
  - GPU DataFrame operations for filters/sorts/groupby.
  - Keep CPU fallback path (detect cudf import).
  - Transfer minimal columns to GPU; avoid round-tripping full dataset each query.
- Limitations: Tkinter rendering remains CPU-bound; GPU accelerates filter prep only.

### Suggested Layered Backend
1. Loader:
   - Detect file size; choose backend (pandas < 200K, Polars/DuckDB otherwise).
2. Indexer:
   - Build token index for selected text columns.
   - Build date range index (sorted list of (timestamp, row_id)).
3. Query Planner:
   - Compose boolean masks from:
     - Token set intersections (OR/AND logic).
     - Date range via bisect on sorted dates.
     - Department filter via precomputed mapping dept -> row ids.
4. Materializer:
   - Produce lightweight list of row ids; only gather full row values for visible window.

### Algorithmic Notes
- Token Index: O(N * avg_tokens) build, then O(k) set intersections per query.
- Date Filter: O(log N) bounds + O(result) merging vs O(N) scan.
- Window Rendering: constant-time per visible row; overall UI cost O(visible_rows).

### Memory Tips
- Convert categorical-like columns (Department, Status) to category dtype.
- Use pd.to_datetime(..., cache=True) once.
- Drop raw text/HTML columns not displayed.
- Persist processed DataFrame (.parquet) for instant reload.

### Async / Threading
- Use worker thread for filter computation; communicate via queue.
- Avoid touching Tk widgets outside main thread.
- For CPU-bound heavy queries, consider multiprocessing (DuckDB/Polars may already parallelize).

### Roadmap Order
1. Debounce + async (DONE)
2. Cache lowercased & token lists
3. Virtualized table
4. Inverted index + date index
5. Backend switch (DuckDB/Polars)
6. GPU (optional RAPIDS path)
7. Master-detail lazy expansion

### Validation & Profiling
- Use cProfile + snakeviz on representative 100K & 1M synthetic datasets.
- Track:
  - Filter latency P95
  - UI thread blocked time
  - Memory footprint (RSS)
- Add a diagnostics panel (future) to display timings.

---

Feel free to prune or re-order based on priority.
