"""
Data Processing Module for Vehicle Log Channel Appender
Contains all data processing, interpolation, and signal analysis functionality.
"""

import numpy as np
import pandas as pd
from asammdf import MDF, Signal
from scipy.interpolate import griddata, interp1d
from pathlib import Path


class DataProcessor:
    """Handles all data processing operations."""
    
    def __init__(self, logger=None):
        """Initialize the data processor.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
    
    def load_surface_table(self, csv_file_path, x_col, y_col, z_col):
        """Load surface table from CSV file."""
        try:
            # Read the CSV file
            df_full = pd.read_csv(csv_file_path)
            
            # Remove units row if present (check if first row contains non-numeric data)
            if len(df_full) > 0:
                try:
                    pd.to_numeric(df_full.iloc[0][x_col])
                    pd.to_numeric(df_full.iloc[0][y_col]) 
                    pd.to_numeric(df_full.iloc[0][z_col])
                    df = df_full
                except (ValueError, TypeError):
                    df = df_full.iloc[1:].reset_index(drop=True)
            else:
                df = df_full
            
            # Extract valid data points
            valid_data = []
            for idx, row in df.iterrows():
                try:
                    x_val = pd.to_numeric(row[x_col], errors='coerce')
                    y_val = pd.to_numeric(row[y_col], errors='coerce') 
                    z_val = pd.to_numeric(row[z_col], errors='coerce')
                    
                    if pd.notna(x_val) and pd.notna(y_val) and pd.notna(z_val):
                        valid_data.append([x_val, y_val, z_val])
                except (ValueError, TypeError, KeyError):
                    continue
            
            if not valid_data:
                raise ValueError("No valid data points found in CSV file")
            
            valid_data = np.array(valid_data)
            x_data = valid_data[:, 0]
            y_data = valid_data[:, 1]
            z_data = valid_data[:, 2]
            
            # Create interpolation grids
            x_unique = sorted(np.unique(x_data))
            y_unique = sorted(np.unique(y_data))
            
            # Create meshgrid for interpolation
            X_grid, Y_grid = np.meshgrid(x_unique, y_unique)
            
            # Interpolate Z values using griddata
            Z_grid = griddata(
                points=(x_data, y_data),
                values=z_data,
                xi=(X_grid, Y_grid),
                method='linear',
                fill_value=np.nan
            )
            
            # Fill NaN values with nearest neighbor
            mask_nan = np.isnan(Z_grid)
            if np.any(mask_nan):
                Z_nearest = griddata(
                    points=(x_data, y_data),
                    values=z_data,
                    xi=(X_grid, Y_grid),
                    method='nearest'
                )
                Z_grid[mask_nan] = Z_nearest[mask_nan]
            
            return np.array(x_unique), np.array(y_unique), Z_grid
            
        except Exception as e:
            raise Exception(f"Error loading surface table: {str(e)}")
    
    def interpolate_z_value(self, rpm, etasp, x_values, y_values, z_matrix):
        """Interpolate Z value for given RPM and ETASP using bilinear interpolation."""
        try:
            x_values = np.array(x_values)
            y_values = np.array(y_values)
            
            # Check if point is within bounds
            if rpm < x_values.min() or rpm > x_values.max() or etasp < y_values.min() or etasp > y_values.max():
                # Use nearest neighbor for out-of-bounds points
                x_idx = np.argmin(np.abs(x_values - rpm))
                y_idx = np.argmin(np.abs(y_values - etasp))
                return z_matrix[y_idx, x_idx]
            
            # Find surrounding points for bilinear interpolation
            x_idx = np.searchsorted(x_values, rpm, side='right') - 1
            y_idx = np.searchsorted(y_values, etasp, side='right') - 1
            
            # Ensure indices are within bounds
            x_idx = max(0, min(x_idx, len(x_values) - 2))
            y_idx = max(0, min(y_idx, len(y_values) - 2))
            
            # Get the four surrounding points
            x1, x2 = x_values[x_idx], x_values[x_idx + 1]
            y1, y2 = y_values[y_idx], y_values[y_idx + 1]
            
            z11 = z_matrix[y_idx, x_idx]
            z12 = z_matrix[y_idx + 1, x_idx]
            z21 = z_matrix[y_idx, x_idx + 1]
            z22 = z_matrix[y_idx + 1, x_idx + 1]
            
            # Check for NaN values and use nearest neighbor if needed
            if np.isnan([z11, z12, z21, z22]).any():
                # Find the nearest non-NaN value
                distances = []
                values = []
                for i, z_val in enumerate([z11, z12, z21, z22]):
                    if not np.isnan(z_val):
                        if i == 0:
                            dist = np.sqrt((rpm - x1)**2 + (etasp - y1)**2)
                        elif i == 1:
                            dist = np.sqrt((rpm - x1)**2 + (etasp - y2)**2)
                        elif i == 2:
                            dist = np.sqrt((rpm - x2)**2 + (etasp - y1)**2)
                        else:
                            dist = np.sqrt((rpm - x2)**2 + (etasp - y2)**2)
                        distances.append(dist)
                        values.append(z_val)
                
                if values:
                    return values[np.argmin(distances)]
                else:
                    return np.nan
            
            # Bilinear interpolation
            z_x1 = z11 * (x2 - rpm) / (x2 - x1) + z21 * (rpm - x1) / (x2 - x1)
            z_x2 = z12 * (x2 - rpm) / (x2 - x1) + z22 * (rpm - x1) / (x2 - x1)
            z_interpolated = z_x1 * (y2 - etasp) / (y2 - y1) + z_x2 * (etasp - y1) / (y2 - y1)
            
            return z_interpolated
            
        except Exception as e:
            self.logger(f"Interpolation error: {e}")
            return np.nan


class ChannelAnalyzer:
    """Analyzes channel sampling rates and properties."""
    
    def __init__(self, logger=None):
        """Initialize the channel analyzer.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
    
    def analyze_channel_sampling_rates(self, vehicle_data, custom_channels, vehicle_file_path):
        """Analyze sampling rates of all channels used in custom channel configurations."""
        if not vehicle_data or not custom_channels:
            return {}
        
        file_ext = Path(vehicle_file_path).suffix.lower()
        channel_analysis = {}
        
        # Get all unique channels used in custom configurations
        used_channels = set()
        for config in custom_channels:
            used_channels.add(config['vehicle_x_channel'])
            used_channels.add(config['vehicle_y_channel'])
        
        try:
            if file_ext in ['.mdf', '.mf4', '.dat']:
                for channel_name in used_channels:
                    try:
                        # Get channel info without raster to see original sampling
                        signal = vehicle_data.get(channel_name)
                        if signal is not None and len(signal.timestamps) > 1:
                            # Calculate sampling statistics
                            time_diffs = np.diff(signal.timestamps)
                            min_interval = np.min(time_diffs[time_diffs > 0])
                            avg_interval = np.mean(time_diffs)
                            max_interval = np.max(time_diffs)
                            
                            # Calculate suggested minimum raster (slightly larger than minimum interval)
                            suggested_min_raster = min_interval * 1.1
                            
                            channel_analysis[channel_name] = {
                                'min_interval': min_interval,
                                'avg_interval': avg_interval,
                                'max_interval': max_interval,
                                'suggested_min_raster': suggested_min_raster,
                                'sample_count': len(signal.samples),
                                'duration': signal.timestamps[-1] - signal.timestamps[0]
                            }
                        else:
                            channel_analysis[channel_name] = {
                                'error': 'Channel not found or empty'
                            }
                    except Exception as e:
                        channel_analysis[channel_name] = {
                            'error': str(e)
                        }
            else:  # CSV files don't have timestamp info
                for channel_name in used_channels:
                    if channel_name in vehicle_data.columns:
                        channel_analysis[channel_name] = {
                            'sample_count': len(vehicle_data),
                            'note': 'CSV file - no timing information available'
                        }
                    else:
                        channel_analysis[channel_name] = {
                            'error': 'Channel not found in CSV'
                        }
        except Exception as e:
            self.logger(f"❌ Error analyzing channel sampling rates: {str(e)}")
        
        return channel_analysis
    
    def get_interpolated_signal_data(self, vehicle_data, vehicle_file_path, channel_name, target_raster):
        """Get signal data with interpolation if needed for target raster."""
        file_ext = Path(vehicle_file_path).suffix.lower()
        
        if file_ext == '.csv':
            # For CSV files, just return the data as-is
            data = pd.to_numeric(vehicle_data[channel_name], errors='coerce')
            timestamps = np.arange(len(data), dtype=np.float64) * target_raster
            return data.values, timestamps
        
        # For MDF files, try to get data at target raster first
        try:
            signal = vehicle_data.get(channel_name, raster=target_raster)
            if signal is not None and len(signal.samples) > 0:
                self.logger(f"✅ Direct raster extraction successful for {channel_name}: {len(signal.samples)} samples")
                return signal.samples, signal.timestamps
        except Exception as e:
            # If raster-based extraction fails, fall back to interpolation
            self.logger(f"⚠️ Direct raster extraction failed for {channel_name}, using interpolation: {str(e)}")
            pass
        
        # Fallback: get original signal and interpolate
        try:
            original_signal = vehicle_data.get(channel_name)
            if original_signal is None or len(original_signal.samples) == 0:
                raise Exception(f"Channel {channel_name} not found or empty")
            
            # Create target timestamps
            start_time = original_signal.timestamps[0]
            end_time = original_signal.timestamps[-1]
            target_timestamps = np.arange(start_time, end_time + target_raster, target_raster)
            
            # Interpolate to target timestamps
            interpolator = interp1d(
                original_signal.timestamps, 
                original_signal.samples,
                kind='linear',
                bounds_error=False,
                fill_value='extrapolate'
            )
            interpolated_samples = interpolator(target_timestamps)
            
            self.logger(f"🔄 Interpolated {channel_name}: {len(original_signal.samples)} -> {len(interpolated_samples)} samples")
            return interpolated_samples, target_timestamps
            
        except Exception as e:
            raise Exception(f"Failed to get data for {channel_name}: {str(e)}")