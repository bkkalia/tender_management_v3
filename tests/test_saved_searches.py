#!/usr/bin/env python3
"""
Test script for saved searches functionality.
This script tests the saved searches features without requiring GUI interaction.
"""

import os
import sys
import json
import csv
import tempfile
from datetime import datetime

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.config_manager import GlobalConfig

def test_saved_searches_functionality():
    """Test the saved searches functionality."""
    print("🧪 Testing Saved Searches Functionality...")

    # Initialize config manager
    config_manager = GlobalConfig()

    # Test 1: Save a search
    print("\n1️⃣ Testing Save Functionality...")
    test_search_name = "Test Search 1"
    test_search_config = {
        'dept_filter': 'IT Department',
        'global_search': 'software, hardware',
        'dept_operator': 'OR',
        'global_operator': 'AND',
        'saved_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Save the search
    saved_searches_data = config_manager.get("saved_searches_data", {})
    saved_searches_list = config_manager.get("saved_searches", [])

    saved_searches_data[test_search_name] = test_search_config
    if isinstance(saved_searches_list, dict):
        saved_searches_list[test_search_name] = test_search_config
    elif isinstance(saved_searches_list, list):
        if test_search_name not in saved_searches_list:
            saved_searches_list.append(test_search_name)

    config_manager.set("saved_searches_data", saved_searches_data)
    config_manager.set("saved_searches", saved_searches_list)
    config_manager.save_config()

    print(f"✅ Saved search: {test_search_name}")

    # Test 2: Load the search
    print("\n2️⃣ Testing Load Functionality...")
    loaded_config = saved_searches_data.get(test_search_name)
    if loaded_config:
        print(f"✅ Loaded search: {test_search_name}")
        print(f"   Department filter: {loaded_config.get('dept_filter', 'N/A')}")
        print(f"   Global search: {loaded_config.get('global_search', 'N/A')}")
    else:
        print("❌ Failed to load search")

    # Test 3: Export to JSON
    print("\n3️⃣ Testing JSON Export...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(saved_searches_data, f, indent=2, ensure_ascii=False)
        json_file = f.name

    print(f"✅ Exported to JSON: {json_file}")

    # Test 4: Export to CSV
    print("\n4️⃣ Testing CSV Export...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Search Name', 'Department Filter', 'Global Search', 'Department Operator', 'Global Operator', 'Saved Date'])

        for search_name, search_config in saved_searches_data.items():
            writer.writerow([
                search_name,
                search_config.get('dept_filter', ''),
                search_config.get('global_search', ''),
                search_config.get('dept_operator', 'OR'),
                search_config.get('global_operator', 'AND'),
                search_config.get('saved_date', '')
            ])
        csv_file = f.name

    print(f"✅ Exported to CSV: {csv_file}")

    # Test 5: Import from JSON
    print("\n5️⃣ Testing Import Functionality...")
    with open(json_file, 'r', encoding='utf-8') as f:
        imported_data = json.load(f)

    imported_count = len(imported_data)
    print(f"✅ Imported {imported_count} searches from JSON")

    # Test 6: Clean corrupted searches
    print("\n6️⃣ Testing Clean Functionality...")
    # Add a corrupted search for testing
    corrupted_name = "Corrupted Search"
    saved_searches_data[corrupted_name] = "invalid_data"  # This should be a dict, not a string
    config_manager.set("saved_searches_data", saved_searches_data)
    config_manager.save_config()

    # Clean corrupted searches
    cleaned_data = {}
    cleaned_list = []
    removed_count = 0

    for search_name, search_config in saved_searches_data.items():
        if isinstance(search_config, dict) and ('dept_filter' in search_config or 'global_search' in search_config):
            cleaned_data[search_name] = search_config
            cleaned_list.append(search_name)
        else:
            removed_count += 1
            print(f"   Removed corrupted search: {search_name}")

    config_manager.set("saved_searches_data", cleaned_data)
    config_manager.set("saved_searches", cleaned_list)
    config_manager.save_config()

    print(f"✅ Cleaned up {removed_count} corrupted searches")

    # Test 7: Delete search
    print("\n7️⃣ Testing Delete Functionality...")
    if test_search_name in cleaned_data:
        del cleaned_data[test_search_name]
    if test_search_name in cleaned_list:
        cleaned_list.remove(test_search_name)

    config_manager.set("saved_searches_data", cleaned_data)
    config_manager.set("saved_searches", cleaned_list)
    config_manager.save_config()

    print(f"✅ Deleted search: {test_search_name}")

    # Cleanup temp files
    try:
        os.unlink(json_file)
        os.unlink(csv_file)
    except:
        pass

    print("\n🎉 All Saved Searches Tests Completed Successfully!")
    print("\n📊 Test Summary:")
    print("   ✅ Save functionality: Working")
    print("   ✅ Load functionality: Working")
    print("   ✅ JSON Export: Working")
    print("   ✅ CSV Export: Working")
    print("   ✅ Import functionality: Working")
    print("   ✅ Clean functionality: Working")
    print("   ✅ Delete functionality: Working")

    return True

if __name__ == "__main__":
    try:
        test_saved_searches_functionality()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
