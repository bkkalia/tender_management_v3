#!/usr/bin/env python3
"""
Dummy Data Generator for Tender Management Utility v3

This script generates large datasets for performance testing.
Creates Excel files with realistic tender data for benchmarking.

Usage:
    python dummy_data_generator.py --rows 100000 --files 10

Features:
- Generates unique tender IDs across all files
- Realistic department, title, and value distributions
- Proper date ranges and status distributions
- Saves to Downloads/dummy_data folder (separate from real data)
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import time

class DummyDataGenerator:
    """Generator for realistic tender data for performance testing."""

    def __init__(self):
        # Realistic data distributions based on typical tender data
        self.departments = [
            'IT', 'HR', 'Finance', 'Operations', 'Procurement',
            'Legal', 'Marketing', 'Engineering', 'Facilities', 'Security'
        ]

        self.organisation_chains = [
            'Government of India/Ministry of IT',
            'Government of India/Ministry of Finance',
            'Government of India/Ministry of Defence',
            'State Government/Department of Health',
            'State Government/Department of Education',
            'Municipal Corporation/Public Works',
            'Public Sector Undertaking/Railways',
            'Public Sector Undertaking/Telecommunications',
            'Private Sector/Corporate Procurement',
            'Educational Institution/University Grants'
        ]

        self.titles = [
            'Software License Renewal', 'Hardware Maintenance Contract',
            'Consulting Services Agreement', 'Office Supplies Procurement',
            'IT Equipment Purchase', 'Training Program Development',
            'Facility Management Services', 'Security System Upgrade',
            'Network Infrastructure Enhancement', 'Cloud Services Migration',
            'Data Center Expansion', 'Cybersecurity Assessment',
            'Employee Benefits Administration', 'Financial Audit Services',
            'Legal Document Review', 'Marketing Campaign Management',
            'Engineering Design Services', 'Maintenance Contract Renewal',
            'Supply Chain Optimization', 'Quality Assurance Program'
        ]

        self.status_distribution = ['Live'] * 60 + ['Expired'] * 35 + ['Awarded'] * 5  # More live tenders

        # Value ranges by department (in USD)
        self.value_ranges = {
            'IT': (50000, 2000000),
            'HR': (25000, 500000),
            'Finance': (100000, 5000000),
            'Operations': (75000, 1500000),
            'Procurement': (100000, 10000000),
            'Legal': (50000, 1000000),
            'Marketing': (25000, 750000),
            'Engineering': (200000, 5000000),
            'Facilities': (100000, 2000000),
            'Security': (75000, 1500000)
        }

    def generate_tender_data(self, num_rows: int, start_id: int = 1) -> pd.DataFrame:
        """
        Generate a DataFrame with realistic tender data using standard column headers.

        Args:
            num_rows: Number of rows to generate
            start_id: Starting tender ID number

        Returns:
            DataFrame with tender data
        """
        print(f"Generating {num_rows} rows of tender data (starting ID: {start_id})...")

        # Generate serial numbers
        serial_numbers = list(range(start_id, start_id + num_rows))

        # Generate tender IDs
        tender_ids = [f'T{i:06d}' for i in serial_numbers]

        # Generate departments with realistic distribution
        dept_weights = [0.25, 0.15, 0.15, 0.10, 0.10, 0.08, 0.07, 0.05, 0.03, 0.02]  # IT gets most
        departments = np.random.choice(self.departments, num_rows, p=dept_weights)

        # Generate organisation chains
        org_chains = np.random.choice(self.organisation_chains, num_rows)

        # Generate titles and ref numbers
        titles = np.random.choice(self.titles, num_rows)
        title_refs = [f"{title} - Ref: {tid}" for title, tid in zip(titles, tender_ids)]

        # Generate dates
        base_date = datetime.now()
        e_published_dates = []
        closing_dates = []
        opening_dates = []

        for _ in range(num_rows):
            # e-Published date: 1-30 days before closing
            closing_offset = np.random.randint(-30, 90)
            closing_date = base_date + timedelta(days=closing_offset)
            published_offset = np.random.randint(1, 31)  # 1-30 days before closing
            published_date = closing_date - timedelta(days=published_offset)

            # Opening date: same as published or 1-7 days after
            opening_offset = np.random.randint(0, 8)
            opening_date = published_date + timedelta(days=opening_offset)

            e_published_dates.append(published_date)
            closing_dates.append(closing_date)
            opening_dates.append(opening_date)

        # Generate statuses
        statuses = np.random.choice(self.status_distribution, num_rows)

        # Generate URLs (placeholder realistic URLs)
        base_urls = [
            "https://tenders.gov.in",
            "https://eprocure.gov.in",
            "https://etenders.kerala.gov.in",
            "https://www.tenderwizard.com",
            "https://www.tendernews.com"
        ]

        direct_urls = [f"{np.random.choice(base_urls)}/tender/{tid}" for tid in tender_ids]
        status_urls = [f"{url}/status" for url in direct_urls]

        # Create DataFrame with exact column headers as requested
        data = {
            'Department Name': departments,
            'S.No': serial_numbers,
            'e-Published Date': e_published_dates,
            'Closing Date': closing_dates,
            'Opening Date': opening_dates,
            'Organisation Chain': org_chains,
            'Title and Ref.No./Tender ID': title_refs,
            'Tender ID (Extracted)': tender_ids,
            'Direct URL': direct_urls,
            'Status URL': status_urls
        }

        return pd.DataFrame(data)

    def save_to_excel(self, df: pd.DataFrame, filename: str, output_dir: str) -> str:
        """
        Save DataFrame to Excel file.

        Args:
            df: DataFrame to save
            filename: Filename without extension
            output_dir: Output directory

        Returns:
            Full path to saved file
        """
        filepath = os.path.join(output_dir, f"{filename}.xlsx")

        print(f"Saving {len(df)} rows to {filepath}...")
        start_time = time.time()

        # Use openpyxl engine for better compatibility
        df.to_excel(filepath, index=False, engine='openpyxl')

        end_time = time.time()
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB

        print(f"   Saved in {end_time - start_time:.1f} seconds ({file_size:.1f} MB)")
        return filepath

def create_output_directory() -> str:
    """Create and return the output directory path."""
    # Get Downloads directory
    if os.name == 'nt':  # Windows
        downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    else:  # Linux/Mac
        downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')

    # Create dummy_data subdirectory
    output_dir = os.path.join(downloads_dir, 'dummy_data')

    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"Output directory: {output_dir}")
    return output_dir

def generate_multiple_files(num_files: int, rows_per_file: int, output_dir: str):
    """
    Generate multiple Excel files with unique tender IDs.
    Uses new naming scheme and doesn't overwrite existing files.

    Args:
        num_files: Number of files to generate
        rows_per_file: Number of rows per file
        output_dir: Output directory
    """
    generator = DummyDataGenerator()
    total_start_time = time.time()

    # Format row count for filename (e.g., 100k, 50k, 25k)
    if rows_per_file >= 1000000:
        row_suffix = f"{rows_per_file // 1000000}M"
    elif rows_per_file >= 1000:
        row_suffix = f"{rows_per_file // 1000}k"
    else:
        row_suffix = str(rows_per_file)

    print(f"\n🚀 Generating {num_files} files with {rows_per_file:,} rows each...")
    print(f"Total records: {num_files * rows_per_file:,}")
    print(f"File naming: Dummy_{row_suffix}_records_XX.xlsx")
    print("=" * 60)

    generated_files = []
    file_counter = 1

    for file_num in range(1, num_files + 1):
        print(f"\n📄 Generating file {file_num}/{num_files}...")

        # Find next available file number (don't overwrite existing files)
        while True:
            filename = f"Dummy_{row_suffix}_records_{file_counter:02d}"
            filepath = os.path.join(output_dir, f"{filename}.xlsx")
            if not os.path.exists(filepath):
                break
            file_counter += 1

        # Calculate starting ID to ensure uniqueness across files
        start_id = (file_num - 1) * rows_per_file + 1

        # Generate data
        df = generator.generate_tender_data(rows_per_file, start_id)

        # Save file
        actual_filepath = generator.save_to_excel(df, filename, output_dir)
        generated_files.append(actual_filepath)

        # Progress update
        total_generated = file_num * rows_per_file
        print(f"✅ File {file_num} complete. Total records generated: {total_generated:,}")

    total_end_time = time.time()
    total_time = total_end_time - total_start_time

    print("\n" + "=" * 60)
    print("🎉 GENERATION COMPLETE")
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   Files created: {num_files}")
    print(f"   Rows per file: {rows_per_file:,}")
    print(f"   Total rows: {num_files * rows_per_file:,}")
    print(f"   Total time: {total_time:.1f} seconds")
    print(f"   Average time per file: {total_time/num_files:.1f} seconds")
    print(f"   Output directory: {output_dir}")
    print(f"\n📁 Files generated:")
    for i, filepath in enumerate(generated_files, 1):
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
        print(f"   {i:2d}. {filename} ({file_size:.1f} MB)")

    print(f"\n💡 Usage Tips:")
    print(f"   • Use these files for performance testing")
    print(f"   • Each file has unique tender IDs (T000001, T000002, etc.)")
    print(f"   • Files are completely separate from your real data")
    print(f"   • Safe to delete when testing is complete")

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate dummy tender data for performance testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dummy_data_generator.py --rows 100000 --files 10
  python dummy_data_generator.py --rows 50000 --files 5
  python dummy_data_generator.py --rows 25000 --files 20
        """
    )

    parser.add_argument(
        '--rows', '-r',
        type=int,
        default=100000,
        help='Number of rows per file (default: 100,000)'
    )

    parser.add_argument(
        '--files', '-f',
        type=int,
        default=10,
        help='Number of files to generate (default: 10)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Custom output directory (default: Downloads/dummy_data)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.rows <= 0:
        print("❌ Error: Number of rows must be positive")
        sys.exit(1)

    if args.files <= 0:
        print("❌ Error: Number of files must be positive")
        sys.exit(1)

    if args.rows > 1000000:  # Reasonable limit
        print("⚠️  Warning: Large row count may cause memory issues")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    # Create output directory
    if args.output:
        output_dir = args.output
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = create_output_directory()

    # Check available disk space (rough estimate: 50 bytes per row)
    estimated_size_mb = (args.rows * args.files * 50) / (1024 * 1024)
    try:
        import shutil
        total, used, free = shutil.disk_usage(output_dir)
        free_mb = free / (1024 * 1024)

        if free_mb < estimated_size_mb * 1.5:  # 50% buffer
            print(f"❌ Error: Insufficient disk space. Need {estimated_size_mb:.1f} MB, have {free_mb:.1f} MB")
            sys.exit(1)
    except:
        pass  # Skip disk space check if not available

    print(f"📊 Generation Plan:")
    print(f"   Rows per file: {args.rows:,}")
    print(f"   Number of files: {args.files}")
    print(f"   Total rows: {args.rows * args.files:,}")
    print(f"   Estimated total size: {estimated_size_mb:.1f} MB")
    # Generate files
    try:
        generate_multiple_files(args.files, args.rows, output_dir)
    except KeyboardInterrupt:
        print("\n⏹️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
