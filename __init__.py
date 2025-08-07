"""
Vehicle Log Channel Appender - Modular Package

A modular implementation of the Vehicle Log Channel Appender for processing vehicle data
with surface table interpolation and custom channel generation.

This package provides:
- ModernUI components for user interface
- Data processing and interpolation capabilities
- File management for MDF/CSV files
- Settings and configuration management
- Channel management with filtering
- Comprehensive error handling and logging

Usage:
    from vehicle_log_channel_appender_modular import VehicleLogChannelAppenderModular
    
    # Create and run the application
    app = VehicleLogChannelAppenderModular()
    app.run()
"""

# Import main components for easy access
from .vehicle_log_channel_appender_modular import VehicleLogChannelAppenderModular

# Import modular components
from .ui_components import ModernAutocompleteCombobox, ModernProgressDialog
from .data_processing import DataProcessor, ChannelAnalyzer
from .file_management import FileManager, OutputGenerator
from .settings_management import SettingsManager, ConfigurationManager
from .channel_management import ChannelManager, ChannelValidator
from .filtering_system import ChannelFilter, TextFilterHelper

__version__ = "3.0.0"
__author__ = "Vehicle Log Channel Appender Team"
__description__ = "Modular vehicle log channel processing application"

# Define what gets imported with "from package import *"
__all__ = [
    'VehicleLogChannelAppenderModular',
    'ModernAutocompleteCombobox',
    'ModernProgressDialog',
    'DataProcessor',
    'ChannelAnalyzer',
    'FileManager',
    'OutputGenerator',
    'SettingsManager',
    'ConfigurationManager',
    'ChannelManager',
    'ChannelValidator',
    'ChannelFilter',
    'TextFilterHelper'
]