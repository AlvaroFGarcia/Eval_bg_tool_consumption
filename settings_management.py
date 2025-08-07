"""
Settings Management Module for Vehicle Log Channel Appender
Contains all settings and configuration management functionality.
"""

import json
import os
from datetime import datetime
from pathlib import Path


class SettingsManager:
    """Handles all settings operations."""
    
    def __init__(self, logger=None):
        """Initialize the settings manager.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
        self.slot_names = {1: "Slot 1", 2: "Slot 2", 3: "Slot 3"}
    
    def get_all_settings(self, app_state):
        """Get all current settings in a single dictionary.
        
        Args:
            app_state: Dictionary containing current application state
            
        Returns:
            dict: All current settings
        """
        return {
            'vehicle_file': app_state.get('vehicle_file_path'),
            'custom_channels': app_state.get('custom_channels', []),
            'output_format': app_state.get('output_format', 'mf4'),
            'theme': app_state.get('theme', 'dark'),
            'slot_names': self.slot_names,
            'form_settings': app_state.get('form_settings', {}),
            'saved_at': datetime.now().isoformat()
        }
    
    def save_settings(self, app_state, filename='channel_appender_settings_modern.json'):
        """Auto-save current settings to default file.
        
        Args:
            app_state: Dictionary containing current application state
            filename: Filename to save to
        """
        try:
            settings = self.get_all_settings(app_state)
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=2)
            self.logger(f"✅ Settings auto-saved to {filename}")
        except Exception as e:
            self.logger(f"❌ Error auto-saving settings: {str(e)}")
    
    def load_settings_on_startup(self, filename='channel_appender_settings_modern.json'):
        """Load settings from default file on startup.
        
        Args:
            filename: Filename to load from
            
        Returns:
            dict or None: Loaded settings or None if not found
        """
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    settings = json.load(f)
                self.logger("✅ Previous settings loaded automatically")
                return settings
            return None
        except Exception as e:
            self.logger(f"⚠️ Could not load previous settings: {str(e)}")
            return None
    
    def save_settings_as(self, app_state, file_path):
        """Save settings to a specific file.
        
        Args:
            app_state: Dictionary containing current application state
            file_path: Path to save the settings file
        """
        try:
            settings = self.get_all_settings(app_state)
            num_channels = len(app_state.get('custom_channels', []))
            settings['description'] = f"Settings saved on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} with {num_channels} custom channels"
            
            with open(file_path, 'w') as f:
                json.dump(settings, f, indent=2)
            self.logger(f"✅ Settings saved to {os.path.basename(file_path)}")
            return True
        except Exception as e:
            self.logger(f"❌ Error saving settings: {str(e)}")
            return False
    
    def load_settings_from(self, file_path):
        """Load settings from a specific file.
        
        Args:
            file_path: Path to load the settings file from
            
        Returns:
            dict or None: Loaded settings or None if failed
        """
        try:
            with open(file_path, 'r') as f:
                settings = json.load(f)
            self.logger(f"✅ Settings loaded from {os.path.basename(file_path)}")
            return settings
        except Exception as e:
            self.logger(f"❌ Error loading settings: {str(e)}")
            return None
    
    def quick_save_settings(self, app_state, slot):
        """Quick save settings to a numbered slot.
        
        Args:
            app_state: Dictionary containing current application state
            slot: Slot number (1-3)
        """
        try:
            settings = self.get_all_settings(app_state)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            num_channels = len(app_state.get('custom_channels', []))
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            
            settings['description'] = f"Quick save slot {slot} ({slot_name}) - {timestamp} ({num_channels} channels)"
            settings['slot_name'] = slot_name
            
            filename = f"quick_save_slot_{slot}_modern.json"
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.logger(f"✅ Quick saved to slot {slot} ({slot_name}): {num_channels} channels")
            return True
            
        except Exception as e:
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            self.logger(f"❌ Error quick saving to slot {slot} ({slot_name}): {str(e)}")
            return False
    
    def quick_load_settings(self, slot):
        """Quick load settings from a numbered slot.
        
        Args:
            slot: Slot number (1-3)
            
        Returns:
            dict or None: Loaded settings or None if slot is empty/failed
        """
        filename = f"quick_save_slot_{slot}_modern.json"
        
        if not os.path.exists(filename):
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            self.logger(f"⚠️ Quick save slot {slot} ({slot_name}) is empty")
            return None
        
        try:
            with open(filename, 'r') as f:
                settings = json.load(f)
            
            num_channels = len(settings.get('custom_channels', []))
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            
            self.logger(f"✅ Quick loaded from slot {slot} ({slot_name}): {num_channels} channels")
            return settings
            
        except Exception as e:
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            self.logger(f"❌ Error quick loading from slot {slot} ({slot_name}): {str(e)}")
            return None
    
    def update_slot_name(self, slot, new_name):
        """Update slot name.
        
        Args:
            slot: Slot number (1-3)
            new_name: New name for the slot
        """
        if new_name.strip():
            self.slot_names[slot] = new_name.strip()
        else:
            self.slot_names[slot] = f"Slot {slot}"
        self.logger(f"✅ Renamed slot {slot} to '{self.slot_names[slot]}'")
    
    def get_slot_name(self, slot):
        """Get the name of a slot.
        
        Args:
            slot: Slot number (1-3)
            
        Returns:
            str: Slot name
        """
        return self.slot_names.get(slot, f"Slot {slot}")


class ConfigurationManager:
    """Handles channel configuration import/export."""
    
    def __init__(self, logger=None):
        """Initialize the configuration manager.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
    
    def export_channel_config(self, custom_channels, file_path):
        """Export channel configuration to JSON.
        
        Args:
            custom_channels: List of custom channel configurations
            file_path: Path to save the configuration file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not custom_channels:
            self.logger("⚠️ No channels to export")
            return False
        
        try:
            config = {
                'channels': custom_channels,
                'exported_at': datetime.now().isoformat(),
                'total_channels': len(custom_channels)
            }
            
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.logger(f"📤 Channel configuration exported: {os.path.basename(file_path)}")
            return True
            
        except Exception as e:
            self.logger(f"❌ Error exporting configuration: {str(e)}")
            return False
    
    def import_channel_config(self, file_path):
        """Import channel configuration from JSON.
        
        Args:
            file_path: Path to load the configuration file from
            
        Returns:
            dict or None: Configuration data or None if failed
        """
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            
            # Validate configuration format
            if 'channels' not in config:
                self.logger("❌ Invalid configuration file format! Missing 'channels' key.")
                return None
            
            imported_channels = config['channels']
            if not isinstance(imported_channels, list):
                self.logger("❌ Invalid configuration file format! 'channels' is not a list.")
                return None
            
            self.logger(f"📥 Channel configuration loaded: {len(imported_channels)} channels")
            return config
            
        except json.JSONDecodeError:
            self.logger("❌ Invalid JSON file format!")
            return None
        except Exception as e:
            self.logger(f"❌ Error importing configuration: {str(e)}")
            return None
    
    def merge_channel_configs(self, existing_channels, imported_channels, mode="add"):
        """Merge imported channels with existing ones.
        
        Args:
            existing_channels: List of existing custom channels
            imported_channels: List of imported custom channels
            mode: "add" to add to existing, "replace" to replace all
            
        Returns:
            tuple: (merged_channels, conflicts_list)
        """
        conflicts = []
        
        if mode == "replace":
            return imported_channels, []
        
        # Add mode - check for conflicts and rename as needed
        existing_names = [ch['name'] for ch in existing_channels]
        merged_channels = existing_channels.copy()
        
        for channel in imported_channels:
            # Validate channel structure
            required_fields = ['name', 'csv_file', 'x_column', 'y_column', 'z_column', 
                             'vehicle_x_channel', 'vehicle_y_channel']
            
            if not all(field in channel for field in required_fields):
                self.logger(f"⚠️ Skipping invalid channel: {channel.get('name', 'Unknown')}")
                continue
            
            original_name = channel['name']
            
            if original_name in existing_names:
                # Generate unique name
                counter = 1
                while f"{original_name}_{counter}" in existing_names:
                    counter += 1
                channel['name'] = f"{original_name}_{counter}"
                conflicts.append(f"{original_name} → {channel['name']}")
                existing_names.append(channel['name'])
            
            merged_channels.append(channel)
        
        return merged_channels, conflicts