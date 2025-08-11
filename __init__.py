"""
Vehicle Log Channel Appender - Modular Package

This package provides a modular implementation of the Vehicle Log Channel Appender
with all components separated for better maintainability and testing.

Main Components:
- VehicleLogChannelAppenderModular: Main application class
- ChannelManager: Channel CRUD operations 
- ChannelValidator: Channel validation logic
- SettingsManager: Settings persistence
- ConfigurationManager: Import/export functionality
- ChannelFilter: Search and filtering
- DataProcessor: Surface table processing
- ChannelAnalyzer: Signal analysis
- FileManager: File I/O operations
- OutputGenerator: Output generation
- UI Components: Modern UI elements

Usage:
    from vehicle_log_channel_appender_modular import main
    main()
"""

__version__ = "1.0.0"
__author__ = "Vehicle Log Channel Appender Team"

# Import main function for easy access
from .vehicle_log_channel_appender_modular import main

__all__ = ['main']