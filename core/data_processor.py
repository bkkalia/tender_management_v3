# core/data_processor.py
import pandas as pd
from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING, Tuple
import logging
import os
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from core.config_manager import GlobalConfig

logger = logging.getLogger(__name__)

class TenderDataProcessor:
    """
    Processes tender data for the Search & Dashboard tab.
    Handles loading, filtering, and stats calculation.
    """
    def __init__(self, config: 'GlobalConfig'):
        self.config = config
        self.raw_data = pd.DataFrame()
        self.filtered_data = pd.DataFrame()
        self.last_loaded_files = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Track which columns are date columns to avoid repeated conversions
        self.date_columns = []

    def load_data_from_files(self, file_paths: List[str]) -> Tuple[bool, str]:
        """
        Load data from Excel or CSV files into raw_data DataFrame.
        
        Args:
            file_paths: List of file paths to load
            
        Returns:
            Tuple of (success, message)
        """
        if not file_paths:
            return False, "No files provided."

        all_dfs = []
        loaded_count = 0
        
        # Store file paths for reference
        self.last_loaded_files = file_paths
        self.config.set("last_loaded_files", file_paths)
        self.config.save_config()

        for file_path in file_paths:
            try:
                self.logger.info(f"Loading data from: {file_path}")
                
                # Create a dictionary of columns that should be treated as strings
                string_columns = {}
                
                # For Excel files, we can specify dtypes for common ID/title columns
                if file_path.lower().endswith(('.xlsx', '.xls')):
                    # Pre-scan the Excel file to identify ID and title columns
                    try:
                        # Just read the column names first
                        df_cols = pd.read_excel(file_path, engine='openpyxl', nrows=0)
                        
                        # Identify ID and title columns
                        for col in df_cols.columns:
                            col_lower = str(col).lower()
                            if any(term in col_lower for term in ['id', 'title', 'reference', 'ref.no', 'tender', 'name']):
                                string_columns[col] = str
                                
                        # Now read with proper dtypes
                        df = pd.read_excel(file_path, engine='openpyxl', dtype=string_columns)
                    except Exception as e:
                        self.logger.warning(f"Pre-scan for column types failed: {e}, using default loading")
                        df = pd.read_excel(file_path, engine='openpyxl')
                elif file_path.lower().endswith('.csv'):
                    try:
                        # Similar pre-scan for CSV
                        df_cols = pd.read_csv(file_path, nrows=0)
                        for col in df_cols.columns:
                            col_lower = str(col).lower()
                            if any(term in col_lower for term in ['id', 'title', 'reference', 'ref.no', 'tender', 'name']):
                                string_columns[col] = str
                        
                        df = pd.read_csv(file_path, dtype=string_columns)
                    except:
                        df = pd.read_csv(file_path)
                else:
                    self.logger.warning(f"Unsupported file type: {file_path}")
                    continue
                
                # Convert any NaN values in string columns to empty strings
                for col in df.columns:
                    if df[col].dtype == 'object' or 'id' in str(col).lower() or 'tender' in str(col).lower():
                        df[col] = df[col].fillna('').astype(str)
            
                if not df.empty:
                    all_dfs.append(df)
                    loaded_count += 1
            except Exception as e:
                self.logger.error(f"Error loading file {file_path}: {e}")

        if not all_dfs:
            self.raw_data = pd.DataFrame()
            self.filtered_data = pd.DataFrame()
            return False, f"Failed to load any data from {len(file_paths)} files."

        # Combine all DataFrames
        self.raw_data = pd.concat(all_dfs, ignore_index=True)
        self.filtered_data = self.raw_data.copy()
        
        # Identify and convert date columns
        self._identify_and_convert_date_columns()
        
        total_records = len(self.raw_data)
        self.logger.info(f"Successfully loaded {total_records} records from {loaded_count} files.")
        return True, f"Successfully loaded {total_records} records from {loaded_count} files."

    def _identify_and_convert_date_columns(self):
        """Identify and convert date columns to datetime format, focusing on closing dates."""
        self.date_columns = []
        self.closing_date_columns = []  # Specifically for closing dates
        
        # First, check for columns that definitely shouldn't be dates
        non_date_columns = []
        for col in self.raw_data.columns:
            col_lower = str(col).lower()
            
            # Explicitly exclude title and ID columns from date detection
            if any(keyword in col_lower for keyword in ['title', 'id', 'tender id', 'ref.no', 'reference']):
                non_date_columns.append(col)
                continue
        
        # Now identify closing date columns from remaining columns
        closing_keywords = ['closing', 'due', 'deadline', 'end', 'expiry', 'expiration']
        
        for col in self.raw_data.columns:
            # Skip columns we've explicitly identified as non-date
            if col in non_date_columns:
                continue
                
            col_lower = str(col).lower()
            
            # Check if column name suggests it's a closing date
            if any(keyword in col_lower for keyword in closing_keywords):
                try:
                    # Try to convert to datetime with explicit format handling to avoid pandas warning
                    # First, try common date formats
                    date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']
                    converted = False
                    
                    for date_format in date_formats:
                        try:
                            self.raw_data[col] = pd.to_datetime(self.raw_data[col], format=date_format, errors='coerce')
                            converted = True
                            self.logger.info(f"Converted '{col}' to datetime format using {date_format} (closing date)")
                            break
                        except (ValueError, TypeError):
                            continue
                    
                    if not converted:
                        # Fallback to automatic inference with explicit format specification
                        self.raw_data[col] = pd.to_datetime(self.raw_data[col], errors='coerce', infer_datetime_format=True)
                        self.logger.info(f"Converted '{col}' to datetime format using automatic inference (closing date)")
                    
                    self.filtered_data[col] = self.raw_data[col]
                    self.date_columns.append(col)
                    self.closing_date_columns.append(col)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to convert '{col}' to datetime: {e}")
            
            # Also look for other date columns, but mark them as not closing dates
            elif 'date' in col_lower and not any(keyword in col_lower for keyword in closing_keywords):
                # Skip if it's in the non-date list
                if col in non_date_columns:
                    continue
                
                try:
                    # Try to convert to datetime with format handling
                    date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']
                    converted = False
                    
                    for date_format in date_formats:
                        try:
                            self.raw_data[col] = pd.to_datetime(self.raw_data[col], format=date_format, errors='coerce')
                            converted = True
                            break
                        except (ValueError, TypeError):
                            continue
                    
                    if not converted:
                        self.raw_data[col] = pd.to_datetime(self.raw_data[col], errors='coerce', infer_datetime_format=True)
                    
                    self.filtered_data[col] = self.raw_data[col]
                    self.date_columns.append(col)
                    self.logger.debug(f"Converted '{col}' to datetime format (non-closing date)")
                except:
                    pass  # Not a date column or failed conversion

        # If no closing date columns were found, try to infer from data patterns
        if not self.closing_date_columns and self.date_columns:
            self.closing_date_columns = self.date_columns
            self.logger.warning("No explicit closing date columns found, using all date columns")
        
        self.logger.info(f"Identified closing date columns: {self.closing_date_columns}")
        self.logger.debug(f"All date columns: {self.date_columns}")

    def _find_department_column(self) -> Optional[str]:
        """
        Find the column that contains department information based on common naming patterns.
        Returns the column name if found, None otherwise.
        """
        if self.raw_data.empty:
            return None
            
        # Check for common department column names
        dept_keywords = ['department', 'dept', 'organization', 'organisation', 'ministry', 'agency']
        
        for col in self.raw_data.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in dept_keywords):
                return col
                
        # If no dedicated department column is found, return None
        return None

    def apply_filters(self, filters: Dict[str, Any]) -> None:
        """Apply filters to the raw data."""
        if self.raw_data.empty:
            self.filtered_data = self.raw_data.copy()
            return
            
        # Start with all data
        filtered_df = self.raw_data.copy()
        
        # Store search terms for highlighting
        self.search_terms = []
        
        # Apply department filter if provided
        if 'Department' in filters and filters['Department']:
            dept_terms = [term.strip() for term in filters['Department'].lower().split(',') if term.strip()]
            if dept_terms:
                # Find department column
                dept_col = self._find_department_column()
                if dept_col:
                    # Create a mask for matching departments
                    if filters.get('DepartmentOperator', 'OR') == 'OR':
                        # OR logic - match any term
                        dept_mask = pd.Series(False, index=filtered_df.index)
                        
                        for term in dept_terms:
                            term_match = filtered_df[dept_col].astype(str).str.lower().str.contains(term, na=False)
                            dept_mask = dept_mask | term_match
                        
                        filtered_df = filtered_df[dept_mask]
                    else:
                        # AND logic - match all terms
                        dept_mask = pd.Series(True, index=filtered_df.index)
                        
                        for term in dept_terms:
                            term_match = filtered_df[dept_col].astype(str).str.lower().str.contains(term, na=False)
                            dept_mask = dept_mask & term_match
                        
                        filtered_df = filtered_df[dept_mask]
        
        # Apply global search filter if provided
        if 'GlobalSearch' in filters and filters['GlobalSearch']:
            search_terms = [term.strip() for term in filters['GlobalSearch'].lower().split(',') if term.strip()]
            
            # Store search terms for highlighting in UI
            self.search_terms = search_terms
            
            if search_terms:
                if filters.get('GlobalSearchOperator', 'AND') == 'AND':
                    # AND logic - all terms must match
                    global_mask = pd.Series(True, index=filtered_df.index)
                    
                    for term in search_terms:
                        # Create a mask for this term (any column containing this term)
                        term_mask = pd.Series(False, index=filtered_df.index)
                        
                        for col in filtered_df.columns:
                            if filtered_df[col].dtype == 'object':  # Text columns
                                col_match = filtered_df[col].fillna('').astype(str).str.lower().str.contains(term, na=False)
                                term_mask = term_mask | col_match
                        
                        # AND this term's matches with the global mask (all terms must match)
                        global_mask = global_mask & term_mask
                else:
                    # OR logic - any term can match
                    global_mask = pd.Series(False, index=filtered_df.index)
                    
                    for term in search_terms:
                        # Create a mask for this term (any column containing this term)
                        term_mask = pd.Series(False, index=filtered_df.index)
                        
                        for col in filtered_df.columns:
                            if filtered_df[col].dtype == 'object':  # Text columns
                                col_match = filtered_df[col].fillna('').astype(str).str.lower().str.contains(term, na=False)
                                term_mask = term_mask | col_match
                        
                        # OR this term's matches with the global mask (any term can match)
                        global_mask = global_mask | term_mask
                
                # Apply the final mask
                filtered_df = filtered_df[global_mask]
        else:
            self.search_terms = []
        
        # Apply date filter if provided
        if 'DateFilter' in filters and filters['DateFilter']:
            date_filter = filters['DateFilter']
            date_filtered = self._filter_by_date(filtered_df, date_filter)
            if date_filtered is not None:
                filtered_df = date_filtered
        
        # Update filtered data
        self.filtered_data = filtered_df

    def _filter_by_date(self, df: pd.DataFrame, date_filter: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Filter the DataFrame by date based on the provided date filter criteria.
        
        Args:
            df: The DataFrame to filter.
            date_filter: A dictionary containing the date filter criteria.
        
        Returns:
            A filtered DataFrame or None if no valid date filter is provided.
        """
        if df.empty or 'type' not in date_filter:
            return None
            
        # Ensure we have closing date columns
        if not self.closing_date_columns:
            self.logger.warning("No closing date columns found for date filtering")
            return None
            
        filter_type = date_filter['type']
        
        # Use pandas Timestamp for precise time comparisons
        current_time = pd.Timestamp.now()
        today_start = current_time.normalize()  # Start of today (00:00:00)
        today_end = today_start + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)  # End of today (23:59:59.999999)
        
        # Use the first closing date column for filtering
        date_col = self.closing_date_columns[0]
        
        try:
            if filter_type == 'all':
                # Return all data without date filtering
                return df.copy()
                
            elif filter_type == 'today':
                mask = (df[date_col] >= today_start) & (df[date_col] <= today_end)
                return df[mask].copy()
                
            elif filter_type == 'next_3_days':
                end_date = today_start + pd.Timedelta(days=3, hours=23, minutes=59, seconds=59)
                mask = (df[date_col] >= current_time) & (df[date_col] <= end_date)
                return df[mask].copy()
                
            elif filter_type == 'next_7_days':
                end_date = today_start + pd.Timedelta(days=7, hours=23, minutes=59, seconds=59)
                mask = (df[date_col] >= current_time) & (df[date_col] <= end_date)
                return df[mask].copy()
                
            elif filter_type == 'next_30_days':
                end_date = today_start + pd.Timedelta(days=30, hours=23, minutes=59, seconds=59)
                mask = (df[date_col] >= current_time) & (df[date_col] <= end_date)
                return df[mask].copy()
                
            elif filter_type == 'expired':
                mask = df[date_col] < current_time
                return df[mask].copy()
                
            elif filter_type == 'live':
                mask = df[date_col] > current_time
                return df[mask].copy()
                
            elif filter_type == 'custom':
                start_date = date_filter.get('start_date')
                end_date = date_filter.get('end_date')
                
                if not start_date or not end_date:
                    self.logger.warning("Custom date filter missing start_date or end_date")
                    return None
                
                try:
                    # Convert string dates to pandas timestamps
                    start_timestamp = pd.Timestamp(start_date)
                    # Set end date to end of day (23:59:59) for inclusive filtering
                    end_timestamp = pd.Timestamp(end_date) + pd.Timedelta(hours=23, minutes=59, seconds=59)
                    
                    self.logger.info(f"Custom date filter: {start_timestamp} to {end_timestamp}")
                    
                    mask = (df[date_col] >= start_timestamp) & (df[date_col] <= end_timestamp)
                    filtered_result = df[mask].copy()
                    
                    self.logger.info(f"Custom date filter returned {len(filtered_result)} records")
                    return filtered_result
                    
                except Exception as e:
                    self.logger.error(f"Error parsing custom date range: {e}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error in date filtering: {e}")
            return None
        
        return None

    def reset_filters(self) -> None:
        """Reset all filters, returning to the original data."""
        self.filtered_data = self.raw_data.copy()

    def get_filtered_data_for_display(self) -> pd.DataFrame:
        """Get filtered data for display in the UI."""
        return self.filtered_data.copy()

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Calculate dashboard statistics based on the raw and filtered data."""
        stats = {
            "total_tenders": 0,
            "filtered_tenders": 0,
            "match_percentage": 0,
            "unique_departments": 0,
            "closing_today": 0,
            "closing_next_3_days": 0,
            "closing_next_7_days": 0,
            "expired_tenders": 0,
            "live_tenders": 0,  # Add live tenders count
            "data_sources": 0
        }
        
        # Basic counts
        if not self.raw_data.empty:
            stats["total_tenders"] = len(self.raw_data)
            stats["filtered_tenders"] = len(self.filtered_data)
            
            # Calculate match percentage
            if stats["total_tenders"] > 0:
                stats["match_percentage"] = int((stats["filtered_tenders"] / stats["total_tenders"]) * 100)
            
            # Count unique departments
            dept_columns = [col for col in self.raw_data.columns 
                          if 'department' in str(col).lower() or 'dept' in str(col).lower()]
            
            if dept_columns:
                unique_depts = set()
                for col in dept_columns:
                    depts = self.raw_data[col].dropna().astype(str)
                    unique_depts.update(d.strip() for d in depts if d.strip() and d.strip().lower() not in ['nan', 'none', ''])
                stats["unique_departments"] = len(unique_depts)
            
            # Date-based stats - ONLY USE CLOSING DATE COLUMNS with precise time handling
            if hasattr(self, 'closing_date_columns') and self.closing_date_columns:
                current_time = pd.Timestamp.now()  # Use precise timestamp for all calculations
                today_start = current_time.normalize()
                today_end = today_start + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
                
                for col in self.closing_date_columns:
                    # Skip columns that aren't datetime type
                    if not pd.api.types.is_datetime64_dtype(self.raw_data[col]):
                        continue
                        
                    # Get non-NA values for this column
                    valid_dates = self.raw_data[~self.raw_data[col].isna()]
                    if valid_dates.empty:
                        continue
                    
                    # Closing today (precise time comparison)
                    stats["closing_today"] += ((valid_dates[col] >= today_start) & 
                                            (valid_dates[col] <= today_end)).sum()
                    
                    # Next 3 days (from now to 3 days ahead)
                    end_3_days = today_start + pd.Timedelta(days=3, hours=23, minutes=59, seconds=59)
                    stats["closing_next_3_days"] += ((valid_dates[col] >= current_time) & 
                                                  (valid_dates[col] <= end_3_days)).sum()
                    
                    # Next 7 days (from now to 7 days ahead)
                    end_7_days = today_start + pd.Timedelta(days=7, hours=23, minutes=59, seconds=59)
                    stats["closing_next_7_days"] += ((valid_dates[col] >= current_time) & 
                                                  (valid_dates[col] <= end_7_days)).sum()
                    
                    # Expired - closing date/time has passed
                    stats["expired_tenders"] += (valid_dates[col] < current_time).sum()
                    
                    # Live - closing date/time is in the future
                    stats["live_tenders"] += (valid_dates[col] > current_time).sum()

            # Count data sources
            stats["data_sources"] = len(set(self.last_loaded_files))
        
        return stats

    def get_display_data(self) -> Optional[pd.DataFrame]:
        """
        Returns the filtered data, possibly a subset of columns for display.
        """
        if self.filtered_data is not None and not self.filtered_data.empty:
            # For display, we might want to select specific columns
            columns_to_display = ['Department Name', 'Tender Title', 'Closing Date', 'Tender Value'] # Example subset
            return self.filtered_data[columns_to_display]
        return self.filtered_data

    def get_column_names(self) -> List[str]:
        """
        Returns the column names from the filtered data.
        """
        if self.filtered_data is not None and not self.filtered_data.empty:
            return list(self.filtered_data.columns)
        return []
            
    def get_distinct_departments(self) -> List[str]:
        """
        Returns a sorted list of unique department names from the loaded data.
        """
        if self.raw_data is None or self.raw_data.empty:
            return ["N/A"]
        
        department_col = self.config.get('column_mappings', {}).get('department', 'Department')
        if department_col in self.raw_data.columns:
            # Fill NaN values with 'Unknown', get unique values, sort, and convert to list
            return sorted(list(self.raw_data[department_col].fillna('Unknown').unique()))
        return ["N/A"]