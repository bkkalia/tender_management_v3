# AI Agent Instructions for Tender Management Utility (Version 3)

## 🎯 **Project Vision & Core Goals**

This Python application is a **Tender Search & Management Utility (Version 3)**.
The primary goal is to rewrite an existing application to be more robust, maintainable, and feature-rich, focusing on:

1.  **Advanced Search & Dashboard:** Process Excel/CSV tender data, offer advanced filtering with precise date/time handling, and display key metrics on a dynamic dashboard.
2.  **Excel File Merging:** Intelligently merge new daily scraped tender data (Excel/CSV) with existing consolidated data, handling duplicates and (eventually) changes.
3.  **Calendar & Basic Team Management:** Manage tender deadlines and assignments (future phase, placeholders for now).
4.  **Global Settings:** Centralized configuration for all application modules.
5.  **Logging:** Comprehensive logging for diagnostics and auditing.

**Target Users:** Small teams managing tender procurement processes.
**Data Source:** Primarily Excel and CSV files, often from daily web scrapes.

---

## 🏗️ **Core Architecture & Design (MANDATORY)**

*   **Language:** Python 3.x
*   **UI Framework:** `tkinter` with `ttk` for theming.
*   **Modularity:** Code is organized into `ui/`, `core/`, and `utils/` directories.
*   **MVC (Model-View-Controller) Influence:**
    *   **View:** UI elements in `ui/` (e.g., `SearchDashboardTab`, `PortalDataMergerTab`).
    *   **Controller/Logic:** Core processing logic in `core/` (e.g., `TenderDataProcessor`, `PortalDataMerger`).
    *   **Model (Data Structures):** Primarily `pandas` DataFrames for tender data. Future: Pydantic/dataclasses for structured objects.
*   **Configuration-Driven:**
    *   `GlobalConfig` (`core/config_manager.py`) manages `app_config.json`.
    *   `FeatureConfig` for module-specific settings (future).
*   **Error Handling:**
    *   Use `try-except` blocks for operations that might fail (file I/O, data processing).
    *   Log errors using the `logging` module.
    *   Provide user-friendly messages via `tkinter.messagebox`.
*   **Logging:**
    *   Standard `logging` module, configured in `utils/logger_setup.py`.
    *   Use `logger = logging.getLogger(__name__)` in each module.
    *   Employ appropriate log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

---

## 🎨 **UI/UX Guidelines (MANDATORY)**

*   **Constants:** Colors, Fonts, Spacing are defined in `utils/constants.py`. ALWAYS use these.
    *   `COLORS['primary']`, `FONTS['heading']`, `SPACING['medium']`.
    *   New fonts added: `'button'` for consistent button styling.
    *   Colors include basic colors like `'white'` and `'black'` for contrast.
*   **Common Widgets:** Use helper functions from `ui/common_widgets.py`:
    *   `create_labeled_frame()`
    *   `create_action_button()` (uses `ttk.Button` with basic styling)
    *   `create_info_label()`
    *   `create_input_entry()`
*   **Layout:** Use `pack()` and `grid()` appropriately. Prefer `ttk` widgets over base `tk` widgets for better theming.
*   **Responsiveness:** Ensure UI elements resize and arrange reasonably.
*   **Tooltips:** Use the `create_tooltip()` function to add helpful hover text to UI elements.

---

## 💾 **Data Management**

*   **Input:** Excel (`.xlsx`, `.xls`) and CSV (`.csv`) files. Use `pandas` for reading.
    *   `pd.read_excel(..., engine='openpyxl')`
    *   `pd.read_csv(...)`
*   **Main Data Structure:** `pandas.DataFrame` for tender lists.
*   **Date/Time Handling (CRITICAL):**
    *   **Closing Date Processing:** All closing date columns must be converted to `datetime` objects with full date AND time information.
    *   **Time Precision:** When comparing dates for expiry/live status, use `pd.Timestamp.now()` (includes time) rather than `datetime.now().date()` (date only).
    *   **Missing Time Data:** If source data contains only dates without time, assume end-of-day (23:59:59) for closing dates to be conservative.
    *   **Timezone Handling:** Consider local timezone for accurate comparisons (future enhancement).
*   **Data Processing:**
    *   `TenderDataProcessor` (`core/data_processor.py`): Handles loading, filtering, and calculating dashboard stats for the Search tab.
        *   **Enhanced Date Filtering:** Must support precise time-based filtering for Live/Expired status.
        *   **Filter Categories:** All, Live (closing date/time > now), Expired (closing date/time <= now).
    *   `PortalDataMerger` (`core/file_merger.py`): Handles merging logic.
        *   **Unique Key for Merging:** Defined in `GlobalConfig` (e.g., `merger_unique_key`).
        *   **Critical Fields for Change Detection (Future):** Defined in `GlobalConfig`.
*   **Storage:**
    *   Input files are user-provided.
    *   Merged files are saved to a user-configurable output directory.
    *   Application settings (`app_config.json`) are saved by `GlobalConfig`.
