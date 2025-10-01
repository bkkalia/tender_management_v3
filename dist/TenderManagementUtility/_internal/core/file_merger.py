# core/file_merger.py
import pandas as pd
from typing import List, Dict, Any, Tuple, TYPE_CHECKING, Union, Optional
import logging
import os
import re
import zipfile
from datetime import datetime
import csv

if TYPE_CHECKING:
    from core.config_manager import GlobalConfig # Corrected import for GlobalConfig

logger = logging.getLogger(__name__)

class PortalDataMerger:
    """
    Smart merger for daily portal scraping data.
    Handles portal-specific merging, dynamic unique keys, and backups.
    """
    def __init__(self, config: 'GlobalConfig'):
        self.config = config
        # Preferred unique keys, in order of preference
        self.preferred_unique_keys: List[str] = self.config.get(
            "merger_preferred_unique_keys",
            ["Tender ID (Extracted)", "Title and Ref.No./Tender ID", "Tender ID"]
        )
        self.merger_critical_fields: List[str] = self.config.get("merger_critical_fields", ["Closing Date", "Status", "Value"])
        self.max_backups_per_portal: int = self.config.get("merger_max_backups", 5)
        self.backup_subfolder_name: str = "portal_backups" # Subfolder within the output_folder for backups

    def _load_portal_base_urls(self, base_urls_csv_path=None):
        """
        Load portal base URLs and names from base_urls.csv for accurate portal identification.
        Returns a dict mapping lowercased keywords to canonical portal names.
        """
        if base_urls_csv_path is None:
            base_urls_csv_path = os.path.join(os.path.dirname(__file__), "..", "base_urls.csv")
        portal_map = {}
        try:
            with open(base_urls_csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    keyword = row.get("Keyword", "").strip().lower()
                    name = row.get("Name", "").strip()
                    if keyword and name:
                        portal_map[keyword] = name
        except Exception as e:
            logger.warning(f"Could not load portal base URLs: {e}")
        return portal_map

    def _extract_portal_name(self, file_path):
        """
        Improved portal name extraction using base_urls.csv keywords.
        Ensures all files from the same portal (regardless of suffix) are merged together.
        """
        filename = os.path.basename(file_path).lower()
        portal_map = getattr(self, "_portal_map", None)
        if portal_map is None:
            portal_map = self._load_portal_base_urls()
            self._portal_map = portal_map

        # Try to match any keyword from base_urls.csv in the filename
        for keyword, canonical_name in portal_map.items():
            # Match if keyword is present anywhere in filename (case-insensitive)
            if keyword.lower() in filename:
                return canonical_name
        # Fallback: use first part of filename before first underscore
        return filename.split("_")[0]


    
    def _determine_unique_key(self, df1: pd.DataFrame, df2: Optional[pd.DataFrame]) -> Optional[str]:
        """
        Determine unique key from preferred list, case-insensitive and space-insensitive.
        """
        def normalize(col: str) -> str:
            return re.sub(r'[^a-z0-9]', '', col.lower())

        df1_cols = {normalize(c): c for c in df1.columns}
        df2_cols = {normalize(c): c for c in (df2.columns if df2 is not None else [])}

        for key in self.preferred_unique_keys:
            norm_key = normalize(key)
            if norm_key in df1_cols:
                if df2 is None or df2.empty or norm_key in df2_cols:
                    actual = df1_cols[norm_key]
                    logger.info(f"Using unique key: '{actual}' for merging (matched from '{key}').")
                    return actual

        logger.warning(f"No suitable unique key found. Preferred list: {self.preferred_unique_keys}")
        return None



    def _backup_existing_file(self, existing_file_path: str, portal_name: str, base_output_folder: str) -> None:
        """Creates a timestamped ZIP backup of the existing file, managing backup versions."""
        if not os.path.exists(existing_file_path):
            logger.info(f"No existing file at {existing_file_path} to back up.")
            return

        backup_portal_folder = os.path.join(base_output_folder, self.backup_subfolder_name, portal_name)
        os.makedirs(backup_portal_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_basename = os.path.basename(existing_file_path)
        backup_zip_name = f"{os.path.splitext(original_basename)[0]}_backup_{timestamp}.zip"
        backup_zip_path = os.path.join(backup_portal_folder, backup_zip_name)

        try:
            with zipfile.ZipFile(backup_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(existing_file_path, arcname=original_basename)
            logger.info(f"Backup of '{original_basename}' created at '{backup_zip_path}'")

            # Manage backup versions
            existing_backups = sorted(
                [os.path.join(backup_portal_folder, f) for f in os.listdir(backup_portal_folder) if f.endswith('.zip')],
                key=os.path.getmtime
            )
            
            while len(existing_backups) > self.max_backups_per_portal:
                oldest_backup = existing_backups.pop(0)
                os.remove(oldest_backup)
                logger.info(f"Removed oldest backup: '{oldest_backup}' to maintain max {self.max_backups_per_portal} versions.")
        except Exception as e:
            logger.error(f"Error creating or managing backup for '{existing_file_path}': {e}", exc_info=True)

    def load_excel_or_csv(self, file_path: str) -> pd.DataFrame:
        """Helper to load a single Excel or CSV file."""
        try:
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                return pd.read_excel(file_path, engine='openpyxl')
            elif file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            else:
                logger.warning(f"Unsupported file type for merging: {file_path}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading file {file_path} for merging: {e}")
            return pd.DataFrame()

    def merge_portal_files(self, files_list: List[str], output_folder: str, portal_name: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Merge multiple files for a specific portal in chronological order (oldest first).
        This ensures that newer data takes precedence over older data for the same tender ID.
        
        Args:
            files_list: List of file paths to merge, expected to be pre-sorted oldest to newest
            output_folder: Folder where the merged file will be stored
            portal_name: Optional portal name. If None, it will be extracted from the first file.
            
        Returns:
            Tuple of (success, message, output_path)
        """
        if not files_list:
            return False, "No files provided for merging.", ""
            
        if portal_name is None:
            portal_name = self._extract_portal_name(files_list[0])
            logger.info(f"Extracted portal name: {portal_name} from file: {os.path.basename(files_list[0])}")
            
        if not all(os.path.exists(f) for f in files_list):
            missing_files = [f for f in files_list if not os.path.exists(f)]
            return False, f"The following files do not exist: {', '.join(missing_files)}", ""
            
        # Determine file extension for the output file from the first file
        file_ext = os.path.splitext(files_list[0])[1]
        consolidated_master_filename = f"{portal_name}_consolidated_master{file_ext}"
        output_path = os.path.join(output_folder, consolidated_master_filename)
        
        # Create backup of existing master file if it exists
        if os.path.exists(output_path):
            self._backup_existing_file(output_path, portal_name if portal_name is not None else "unknown_portal", output_folder)
            existing_df = self.load_excel_or_csv(output_path)
        else:
            existing_df = pd.DataFrame()
            logger.info(f"No existing consolidated file found for portal '{portal_name}'. Creating new master.")
        
        # For logging purposes, record initial data count
        total_input_records = 0
        total_unique_records = 0
        
        # Process input files in order (oldest to newest)
        all_dfs = []
        if not existing_df.empty:
            all_dfs.append(existing_df)
            logger.info(f"Starting with {len(existing_df)} existing records from master file.")
        
        # For enhanced reporting, track changes during merge
        new_records_count = 0
        updated_records_count = 0
        unchanged_records_count = 0
        
        # Track record status across processing
        existing_ids = set()
        
        # Read all new data files and track counts
        total_input_records = len(existing_df) if not existing_df.empty else 0
        
        for file_path in files_list:
            new_df = self.load_excel_or_csv(file_path)
            if not new_df.empty:
                total_input_records += len(new_df)
                all_dfs.append(new_df)
                logger.info(f"Loaded {len(new_df)} records from {os.path.basename(file_path)}")
        
        if not all_dfs:
            return False, f"No data could be loaded from any of the {len(files_list)} files.", ""
        
        # Combine all dataframes
        combined_df = pd.concat(all_dfs, ignore_index=True)

        logger.info(f"Columns in combined data: {list(combined_df.columns)}")
        logger.info(f"Preferred unique keys: {self.preferred_unique_keys}")

        # Determine unique key from preferred list
        unique_key = None
        for key in self.preferred_unique_keys:
            if key in combined_df.columns:
                unique_key = key
                logger.info(f"Selected unique key: {unique_key}")
                break
        if not unique_key:
            logger.warning("No suitable unique key found in merged data.")
            return False, "No suitable unique key found in merged data.", ""
        
        # Track existing_ids after determining unique_key
        if not existing_df.empty and unique_key in existing_df.columns:
            existing_ids = set(existing_df[unique_key].astype(str).unique())
        else:
            existing_ids = set()

        # Convert closing date to datetime if available
        closing_date_col = next((col for col in combined_df.columns if 'closing date' in col.lower()), None)
        if closing_date_col:
            combined_df[closing_date_col] = pd.to_datetime(combined_df[closing_date_col], errors='coerce')
            # Sort by Tender ID ascending, Closing Date descending
            combined_df.sort_values([unique_key, closing_date_col], ascending=[True, False], inplace=True)
        else:
            combined_df.sort_values([unique_key], ascending=True, inplace=True)

        # Drop duplicates, keep latest closing date
        merged_df = combined_df.drop_duplicates(subset=[unique_key], keep='first')
        total_unique_records = len(merged_df)

        # Enhanced statistics for the merge process
        dupes_removed = len(combined_df) - len(merged_df)
        
        # Calculate how many records were actually updated with newer info
        # This is approximate since we don't have full diff tracking
        if existing_df.empty:
            # No existing data, all records are new
            new_records_count = total_unique_records
            updated_records_count = 0
            unchanged_records_count = 0
        else:
            # Some existing data was present
            final_ids = set(merged_df[unique_key].astype(str).unique())
            new_records_count = len(final_ids - existing_ids)
            # Records that existed before and still exist now
            common_ids = final_ids.intersection(existing_ids)
            
            # We assume records with common IDs were updated, though they might be identical
            # This is an approximation without full record comparison
            updated_records_count = len(common_ids)
            
            # Unchanged is just an estimate (assuming all common are updated)
            unchanged_records_count = 0
        
        logger.info(
            f"Merge for portal '{portal_name}': {total_input_records} total input records -> "
            f"{total_unique_records} unique records (removed {dupes_removed} duplicates)"
        )
        
        # Create output directory if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Save merged data
        try:
            if file_ext.lower() == '.xlsx':
                merged_df.to_excel(output_path, index=False, engine='openpyxl')
            elif file_ext.lower() == '.csv':
                merged_df.to_csv(output_path, index=False)
            else:
                logger.warning(f"Unrecognized file extension {file_ext}. Saving as Excel.")
                output_path = os.path.join(output_folder, f"{portal_name}_consolidated_master.xlsx")
                merged_df.to_excel(output_path, index=False, engine='openpyxl')
                
            success_msg = f"Successfully merged {len(files_list)} files for portal '{portal_name}'.\n" \
                         f"Summary: {total_unique_records} total records in merged file\n" \
                         f"• {new_records_count} new records added\n" \
                         f"• {updated_records_count} existing records updated with newer data\n" \
                         f"• {dupes_removed} duplicate records resolved\n" \
                         f"Output file: {os.path.basename(output_path)}"
                         
            logger.info(success_msg)
            return True, success_msg, output_path
        except Exception as e:
            error_msg = f"Error saving merged file for portal '{portal_name}': {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, ""

    def merge_portal_data(self,
                          new_data_file: str,
                          existing_data_file: Optional[str],
                          output_folder: str) -> Tuple[bool, str, str]:
        """
        Intelligent merge of portal data.
        If existing_data_file is None, attempts to find a standard master file for the portal.
        Prioritizes records with the latest 'Closing Date' for duplicates.
        """
        # For backwards compatibility, delegate to merge_portal_files
        portal_name = self._extract_portal_name(new_data_file)
        
        # If existing file is provided, use the older implementation
        if existing_data_file:
            # Original implementation supports explicit existing_data_file argument
            return self._legacy_merge_portal_data(new_data_file, existing_data_file, output_folder)
        else:
            # Otherwise, delegate to the new implementation with a single-item list
            return self.merge_portal_files([new_data_file], output_folder, portal_name)

    def _legacy_merge_portal_data(self,
                                 new_data_file: str,
                                 existing_data_file: Optional[str], 
                                 output_folder: str) -> Tuple[bool, str, str]:
        """Legacy implementation of merge_portal_data for backwards compatibility."""
        if not new_data_file or not os.path.exists(new_data_file):
            return False, f"New data file path is invalid or file does not exist: {new_data_file}", ""

        portal_name = self._extract_portal_name(new_data_file)
        logger.info(f"Processing merge for portal: '{portal_name}' from new file: '{os.path.basename(new_data_file)}'")

        new_df = self.load_excel_or_csv(new_data_file)
        if new_df.empty:
            return False, f"New data file '{os.path.basename(new_data_file)}' is empty or could not be loaded.", ""

        # Ensure date columns are present and attempt conversion early
        # Define potential date columns
        closing_date_col_actual = next((col for col in new_df.columns if 'closing date' in col.lower()), None)
        epub_date_col_actual = next((col for col in new_df.columns if 'e-published date' in col.lower() or 'published date' in col.lower()), None)

        if closing_date_col_actual:
            new_df[closing_date_col_actual] = pd.to_datetime(new_df[closing_date_col_actual], errors='coerce')
            logger.debug(f"Converted '{closing_date_col_actual}' in new_df to datetime.")
        if epub_date_col_actual:
            new_df[epub_date_col_actual] = pd.to_datetime(new_df[epub_date_col_actual], errors='coerce')
            logger.debug(f"Converted '{epub_date_col_actual}' in new_df to datetime.")


        new_file_ext = os.path.splitext(new_data_file)[1] 
        consolidated_master_filename = f"{portal_name}_consolidated_master{new_file_ext}"
        
        actual_existing_file_path_to_use = None
        
        if existing_data_file and os.path.exists(existing_data_file):
            actual_existing_file_path_to_use = existing_data_file
            logger.info(f"Explicit existing file provided by caller: {actual_existing_file_path_to_use}")
        else:
            potential_master_path = os.path.join(output_folder, consolidated_master_filename)
            if os.path.exists(potential_master_path):
                actual_existing_file_path_to_use = potential_master_path
                logger.info(f"Found existing consolidated master file for portal '{portal_name}': {actual_existing_file_path_to_use}")
            else:
                logger.info(f"No existing consolidated file provided or found for portal '{portal_name}'. A new master file will be created: '{consolidated_master_filename}'")
        
        existing_df = pd.DataFrame()
        if actual_existing_file_path_to_use:
            self._backup_existing_file(actual_existing_file_path_to_use, portal_name, output_folder)
            existing_df = self.load_excel_or_csv(actual_existing_file_path_to_use)
            if not existing_df.empty:
                # Ensure date columns are converted in existing_df as well
                existing_closing_date_col = next((col for col in existing_df.columns if 'closing date' in col.lower()), None)
                existing_epub_date_col = next((col for col in existing_df.columns if 'e-published date' in col.lower() or 'published date' in col.lower()), None)

                if existing_closing_date_col:
                    existing_df[existing_closing_date_col] = pd.to_datetime(existing_df[existing_closing_date_col], errors='coerce')
                    logger.debug(f"Converted '{existing_closing_date_col}' in existing_df to datetime.")
                if existing_epub_date_col:
                    existing_df[existing_epub_date_col] = pd.to_datetime(existing_df[existing_epub_date_col], errors='coerce')
                    logger.debug(f"Converted '{existing_epub_date_col}' in existing_df to datetime.")
            
            if existing_df.empty and os.path.exists(actual_existing_file_path_to_use):
                 logger.warning(f"Existing file '{actual_existing_file_path_to_use}' was found but could not be loaded as DataFrame.")

        unique_key = self._determine_unique_key(new_df, existing_df if not existing_df.empty else None)
        if not unique_key:
            msg = f"Cannot merge. No common unique key found in new data (and existing, if any) for portal '{portal_name}'. Preferred keys: {self.preferred_unique_keys}"
            logger.error(msg)
            return False, msg, ""
        
        if new_df.empty:
            return False, "New data file is empty or could not be loaded.", ""
        if unique_key not in new_df.columns:
            return False, f"Determined unique key '{unique_key}' not found in new data.", ""


        if existing_df.empty:
            logger.info(f"No valid existing data for portal '{portal_name}'. Using only new data from '{os.path.basename(new_data_file)}'.")
            if unique_key in new_df.columns:
                nan_in_new_key = new_df[unique_key].isna().sum()
                empty_strings_in_new_key = (new_df[unique_key].astype(str) == '').sum()
                if nan_in_new_key > 0 or empty_strings_in_new_key > 0:
                    logger.info(f"New data for portal '{portal_name}' has {nan_in_new_key} NaN values and {empty_strings_in_new_key} empty strings in unique key '{unique_key}' before any merge.")
            # Sort new_df by dates if it's the only source, to handle internal duplicates correctly
            sort_by_columns = [unique_key]
            ascending_order = [True]
            if closing_date_col_actual:
                sort_by_columns.append(closing_date_col_actual)
                ascending_order.append(False) # False for descending (latest first)
            if epub_date_col_actual:
                sort_by_columns.append(epub_date_col_actual)
                ascending_order.append(False) # False for descending (latest first)
            
            if len(sort_by_columns) > 1: # Only sort if date columns are present
                 new_df.sort_values(by=sort_by_columns, ascending=ascending_order, na_position='last', inplace=True)
            
            # Convert unique key to string before dropping duplicates
            new_df[unique_key] = new_df[unique_key].astype(str)
            merged_df = new_df.drop_duplicates(subset=[unique_key], keep='first') # 'first' because we sorted to bring the best record to the top
            logger.info(f"Initial data for portal '{portal_name}': {len(new_df)} new -> {len(merged_df)} unique records using key '{unique_key}'.")

        else:
            if unique_key not in existing_df.columns:
                 return False, f"Determined unique key '{unique_key}' not found in existing data ('{(os.path.basename(actual_existing_file_path_to_use) if actual_existing_file_path_to_use is not None else 'unknown existing file')}'). Cannot merge.", ""
            
            logger.debug(f"Shape of existing_df: {existing_df.shape}, new_df: {new_df.shape} before concat.")
            nan_in_existing_key_before_concat = existing_df[unique_key].isna().sum()
            empty_in_existing_key_before_concat = (existing_df[unique_key].astype(str) == '').sum()
            nan_in_new_key_before_concat = new_df[unique_key].isna().sum()
            empty_in_new_key_before_concat = (new_df[unique_key].astype(str) == '').sum()
            logger.info(f"Unique key '{unique_key}' stats before concat: Existing DF (NaNs={nan_in_existing_key_before_concat}, EmptyStr={empty_in_existing_key_before_concat}), New DF (NaNs={nan_in_new_key_before_concat}, EmptyStr={empty_in_new_key_before_concat})")

            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            logger.debug(f"Shape of combined_df after concat: {combined_df.shape}")
            
            # Ensure unique key is string type for consistent processing
            combined_df[unique_key] = combined_df[unique_key].astype(str)
            logger.info(f"Converted unique key '{unique_key}' to 'str' for consistent de-duplication in combined_df.")

            # Determine actual date column names in combined_df (could differ if one df lacked them)
            final_closing_date_col = next((col for col in combined_df.columns if 'closing date' in col.lower()), None)
            final_epub_date_col = next((col for col in combined_df.columns if 'e-published date' in col.lower() or 'published date' in col.lower()), None)

            # Prepare for sorting: unique key first, then by dates
            sort_by_columns = [unique_key]
            ascending_order = [True] # Ascending for unique_key

            if final_closing_date_col:
                # Ensure it's datetime before sorting
                combined_df[final_closing_date_col] = pd.to_datetime(combined_df[final_closing_date_col], errors='coerce')
                sort_by_columns.append(final_closing_date_col)
                ascending_order.append(False) # False for descending (latest Closing Date first)
                logger.info(f"Sorting by '{final_closing_date_col}' (descending).")
            else:
                logger.warning("No 'Closing Date' column found in combined_df for sorting.")
            
            if final_epub_date_col:
                 # Ensure it's datetime before sorting
                combined_df[final_epub_date_col] = pd.to_datetime(combined_df[final_epub_date_col], errors='coerce')
                sort_by_columns.append(final_epub_date_col)
                ascending_order.append(False) # False for descending (latest e-Published Date first)
                logger.info(f"Additionally sorting by '{final_epub_date_col}' (descending) as tie-breaker.")
            else:
                logger.warning("No 'e-Published Date' column found in combined_df for tie-breaker sorting.")

            logger.info(f"Sorting combined_df by {sort_by_columns} with orders {ascending_order}.")
            combined_df.sort_values(by=sort_by_columns, ascending=ascending_order, na_position='last', inplace=True)
            
            # After sorting, the first occurrence of each unique_key is the one to keep
            merged_df = combined_df.drop_duplicates(subset=[unique_key], keep='first')
            logger.info(f"Merge for portal '{portal_name}': {len(existing_df)} existing, {len(new_df)} new, {len(combined_df)} combined -> {len(merged_df)} merged records using key '{unique_key}' (kept first after sorting by dates).")

        # Save merged data to the standard consolidated master file path
        output_path = os.path.join(output_folder, consolidated_master_filename)
        os.makedirs(output_folder, exist_ok=True) # Ensure output folder exists

        try:
            if new_file_ext == '.xlsx':
                merged_df.to_excel(output_path, index=False, engine='openpyxl')
            elif new_file_ext == '.csv':
                merged_df.to_csv(output_path, index=False)
            else: # Should not happen if new_file_ext is derived correctly
                 logger.warning(f"Unexpected file extension '{new_file_ext}' for output. Defaulting to Excel.")
                 merged_df.to_excel(output_path, index=False, engine='openpyxl')

            msg = f"Merge successful for portal '{portal_name}'. Output: {output_path}. {len(merged_df)} records."
            logger.info(msg)
            return True, msg, output_path
        except Exception as e:
            logger.error(f"Error saving merged file for portal '{portal_name}': {e}", exc_info=True)
            return False, f"Error saving merged file for portal '{portal_name}': {e}", ""

    # Placeholder for more advanced methods from your guide:
    # def detect_changes(self, old_record: Dict, new_record: Dict) -> List[Any]: pass
    # def resolve_conflicts(self, conflicts: List[Any]) -> List[Any]: pass
