#!/usr/bin/env python3
"""
Test script to demonstrate the Excel-like filtering functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

try:
    from vehicle_log_channel_appender_modern import VehicleLogChannelAppenderModern
    import customtkinter as ctk
    
    def test_excel_filters():
        """Test the Excel-like filtering functionality."""
        print("🔽 Testing Excel-like Filter Implementation")
        print("=" * 50)
        
        # Create the application
        app = VehicleLogChannelAppenderModern()
        
        # Add some test channels to demonstrate filtering
        test_channels = [
            {
                'name': 'Turbo_Pressure_MAP1',
                'csv_file': '/test/turbo_map.csv',
                'x_column': 'RPM',
                'y_column': 'Load',
                'z_column': 'Pressure',
                'vehicle_x_channel': 'Engine_RPM',
                'vehicle_y_channel': 'Engine_Load',
                'units': 'bar',
                'comment': 'Main turbo pressure'
            },
            {
                'name': 'Turbo_Pressure_MAP2',
                'csv_file': '/test/turbo_map.csv',
                'x_column': 'RPM',
                'y_column': 'Load',
                'z_column': 'Pressure_Alt',
                'vehicle_x_channel': 'Engine_RPM',
                'vehicle_y_channel': 'Engine_Load',
                'units': 'bar',
                'comment': 'Secondary turbo pressure'
            },
            {
                'name': 'Fuel_Injection_Timing',
                'csv_file': '/test/injection_map.csv',
                'x_column': 'RPM',
                'y_column': 'ETASP',
                'z_column': 'Timing',
                'vehicle_x_channel': 'Engine_RPM',
                'vehicle_y_channel': 'Engine_TorquePercent',
                'units': 'deg',
                'comment': 'Fuel injection timing'
            },
            {
                'name': 'Exhaust_Gas_Temperature',
                'csv_file': '/test/egt_map.csv',
                'x_column': 'RPM',
                'y_column': 'Load',
                'z_column': 'Temperature',
                'vehicle_x_channel': 'Engine_RPM',
                'vehicle_y_channel': 'Engine_Load',
                'units': '°C',
                'comment': 'EGT calculation'
            }
        ]
        
        app.custom_channels = test_channels
        
        # Test filter initialization
        print("✅ Filter initialization:")
        for col_name, filter_config in app.excel_filters.items():
            print(f"   {col_name}: {filter_config}")
        
        # Test unique value extraction
        print("\n✅ Unique values per column:")
        for col_name in ["Name", "Units", "Comment"]:
            unique_vals = app.get_unique_values_for_column(col_name)
            print(f"   {col_name}: {unique_vals}")
        
        # Test channel column value extraction
        print("\n✅ Channel value extraction test:")
        test_channel = test_channels[0]
        for col_name in ["Name", "CSV File", "Units", "Comment"]:
            value = app.get_channel_column_value(test_channel, col_name)
            print(f"   {col_name}: '{value}'")
        
        print("\n🎉 Excel-like filtering implementation ready!")
        print("\nFeatures implemented:")
        print("• 🔽 Clickable filter icons in column headers")
        print("• ✅ Include/Exclude filter modes")
        print("• 🔍 Custom text filters (contains, starts with, ends with, equals, not contains)")
        print("• ✅ Select All / Clear All functionality")
        print("• 📊 Value counts displayed for each option")
        print("• 🧹 Clear individual and all filters")
        print("• 🔗 Integration with existing search and legacy filters")
        print("• 📋 Visual indicators in headers when filters are active")
        
        # Start the application to test interactively
        print("\n🚀 Starting application for interactive testing...")
        app.run()
        
    if __name__ == "__main__":
        test_excel_filters()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required packages are installed:")
    print("  pip install customtkinter pandas numpy scipy asammdf")
except Exception as e:
    print(f"❌ Error: {e}")