*   **File Management:**
    *   Properly initialize variables before use to avoid "unbound variable" errors.
    *   Initialize placeholders for data structures that are populated later.

---

## 🐍 **Python Coding Standards (MANDATORY)**

1.  **Type Hints:** Use type hints for function signatures and important variables.
    ```python
    from typing import List, Dict, Any, Optional, Tuple
    import pandas as pd

    def process_data(data: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        # ...
        pass
    ```
2.  **Docstrings:** Write clear docstrings for classes and public methods (Google style or reST style).
    ```python
    class MyClass:
        """
        Brief description of the class.

        More detailed explanation if needed.

        Attributes:
            attribute_name (type): Description of attribute.
        """
        def my_method(self, param1: int) -> str:
            """
            Brief description of method.

            Args:
                param1: Description of parameter 1.

            Returns:
                Description of what is returned.

            Raises:
                SomeException: If something goes wrong.
            """
            pass
    ```
3.  **Imports:**
    *   Organize imports: standard library, then third-party, then local application modules.
    *   Use absolute imports for local modules (e.g., `from core.data_processor import TenderDataProcessor`).
    *   For type checking only, use `if TYPE_CHECKING:` block.
4.  **Naming Conventions:**
    *   `snake_case` for functions, methods, variables, and modules.
    *   `PascalCase` (or `CamelCase`) for classes.
    *   `UPPER_SNAKE_CASE` for constants.
5.  **Clarity & Readability:** Prioritize clear, understandable code. Avoid overly complex one-liners.
6.  **Error Handling (Reiteration):**
    ```python
    try:
        result = risky_operation()
        logger.info(f"Operation successful: {result}")
    except FileNotFoundError as e:
        logger.error(f"File not found during operation: {e}")
        messagebox.showerror("File Error", f"Could not find file: {e.filename}")
    except pd.errors.EmptyDataError as e:
        logger.warning(f"Empty data encountered: {e}")
        # Handle gracefully
    except Exception as e:
        logger.critical(f"Unexpected error in operation: {e}", exc_info=True)
        messagebox.showerror("Unexpected Error", "An unexpected error occurred. Please check logs.")
        # Potentially re-raise or handle specific fallback
    ```
7.  **Variable Initialization:** 
    *   Always initialize variables before use to avoid "unbound variable" errors.
    *   Use default/empty values for containers that will be populated later.

---

## ⚙️ **Current Focus / Tasks**

*   **PRIORITY 1: Date/Time Filter System Overhaul:**
    *   **Precise Time Handling:**
        *   Update `TenderDataProcessor._identify_and_convert_date_columns()` to preserve time information when converting date columns.
        *   For dates without time, append "23:59:59" to closing dates for conservative expiry calculations.
        *   Use `pd.Timestamp.now()` instead of `datetime.now().date()` for all date comparisons.
    *   **Enhanced Filter Options:**
        *   **All:** Show all records regardless of closing date/time.
        *   **Live:** Show only tenders where closing date/time > current date/time.
        *   **Expired:** Show only tenders where closing date/time <= current date/time.
        *   **Today:** Closing between start of today and end of today.
        *   **Next 3/7/30 Days:** Closing within the specified timeframe from now.
        *   **Custom Range:** User-specified date/time range.
    *   **Dashboard Stats Update:**
        *   Ensure all dashboard statistics (closing_today, expired_tenders, etc.) use precise time comparisons.
        *   Add "Live Tenders" count to dashboard.

*   **PRIORITY 2: Filter System Review & Fixes:**
    *   **Department Filter:**
        *   Verify case-insensitive matching works correctly.
        *   Test both OR and AND operators with multiple comma-separated terms.
        *   Ensure department column detection is robust across different data sources.
    *   **Global Search Filter:**
        *   Verify live search (on key release) functionality.
        *   Test OR and AND operators with multiple search terms.
        *   Ensure search works across all text columns correctly.
    *   **Date Filter Integration:**
        *   Verify that date filters work in combination with text filters.
        *   Test preset date buttons (Today, Next 3 Days, etc.) for accuracy.
        *   Ensure custom date range picker works correctly.
    *   **Filter Interaction Testing:**
        *   Test combinations of department + global search + date filters.
        *   Verify filter reset functionality clears all active filters.
        *   Ensure saved search profiles work correctly.

*   **Bug Fixing & Performance:**
    *   Address any remaining errors from filter operations.
    *   Optimize filter performance for large datasets.
    *   Fix any UI responsiveness issues during filtering.

*   **Search & Dashboard (`SearchDashboardTab`) - Continued:**
    *   Reliable data loading from multiple Excel/CSV files within selected folders. **Data loading should be live when folders are added.**
    *   **Updated filtering workflow:**
        1. Apply date/time filters with precise timestamp comparisons.
        2. Apply department filters with improved pattern matching.
        3. Apply global search filters across all relevant columns.
    *   Correct population of the `ttk.Treeview` with filtered data.
    *   Dynamic update of dashboard statistics with time-aware calculations.
    *   **Implement copy functionality for Treeview (cell, row, selected rows).**
    *   **Handle URLs in Treeview: double-click to open in browser; copy should provide the original URL.**

