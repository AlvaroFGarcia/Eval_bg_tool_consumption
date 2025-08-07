"""
Vehicle Log Channel Appender - Modular Edition
Complete implementation with ALL features from the original, now properly modularized.

This version maintains all the same functionality while using a clean modular architecture.
"""

import numpy as np
import pandas as pd
from asammdf import MDF, Signal
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import tkinter.ttk as ttk
import os
from pathlib import Path
import json
from datetime import datetime
import threading
from typing import List, Dict, Optional

# Import modular components
from ui_components import ModernAutocompleteCombobox, ModernProgressDialog
from data_processing import DataProcessor, ChannelAnalyzer
from file_management import FileManager, OutputGenerator
from settings_management import SettingsManager, ConfigurationManager
from channel_management import ChannelManager, ChannelValidator
from filtering_system import ChannelFilter, TextFilterHelper

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark")  # Default to dark mode
ctk.set_default_color_theme("blue")  # Professional blue theme


class VehicleLogChannelAppenderModular:
    """Modular version of the Vehicle Log Channel Appender."""
    
    def __init__(self):
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("🚗 Vehicle Log Channel Appender - Modular Edition")
        self.root.geometry("1200x700")
        
        # Set window icon and properties
        self.setup_window_properties()
        
        # Initialize modular components
        self.data_processor = DataProcessor(logger=self.log_status)
        self.channel_analyzer = ChannelAnalyzer(logger=self.log_status)
        self.file_manager = FileManager(logger=self.log_status)
        self.output_generator = OutputGenerator(logger=self.log_status)
        self.settings_manager = SettingsManager(logger=self.log_status)
        self.config_manager = ConfigurationManager(logger=self.log_status)
        self.channel_manager = ChannelManager(logger=self.log_status)
        self.channel_validator = ChannelValidator(logger=self.log_status)
        self.channel_filter = ChannelFilter(logger=self.log_status)
        
        # Data storage
        self.vehicle_file_path = None
        self.vehicle_data = None
        self.available_channels = []
        self.reference_timestamps = None
        
        # UI state variables
        self.search_var = ctk.StringVar()
        self.channel_name_var = ctk.StringVar()
        self.csv_file_var = ctk.StringVar()
        self.x_col_var = ctk.StringVar()
        self.y_col_var = ctk.StringVar()
        self.z_col_var = ctk.StringVar()
        self.veh_x_var = ctk.StringVar()
        self.veh_y_var = ctk.StringVar()
        self.units_var = ctk.StringVar()
        self.comment_var = ctk.StringVar()
        self.preserve_settings_var = ctk.BooleanVar(value=True)
        self.output_format_var = ctk.StringVar(value="mf4")
        self.theme_var = ctk.StringVar(value="dark")
        
        # UI components will be created in setup
        self.channels_tree = None
        self.status_text = None
        
        # Setup UI
        self.setup_ui()
        self.setup_bindings()
        
        # Load settings on startup
        self.load_settings_on_startup()
        
        # Initialize with welcome message
        self.log_status("🎉 Welcome to Vehicle Log Channel Appender - Modular Edition!")
        self.log_status("💡 Select a vehicle file and configure custom channels to begin")
    
    def setup_window_properties(self):
        """Configure window properties for compatibility."""
        # Center window on screen
        self.root.update_idletasks()
        width = 1200
        height = 700
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set minimum size for usability
        self.root.minsize(1200, 700)
        
        # Configure grid weights for responsive design
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
    
    def setup_ui(self):
        """Setup the modern user interface."""
        # Create main container with sidebar
        self.setup_sidebar()
        self.setup_main_content()
    
    def setup_sidebar(self):
        """Create modern sidebar with navigation and settings."""
        self.sidebar_frame = ctk.CTkFrame(self.root, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.sidebar_frame.grid_propagate(False)
        
        # App title in sidebar
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="🚗 Vehicle Log\nChannel Appender",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Version label
        version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Modular Edition v3.0",
            font=ctk.CTkFont(size=12)
        )
        version_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # File selection section
        self.file_frame = ctk.CTkFrame(self.sidebar_frame)
        self.file_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        file_label = ctk.CTkLabel(
            self.file_frame,
            text="📁 Vehicle File",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        file_label.pack(pady=(15, 5))
        
        self.select_file_button = ctk.CTkButton(
            self.file_frame,
            text="Select Vehicle File",
            command=self.select_vehicle_file,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.select_file_button.pack(pady=(0, 10), padx=10, fill="x")
        
        self.file_status_label = ctk.CTkLabel(
            self.file_frame,
            text="No file selected",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.file_status_label.pack(pady=(0, 15))
        
        # Settings section
        self.setup_settings_section()
    
    def setup_settings_section(self):
        """Setup the settings section in sidebar."""
        self.settings_frame = ctk.CTkFrame(self.sidebar_frame)
        self.settings_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        settings_label = ctk.CTkLabel(
            self.settings_frame,
            text="⚙️ Settings",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        settings_label.pack(pady=(15, 10))
        
        # Theme selector
        theme_label = ctk.CTkLabel(
            self.settings_frame,
            text="Theme:",
            font=ctk.CTkFont(size=12)
        )
        theme_label.pack(pady=(0, 5))
        
        self.theme_menu = ctk.CTkOptionMenu(
            self.settings_frame,
            values=["Dark", "Light"],
            command=self.change_theme,
            font=ctk.CTkFont(size=11)
        )
        self.theme_menu.pack(pady=(0, 15), padx=10, fill="x")
        
        # Quick save/load section
        self.setup_quick_save_load()
        
        # Main settings buttons
        self.save_settings_btn = ctk.CTkButton(
            self.settings_frame,
            text="💾 Save Settings As...",
            command=self.save_settings_as,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.save_settings_btn.pack(pady=(10, 5), padx=10, fill="x")
        
        self.load_settings_btn = ctk.CTkButton(
            self.settings_frame,
            text="📁 Load Settings From...",
            command=self.load_settings_from,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.load_settings_btn.pack(pady=(0, 15), padx=10, fill="x")
    
    def setup_quick_save_load(self):
        """Setup quick save/load controls."""
        quick_frame = ctk.CTkFrame(self.settings_frame)
        quick_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        quick_label = ctk.CTkLabel(
            quick_frame,
            text="⚡ Quick Save/Load:",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        quick_label.pack(pady=(10, 5))
        
        self.slot_name_entries = {}
        
        # Quick save/load buttons with names
        for i in range(1, 4):
            slot_frame = ctk.CTkFrame(quick_frame)
            slot_frame.pack(fill="x", pady=2)
            
            save_btn = ctk.CTkButton(
                slot_frame,
                text=f"S{i}",
                command=lambda slot=i: self.quick_save_settings(slot),
                width=30,
                height=25,
                font=ctk.CTkFont(size=10)
            )
            save_btn.pack(side="left", padx=(10, 5), pady=5)
            
            load_btn = ctk.CTkButton(
                slot_frame,
                text=f"L{i}",
                command=lambda slot=i: self.quick_load_settings(slot),
                width=30,
                height=25,
                font=ctk.CTkFont(size=10)
            )
            load_btn.pack(side="left", padx=5, pady=5)
            
            # Editable slot name entry
            name_entry = ctk.CTkEntry(
                slot_frame,
                width=120,
                height=25,
                font=ctk.CTkFont(size=9),
                placeholder_text=f"Slot {i}"
            )
            name_entry.pack(side="left", padx=(10, 5), pady=5)
            name_entry.insert(0, self.settings_manager.get_slot_name(i))
            name_entry.bind('<KeyRelease>', lambda e, slot=i: self.update_slot_name(slot, e))
            self.slot_name_entries[i] = name_entry
            
            # Rename button
            rename_btn = ctk.CTkButton(
                slot_frame,
                text="✏️",
                command=lambda slot=i: self.rename_slot_dialog(slot),
                width=25,
                height=25,
                font=ctk.CTkFont(size=8)
            )
            rename_btn.pack(side="right", padx=5, pady=5)
    
    def setup_main_content(self):
        """Setup the main content area with tabs."""
        # Main content frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 20), pady=20)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add tabs
        self.tabview.add("🔧 Processing")
        self.tabview.add("⚙️ Custom Channels")
        self.tabview.add("📋 Status Log")
        
        # Setup tab content
        self.setup_processing_tab()
        self.setup_custom_channels_tab()
        self.setup_status_log_tab()
    
    def setup_processing_tab(self):
        """Setup the processing tab with modern controls."""
        processing_tab = self.tabview.tab("🔧 Processing")
        
        # Create scrollable frame
        self.processing_scroll = ctk.CTkScrollableFrame(processing_tab)
        self.processing_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Output format selection
        format_frame = ctk.CTkFrame(self.processing_scroll)
        format_frame.pack(fill="x", pady=(0, 20))
        
        format_title = ctk.CTkLabel(
            format_frame,
            text="📊 Output Format",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        format_title.pack(pady=(20, 15))
        
        format_options_frame = ctk.CTkFrame(format_frame)
        format_options_frame.pack(padx=20, pady=(0, 20))
        
        self.format_radio_mf4 = ctk.CTkRadioButton(
            format_options_frame,
            text="🔧 MF4 (Recommended for calculated channels)",
            variable=self.output_format_var,
            value="mf4",
            font=ctk.CTkFont(size=12)
        )
        self.format_radio_mf4.pack(anchor="w", padx=20, pady=5)
        
        self.format_radio_csv = ctk.CTkRadioButton(
            format_options_frame,
            text="📈 CSV (For data analysis)",
            variable=self.output_format_var,
            value="csv",
            font=ctk.CTkFont(size=12)
        )
        self.format_radio_csv.pack(anchor="w", padx=20, pady=(5, 15))
        
        # Processing information
        info_frame = ctk.CTkFrame(self.processing_scroll)
        info_frame.pack(fill="x", pady=(0, 20))
        
        info_title = ctk.CTkLabel(
            info_frame,
            text="💡 Processing Information",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        info_title.pack(pady=(20, 10))
        
        info_text = ctk.CTkLabel(
            info_frame,
            text="Configure custom channels in the 'Custom Channels' tab, then process them here.\n"
                 "The tool will create calculated channels based on surface table interpolation.",
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        info_text.pack(padx=20, pady=(0, 20))
        
        # Process button
        self.process_button = ctk.CTkButton(
            self.processing_scroll,
            text="🚀 Process All Custom Channels",
            command=self.process_all_channels,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.process_button.pack(pady=20, padx=20, fill="x")
    
    def setup_custom_channels_tab(self):
        """Setup the custom channels tab with complete functionality."""
        channels_tab = self.tabview.tab("⚙️ Custom Channels")
        
        # Create scrollable container
        self.channels_scroll = ctk.CTkScrollableFrame(channels_tab)
        self.channels_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            self.channels_scroll,
            text="⚙️ Custom Channel Management",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Channel addition form
        self.setup_channel_form()
        
        # Channels table with search and filters
        self.setup_channels_table()
    
    def setup_channel_form(self):
        """Setup the channel addition form."""
        form_frame = ctk.CTkFrame(self.channels_scroll)
        form_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        form_title = ctk.CTkLabel(
            form_frame,
            text="➕ Add New Custom Channel",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        form_title.pack(pady=(15, 15))
        
        # Main form container
        main_form = ctk.CTkFrame(form_frame)
        main_form.pack(fill="x", padx=20, pady=(0, 15))
        
        # Channel name
        name_frame = ctk.CTkFrame(main_form)
        name_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(name_frame, text="📝 Channel Name:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=10)
        self.channel_name_entry = ctk.CTkEntry(name_frame, textvariable=self.channel_name_var, 
                                              placeholder_text="Enter channel name", width=250)
        self.channel_name_entry.pack(side="left", padx=10, pady=10)
        
        # CSV Surface Table file
        csv_frame = ctk.CTkFrame(main_form)
        csv_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(csv_frame, text="📊 Surface Table CSV:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=10)
        self.csv_file_entry = ctk.CTkEntry(csv_frame, textvariable=self.csv_file_var, 
                                          placeholder_text="Select CSV file", width=200)
        self.csv_file_entry.pack(side="left", padx=10, pady=10)
        
        self.browse_csv_btn = ctk.CTkButton(csv_frame, text="📁 Browse", 
                                           command=self.browse_csv_file, width=80)
        self.browse_csv_btn.pack(side="left", padx=5, pady=10)
        
        # CSV columns configuration
        self.setup_csv_config(main_form)
        
        # Vehicle channels configuration
        self.setup_vehicle_config(main_form)
        
        # Units and comment
        self.setup_meta_config(main_form)
        
        # Add button and preserve settings
        add_frame = ctk.CTkFrame(main_form)
        add_frame.pack(fill="x", padx=10, pady=15)
        
        self.preserve_checkbox = ctk.CTkCheckBox(
            add_frame,
            text="💾 Keep settings after adding channel",
            variable=self.preserve_settings_var,
            font=ctk.CTkFont(size=11)
        )
        self.preserve_checkbox.pack(side="left", padx=10, pady=10)
        
        self.add_channel_button = ctk.CTkButton(
            add_frame,
            text="➕ Add Custom Channel",
            command=self.add_custom_channel,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.add_channel_button.pack(side="right", padx=10, pady=10)
    
    def setup_csv_config(self, parent):
        """Setup CSV configuration section."""
        csv_config_frame = ctk.CTkFrame(parent)
        csv_config_frame.pack(fill="x", padx=10, pady=10)
        
        csv_config_title = ctk.CTkLabel(
            csv_config_frame,
            text="📋 CSV Surface Table Configuration",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        csv_config_title.pack(pady=(10, 10))
        
        # CSV columns in a grid
        csv_grid = ctk.CTkFrame(csv_config_frame)
        csv_grid.pack(fill="x", padx=20, pady=(0, 15))
        
        # X column
        ctk.CTkLabel(csv_grid, text="📊 X-axis Column (e.g., RPM):", 
                    font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.x_col_combo = ModernAutocompleteCombobox(csv_grid, variable=self.x_col_var, width=180)
        self.x_col_combo.grid(row=0, column=1, padx=10, pady=5)
        
        # Y column
        ctk.CTkLabel(csv_grid, text="📈 Y-axis Column (e.g., ETASP):", 
                    font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.y_col_combo = ModernAutocompleteCombobox(csv_grid, variable=self.y_col_var, width=180)
        self.y_col_combo.grid(row=1, column=1, padx=10, pady=5)
        
        # Z column
        ctk.CTkLabel(csv_grid, text="📋 Z-axis Column (Values):", 
                    font=ctk.CTkFont(size=11)).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.z_col_combo = ModernAutocompleteCombobox(csv_grid, variable=self.z_col_var, width=180)
        self.z_col_combo.grid(row=2, column=1, padx=10, pady=5)
    
    def setup_vehicle_config(self, parent):
        """Setup vehicle configuration section."""
        veh_config_frame = ctk.CTkFrame(parent)
        veh_config_frame.pack(fill="x", padx=10, pady=10)
        
        veh_config_title = ctk.CTkLabel(
            veh_config_frame,
            text="🚗 Vehicle Log Channel Selection",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        veh_config_title.pack(pady=(10, 10))
        
        # Vehicle channels in a grid
        veh_grid = ctk.CTkFrame(veh_config_frame)
        veh_grid.pack(fill="x", padx=20, pady=(0, 15))
        
        # Vehicle X channel
        ctk.CTkLabel(veh_grid, text="🔧 Vehicle X Channel:", 
                    font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.veh_x_combo = ModernAutocompleteCombobox(veh_grid, variable=self.veh_x_var, width=200)
        self.veh_x_combo.grid(row=0, column=1, padx=10, pady=5)
        
        # Vehicle Y channel
        ctk.CTkLabel(veh_grid, text="📊 Vehicle Y Channel:", 
                    font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.veh_y_combo = ModernAutocompleteCombobox(veh_grid, variable=self.veh_y_var, width=200)
        self.veh_y_combo.grid(row=1, column=1, padx=10, pady=5)
    
    def setup_meta_config(self, parent):
        """Setup metadata configuration section."""
        meta_frame = ctk.CTkFrame(parent)
        meta_frame.pack(fill="x", padx=10, pady=10)
        
        meta_grid = ctk.CTkFrame(meta_frame)
        meta_grid.pack(fill="x", padx=20, pady=15)
        
        # Units
        ctk.CTkLabel(meta_grid, text="📏 Units:", 
                    font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.units_entry = ctk.CTkEntry(meta_grid, textvariable=self.units_var, 
                                       placeholder_text="e.g., bar, %", width=120)
        self.units_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Comment
        ctk.CTkLabel(meta_grid, text="💬 Comment:", 
                    font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.comment_entry = ctk.CTkEntry(meta_grid, textvariable=self.comment_var, 
                                         placeholder_text="Optional comment", width=200)
        self.comment_entry.grid(row=0, column=3, padx=10, pady=5)
    
    def setup_channels_table(self):
        """Setup the channels table with search and filtering."""
        table_frame = ctk.CTkFrame(self.channels_scroll)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 20))
        
        table_title = ctk.CTkLabel(
            table_frame,
            text="📋 Configured Custom Channels",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        table_title.pack(pady=(15, 5))
        
        # Search and filter controls
        self.setup_search_controls(table_frame)
        
        # Create treeview for channels
        self.setup_treeview(table_frame)
        
        # Table management buttons
        self.setup_table_controls(table_frame)
    
    def setup_search_controls(self, parent):
        """Setup search and filter controls."""
        search_frame = ctk.CTkFrame(parent)
        search_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        search_controls = ctk.CTkFrame(search_frame)
        search_controls.pack(fill="x", padx=15, pady=15)
        
        # Search
        ctk.CTkLabel(search_controls, text="🔍 Search:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(
            search_controls,
            textvariable=self.search_var,
            placeholder_text="Type to search channels...",
            width=200
        )
        self.search_entry.pack(side="left", padx=10)
        
        self.clear_search_btn = ctk.CTkButton(
            search_controls,
            text="✖️ Clear",
            command=self.clear_search,
            width=60,
            height=28
        )
        self.clear_search_btn.pack(side="left", padx=5)
        
        # Filter buttons
        self.clear_all_filters_btn = ctk.CTkButton(
            search_controls,
            text="🧹 Clear All Filters",
            command=self.clear_all_excel_filters,
            width=120,
            height=28
        )
        self.clear_all_filters_btn.pack(side="right", padx=5)
    
    def setup_treeview(self, parent):
        """Setup the treeview for displaying channels."""
        # Configure treeview style with explicit theme
        style = ttk.Style()
        
        try:
            style.theme_use('clam')
        except:
            pass
            
        # Configure the treeview with high contrast colors
        style.configure("Modern.Treeview", 
                       background="#2b2b2b",
                       foreground="#ffffff",
                       fieldbackground="#2b2b2b",
                       font=("Segoe UI", 10),
                       rowheight=25,
                       borderwidth=0)
        
        # Configure headers with very high contrast
        style.configure("Modern.Treeview.Heading", 
                       background="#666666",
                       foreground="#ffffff",
                       relief="raised",
                       borderwidth=1,
                       font=("Segoe UI", 10, "bold"),
                       anchor="center",
                       focuscolor="none")
        
        # Configure hover and selection states
        style.map("Modern.Treeview.Heading",
                 background=[('active', '#777777')],
                 foreground=[('active', '#ffffff')])
        style.map("Modern.Treeview",
                 background=[('selected', '#0d7377')],
                 foreground=[('selected', '#ffffff')])
        
        # Table container with proper scrollbars
        tree_container = ctk.CTkFrame(parent)
        tree_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Configure grid for proper scrollbar alignment
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Create treeview for custom channels
        columns = ("Name", "CSV File", "X Col", "Y Col", "Z Col", "Veh X", "Veh Y", "Units", "Comment")
        
        self.channels_tree = ttk.Treeview(tree_container, 
                                         columns=columns, 
                                         show="headings", 
                                         height=12,
                                         style="Modern.Treeview")
        
        # Configure columns with filter icons
        column_widths = {"Name": 120, "CSV File": 150, "X Col": 80, "Y Col": 80, "Z Col": 80, 
                        "Veh X": 120, "Veh Y": 120, "Units": 60, "Comment": 150}
        
        for col in columns:
            # Add filter icon to column header
            header_text = self.channel_filter.get_column_header_text(col)
            self.channels_tree.heading(col, text=header_text, anchor="center", 
                                     command=lambda c=col: self.show_excel_filter(c))
            self.channels_tree.column(col, width=column_widths.get(col, 100), minwidth=60, anchor="center")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.channels_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.channels_tree.xview)
        
        self.channels_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout for proper alignment
        self.channels_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
    
    def setup_table_controls(self, parent):
        """Setup table management controls."""
        controls_frame = ctk.CTkFrame(parent)
        controls_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        # First row - main actions
        controls_row1 = ctk.CTkFrame(controls_frame)
        controls_row1.pack(fill="x", padx=5, pady=(5, 2))
        
        self.edit_channel_btn = ctk.CTkButton(
            controls_row1,
            text="✏️ Edit Selected",
            command=self.edit_selected_channel,
            width=120,
            height=30
        )
        self.edit_channel_btn.pack(side="left", padx=5)
        
        self.delete_channel_btn = ctk.CTkButton(
            controls_row1,
            text="🗑️ Delete Selected",
            command=self.delete_selected_channel,
            width=120,
            height=30
        )
        self.delete_channel_btn.pack(side="left", padx=5)
        
        self.duplicate_channel_btn = ctk.CTkButton(
            controls_row1,
            text="📋 Duplicate",
            command=self.duplicate_selected_channel,
            width=100,
            height=30
        )
        self.duplicate_channel_btn.pack(side="left", padx=5)
        
        self.clear_all_btn = ctk.CTkButton(
            controls_row1,
            text="🧹 Clear All",
            command=self.clear_all_channels,
            width=100,
            height=30
        )
        self.clear_all_btn.pack(side="left", padx=5)
        
        # Second row - import/export
        controls_row2 = ctk.CTkFrame(controls_frame)
        controls_row2.pack(fill="x", padx=5, pady=(2, 5))
        
        self.import_config_btn = ctk.CTkButton(
            controls_row2,
            text="📥 Import Config",
            command=self.import_channel_config,
            width=120,
            height=30
        )
        self.import_config_btn.pack(side="left", padx=5)
        
        self.export_config_btn = ctk.CTkButton(
            controls_row2,
            text="📤 Export Config",
            command=self.export_channel_config,
            width=120,
            height=30
        )
        self.export_config_btn.pack(side="left", padx=5)
    
    def setup_status_log_tab(self):
        """Setup the status log tab."""
        log_tab = self.tabview.tab("📋 Status Log")
        
        # Log container
        log_container = ctk.CTkFrame(log_tab)
        log_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title and controls
        log_header = ctk.CTkFrame(log_container)
        log_header.pack(fill="x", padx=20, pady=(20, 10))
        
        log_title = ctk.CTkLabel(
            log_header,
            text="📋 Application Status Log",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        log_title.pack(side="left", pady=10)
        
        self.clear_log_button = ctk.CTkButton(
            log_header,
            text="🗑️ Clear Log",
            command=self.clear_status_log,
            height=30,
            width=100,
            font=ctk.CTkFont(size=11)
        )
        self.clear_log_button.pack(side="right", pady=10)
        
        # Status log display
        self.status_text = ctk.CTkTextbox(
            log_container,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.status_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    def setup_bindings(self):
        """Setup event bindings."""
        # Search functionality
        self.search_var.trace('w', self.on_search_change)
        
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    # Event handlers and core functionality methods will be continued in a follow-up...
    # This is getting quite long, so I'll continue with the rest in the next part
    
    def log_status(self, message):
        """Add a message to the status log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'status_text') and self.status_text:
            self.status_text.insert("end", formatted_message)
            self.status_text.see("end")
        else:
            print(formatted_message.strip())  # Fallback for early logging
    
    # Event Handlers
    def change_theme(self, theme):
        """Change the application theme."""
        theme_lower = theme.lower()
        ctk.set_appearance_mode(theme_lower)
        self.log_status(f"🎨 Theme changed to {theme} mode")

    def select_vehicle_file(self):
        """Open file dialog to select vehicle file."""
        file_path = filedialog.askopenfilename(
            title="Select Vehicle File",
            filetypes=[
                ("All Supported", "*.csv *.dat *.mdf *.mf4"),
                ("CSV Files", "*.csv"),
                ("DAT Files", "*.dat"),
                ("MDF Files", "*.mdf"),
                ("MF4 Files", "*.mf4")
            ]
        )
        
        if file_path:
            self.vehicle_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_status_label.configure(text=f"📁 {filename}")
            self.log_status(f"✅ Vehicle file selected: {filename}")
            
            # Load vehicle file
            try:
                self.vehicle_data, self.available_channels = self.file_manager.load_vehicle_file(file_path)
                # Update channel comboboxes
                self.veh_x_combo.set_completion_list(self.available_channels)
                self.veh_y_combo.set_completion_list(self.available_channels)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load vehicle file: {str(e)}")
                self.log_status(f"❌ Error loading vehicle file: {str(e)}")

    def browse_csv_file(self):
        """Browse for CSV surface table file and load its columns."""
        file_path = filedialog.askopenfilename(
            title="Select Surface Table CSV File",
            filetypes=[("CSV Files", "*.csv")]
        )
        
        if file_path:
            self.csv_file_var.set(file_path)
            
            # Load CSV columns for selection
            try:
                columns = self.file_manager.load_csv_columns(file_path)
                # Update comboboxes with available columns
                self.x_col_combo.set_completion_list(columns)
                self.y_col_combo.set_completion_list(columns)
                self.z_col_combo.set_completion_list(columns)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read CSV file: {str(e)}")

    def add_custom_channel(self):
        """Add a new custom channel configuration."""
        # Create channel configuration
        channel_config = self.channel_manager.create_channel_config(
            name=self.channel_name_var.get(),
            csv_file=self.csv_file_var.get(),
            x_column=self.x_col_var.get(),
            y_column=self.y_col_var.get(),
            z_column=self.z_col_var.get(),
            vehicle_x_channel=self.veh_x_var.get(),
            vehicle_y_channel=self.veh_y_var.get(),
            units=self.units_var.get(),
            comment=self.comment_var.get()
        )
        
        # Try to add the channel
        success, error_message = self.channel_manager.add_channel(channel_config)
        
        if success:
            # Update display
            self.update_channels_display()
            
            # Auto-save settings
            self.save_settings()
            
            # Clear input fields only if preserve_settings is False
            if not self.preserve_settings_var.get():
                self.clear_channel_form()
            else:
                # Just clear the name field for the next channel
                self.channel_name_var.set("")
        else:
            messagebox.showerror("Error", error_message)

    def clear_channel_form(self):
        """Clear all channel form fields."""
        self.channel_name_var.set("")
        self.csv_file_var.set("")
        self.x_col_var.set("")
        self.y_col_var.set("")
        self.z_col_var.set("")
        self.veh_x_var.set("")
        self.veh_y_var.set("")
        self.units_var.set("")
        self.comment_var.set("")

    def update_channels_display(self):
        """Update the channels display with current channels using filtering."""
        # Get filtered channels
        all_channels = self.channel_manager.get_all_channels()
        filtered_channels = self.channel_filter.filter_channels(all_channels)
        
        # Clear existing items
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
        
        # Add filtered channels to display
        for channel in filtered_channels:
            values = [
                channel.get('name', ''),
                os.path.basename(channel.get('csv_file', '')),
                channel.get('x_column', ''),
                channel.get('y_column', ''),
                channel.get('z_column', ''),
                channel.get('vehicle_x_channel', ''),
                channel.get('vehicle_y_channel', ''),
                channel.get('units', ''),
                channel.get('comment', '')
            ]
            self.channels_tree.insert("", "end", values=values)
        
        # Update column headers
        self.update_column_headers()
        
        # Log filter results
        status_message = self.channel_filter.get_filter_status(len(all_channels), len(filtered_channels))
        self.log_status(status_message)

    def update_column_headers(self):
        """Update column headers to show filter status."""
        columns = ["Name", "CSV File", "X Col", "Y Col", "Z Col", "Veh X", "Veh Y", "Units", "Comment"]
        
        for col in columns:
            header_text = self.channel_filter.get_column_header_text(col)
            self.channels_tree.heading(col, text=header_text)

    def on_search_change(self, *args):
        """Handle search text changes."""
        search_term = self.search_var.get()
        self.channel_filter.set_search_term(search_term)
        self.update_channels_display()

    def clear_search(self):
        """Clear search field and reapply filters."""
        self.search_var.set("")

    def clear_all_excel_filters(self):
        """Clear all Excel-like column filters."""
        self.channel_filter.clear_all_excel_filters()
        self.update_channels_display()

    def show_excel_filter(self, column_name):
        """Show Excel-like filter dialog for a specific column."""
        all_channels = self.channel_manager.get_all_channels()
        unique_values = self.channel_filter.get_unique_values_for_column(all_channels, column_name)
        
        if not unique_values:
            messagebox.showinfo("No Data", f"No data available for column '{column_name}' to filter.")
            return
        
        # Create filter dialog - simplified version for modular approach
        filter_dialog = ctk.CTkToplevel(self.root)
        filter_dialog.title(f'🔽 Filter: {column_name}')
        filter_dialog.geometry('450x600')
        filter_dialog.transient(self.root)
        filter_dialog.grab_set()
        
        # Center dialog
        x = (filter_dialog.winfo_screenwidth() // 2) - 225
        y = (filter_dialog.winfo_screenheight() // 2) - 300
        filter_dialog.geometry(f"450x600+{x}+{y}")
        
        main_frame = ctk.CTkScrollableFrame(filter_dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"🔽 Filter Column: {column_name}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(5, 15))
        
        # Filter type selection
        filter_type_var = ctk.StringVar(value="include")
        
        include_radio = ctk.CTkRadioButton(
            main_frame,
            text="✅ Include selected values",
            variable=filter_type_var,
            value="include"
        )
        include_radio.pack(anchor="w", pady=2)
        
        exclude_radio = ctk.CTkRadioButton(
            main_frame,
            text="❌ Exclude selected values",
            variable=filter_type_var,
            value="exclude"
        )
        exclude_radio.pack(anchor="w", pady=(2, 15))
        
        # Values selection
        ctk.CTkLabel(main_frame, text="Values:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 5))
        
        # Create checkboxes for each unique value
        value_vars = {}
        current_filter = self.channel_filter.excel_filters[column_name]
        
        for value in unique_values:
            var = ctk.BooleanVar()
            if not current_filter["selected_values"]:
                var.set(True)  # Select all by default
            else:
                var.set(value in current_filter["selected_values"])
            
            value_vars[value] = var
            
            checkbox = ctk.CTkCheckBox(
                main_frame,
                text=value,
                variable=var
            )
            checkbox.pack(anchor="w", padx=5, pady=2)
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=15)
        
        def apply_filter():
            selected_values = {value for value, var in value_vars.items() if var.get()}
            filter_type = filter_type_var.get()
            
            self.channel_filter.set_excel_filter(column_name, selected_values, filter_type)
            self.update_channels_display()
            filter_dialog.destroy()
        
        def clear_filter():
            self.channel_filter.clear_excel_filter(column_name)
            self.update_channels_display()
            filter_dialog.destroy()
        
        apply_btn = ctk.CTkButton(button_frame, text='✅ Apply', command=apply_filter, width=100)
        apply_btn.pack(side='left', padx=5)
        
        clear_btn = ctk.CTkButton(button_frame, text='🧹 Clear', command=clear_filter, width=100)
        clear_btn.pack(side='left', padx=5)
        
        cancel_btn = ctk.CTkButton(button_frame, text='❌ Cancel', command=filter_dialog.destroy, width=100)
        cancel_btn.pack(side='left', padx=5)

    def edit_selected_channel(self):
        """Edit the selected channel."""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to edit!")
            return
        
        item = selection[0]
        values = self.channels_tree.item(item)['values']
        channel_name = values[0]
        
        # Find the channel
        channel, channel_index = self.channel_manager.find_channel_by_name(channel_name)
        if channel is None:
            messagebox.showerror("Error", "Channel not found!")
            return
        
        # Populate form with channel data
        self.channel_name_var.set(channel['name'])
        self.csv_file_var.set(channel['csv_file'])
        self.x_col_var.set(channel['x_column'])
        self.y_col_var.set(channel['y_column'])
        self.z_col_var.set(channel['z_column'])
        self.veh_x_var.set(channel['vehicle_x_channel'])
        self.veh_y_var.set(channel['vehicle_y_channel'])
        self.units_var.set(channel['units'])
        self.comment_var.set(channel['comment'])
        
        # Load CSV columns if file exists
        if os.path.exists(channel['csv_file']):
            try:
                columns = self.file_manager.load_csv_columns(channel['csv_file'])
                self.x_col_combo.set_completion_list(columns)
                self.y_col_combo.set_completion_list(columns)
                self.z_col_combo.set_completion_list(columns)
            except Exception:
                pass
        
        # Switch to Custom Channels tab
        self.tabview.set("⚙️ Custom Channels")
        
        # Delete the original and let user re-add as edited
        self.channel_manager.delete_channel(channel_index)
        self.update_channels_display()
        
        self.log_status(f"✏️ Editing channel: {channel_name}")

    def delete_selected_channel(self):
        """Delete the selected channel."""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to delete!")
            return
        
        item = selection[0]
        values = self.channels_tree.item(item)['values']
        channel_name = values[0]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete channel '{channel_name}'?"):
            success, error_msg = self.channel_manager.delete_channel_by_name(channel_name)
            if success:
                self.update_channels_display()
                self.save_settings()
            else:
                messagebox.showerror("Error", error_msg)

    def duplicate_selected_channel(self):
        """Duplicate the selected channel."""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to duplicate!")
            return
        
        item = selection[0]
        values = self.channels_tree.item(item)['values']
        channel_name = values[0]
        
        channel, channel_index = self.channel_manager.find_channel_by_name(channel_name)
        if channel is not None:
            success, error_msg = self.channel_manager.duplicate_channel(channel_index)
            if success:
                self.update_channels_display()
                self.save_settings()
            else:
                messagebox.showerror("Error", error_msg)

    def clear_all_channels(self):
        """Clear all custom channels after confirmation."""
        channel_count = self.channel_manager.get_channel_count()
        if channel_count == 0:
            return
        
        result = messagebox.askyesno(
            "Confirm Clear",
            f"Are you sure you want to clear all {channel_count} custom channels?"
        )
        
        if result:
            self.channel_manager.clear_all_channels()
            self.update_channels_display()
            self.save_settings()

    def export_channel_config(self):
        """Export channel configuration to JSON."""
        channels = self.channel_manager.get_all_channels()
        if not channels:
            messagebox.showwarning("Warning", "No channels to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Channel Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            success = self.config_manager.export_channel_config(channels, file_path)
            if success:
                messagebox.showinfo("Export Complete", f"Configuration exported successfully to:\n{os.path.basename(file_path)}")

    def import_channel_config(self):
        """Import channel configuration from JSON."""
        file_path = filedialog.askopenfilename(
            title="Import Channel Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            config = self.config_manager.import_channel_config(file_path)
            if config is None:
                return
            
            imported_channels = config['channels']
            current_channels = self.channel_manager.get_all_channels()
            
            # Ask user about merge strategy
            num_channels = len(imported_channels)
            total_current = len(current_channels)
            
            if total_current > 0:
                choice = messagebox.askyesnocancel(
                    "Import Channels",
                    f"Import {num_channels} channels?\n\n"
                    f"Yes: Add to existing {total_current} channels\n"
                    f"No: Replace all existing channels\n"
                    f"Cancel: Don't import"
                )
                
                if choice is None:  # Cancel
                    return
                elif choice:  # Yes - add
                    mode = "add"
                else:  # No - replace
                    mode = "replace"
            else:
                mode = "add"
            
            # Merge configurations
            merged_channels, conflicts = self.config_manager.merge_channel_configs(
                current_channels, imported_channels, mode
            )
            
            # Update channel manager
            self.channel_manager.set_all_channels(merged_channels)
            self.update_channels_display()
            self.save_settings()
            
            # Show results
            result_msg = f"✅ Successfully imported {len(imported_channels)} channel(s)"
            if conflicts:
                result_msg += f"\n\nRenamed due to conflicts:\n" + "\n".join(conflicts)
            
            messagebox.showinfo("Import Complete", result_msg)

    # Settings Management
    def save_settings(self):
        """Auto-save current settings."""
        app_state = self.get_current_app_state()
        self.settings_manager.save_settings(app_state)

    def get_current_app_state(self):
        """Get current application state for settings."""
        return {
            'vehicle_file_path': self.vehicle_file_path,
            'custom_channels': self.channel_manager.get_all_channels(),
            'output_format': self.output_format_var.get(),
            'theme': self.theme_menu.get(),
            'form_settings': {
                'channel_name': self.channel_name_var.get(),
                'csv_file': self.csv_file_var.get(),
                'x_column': self.x_col_var.get(),
                'y_column': self.y_col_var.get(),
                'z_column': self.z_col_var.get(),
                'vehicle_x_channel': self.veh_x_var.get(),
                'vehicle_y_channel': self.veh_y_var.get(),
                'units': self.units_var.get(),
                'comment': self.comment_var.get(),
                'preserve_settings': self.preserve_settings_var.get()
            }
        }

    def load_settings_on_startup(self):
        """Load settings from default file on startup."""
        settings = self.settings_manager.load_settings_on_startup()
        if settings:
            self.restore_settings(settings)

    def save_settings_as(self):
        """Save settings to a new file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        num_channels = self.channel_manager.get_channel_count()
        vehicle_name = "NoVehicle"
        if self.vehicle_file_path:
            vehicle_name = Path(self.vehicle_file_path).stem
        
        default_name = f"settings_{vehicle_name}_{num_channels}channels_{timestamp}.json"
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Settings As",
            initialvalue=default_name
        )
        
        if file_path:
            app_state = self.get_current_app_state()
            success = self.settings_manager.save_settings_as(app_state, file_path)
            if success:
                messagebox.showinfo("Settings Saved", f"Settings saved successfully to:\n{os.path.basename(file_path)}")

    def load_settings_from(self):
        """Load settings from a file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Settings From"
        )
        
        if file_path:
            settings = self.settings_manager.load_settings_from(file_path)
            if settings:
                # Show preview
                num_channels = len(settings.get('custom_channels', []))
                vehicle_file = settings.get('vehicle_file', 'None')
                description = settings.get('description', 'No description available')
                
                preview_msg = (f"Settings Preview:\n"
                             f"• Custom Channels: {num_channels}\n"
                             f"• Vehicle File: {os.path.basename(vehicle_file) if vehicle_file else 'None'}\n"
                             f"• Description: {description}\n\n"
                             f"Load these settings?")
                
                if messagebox.askyesno("Load Settings", preview_msg):
                    self.restore_settings(settings)
                    messagebox.showinfo("Settings Loaded", f"Settings loaded successfully!\n{num_channels} custom channels restored.")

    def quick_save_settings(self, slot):
        """Quick save settings to a numbered slot."""
        app_state = self.get_current_app_state()
        self.settings_manager.quick_save_settings(app_state, slot)

    def quick_load_settings(self, slot):
        """Quick load settings from a numbered slot."""
        settings = self.settings_manager.quick_load_settings(slot)
        if settings:
            self.restore_settings(settings)

    def update_slot_name(self, slot, event):
        """Update slot name when entry is modified."""
        new_name = self.slot_name_entries[slot].get()
        self.settings_manager.update_slot_name(slot, new_name)

    def rename_slot_dialog(self, slot):
        """Open dialog to rename a slot."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Rename Slot {slot}")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create layout
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        label = ctk.CTkLabel(main_frame, text=f"Enter new name for Slot {slot}:")
        label.pack(pady=(0, 10))
        
        name_var = ctk.StringVar(value=self.settings_manager.get_slot_name(slot))
        entry = ctk.CTkEntry(main_frame, textvariable=name_var, width=200)
        entry.pack(pady=(0, 15))
        entry.focus()
        entry.select_range(0, 'end')
        
        def confirm():
            new_name = name_var.get().strip()
            if new_name:
                self.settings_manager.update_slot_name(slot, new_name)
                self.slot_name_entries[slot].delete(0, 'end')
                self.slot_name_entries[slot].insert(0, new_name)
            dialog.destroy()
        
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack()
        
        ok_btn = ctk.CTkButton(button_frame, text="OK", command=confirm, width=60)
        ok_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy, width=60)
        cancel_btn.pack(side="left", padx=5)
        
        entry.bind('<Return>', lambda e: confirm())

    def restore_settings(self, settings):
        """Restore settings from dictionary."""
        try:
            # Restore custom channels
            if 'custom_channels' in settings:
                self.channel_manager.set_all_channels(settings['custom_channels'])
                self.update_channels_display()
            
            # Restore output format
            if 'output_format' in settings:
                self.output_format_var.set(settings['output_format'])
            
            # Restore theme
            if 'theme' in settings:
                self.theme_menu.set(settings['theme'])
                self.change_theme(settings['theme'])
            
            # Restore form settings
            if 'form_settings' in settings:
                form = settings['form_settings']
                self.channel_name_var.set(form.get('channel_name', ''))
                self.csv_file_var.set(form.get('csv_file', ''))
                self.x_col_var.set(form.get('x_column', ''))
                self.y_col_var.set(form.get('y_column', ''))
                self.z_col_var.set(form.get('z_column', ''))
                self.veh_x_var.set(form.get('vehicle_x_channel', ''))
                self.veh_y_var.set(form.get('vehicle_y_channel', ''))
                self.units_var.set(form.get('units', ''))
                self.comment_var.set(form.get('comment', ''))
                self.preserve_settings_var.set(form.get('preserve_settings', True))
                
                # Load CSV columns if file exists
                csv_file = form.get('csv_file', '')
                if csv_file and os.path.exists(csv_file):
                    try:
                        columns = self.file_manager.load_csv_columns(csv_file)
                        self.x_col_combo.set_completion_list(columns)
                        self.y_col_combo.set_completion_list(columns)
                        self.z_col_combo.set_completion_list(columns)
                    except Exception:
                        pass
            
            # Restore vehicle file if it exists
            if 'vehicle_file' in settings and settings['vehicle_file']:
                if os.path.exists(settings['vehicle_file']):
                    self.vehicle_file_path = settings['vehicle_file']
                    filename = os.path.basename(self.vehicle_file_path)
                    self.file_status_label.configure(text=f"📁 {filename}")
                    try:
                        self.vehicle_data, self.available_channels = self.file_manager.load_vehicle_file(self.vehicle_file_path)
                        self.veh_x_combo.set_completion_list(self.available_channels)
                        self.veh_y_combo.set_completion_list(self.available_channels)
                    except Exception as e:
                        self.log_status(f"⚠️ Could not reload vehicle file: {str(e)}")
                        
        except Exception as e:
            self.log_status(f"❌ Error restoring settings: {str(e)}")

    # Processing
    def process_all_channels(self):
        """Process all configured custom channels."""
        if not self.vehicle_data:
            messagebox.showerror("Error", "Please select a vehicle file first!")
            return
        
        channels = self.channel_manager.get_all_channels()
        if not channels:
            messagebox.showerror("Error", "Please configure at least one custom channel!")
            return
        
        # For MDF files, ask for raster once
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        raster = None
        if file_ext in ['.mdf', '.mf4', '.dat']:
            raster = self.ask_for_raster()
            if raster is None:
                self.log_status("⚠️ Processing cancelled by user.")
                return
        
        try:
            self.log_status("🚀 Starting processing of all custom channels...")
            
            # Process each custom channel
            calculated_signals = []
            csv_export_data = None
            
            for i, channel_config in enumerate(channels):
                self.log_status(f"⚙️ Processing channel {i+1}/{len(channels)}: {channel_config['name']}")
                
                # Load surface table
                try:
                    x_values, y_values, z_matrix = self.data_processor.load_surface_table(
                        channel_config['csv_file'],
                        channel_config['x_column'],
                        channel_config['y_column'], 
                        channel_config['z_column']
                    )
                except Exception as e:
                    self.log_status(f"❌ Error loading surface table for {channel_config['name']}: {str(e)}")
                    continue
                
                # Extract vehicle data
                try:
                    if file_ext == '.csv':
                        x_data = pd.to_numeric(self.vehicle_data[channel_config['vehicle_x_channel']], errors='coerce')
                        y_data = pd.to_numeric(self.vehicle_data[channel_config['vehicle_y_channel']], errors='coerce')
                        timestamps = np.arange(len(x_data), dtype=np.float64) * (raster or 0.01)
                    else:  # MDF files
                        x_data, x_timestamps = self.channel_analyzer.get_interpolated_signal_data(
                            self.vehicle_data, self.vehicle_file_path, channel_config['vehicle_x_channel'], raster)
                        y_data, y_timestamps = self.channel_analyzer.get_interpolated_signal_data(
                            self.vehicle_data, self.vehicle_file_path, channel_config['vehicle_y_channel'], raster)
                        
                        # Align timestamps
                        min_length = min(len(x_data), len(y_data))
                        x_data = x_data[:min_length]
                        y_data = y_data[:min_length]
                        timestamps = x_timestamps[:min_length]
                    
                    self.log_status(f"✅ Vehicle data extracted for {channel_config['name']}: {len(x_data)} samples")
                except Exception as e:
                    self.log_status(f"❌ Error extracting vehicle data for {channel_config['name']}: {str(e)}")
                    continue
                
                # Interpolate values
                try:
                    z_interpolated = []
                    valid_points = 0
                    
                    for x_val, y_val in zip(x_data, y_data):
                        if pd.notna(x_val) and pd.notna(y_val):
                            z_val = self.data_processor.interpolate_z_value(x_val, y_val, x_values, y_values, z_matrix)
                            z_interpolated.append(z_val)
                            if not np.isnan(z_val):
                                valid_points += 1
                        else:
                            z_interpolated.append(np.nan)
                    
                    self.log_status(f"✅ Interpolated {valid_points}/{len(z_interpolated)} valid points for {channel_config['name']}")
                    
                    # Create signal for MDF output
                    if self.output_format_var.get() == "mf4" and file_ext != '.csv':
                        signal = self.output_generator.create_calculated_signal(
                            channel_config, z_interpolated, timestamps)
                        calculated_signals.append(signal)
                    
                    # Store for CSV output
                    if file_ext == '.csv' or self.output_format_var.get() == "csv":
                        if file_ext == '.csv':
                            # Add to existing dataframe
                            self.vehicle_data[channel_config['name']] = z_interpolated
                        else:
                            # Create CSV export data
                            if csv_export_data is None:
                                csv_export_data = self.output_generator.prepare_csv_export_data(
                                    timestamps, {channel_config['name']: z_interpolated})
                            else:
                                csv_export_data[channel_config['name']] = z_interpolated
                            
                except Exception as e:
                    self.log_status(f"❌ Error interpolating {channel_config['name']}: {str(e)}")
                    continue
            
            # Save output
            self.file_manager.save_output(
                calculated_signals, 
                self.vehicle_file_path, 
                self.output_format_var.get(),
                vehicle_data=self.vehicle_data if file_ext == '.csv' else None,
                csv_export_data=csv_export_data
            )
            
            messagebox.showinfo("Success", f"Processing completed successfully!\nCreated {len(calculated_signals)} calculated channels.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
            self.log_status(f"❌ Processing error: {str(e)}")

    def ask_for_raster(self):
        """Ask user for raster value with channel analysis."""
        # Create simplified raster dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title('🎯 Set Time Raster')
        dialog.geometry('600x400')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        x = (dialog.winfo_screenwidth() // 2) - 300
        y = (dialog.winfo_screenheight() // 2) - 200
        dialog.geometry(f"600x400+{x}+{y}")
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text="🎯 Set Time Raster for Processing",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Analyze channels
        all_channels = self.channel_manager.get_all_channels()
        analysis = self.channel_analyzer.analyze_channel_sampling_rates(
            self.vehicle_data, all_channels, self.vehicle_file_path)
        
        # Calculate recommended raster
        overall_min_raster = 0.001
        if analysis:
            min_rasters = [a.get('suggested_min_raster', 0.001) 
                          for a in analysis.values() 
                          if 'suggested_min_raster' in a]
            if min_rasters:
                overall_min_raster = max(min_rasters)
        
        info_text = ctk.CTkLabel(
            main_frame,
            text=f"Recommended minimum raster: {overall_min_raster:.6f} seconds\n\n"
                 "Enter raster value in seconds:",
            font=ctk.CTkFont(size=12)
        )
        info_text.pack(pady=(0, 15))
        
        raster_var = ctk.StringVar(value=str(overall_min_raster))
        raster_entry = ctk.CTkEntry(main_frame, textvariable=raster_var, width=200)
        raster_entry.pack(pady=(0, 20))
        raster_entry.focus()
        
        result = [None]
        
        def confirm_raster():
            try:
                raster_value = float(raster_var.get())
                if raster_value <= 0:
                    messagebox.showerror('Error', 'Raster value must be positive!')
                    return
                result[0] = raster_value
                dialog.destroy()
            except ValueError:
                messagebox.showerror('Error', 'Please enter a valid number!')
        
        def cancel_raster():
            dialog.destroy()
        
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack()
        
        ok_btn = ctk.CTkButton(button_frame, text='✅ OK', command=confirm_raster, width=100)
        ok_btn.pack(side='left', padx=10)
        
        cancel_btn = ctk.CTkButton(button_frame, text='❌ Cancel', command=cancel_raster, width=100)
        cancel_btn.pack(side='left', padx=10)
        
        raster_entry.bind('<Return>', lambda e: confirm_raster())
        dialog.wait_window()
        return result[0]

    # Status log management
    def clear_status_log(self):
        """Clear the status log."""
        self.status_text.delete("1.0", "end")
        self.log_status("🧹 Status log cleared.")

    def on_closing(self):
        """Handle application closing with save options."""
        num_channels = self.channel_manager.get_channel_count()
        
        if num_channels > 0:
            # Ask if user wants to save
            result = messagebox.askyesnocancel(
                "Save Before Exit?",
                f"You have {num_channels} custom channel(s) configured.\n\n"
                "Save settings before exiting?\n\n"
                "• Yes: Auto-save to default file\n"
                "• No: Exit without saving\n"
                "• Cancel: Stay in application"
            )
            
            if result is True:  # Yes - save
                self.save_settings()
                self.log_status("✅ Auto-saved settings before exit")
                self.root.destroy()
            elif result is False:  # No - don't save
                self.root.destroy()
            # Cancel - do nothing (stay open)
        else:
            # No channels, simple exit
            if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
                self.root.destroy()
    
    def run(self):
        """Start the application."""
        self.root.mainloop()


def main():
    """Main function to run the application."""
    try:
        app = VehicleLogChannelAppenderModular()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {e}")
        input("Press Enter to continue...")


if __name__ == "__main__":
    main()