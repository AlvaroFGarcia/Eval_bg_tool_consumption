#!/usr/bin/env python3
"""
Test script for Vehicle Log Channel Appender
Demonstrates the interpolation and channel appending functionality
"""

import numpy as np
import pandas as pd
from scipy.interpolate import griddata
import os

def test_interpolation():
    """Test the interpolation functionality"""
    print("Testing Vehicle Log Channel Appender functionality...")
    
    # Load the sample surface table
    print("\n1. Loading CSV surface table...")
    surface_df = pd.read_csv('sample_surface_table.csv')
    print(f"   Surface table loaded with {len(surface_df)} points")
    print(f"   RPM range: {surface_df['RPM'].min()} - {surface_df['RPM'].max()}")
    print(f"   ETASP range: {surface_df['ETASP'].min():.2f} - {surface_df['ETASP'].max():.2f}")
    print(f"   Z range: {surface_df['Fuel_Consumption'].min():.2f} - {surface_df['Fuel_Consumption'].max():.2f}")
    
    # Load the sample vehicle log
    print("\n2. Loading vehicle log file...")
    vehicle_df = pd.read_csv('sample_vehicle_log.csv')
    print(f"   Vehicle log loaded with {len(vehicle_df)} data points")
    print(f"   Available channels: {list(vehicle_df.columns)}")
    
    # Extract RPM and ETASP data
    print("\n3. Extracting RPM and ETASP data...")
    rpm_data = vehicle_df['Engine_RPM'].values
    etasp_data = vehicle_df['Engine_ETASP'].values
    print(f"   RPM range in vehicle log: {rpm_data.min()} - {rpm_data.max()}")
    print(f"   ETASP range in vehicle log: {etasp_data.min():.2f} - {etasp_data.max():.2f}")
    
    # Perform interpolation
    print("\n4. Performing interpolation...")
    
    # Create points for interpolation from surface table
    points = np.column_stack((surface_df['RPM'].values, surface_df['ETASP'].values))
    values = surface_df['Fuel_Consumption'].values
    
    # Create target points from vehicle log
    target_points = np.column_stack((rpm_data, etasp_data))
    
    # Interpolate using linear method first, then nearest for NaN values
    interpolated_z = griddata(points, values, target_points, method='linear', fill_value=np.nan)
    
    # Fill NaN values with nearest neighbor interpolation
    nan_mask = np.isnan(interpolated_z)
    if np.any(nan_mask):
        interpolated_z_nearest = griddata(points, values, target_points, method='nearest')
        interpolated_z[nan_mask] = interpolated_z_nearest[nan_mask]
    
    print(f"   Interpolation complete. {np.sum(nan_mask)} values filled with nearest neighbor")
    print(f"   Calculated Z range: {interpolated_z.min():.2f} - {interpolated_z.max():.2f}")
    
    # Add calculated channel to vehicle log
    print("\n5. Adding calculated channel to vehicle log...")
    vehicle_df['Calculated_Fuel_Consumption'] = interpolated_z
    
    # Save to new file
    output_file = 'sample_vehicle_log_with_Calculated_Fuel_Consumption.csv'
    vehicle_df.to_csv(output_file, index=False)
    print(f"   Output saved to: {output_file}")
    
    # Display some results
    print("\n6. Sample results:")
    print("   Time | RPM  | ETASP | Calculated_FC")
    print("   -----|------|-------|---------------")
    for i in range(0, len(vehicle_df), 5):  # Show every 5th row
        row = vehicle_df.iloc[i]
        print(f"   {row['Time']:4.1f} | {row['Engine_RPM']:4.0f} | {row['Engine_ETASP']:5.2f} | {row['Calculated_Fuel_Consumption']:8.2f}")
    
    print(f"\nTest completed successfully!")
    print(f"Original file: sample_vehicle_log.csv ({len(vehicle_df.columns)-1} channels)")
    print(f"Output file: {output_file} ({len(vehicle_df.columns)} channels)")
    
    return True

if __name__ == "__main__":
    test_interpolation()