*   **Excel File Merging (`PortalDataMergerTab` & `core/file_merger.py`):**
    *   **UI Workflow:**
        *   User selects one or more *new data files* (daily scrapes) using a listbox.
        *   User specifies a single *output folder* where all consolidated master files and backups will be stored.
        *   The UI **does not** have an input for "Existing Consolidated File"; this is handled automatically.
    *   **Automated Processing per File:**
        *   For each new file selected by the user:
            *   The system extracts the `portal_name` from the new file's name.
            *   It automatically looks for `{portal_name}_consolidated_master.ext` in the specified output folder to use as the existing data. If not found, the new file starts a new master for that portal.
    *   **Portal-Specific Merging:**
        *   The output consolidated file is named consistently per portal (e.g., `output_folder/{portal_name}_consolidated_master.xlsx`).
    *   **Dynamic Unique Key for Merging:**
        *   The system attempts to use a unique key from a preferred list (e.g., "Tender ID (Extracted)", then "Title and Ref.No./Tender ID", then "Tender ID").
        *   The chosen key must exist in the new data file and, if an existing file is being merged, in the existing data file as well.
    *   **Merging Logic with Time Awareness:**
        *   Convert date columns (e.g., 'Closing Date', 'e-Published Date') in both new and existing data to datetime objects, preserving time information.
        *   Concatenate new data with existing data (if any for the portal).
        *   Ensure the chosen `unique_key` column is of string type for consistent de-duplication.
        *   **Sort** the combined data:
            1.  By `unique_key` (ascending).
            2.  Then by `Closing Date` (descending, `na_position='last'` to prioritize valid and later dates).
            3.  Then by `e-Published Date` (descending, `na_position='last'`) as a secondary tie-breaker.
        *   Drop duplicates based on the `unique_key`, keeping the **'first'** record. Due to the prior sorting, this 'first' record will be the one with the latest `Closing Date`.
        *   Future: Implement change detection for `merger_critical_fields` and conflict resolution.
    *   **Backup System:**
        *   Before creating/updating a portal's consolidated master file, if an existing version of that master file is found, it's backed up.
        *   Backups are stored as timestamped ZIP files in a dedicated subfolder (e.g., `output_folder/portal_backups/{portal_name}/`).
        *   A maximum of 5 backup versions are kept per portal; older ones are automatically deleted.
    *   Saving the merged file to the specified output folder, using the portal-specific standardized name.

*   **Settings (`SettingsTab`):**
    *   Allow viewing and editing of key paths (`default_data_folder`, `merged_data_folder`) and merger parameters (`merger_unique_key`, `merger_critical_fields`).
    *   Ensure settings are correctly loaded from and saved to `app_config.json`.
    *   Propagate config changes to relevant components (e.g., re-initialize `TenderDataProcessor` if paths change).

## 🔍 **Filter System Specifications (NEW)**

### **Date/Time Filter Requirements:**
1. **Time Precision:** All date comparisons must include time components, not just dates.
2. **Filter Types:**
   - **All:** No date filtering applied.
   - **Live:** `closing_datetime > pd.Timestamp.now()`
   - **Expired:** `closing_datetime <= pd.Timestamp.now()`
   - **Today:** `start_of_today <= closing_datetime <= end_of_today`
   - **Next X Days:** `now <= closing_datetime <= now + X days`
   - **Custom Range:** User-defined start and end datetime range.

### **Text Filter Requirements:**
1. **Case Insensitive:** All text searches should ignore case.
2. **Live Search:** Filters apply as user types (on key release events).
3. **Multiple Terms:** Support comma-separated terms with AND/OR operators.
4. **Department Filter:** Search specifically in department/organization columns.
5. **Global Search:** Search across all text columns in the dataset.

### **Filter Combination Rules:**
1. **Logical AND:** All active filters must be satisfied simultaneously.
2. **Filter Order:** Apply in sequence: Date → Department → Global Search.
3. **Reset Functionality:** Clear all filters and return to original dataset.
4. **Performance:** Maintain responsiveness even with large datasets (>10k records).

## 🚫 **Avoid**

*   Using date-only comparisons when time precision is required.
*   Ignoring timezone considerations in date/time handling.
*   Creating filters that don't work well together or cause performance issues.
*   Hardcoding date/time formats instead of using pandas datetime parsing.
*   Introducing new major architectural patterns without discussion.
*   Ignoring type hints or docstrings.
*   Hardcoding paths or configuration values that should be in `GlobalConfig`.
*   Complex UI manipulations that deviate from `common_widgets.py` without strong justification.

---

**When Asking for Help/Suggestions (from this AI agent or another):**

1.  **Specify the file** you are working on (e.g., `ui/search_dashboard_tab.py`).
2.  **Describe the specific task or problem** (e.g., "The Live/Expired filter is not working correctly with time precision.").
3.  **Provide the relevant code snippet.**
4.  **Include any error messages (full traceback).**
5.  **Refer to relevant sections of THIS document** if applicable (e.g., "As per 'Filter System Specifications', time precision is required for date comparisons.").