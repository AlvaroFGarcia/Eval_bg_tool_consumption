"""
Channel Management Module for Vehicle Log Channel Appender
Contains custom channel configuration and management functionality.
"""

import os
from typing import List, Dict, Optional, Tuple


class ChannelManager:
    """Manages custom channel configurations."""
    
    def __init__(self, logger=None):
        """Initialize the channel manager.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
        self.custom_channels = []
    
    def add_channel(self, channel_config):
        """Add a new custom channel configuration.
        
        Args:
            channel_config: Dictionary containing channel configuration
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        # Validate the configuration
        validation_result = self.validate_channel_config(channel_config)
        if not validation_result[0]:
            return False, validation_result[1]
        
        # Check if channel already exists
        for channel in self.custom_channels:
            if channel['name'] == channel_config['name']:
                return False, "Channel with this name already exists!"
        
        # Add the channel
        self.custom_channels.append(channel_config.copy())
        self.logger(f"✅ Added custom channel: {channel_config['name']}")
        return True, ""
    
    def update_channel(self, channel_index, new_config):
        """Update an existing channel configuration.
        
        Args:
            channel_index: Index of the channel to update
            new_config: New configuration dictionary
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if channel_index < 0 or channel_index >= len(self.custom_channels):
            return False, "Invalid channel index!"
        
        # Validate the new configuration
        validation_result = self.validate_channel_config(new_config)
        if not validation_result[0]:
            return False, validation_result[1]
        
        # Check if name conflicts with other channels (except the current one)
        for i, channel in enumerate(self.custom_channels):
            if i != channel_index and channel['name'] == new_config['name']:
                return False, "Channel with this name already exists!"
        
        old_name = self.custom_channels[channel_index]['name']
        self.custom_channels[channel_index] = new_config.copy()
        self.logger(f"✅ Updated channel: {old_name} → {new_config['name']}")
        return True, ""
    
    def delete_channel(self, channel_index):
        """Delete a channel by index.
        
        Args:
            channel_index: Index of the channel to delete
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if channel_index < 0 or channel_index >= len(self.custom_channels):
            return False, "Invalid channel index!"
        
        deleted_channel = self.custom_channels.pop(channel_index)
        self.logger(f"🗑️ Deleted channel: {deleted_channel['name']}")
        return True, ""
    
    def delete_channel_by_name(self, channel_name):
        """Delete a channel by name.
        
        Args:
            channel_name: Name of the channel to delete
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        for i, channel in enumerate(self.custom_channels):
            if channel['name'] == channel_name:
                return self.delete_channel(i)
        
        return False, f"Channel '{channel_name}' not found!"
    
    def duplicate_channel(self, channel_index):
        """Duplicate a channel by index.
        
        Args:
            channel_index: Index of the channel to duplicate
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if channel_index < 0 or channel_index >= len(self.custom_channels):
            return False, "Invalid channel index!"
        
        original_channel = self.custom_channels[channel_index].copy()
        
        # Generate unique name
        base_name = original_channel['name']
        new_name = f"{base_name}_copy"
        
        counter = 1
        while any(ch['name'] == new_name for ch in self.custom_channels):
            new_name = f"{base_name}_copy_{counter}"
            counter += 1
        
        original_channel['name'] = new_name
        
        self.custom_channels.append(original_channel)
        self.logger(f"📋 Duplicated channel: {base_name} → {new_name}")
        return True, ""
    
    def find_channel_by_name(self, channel_name):
        """Find a channel by name.
        
        Args:
            channel_name: Name of the channel
            
        Returns:
            tuple: (channel_dict or None, index or -1)
        """
        for i, channel in enumerate(self.custom_channels):
            if channel['name'] == channel_name:
                return channel, i
        return None, -1
    
    def clear_all_channels(self):
        """Clear all custom channels."""
        count = len(self.custom_channels)
        self.custom_channels.clear()
        self.logger(f"🗑️ All {count} custom channels cleared.")
    
    def get_all_channels(self):
        """Get all custom channel configurations.
        
        Returns:
            list: List of channel configurations
        """
        return self.custom_channels.copy()
    
    def set_all_channels(self, channels):
        """Set all custom channel configurations.
        
        Args:
            channels: List of channel configurations
        """
        self.custom_channels = channels.copy()
        self.logger(f"📊 Loaded {len(channels)} custom channels")
    
    def get_channel_count(self):
        """Get the number of configured channels.
        
        Returns:
            int: Number of channels
        """
        return len(self.custom_channels)
    
    def validate_channel_config(self, config):
        """Validate a channel configuration.
        
        Args:
            config: Channel configuration dictionary
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        required_fields = [
            'name', 'csv_file', 'x_column', 'y_column', 'z_column',
            'vehicle_x_channel', 'vehicle_y_channel'
        ]
        
        # Check for required fields
        for field in required_fields:
            if not config.get(field, '').strip():
                return False, f"Field '{field}' is required!"
        
        # Check if CSV file exists
        csv_file = config['csv_file'].strip()
        if not os.path.exists(csv_file):
            return False, "CSV file does not exist!"
        
        # Check that X, Y, Z columns are different
        x_col = config['x_column'].strip()
        y_col = config['y_column'].strip()
        z_col = config['z_column'].strip()
        
        if x_col == y_col or x_col == z_col or y_col == z_col:
            return False, "X, Y, and Z columns must be different!"
        
        return True, ""
    
    def create_channel_config(self, name, csv_file, x_column, y_column, z_column,
                            vehicle_x_channel, vehicle_y_channel, units="", comment=""):
        """Create a new channel configuration dictionary.
        
        Args:
            name: Channel name
            csv_file: Path to CSV surface table file
            x_column: X-axis column name in CSV
            y_column: Y-axis column name in CSV
            z_column: Z-axis column name in CSV
            vehicle_x_channel: Vehicle X channel name
            vehicle_y_channel: Vehicle Y channel name
            units: Units for the channel (optional)
            comment: Comment for the channel (optional)
            
        Returns:
            dict: Channel configuration dictionary
        """
        return {
            'name': name.strip(),
            'csv_file': csv_file.strip(),
            'x_column': x_column.strip(),
            'y_column': y_column.strip(),
            'z_column': z_column.strip(),
            'vehicle_x_channel': vehicle_x_channel.strip(),
            'vehicle_y_channel': vehicle_y_channel.strip(),
            'units': units.strip(),
            'comment': comment.strip()
        }
    
    def get_channels_summary(self):
        """Get a summary of all configured channels.
        
        Returns:
            dict: Summary information
        """
        if not self.custom_channels:
            return {
                'total_channels': 0,
                'csv_files': [],
                'vehicle_channels': []
            }
        
        csv_files = set()
        vehicle_channels = set()
        
        for channel in self.custom_channels:
            csv_files.add(os.path.basename(channel['csv_file']))
            vehicle_channels.add(channel['vehicle_x_channel'])
            vehicle_channels.add(channel['vehicle_y_channel'])
        
        return {
            'total_channels': len(self.custom_channels),
            'csv_files': sorted(list(csv_files)),
            'vehicle_channels': sorted(list(vehicle_channels))
        }


class ChannelValidator:
    """Validates channel configurations and dependencies."""
    
    def __init__(self, logger=None):
        """Initialize the channel validator.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
    
    def validate_csv_file(self, csv_file_path, x_col, y_col, z_col):
        """Validate a CSV file and its columns.
        
        Args:
            csv_file_path: Path to the CSV file
            x_col: X column name
            y_col: Y column name
            z_col: Z column name
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        import pandas as pd
        
        if not os.path.exists(csv_file_path):
            return False, "CSV file does not exist!"
        
        try:
            df = pd.read_csv(csv_file_path, nrows=5)  # Read just a few rows to check structure
            columns = df.columns.tolist()
            
            # Check if required columns exist
            missing_columns = []
            for col_name, col_label in [(x_col, 'X'), (y_col, 'Y'), (z_col, 'Z')]:
                if col_name not in columns:
                    missing_columns.append(f"{col_label} column '{col_name}'")
            
            if missing_columns:
                return False, f"Missing columns in CSV: {', '.join(missing_columns)}"
            
            # Check if columns have numeric data
            for col_name, col_label in [(x_col, 'X'), (y_col, 'Y'), (z_col, 'Z')]:
                try:
                    pd.to_numeric(df[col_name], errors='coerce')
                except Exception:
                    return False, f"{col_label} column '{col_name}' does not contain valid numeric data"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error reading CSV file: {str(e)}"
    
    def validate_vehicle_channels(self, vehicle_data, x_channel, y_channel):
        """Validate that vehicle channels exist in the vehicle data.
        
        Args:
            vehicle_data: Vehicle data object (MDF or DataFrame)
            x_channel: Vehicle X channel name
            y_channel: Vehicle Y channel name
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if vehicle_data is None:
            return False, "No vehicle data loaded!"
        
        # Handle different types of vehicle data
        if hasattr(vehicle_data, 'columns'):  # DataFrame (CSV)
            available_channels = vehicle_data.columns.tolist()
        elif hasattr(vehicle_data, 'channels_db'):  # MDF
            available_channels = list(vehicle_data.channels_db.keys())
        else:
            return False, "Unsupported vehicle data format!"
        
        missing_channels = []
        if x_channel not in available_channels:
            missing_channels.append(f"X channel '{x_channel}'")
        if y_channel not in available_channels:
            missing_channels.append(f"Y channel '{y_channel}'")
        
        if missing_channels:
            return False, f"Missing vehicle channels: {', '.join(missing_channels)}"
        
        return True, ""
    
    def validate_all_channels(self, channels, vehicle_data=None):
        """Validate all channel configurations.
        
        Args:
            channels: List of channel configurations
            vehicle_data: Vehicle data object (optional)
            
        Returns:
            tuple: (is_valid: bool, validation_results: list)
        """
        results = []
        all_valid = True
        
        for i, channel in enumerate(channels):
            channel_results = {
                'index': i,
                'name': channel.get('name', f'Channel {i+1}'),
                'csv_valid': True,
                'vehicle_channels_valid': True,
                'errors': []
            }
            
            # Validate CSV file
            csv_result = self.validate_csv_file(
                channel['csv_file'],
                channel['x_column'],
                channel['y_column'],
                channel['z_column']
            )
            
            if not csv_result[0]:
                channel_results['csv_valid'] = False
                channel_results['errors'].append(f"CSV: {csv_result[1]}")
                all_valid = False
            
            # Validate vehicle channels if vehicle data is available
            if vehicle_data is not None:
                vehicle_result = self.validate_vehicle_channels(
                    vehicle_data,
                    channel['vehicle_x_channel'],
                    channel['vehicle_y_channel']
                )
                
                if not vehicle_result[0]:
                    channel_results['vehicle_channels_valid'] = False
                    channel_results['errors'].append(f"Vehicle: {vehicle_result[1]}")
                    all_valid = False
            
            results.append(channel_results)
        
        return all_valid, results