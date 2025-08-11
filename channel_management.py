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
    

    
    def delete_channel_by_name(self, channel_name):
        """Delete a channel by name.
        
        Args:
            channel_name: Name of the channel to delete
            
        Returns:
            tuple: (success: bool, error_message: str)
        """
        for i, channel in enumerate(self.custom_channels):
            if channel['name'] == channel_name:
                deleted_channel = self.custom_channels.pop(i)
                self.logger(f"🗑️ Deleted channel: {deleted_channel['name']}")
                return True, ""
        
        return False, f"Channel '{channel_name}' not found!"
    
    def delete_multiple_channels_by_names(self, channel_names):
        """Delete multiple channels by their names.
        
        Args:
            channel_names: List of channel names to delete
            
        Returns:
            tuple: (success_count: int, error_messages: list)
        """
        if not channel_names:
            return 0, ["No channels selected for deletion"]
        
        success_count = 0
        errors = []
        
        # Sort names by index (descending) to avoid index shifting issues
        channels_to_delete = []
        for name in channel_names:
            for i, channel in enumerate(self.custom_channels):
                if channel['name'] == name:
                    channels_to_delete.append((i, channel))
                    break
        
        # Sort by index descending so we delete from the end first
        channels_to_delete.sort(key=lambda x: x[0], reverse=True)
        
        for index, channel in channels_to_delete:
            try:
                deleted_channel = self.custom_channels.pop(index)
                self.logger(f"🗑️ Deleted channel: {deleted_channel['name']}")
                success_count += 1
            except Exception as e:
                errors.append(f"Failed to delete '{channel['name']}': {str(e)}")
        
        return success_count, errors
    
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
    
    def duplicate_multiple_channels_by_names(self, channel_names):
        """Duplicate multiple channels by their names.
        
        Args:
            channel_names: List of channel names to duplicate
            
        Returns:
            tuple: (success_count: int, error_messages: list)
        """
        if not channel_names:
            return 0, ["No channels selected for duplication"]
        
        success_count = 0
        errors = []
        
        for channel_name in channel_names:
            # Find channel by name
            channel_found = False
            for i, channel in enumerate(self.custom_channels):
                if channel['name'] == channel_name:
                    success, error_msg = self.duplicate_channel(i)
                    if success:
                        success_count += 1
                    else:
                        errors.append(f"Failed to duplicate '{channel_name}': {error_msg}")
                    channel_found = True
                    break
            
            if not channel_found:
                errors.append(f"Channel '{channel_name}' not found for duplication")
        
        return success_count, errors
    
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
    



class ChannelValidator:
    """Validates channel configurations and dependencies."""
    
    def __init__(self, logger=None):
        """Initialize the channel validator.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
    
