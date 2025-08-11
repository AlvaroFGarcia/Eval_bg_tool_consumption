"""
Filtering System Module for Vehicle Log Channel Appender
Contains Excel-like filtering and search functionality for channel management.
"""

import os
from typing import Dict, List, Set, Any


class ChannelFilter:
    """Handles filtering and searching of custom channels."""
    
    def __init__(self, logger=None):
        """Initialize the channel filter.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
        self.excel_filters = {}
        self.active_filters = {}
        self.search_term = ""
        
        # Initialize Excel-like filters for all columns
        columns = ["Name", "CSV File", "X Col", "Y Col", "Z Col", "Veh X", "Veh Y", "Units", "Comment"]
        for col in columns:
            self.excel_filters[col] = {
                "enabled": False, 
                "selected_values": set(), 
                "filter_type": "include"
            }
    
    def set_search_term(self, search_term):
        """Set the search term for filtering.
        
        Args:
            search_term: String to search for
        """
        self.search_term = search_term.lower().strip()
    
    def get_channel_column_value(self, channel, column_name):
        """Get the value for a specific column from a channel dictionary.
        
        Args:
            channel: Channel dictionary
            column_name: Name of the column
            
        Returns:
            str: Value for the column
        """
        if column_name == "Name":
            return channel.get('name', '')
        elif column_name == "CSV File":
            return os.path.basename(channel.get('csv_file', ''))
        elif column_name == "X Col":
            return channel.get('x_column', '')
        elif column_name == "Y Col":
            return channel.get('y_column', '')
        elif column_name == "Z Col":
            return channel.get('z_column', '')
        elif column_name == "Veh X":
            return channel.get('vehicle_x_channel', '')
        elif column_name == "Veh Y":
            return channel.get('vehicle_y_channel', '')
        elif column_name == "Units":
            return channel.get('units', '')
        elif column_name == "Comment":
            return channel.get('comment', '')
        else:
            return ''
    
    def get_unique_values_for_column(self, channels, column_name):
        """Get all unique values for a specific column from the channels data.
        
        Args:
            channels: List of channel dictionaries
            column_name: Name of the column
            
        Returns:
            list: Sorted list of unique values
        """
        values = set()
        
        for channel in channels:
            value = self.get_channel_column_value(channel, column_name)
            if value.strip():  # Only add non-empty values
                values.add(value.strip())
        
        return sorted(list(values), key=str.lower)
    
    def apply_search_filter(self, channel):
        """Apply search filter to a single channel.
        
        Args:
            channel: Channel dictionary
            
        Returns:
            bool: True if channel passes search filter
        """
        if not self.search_term:
            return True
        
        # Search across all channel fields
        channel_text = ' '.join([
            channel.get('name', ''),
            os.path.basename(channel.get('csv_file', '')),
            channel.get('x_column', ''),
            channel.get('y_column', ''),
            channel.get('z_column', ''),
            channel.get('vehicle_x_channel', ''),
            channel.get('vehicle_y_channel', ''),
            channel.get('units', ''),
            channel.get('comment', '')
        ]).lower()
        
        return self.search_term in channel_text
    
    def apply_excel_filter(self, channel, column_name, filter_config):
        """Apply Excel-like filter to a single channel for a specific column.
        
        Args:
            channel: Channel dictionary
            column_name: Name of the column
            filter_config: Filter configuration dictionary
            
        Returns:
            bool: True if channel passes the filter
        """
        if not filter_config["enabled"] or not filter_config["selected_values"]:
            return True
        
        channel_value = self.get_channel_column_value(channel, column_name)
        filter_type = filter_config["filter_type"]
        selected_values = filter_config["selected_values"]
        
        if filter_type == "include":
            # Show only if value is in selected values
            return channel_value in selected_values
        elif filter_type == "exclude":
            # Hide if value is in selected values
            return channel_value not in selected_values
        
        return True
    
    def apply_legacy_filters(self, channel):
        """Apply legacy advanced filters to a single channel.
        
        Args:
            channel: Channel dictionary
            
        Returns:
            bool: True if channel passes all legacy filters
        """
        if not any(self.active_filters.values()):
            return True
        
        # Name filter
        if self.active_filters.get('name'):
            if self.active_filters['name'].lower() not in channel.get('name', '').lower():
                return False
        
        # CSV file filter
        if self.active_filters.get('csv'):
            csv_basename = os.path.basename(channel.get('csv_file', ''))
            if self.active_filters['csv'].lower() not in csv_basename.lower():
                return False
        
        # Vehicle X channel filter
        if self.active_filters.get('veh_x'):
            if self.active_filters['veh_x'].lower() not in channel.get('vehicle_x_channel', '').lower():
                return False
        
        # Vehicle Y channel filter
        if self.active_filters.get('veh_y'):
            if self.active_filters['veh_y'].lower() not in channel.get('vehicle_y_channel', '').lower():
                return False
        
        # Units filter
        if self.active_filters.get('units'):
            if self.active_filters['units'].lower() not in channel.get('units', '').lower():
                return False
        
        # Comment filter
        if self.active_filters.get('comment'):
            if self.active_filters['comment'].lower() not in channel.get('comment', '').lower():
                return False
        
        return True
    
    def filter_channels(self, channels):
        """Apply all filters to a list of channels.
        
        Args:
            channels: List of channel dictionaries
            
        Returns:
            list: Filtered list of channels
        """
        filtered_channels = []
        
        for channel in channels:
            show_channel = True
            
            # Apply search filter first
            if not self.apply_search_filter(channel):
                show_channel = False
            
            # Apply Excel column filters
            if show_channel:
                for column_name, filter_config in self.excel_filters.items():
                    if not self.apply_excel_filter(channel, column_name, filter_config):
                        show_channel = False
                        break
            
            # Apply legacy advanced filters
            if show_channel:
                if not self.apply_legacy_filters(channel):
                    show_channel = False
            
            if show_channel:
                filtered_channels.append(channel)
        
        return filtered_channels
    
    def set_excel_filter(self, column_name, selected_values, filter_type="include"):
        """Set Excel-like filter for a column.
        
        Args:
            column_name: Name of the column
            selected_values: Set of selected values
            filter_type: "include" or "exclude"
        """
        if column_name in self.excel_filters:
            self.excel_filters[column_name]["selected_values"] = selected_values
            self.excel_filters[column_name]["filter_type"] = filter_type
            self.excel_filters[column_name]["enabled"] = bool(selected_values)
            
            filter_type_text = "Include" if filter_type == "include" else "Exclude"
            self.logger(f"🔽 {filter_type_text} filter applied to '{column_name}': {len(selected_values)} values selected")
    
    def clear_excel_filter(self, column_name):
        """Clear Excel-like filter for a column.
        
        Args:
            column_name: Name of the column
        """
        if column_name in self.excel_filters:
            self.excel_filters[column_name]["selected_values"] = set()
            self.excel_filters[column_name]["enabled"] = False
            self.logger(f"🧹 Filter cleared for column '{column_name}'")
    
    def clear_all_excel_filters(self):
        """Clear all Excel-like column filters."""
        for column_name in self.excel_filters:
            self.excel_filters[column_name]["enabled"] = False
            self.excel_filters[column_name]["selected_values"] = set()
        self.logger("🧹 All column filters cleared")
    

    
    def get_filter_status(self, total_channels, filtered_channels):
        """Get status information about current filters.
        
        Args:
            total_channels: Total number of channels
            filtered_channels: Number of channels after filtering
            
        Returns:
            str: Status message
        """
        active_excel_filters = sum(1 for f in self.excel_filters.values() if f["enabled"])
        search_active = bool(self.search_term)
        legacy_filters_active = any(self.active_filters.values())
        
        filter_info = []
        if active_excel_filters > 0:
            filter_info.append(f"{active_excel_filters} column filter(s)")
        if legacy_filters_active:
            filter_info.append("legacy filters")
        if search_active:
            filter_info.append(f"search: '{self.search_term}'")
        
        if filter_info:
            return f"🔽 Applied {', '.join(filter_info)}: Showing {filtered_channels}/{total_channels} channels"
        else:
            return f"📊 Showing all {total_channels} channels"
    
    def get_column_header_text(self, column_name):
        """Get the header text for a column with filter indicator.
        
        Args:
            column_name: Name of the column
            
        Returns:
            str: Header text with filter indicator
        """
        if self.excel_filters[column_name]["enabled"] and self.excel_filters[column_name]["selected_values"]:
            # Show filtered icon
            return f"{column_name} 🔽✅"
        else:
            # Show normal filter icon
            return f"{column_name} 🔽"


