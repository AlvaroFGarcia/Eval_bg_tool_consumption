"""
Vehicle Log Channel Appender - Modular Version
Complete implementation with ALL features from the modern version

Enhanced Version with Advanced Raster Analysis and Interpolation

Key Features:
- Modern, dark/light theme UI with CustomTkinter
- Complete CSV surface table interpolation functionality
- All original features preserved and enhanced
- Auto-load last configuration on startup
- Advanced search and filtering
- Quick save/load slots
- Proper raster analysis during processing only
"""

import numpy as np
import pandas as pd
from asammdf import MDF, Signal
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import os
from scipy.interpolate import griddata, interp1d
import tempfile
import shutil
from pathlib import Path
import json
from datetime import datetime
import threading
from typing import List, Dict, Optional

# Import modular components
from ui_components import ModernAutocompleteCombobox, ModernProgressDialog, AdvancedRasterDialog, ExcelFilterDialog
from channel_management import ChannelManager, ChannelValidator
from settings_management import SettingsManager, ConfigurationManager
from filtering_system import ChannelFilter, TextFilterHelper
from data_processing import DataProcessor, ChannelAnalyzer
from file_management import FileManager, OutputGenerator

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark")  # Default to dark mode
ctk.set_default_color_theme("blue")  # Professional blue theme


class VehicleLogChannelAppenderModular:
    """
    Main application class that integrates all modular components
    to provide the complete functionality of the modern version.
    """
    
    def __init__(self):
        # Initialize main window
        self.root = ctk.CTk()
        self.setup_window_properties()
        
        # Initialize modular components
        self.channel_manager = ChannelManager(logger=self)
        self.channel_validator = ChannelValidator(logger=self)
        self.settings_manager = SettingsManager(logger=self)
        self.config_manager = ConfigurationManager(logger=self)
        self.channel_filter = ChannelFilter(logger=self)
        self.data_processor = DataProcessor(logger=self)
        self.channel_analyzer = ChannelAnalyzer(logger=self)
        self.file_manager = FileManager(logger=self)
        self.output_generator = OutputGenerator(logger=self)
        
        # Initialize application state
        self.vehicle_data = None
        self.vehicle_file_path = None
        self.available_channels = []
        self.status_log = []
        
        # Initialize UI variables
        self.channel_name_var = ctk.StringVar()
        self.csv_file_var = ctk.StringVar()
        self.x_col_var = ctk.StringVar()
        self.y_col_var = ctk.StringVar()
        self.z_col_var = ctk.StringVar()
        self.veh_x_var = ctk.StringVar()
        self.veh_y_var = ctk.StringVar()
        self.units_var = ctk.StringVar()
        self.comment_var = ctk.StringVar()
        self.search_var = ctk.StringVar()
        
        # Quick save slot variables
        self.slot_1_name_var = ctk.StringVar(value="Slot 1")
        self.slot_2_name_var = ctk.StringVar(value="Slot 2")
        
        # Initialize UI
        self.setup_ui()
        self.setup_bindings()
        
        # Load settings on startup
        self.load_settings_on_startup()
        
    def setup_window_properties(self):
        """Configure main window properties."""
        self.root.title("🚗 Vehicle Log Channel Appender - Modular Version")
        self.root.geometry("1200x700")
        self.root.minsize(1200, 700)
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - 600
        y = (self.root.winfo_screenheight() // 2) - 350
        self.root.geometry(f"1200x700+{x}+{y}")
        
        # Configure grid weights for responsiveness
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Set window icon (if available)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Setup the complete user interface."""
        # Create main layout with sidebar
        self.setup_sidebar()
        self.setup_main_content()
    
    def setup_sidebar(self):
        """Setup the sidebar with navigation."""
        # Sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self.root, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.sidebar_frame.grid_propagate(False)  # Prevent frame from shrinking
        
        # App title
        title_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="🚗 Vehicle Log\nChannel Appender",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("gray10", "gray90")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Version label
        version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Modular Version",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        version_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Theme selection
        theme_frame = ctk.CTkFrame(self.sidebar_frame)
        theme_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        theme_label = ctk.CTkLabel(
            theme_frame,
            text="🎨 Theme:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        theme_label.pack(padx=10, pady=5)
        
        self.theme_var = ctk.StringVar(value="dark")
        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["dark", "light"],
            variable=self.theme_var,
            command=self.change_theme
        )
        theme_menu.pack(padx=10, pady=5)
        
        # Vehicle file section
        vehicle_frame = ctk.CTkFrame(self.sidebar_frame)
        vehicle_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        vehicle_label = ctk.CTkLabel(
            vehicle_frame,
            text="📁 Vehicle File:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        vehicle_label.pack(padx=10, pady=(10, 5))
        
        select_vehicle_btn = ctk.CTkButton(
            vehicle_frame,
            text="🔍 Select Vehicle File",
            command=self.select_vehicle_file,
            width=200
        )
        select_vehicle_btn.pack(padx=10, pady=5)
        
        self.vehicle_status_label = ctk.CTkLabel(
            vehicle_frame,
            text="No file selected",
            font=ctk.CTkFont(size=10),
            text_color=("gray40", "gray60")
        )
        self.vehicle_status_label.pack(padx=10, pady=(5, 10))
        
        # Quick save/load section
        quick_frame = ctk.CTkFrame(self.sidebar_frame)
        quick_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        quick_label = ctk.CTkLabel(
            quick_frame,
            text="⚡ Quick Save/Load:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        quick_label.pack(padx=10, pady=(10, 5))
        
        # Quick save slot 1
        slot1_frame = ctk.CTkFrame(quick_frame)
        slot1_frame.pack(fill="x", padx=10, pady=2)
        
        self.slot_1_label = ctk.CTkLabel(
            slot1_frame,
            textvariable=self.slot_1_name_var,
            font=ctk.CTkFont(size=10)
        )
        self.slot_1_label.pack(side="left", padx=5, pady=2)
        
        slot1_save_btn = ctk.CTkButton(
            slot1_frame,
            text="💾",
            command=lambda: self.quick_save_settings(1),
            width=30,
            height=25
        )
        slot1_save_btn.pack(side="right", padx=2, pady=2)
        
        slot1_load_btn = ctk.CTkButton(
            slot1_frame,
            text="📂",
            command=lambda: self.quick_load_settings(1),
            width=30,
            height=25
        )
        slot1_load_btn.pack(side="right", padx=2, pady=2)
        
        # Quick save slot 2
        slot2_frame = ctk.CTkFrame(quick_frame)
        slot2_frame.pack(fill="x", padx=10, pady=2)
        
        self.slot_2_label = ctk.CTkLabel(
            slot2_frame,
            textvariable=self.slot_2_name_var,
            font=ctk.CTkFont(size=10)
        )
        self.slot_2_label.pack(side="left", padx=5, pady=2)
        
        slot2_save_btn = ctk.CTkButton(
            slot2_frame,
            text="💾",
            command=lambda: self.quick_save_settings(2),
            width=30,
            height=25
        )
        slot2_save_btn.pack(side="right", padx=2, pady=2)
        
        slot2_load_btn = ctk.CTkButton(
            slot2_frame,
            text="📂",
            command=lambda: self.quick_load_settings(2),
            width=30,
            height=25
        )
        slot2_load_btn.pack(side="right", padx=2, pady=2)
        
        # Bind slot label events for renaming
        self.slot_1_label.bind("<Double-Button-1>", lambda e: self.rename_slot_dialog(1))
        self.slot_2_label.bind("<Double-Button-1>", lambda e: self.rename_slot_dialog(2))
        
        # Settings section
        settings_frame = ctk.CTkFrame(self.sidebar_frame)
        settings_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        settings_label = ctk.CTkLabel(
            settings_frame,
            text="⚙️ Settings:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        settings_label.pack(padx=10, pady=(10, 5))
        
        save_settings_btn = ctk.CTkButton(
            settings_frame,
            text="💾 Save Settings",
            command=self.save_settings,
            width=200
        )
        save_settings_btn.pack(padx=10, pady=2)
        
        save_as_settings_btn = ctk.CTkButton(
            settings_frame,
            text="📁 Save As...",
            command=self.save_settings_as,
            width=200
        )
        save_as_settings_btn.pack(padx=10, pady=2)
        
        load_settings_btn = ctk.CTkButton(
            settings_frame,
            text="📂 Load Settings",
            command=self.load_settings_from,
            width=200
        )
        load_settings_btn.pack(padx=10, pady=(2, 10))
        
    def setup_main_content(self):
        """Setup main content area with tabview."""
        # Main content frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Create tabs
        self.tabview.add("🔧 Processing")
        self.tabview.add("📋 Custom Channels") 
        self.tabview.add("📊 Status Log")
        
        # Setup tab content
        self.setup_processing_tab()
        self.setup_custom_channels_tab()
        self.setup_status_log_tab()
        
    def setup_processing_tab(self):
        """Setup the processing tab."""
        processing_tab = self.tabview.tab("🔧 Processing")
        processing_tab.grid_columnconfigure(0, weight=1)
        processing_tab.grid_rowconfigure(1, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(processing_tab)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        header_label = ctk.CTkLabel(
            header_frame,
            text="🔧 Process Vehicle Log Channels",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header_label.pack(pady=15)
        
        # Main processing frame
        process_frame = ctk.CTkFrame(processing_tab)
        process_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        process_frame.grid_columnconfigure(0, weight=1)
        process_frame.grid_rowconfigure(0, weight=1)
        
        # Instructions
        instructions_text = """
🚀 Process All Configured Channels

This will:
• Analyze sampling rates of vehicle channels
• Load surface tables from CSV files  
• Interpolate values for each timestamp
• Generate calculated channels
• Save output in the same format as input

⚠️  Make sure you have:
• Loaded a vehicle file (MDF or CSV)
• Added at least one custom channel
• Verified all channel configurations
        """.strip()
        
        instructions_label = ctk.CTkLabel(
            process_frame,
            text=instructions_text,
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        instructions_label.pack(pady=20)
        
        # Process button
        self.process_btn = ctk.CTkButton(
            process_frame,
            text="🚀 Process All Channels",
            command=self.process_all_channels,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=300
        )
        self.process_btn.pack(pady=20)
        
        # Status frame
        status_frame = ctk.CTkFrame(process_frame)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        self.process_status_label = ctk.CTkLabel(
            status_frame,
            text="Ready to process",
            font=ctk.CTkFont(size=12)
        )
        self.process_status_label.pack(pady=10)
        
    def setup_custom_channels_tab(self):
        """Setup the custom channels tab."""
        channels_tab = self.tabview.tab("📋 Custom Channels")
        channels_tab.grid_columnconfigure(0, weight=1)
        channels_tab.grid_rowconfigure(1, weight=1)
        
        # Setup channel form
        self.setup_complete_channel_form(channels_tab)
        
        # Setup channels table
        self.setup_complete_channels_table(channels_tab)
        
    def setup_complete_channel_form(self, parent):
        """Setup the complete channel configuration form."""
        # Header
        header_frame = ctk.CTkFrame(parent)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        header_label = ctk.CTkLabel(
            header_frame,
            text="📋 Configure Custom Channels",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header_label.pack(pady=15)
        
        # Main form container in scrollable frame
        self.form_scroll = ctk.CTkScrollableFrame(parent, height=300)
        self.form_scroll.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.form_scroll.grid_columnconfigure(0, weight=1)
        
        # Channel form
        form_frame = ctk.CTkFrame(self.form_scroll)
        form_frame.pack(fill="x", padx=10, pady=10)
        
        # Channel name
        name_frame = ctk.CTkFrame(form_frame)
        name_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(name_frame, text="📝 Channel Name:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=10)
        self.channel_name_entry = ctk.CTkEntry(name_frame, textvariable=self.channel_name_var, 
                                              placeholder_text="Enter channel name", width=250)
        self.channel_name_entry.pack(side="left", padx=10, pady=10)
        
        # CSV Surface Table file
        csv_frame = ctk.CTkFrame(form_frame)
        csv_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(csv_frame, text="📊 Surface Table CSV:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=10)
        self.csv_file_entry = ctk.CTkEntry(csv_frame, textvariable=self.csv_file_var, 
                                          placeholder_text="Select CSV file", width=200)
        self.csv_file_entry.pack(side="left", padx=10, pady=10)
        
        browse_csv_btn = ctk.CTkButton(csv_frame, text="📁 Browse", 
                                      command=self.browse_csv_file, width=80)
        browse_csv_btn.pack(side="left", padx=5, pady=10)
        
        # CSV columns configuration
        csv_config_frame = ctk.CTkFrame(form_frame)
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
        
        # Vehicle channels configuration
        veh_config_frame = ctk.CTkFrame(form_frame)
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
        
        # Units and comment
        meta_frame = ctk.CTkFrame(form_frame)
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
        
        # Form buttons
        button_frame = ctk.CTkFrame(self.form_scroll)
        button_frame.pack(pady=15)
        
        add_btn = ctk.CTkButton(
            button_frame,
            text='➕ Add Channel',
            command=self.add_custom_channel,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            height=35
        )
        add_btn.pack(side='left', padx=5)
        
        clear_btn = ctk.CTkButton(
            button_frame,
            text='🗑️ Clear Form',
            command=self.clear_channel_form,
            width=120,
            height=35
        )
        clear_btn.pack(side='left', padx=5)
        
    def setup_complete_channels_table(self, parent):
        """Setup the complete channels table with search and filters."""
        # Table container frame
        table_container = ctk.CTkFrame(parent)
        table_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        table_container.grid_columnconfigure(0, weight=1)
        table_container.grid_rowconfigure(2, weight=1)
        
        # Search and filter header
        search_frame = ctk.CTkFrame(table_container)
        search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        search_frame.grid_columnconfigure(1, weight=1)
        
        # Search
        ctk.CTkLabel(search_frame, text="🔍 Search:", 
                    font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, 
                                        placeholder_text="Search channels...", width=200)
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        clear_search_btn = ctk.CTkButton(search_frame, text="❌ Clear", 
                                        command=self.clear_search, width=70)
        clear_search_btn.grid(row=0, column=2, padx=5, pady=10)
        
        # Filters button
        filters_btn = ctk.CTkButton(search_frame, text="🔧 Advanced Filters", 
                                   command=self.setup_filters, width=140)
        filters_btn.grid(row=0, column=3, padx=5, pady=10)
        
        # Table info frame
        info_frame = ctk.CTkFrame(table_container)
        info_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.table_info_label = ctk.CTkLabel(
            info_frame,
            text="No channels configured",
            font=ctk.CTkFont(size=12)
        )
        self.table_info_label.pack(pady=5)
        
        # Channels table frame
        self.table_frame = ctk.CTkScrollableFrame(table_container)
        self.table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Create treeview for channels
        columns = ('name', 'csv_file', 'x_column', 'y_column', 'z_column', 
                  'vehicle_x_channel', 'vehicle_y_channel', 'units', 'comment')
        
        self.channels_tree = tk.ttk.Treeview(self.table_frame, columns=columns, show='headings', height=8)
        
        # Configure column headers
        self.channels_tree.heading('name', text='📝 Channel Name')
        self.channels_tree.heading('csv_file', text='📊 CSV File')
        self.channels_tree.heading('x_column', text='📊 X Column')
        self.channels_tree.heading('y_column', text='📈 Y Column')
        self.channels_tree.heading('z_column', text='📋 Z Column')
        self.channels_tree.heading('vehicle_x_channel', text='🔧 Vehicle X')
        self.channels_tree.heading('vehicle_y_channel', text='📊 Vehicle Y')
        self.channels_tree.heading('units', text='📏 Units')
        self.channels_tree.heading('comment', text='💬 Comment')
        
        # Configure column widths
        self.channels_tree.column('name', width=150, minwidth=100)
        self.channels_tree.column('csv_file', width=200, minwidth=150)
        self.channels_tree.column('x_column', width=100, minwidth=80)
        self.channels_tree.column('y_column', width=100, minwidth=80)
        self.channels_tree.column('z_column', width=100, minwidth=80)
        self.channels_tree.column('vehicle_x_channel', width=120, minwidth=100)
        self.channels_tree.column('vehicle_y_channel', width=120, minwidth=100)
        self.channels_tree.column('units', width=80, minwidth=60)
        self.channels_tree.column('comment', width=150, minwidth=100)
        
        # Add scrollbar
        scrollbar = tk.ttk.Scrollbar(self.table_frame, orient="vertical", command=self.channels_tree.yview)
        self.channels_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.channels_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind column header clicks for Excel-style filtering
        for col in columns:
            self.channels_tree.heading(col, command=lambda c=col: self.show_excel_filter(c))
        
        # Table control buttons
        control_frame = ctk.CTkFrame(table_container)
        control_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        edit_btn = ctk.CTkButton(
            control_frame,
            text='✏️ Edit Selected',
            command=self.edit_selected_channel,
            width=120,
            height=35
        )
        edit_btn.pack(side='left', padx=5, pady=10)
        
        duplicate_btn = ctk.CTkButton(
            control_frame,
            text='📋 Duplicate',
            command=self.duplicate_selected_channel,
            width=120,
            height=35
        )
        duplicate_btn.pack(side='left', padx=5, pady=10)
        
        delete_btn = ctk.CTkButton(
            control_frame,
            text='🗑️ Delete Selected',
            command=self.delete_selected_channel,
            width=120,
            height=35
        )
        delete_btn.pack(side='left', padx=5, pady=10)
        
        clear_all_btn = ctk.CTkButton(
            control_frame,
            text='❌ Clear All',
            command=self.clear_all_channels,
            width=120,
            height=35
        )
        clear_all_btn.pack(side='left', padx=5, pady=10)
        
        # Export/Import buttons
        export_btn = ctk.CTkButton(
            control_frame,
            text='📤 Export Config',
            command=self.export_channel_config,
            width=120,
            height=35
        )
        export_btn.pack(side='right', padx=5, pady=10)
        
        import_btn = ctk.CTkButton(
            control_frame,
            text='📥 Import Config',
            command=self.import_channel_config,
            width=120,
            height=35
        )
        import_btn.pack(side='right', padx=5, pady=10)
        
    def setup_status_log_tab(self):
        """Setup the status log tab."""
        log_tab = self.tabview.tab("📊 Status Log")
        log_tab.grid_columnconfigure(0, weight=1)
        log_tab.grid_rowconfigure(1, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(log_tab)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        header_label = ctk.CTkLabel(
            header_frame,
            text="📊 Status Log",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header_label.pack(side="left", padx=20, pady=15)
        
        clear_log_btn = ctk.CTkButton(
            header_frame,
            text="🗑️ Clear Log",
            command=self.clear_status_log,
            width=100
        )
        clear_log_btn.pack(side="right", padx=20, pady=15)
        
        # Log display
        self.log_display = ctk.CTkTextbox(log_tab)
        self.log_display.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        
        # Initial log message
        self.log_status("🚀 Vehicle Log Channel Appender - Modular Version started")
        self.log_status("💡 Load a vehicle file and configure channels to begin")
        
    def setup_bindings(self):
        """Setup event bindings."""
        # Search functionality
        self.search_var.trace_add('write', self.on_search_change)
        
        # Double-click on table for editing
        self.channels_tree.bind('<Double-1>', lambda e: self.edit_selected_channel())
        
    # Core functionality methods
    def change_theme(self, theme):
        """Change the application theme."""
        ctk.set_appearance_mode(theme)
        self.log_status(f"🎨 Theme changed to: {theme}")
        
    def select_vehicle_file(self):
        """Select vehicle file (MDF or CSV)."""
        file_path = filedialog.askopenfilename(
            title="Select Vehicle Log File",
            filetypes=[
                ("All Supported", "*.mdf;*.dat;*.csv"),
                ("MDF Files", "*.mdf"),
                ("DAT Files", "*.dat"), 
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.vehicle_file_path = file_path
            self.load_vehicle_file()
            
    def load_vehicle_file(self):
        """Load the selected vehicle file."""
        if not self.vehicle_file_path:
            return
            
        try:
            # Use file manager to load the file
            result = self.file_manager.load_vehicle_file(self.vehicle_file_path)
            
            if result:
                self.vehicle_data = result
                self.available_channels = list(result.keys()) if hasattr(result, 'keys') else []
                
                # Update vehicle status
                filename = os.path.basename(self.vehicle_file_path)
                self.vehicle_status_label.configure(text=f"✅ {filename}")
                
                # Update channel comboboxes
                self.veh_x_combo.set_completion_list(self.available_channels)
                self.veh_y_combo.set_completion_list(self.available_channels)
                
                # Log success
                self.log_status(f"✅ Loaded vehicle file: {filename}")
                self.log_status(f"📊 Found {len(self.available_channels)} channels")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load vehicle file: {str(e)}")
            self.log_status(f"❌ Error loading vehicle file: {str(e)}")
            
    def browse_csv_file(self):
        """Browse for CSV surface table file."""
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
                
                self.log_status(f"✅ Loaded CSV columns: {', '.join(columns)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read CSV file: {str(e)}")
                self.log_status(f"❌ Error reading CSV file: {str(e)}")
    
    def add_custom_channel(self):
        """Add a custom channel using the channel manager."""
        # Get form values
        name = self.channel_name_var.get().strip()
        csv_file = self.csv_file_var.get().strip()
        x_col = self.x_col_var.get().strip()
        y_col = self.y_col_var.get().strip()
        z_col = self.z_col_var.get().strip()
        veh_x = self.veh_x_var.get().strip()
        veh_y = self.veh_y_var.get().strip()
        units = self.units_var.get().strip()
        comment = self.comment_var.get().strip()
        
        # Create channel config
        try:
            config = self.channel_manager.create_channel_config(
                name, csv_file, x_col, y_col, z_col, veh_x, veh_y, units, comment
            )
            
            # Add channel
            self.channel_manager.add_channel(config)
            
            # Update display
            self.update_channels_display()
            
            # Clear form
            self.clear_channel_form()
            
            # Auto-save settings
            self.save_settings()
            
            self.log_status(f"✅ Added channel: {name}")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log_status(f"❌ Error adding channel: {str(e)}")
    
    def clear_channel_form(self):
        """Clear the channel configuration form."""
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
        """Update the channels table display."""
        # Clear existing items
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
        
        # Get filtered channels
        all_channels = self.channel_manager.get_all_channels()
        filtered_channels = self.channel_filter.filter_channels(all_channels)
        
        # Add channels to table
        for channel in filtered_channels:
            # Extract filename from full path for display
            csv_filename = os.path.basename(channel['csv_file']) if channel['csv_file'] else ""
            
            self.channels_tree.insert('', 'end', values=(
                channel['name'],
                csv_filename,
                channel['x_column'],
                channel['y_column'],
                channel['z_column'],
                channel['vehicle_x_channel'],
                channel['vehicle_y_channel'],
                channel['units'],
                channel['comment']
            ))
        
        # Update info label
        total = len(all_channels)
        filtered = len(filtered_channels)
        
        if total == 0:
            self.table_info_label.configure(text="No channels configured")
        elif total == filtered:
            self.table_info_label.configure(text=f"Showing all {total} channels")
        else:
            self.table_info_label.configure(text=f"Showing {filtered} of {total} channels")
    
    def clear_all_channels(self):
        """Clear all channels after confirmation."""
        if not self.channel_manager.get_all_channels():
            messagebox.showinfo("Info", "No channels to clear!")
            return
            
        result = messagebox.askyesno(
            "Confirm Clear All",
            "Are you sure you want to delete ALL channels?\n\nThis action cannot be undone!"
        )
        
        if result:
            self.channel_manager.clear_all_channels()
            self.update_channels_display()
            self.save_settings()
            self.log_status("🗑️ Cleared all channels")
    
    # Search and filtering
    def on_search_change(self, *args):
        """Handle search text changes."""
        search_term = self.search_var.get()
        self.channel_filter.set_search_term(search_term)
        self.apply_combined_filters()
        
    def apply_combined_filters(self):
        """Apply all filters and update display."""
        self.update_channels_display()
        
    def clear_search(self):
        """Clear search filter."""
        self.search_var.set("")
        self.channel_filter.set_search_term("")
        self.apply_combined_filters()
        
    def setup_filters(self):
        """Setup advanced filters dialog."""
        # This would open an advanced filters dialog
        # For now, we'll implement a simple filter dialog
        filter_dialog = ctk.CTkToplevel(self.root)
        filter_dialog.title("🔧 Advanced Filters")
        filter_dialog.geometry("600x400")
        filter_dialog.transient(self.root)
        filter_dialog.grab_set()
        
        # Center dialog
        filter_dialog.update_idletasks()
        x = (filter_dialog.winfo_screenwidth() // 2) - 300
        y = (filter_dialog.winfo_screenheight() // 2) - 200
        filter_dialog.geometry(f"600x400+{x}+{y}")
        
        # Content
        label = ctk.CTkLabel(
            filter_dialog,
            text="🔧 Advanced Filters\n\nComing Soon!",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        label.pack(expand=True)
        
        close_btn = ctk.CTkButton(
            filter_dialog,
            text="Close",
            command=filter_dialog.destroy
        )
        close_btn.pack(pady=20)
    
    def show_excel_filter(self, column_name):
        """Show Excel-style filter for a column."""
        # Get unique values for the column
        all_channels = self.channel_manager.get_all_channels()
        unique_values = self.channel_filter.get_unique_values_for_column(all_channels, column_name)
        
        if not unique_values:
            messagebox.showinfo("Info", f"No values found for column '{column_name}'")
            return
        
        # Get current filter
        current_filter = self.channel_filter.excel_filters.get(column_name, {})
        
        # Show Excel filter dialog
        dialog = ExcelFilterDialog(
            self.root,
            column_name,
            unique_values,
            current_filter,
            logger=self
        )
        
        dialog.show()
        
        # Apply the filter if one was set
        if hasattr(dialog, 'result_filter') and dialog.result_filter:
            self.channel_filter.set_excel_filter(
                column_name,
                dialog.result_filter.get('selected_values', []),
                dialog.result_filter.get('filter_type', 'include')
            )
            self.apply_combined_filters()
            self.update_column_headers()
    
    def update_column_headers(self):
        """Update column headers to show filter status."""
        for col in self.channels_tree['columns']:
            header_text = self.channel_filter.get_column_header_text(col)
            self.channels_tree.heading(col, text=header_text)
    
    # Channel management operations
    def edit_selected_channel(self):
        """Edit the selected channel."""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to edit!")
            return
            
        item = selection[0]
        values = self.channels_tree.item(item)['values']
        
        # Find the actual channel in the list by name
        channel_name = values[0]
        all_channels = self.channel_manager.get_all_channels()
        
        channel = None
        channel_index = None
        
        for i, ch in enumerate(all_channels):
            if ch['name'] == channel_name:
                channel = ch
                channel_index = i
                break
        
        if not channel:
            messagebox.showerror("Error", "Channel not found!")
            return
        
        # Open edit dialog
        self.open_edit_channel_dialog(channel, channel_index)
    
    def open_edit_channel_dialog(self, channel, channel_index):
        """Open a separate dialog to edit the selected channel."""
        edit_dialog = ctk.CTkToplevel(self.root)
        edit_dialog.title(f'✏️ Edit Channel: {channel["name"]}')
        edit_dialog.geometry('800x700')
        edit_dialog.transient(self.root)
        edit_dialog.grab_set()
        edit_dialog.resizable(True, True)
        
        # Center dialog
        edit_dialog.update_idletasks()
        x = (edit_dialog.winfo_screenwidth() // 2) - 400
        y = (edit_dialog.winfo_screenheight() // 2) - 350
        edit_dialog.geometry(f"800x700+{x}+{y}")
        
        # Create scrollable main frame
        main_frame = ctk.CTkScrollableFrame(edit_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"✏️ Edit Channel: {channel['name']}",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Create form variables for editing
        edit_channel_name_var = ctk.StringVar(value=channel['name'])
        edit_csv_file_var = ctk.StringVar(value=channel['csv_file'])
        edit_x_col_var = ctk.StringVar(value=channel['x_column'])
        edit_y_col_var = ctk.StringVar(value=channel['y_column'])
        edit_z_col_var = ctk.StringVar(value=channel['z_column'])
        edit_veh_x_var = ctk.StringVar(value=channel['vehicle_x_channel'])
        edit_veh_y_var = ctk.StringVar(value=channel['vehicle_y_channel'])
        edit_units_var = ctk.StringVar(value=channel['units'])
        edit_comment_var = ctk.StringVar(value=channel['comment'])
        
        # Main form container - reuse the same layout as the main form
        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        # Channel name
        name_frame = ctk.CTkFrame(form_frame)
        name_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(name_frame, text="📝 Channel Name:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=10)
        edit_channel_name_entry = ctk.CTkEntry(name_frame, textvariable=edit_channel_name_var, 
                                              placeholder_text="Enter channel name", width=250)
        edit_channel_name_entry.pack(side="left", padx=10, pady=10)
        
        # CSV Surface Table file
        csv_frame = ctk.CTkFrame(form_frame)
        csv_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(csv_frame, text="📊 Surface Table CSV:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=10)
        edit_csv_file_entry = ctk.CTkEntry(csv_frame, textvariable=edit_csv_file_var, 
                                          placeholder_text="Select CSV file", width=200)
        edit_csv_file_entry.pack(side="left", padx=10, pady=10)
        
        def browse_edit_csv_file():
            file_path = filedialog.askopenfilename(
                title="Select Surface Table CSV File",
                filetypes=[("CSV Files", "*.csv")]
            )
            
            if file_path:
                edit_csv_file_var.set(file_path)
                
                # Load CSV columns for selection
                try:
                    columns = self.file_manager.load_csv_columns(file_path)
                    
                    # Update comboboxes with available columns
                    edit_x_col_combo.set_completion_list(columns)
                    edit_y_col_combo.set_completion_list(columns)
                    edit_z_col_combo.set_completion_list(columns)
                    
                    self.log_status(f"✅ Loaded CSV columns for editing: {', '.join(columns)}")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to read CSV file: {str(e)}")
                    self.log_status(f"❌ Error reading CSV file: {str(e)}")
        
        edit_browse_csv_btn = ctk.CTkButton(csv_frame, text="📁 Browse", 
                                           command=browse_edit_csv_file, width=80)
        edit_browse_csv_btn.pack(side="left", padx=5, pady=10)
        
        # CSV columns configuration
        csv_config_frame = ctk.CTkFrame(form_frame)
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
        edit_x_col_combo = ModernAutocompleteCombobox(csv_grid, variable=edit_x_col_var, width=180)
        edit_x_col_combo.grid(row=0, column=1, padx=10, pady=5)
        
        # Y column
        ctk.CTkLabel(csv_grid, text="📈 Y-axis Column (e.g., ETASP):", 
                    font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        edit_y_col_combo = ModernAutocompleteCombobox(csv_grid, variable=edit_y_col_var, width=180)
        edit_y_col_combo.grid(row=1, column=1, padx=10, pady=5)
        
        # Z column
        ctk.CTkLabel(csv_grid, text="📋 Z-axis Column (Values):", 
                    font=ctk.CTkFont(size=11)).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        edit_z_col_combo = ModernAutocompleteCombobox(csv_grid, variable=edit_z_col_var, width=180)
        edit_z_col_combo.grid(row=2, column=1, padx=10, pady=5)
        
        # Vehicle channels configuration
        veh_config_frame = ctk.CTkFrame(form_frame)
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
        edit_veh_x_combo = ModernAutocompleteCombobox(veh_grid, variable=edit_veh_x_var, width=200)
        edit_veh_x_combo.grid(row=0, column=1, padx=10, pady=5)
        
        # Vehicle Y channel
        ctk.CTkLabel(veh_grid, text="📊 Vehicle Y Channel:", 
                    font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        edit_veh_y_combo = ModernAutocompleteCombobox(veh_grid, variable=edit_veh_y_var, width=200)
        edit_veh_y_combo.grid(row=1, column=1, padx=10, pady=5)
        
        # Units and comment
        meta_frame = ctk.CTkFrame(form_frame)
        meta_frame.pack(fill="x", padx=10, pady=10)
        
        meta_grid = ctk.CTkFrame(meta_frame)
        meta_grid.pack(fill="x", padx=20, pady=15)
        
        # Units
        ctk.CTkLabel(meta_grid, text="📏 Units:", 
                    font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        edit_units_entry = ctk.CTkEntry(meta_grid, textvariable=edit_units_var, 
                                       placeholder_text="e.g., bar, %", width=120)
        edit_units_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Comment
        ctk.CTkLabel(meta_grid, text="💬 Comment:", 
                    font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=10, pady=5, sticky="w")
        edit_comment_entry = ctk.CTkEntry(meta_grid, textvariable=edit_comment_var, 
                                         placeholder_text="Optional comment", width=200)
        edit_comment_entry.grid(row=0, column=3, padx=10, pady=5)
        
        # Initialize comboboxes with current data
        try:
            # Load CSV columns if file exists
            if os.path.exists(channel['csv_file']):
                columns = self.file_manager.load_csv_columns(channel['csv_file'])
                edit_x_col_combo.set_completion_list(columns)
                edit_y_col_combo.set_completion_list(columns)
                edit_z_col_combo.set_completion_list(columns)
            
            # Load vehicle channels if available
            if self.available_channels:
                edit_veh_x_combo.set_completion_list(self.available_channels)
                edit_veh_y_combo.set_completion_list(self.available_channels)
                
        except Exception as e:
            self.log_status(f"⚠️ Error loading initial data for edit dialog: {str(e)}")
        
        # Buttons frame
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=20)
        
        def save_changes():
            # Validate input
            new_channel_name = edit_channel_name_var.get().strip()
            new_csv_file = edit_csv_file_var.get().strip()
            new_x_col = edit_x_col_var.get().strip()
            new_y_col = edit_y_col_var.get().strip()
            new_z_col = edit_z_col_var.get().strip()
            new_veh_x_channel = edit_veh_x_var.get().strip()
            new_veh_y_channel = edit_veh_y_var.get().strip()
            new_units = edit_units_var.get().strip()
            new_comment = edit_comment_var.get().strip()
            
            # Create new config
            try:
                new_config = self.channel_manager.create_channel_config(
                    new_channel_name, new_csv_file, new_x_col, new_y_col, new_z_col,
                    new_veh_x_channel, new_veh_y_channel, new_units, new_comment
                )
                
                # Check if channel name already exists (except for the current channel)
                all_channels = self.channel_manager.get_all_channels()
                for i, ch in enumerate(all_channels):
                    if i != channel_index and ch['name'] == new_channel_name:
                        messagebox.showerror("Error", "Channel with this name already exists!")
                        return
                
                # Update the channel
                self.channel_manager.update_channel(channel_index, new_config)
                
                # Update display with current filters
                self.apply_combined_filters()
                
                # Auto-save settings
                self.save_settings()
                
                self.log_status(f"✅ Updated channel: {channel['name']} → {new_channel_name}")
                edit_dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", str(e))
                self.log_status(f"❌ Error updating channel: {str(e)}")
            
        def cancel_edit():
            edit_dialog.destroy()
        
        save_btn = ctk.CTkButton(
            button_frame,
            text='✅ Save Changes',
            command=save_changes,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            height=35
        )
        save_btn.pack(side='left', padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text='❌ Cancel',
            command=cancel_edit,
            width=100,
            height=35
        )
        cancel_btn.pack(side='left', padx=5)
        
        self.log_status(f"✏️ Opened edit dialog for channel: {channel['name']}")
        
    def delete_selected_channel(self):
        """Delete the selected channel."""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to delete!")
            return
            
        item = selection[0]
        values = self.channels_tree.item(item)['values']
        channel_name = values[0]
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete channel '{channel_name}'?\n\nThis action cannot be undone!"
        )
        
        if result:
            try:
                self.channel_manager.delete_channel_by_name(channel_name)
                self.update_channels_display()
                self.save_settings()
                self.log_status(f"🗑️ Deleted channel: {channel_name}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete channel: {str(e)}")
                self.log_status(f"❌ Error deleting channel: {str(e)}")
    
    def duplicate_selected_channel(self):
        """Duplicate the selected channel."""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to duplicate!")
            return
            
        item = selection[0]
        values = self.channels_tree.item(item)['values']
        channel_name = values[0]
        
        # Find the channel
        all_channels = self.channel_manager.get_all_channels()
        channel_index = None
        
        for i, ch in enumerate(all_channels):
            if ch['name'] == channel_name:
                channel_index = i
                break
        
        if channel_index is not None:
            try:
                self.channel_manager.duplicate_channel(channel_index)
                self.update_channels_display()
                self.save_settings()
                self.log_status(f"📋 Duplicated channel: {channel_name}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to duplicate channel: {str(e)}")
                self.log_status(f"❌ Error duplicating channel: {str(e)}")
    
    def export_channel_config(self):
        """Export channel configuration."""
        channels = self.channel_manager.get_all_channels()
        if not channels:
            messagebox.showinfo("Info", "No channels to export!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Channel Configuration",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                self.config_manager.export_channel_config(channels, file_path)
                self.log_status(f"📤 Exported {len(channels)} channels to: {os.path.basename(file_path)}")
                messagebox.showinfo("Success", f"Exported {len(channels)} channels successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration: {str(e)}")
                self.log_status(f"❌ Error exporting configuration: {str(e)}")
    
    def import_channel_config(self):
        """Import channel configuration."""
        file_path = filedialog.askopenfilename(
            title="Import Channel Configuration", 
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                imported_channels = self.config_manager.import_channel_config(file_path)
                
                if not imported_channels:
                    messagebox.showinfo("Info", "No valid channels found in the file!")
                    return
                
                # Check if there are existing channels
                existing_channels = self.channel_manager.get_all_channels()
                
                if existing_channels:
                    # Show merge options dialog
                    self.show_import_merge_dialog(imported_channels, file_path)
                else:
                    # No existing channels, just add all
                    self.channel_manager.set_all_channels(imported_channels)
                    self.update_channels_display()
                    self.save_settings()
                    self.log_status(f"📥 Imported {len(imported_channels)} channels from: {os.path.basename(file_path)}")
                    messagebox.showinfo("Success", f"Imported {len(imported_channels)} channels successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import configuration: {str(e)}")
                self.log_status(f"❌ Error importing configuration: {str(e)}")
    
    def show_import_merge_dialog(self, imported_channels, file_path):
        """Show dialog for choosing import merge strategy."""
        merge_dialog = ctk.CTkToplevel(self.root)
        merge_dialog.title("Import Options")
        merge_dialog.geometry("500x300")
        merge_dialog.transient(self.root)
        merge_dialog.grab_set()
        
        # Center dialog
        merge_dialog.update_idletasks()
        x = (merge_dialog.winfo_screenwidth() // 2) - 250
        y = (merge_dialog.winfo_screenheight() // 2) - 150
        merge_dialog.geometry(f"500x300+{x}+{y}")
        
        # Content
        main_frame = ctk.CTkFrame(merge_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text="📥 Import Options",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        info_label = ctk.CTkLabel(
            main_frame,
            text=f"Found {len(imported_channels)} channels in the import file.\nHow would you like to handle existing channels?",
            font=ctk.CTkFont(size=12),
            justify="center"
        )
        info_label.pack(pady=(0, 20))
        
        def replace_all():
            self.channel_manager.set_all_channels(imported_channels)
            self.update_channels_display()
            self.save_settings()
            self.log_status(f"📥 Replaced all channels with {len(imported_channels)} imported channels")
            messagebox.showinfo("Success", f"Imported {len(imported_channels)} channels successfully!")
            merge_dialog.destroy()
        
        def add_to_existing():
            existing_channels = self.channel_manager.get_all_channels()
            merged_channels = self.config_manager.merge_channel_configs(existing_channels, imported_channels, "add")
            self.channel_manager.set_all_channels(merged_channels)
            self.update_channels_display()
            self.save_settings()
            added_count = len(merged_channels) - len(existing_channels)
            self.log_status(f"📥 Added {added_count} new channels from import")
            messagebox.showinfo("Success", f"Added {added_count} new channels successfully!")
            merge_dialog.destroy()
        
        def cancel_import():
            merge_dialog.destroy()
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=20)
        
        replace_btn = ctk.CTkButton(
            button_frame,
            text="🔄 Replace All",
            command=replace_all,
            width=120,
            height=35
        )
        replace_btn.pack(side="left", padx=5)
        
        add_btn = ctk.CTkButton(
            button_frame,
            text="➕ Add to Existing",
            command=add_to_existing,
            width=120,
            height=35
        )
        add_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="❌ Cancel",
            command=cancel_import,
            width=100,
            height=35
        )
        cancel_btn.pack(side="left", padx=5)
    
    # Processing functionality
    def process_all_channels(self):
        """Process all configured channels."""
        # Validate prerequisites
        if not self.vehicle_data:
            messagebox.showerror("Error", "Please load a vehicle file first!")
            return
        
        channels = self.channel_manager.get_all_channels()
        if not channels:
            messagebox.showerror("Error", "No channels configured!")
            return
        
        # Validate all channels
        validation_errors = self.channel_validator.validate_all_channels(channels, self.vehicle_data)
        if validation_errors:
            error_msg = "Channel validation errors:\n\n" + "\n".join(validation_errors)
            messagebox.showerror("Validation Error", error_msg)
            return
        
        # Show progress dialog
        progress_dialog = ModernProgressDialog(
            self.root,
            title="Processing Channels",
            message="Processing all configured channels..."
        )
        
        def process_thread():
            try:
                # Analyze sampling rates
                self.process_status_label.configure(text="Analyzing sampling rates...")
                progress_dialog.update_status("Analyzing channel sampling rates...", 10)
                
                channel_analysis = self.channel_analyzer.analyze_channel_sampling_rates(
                    self.vehicle_data, channels, self.vehicle_file_path
                )
                
                # Ask for raster if needed
                progress_dialog.close()
                target_raster = self.ask_for_raster(channel_analysis)
                
                if target_raster is None:
                    return  # User cancelled
                
                # Reopen progress dialog
                progress_dialog = ModernProgressDialog(
                    self.root,
                    title="Processing Channels", 
                    message="Processing channels with selected raster..."
                )
                
                # Process each channel
                calculated_signals = {}
                total_channels = len(channels)
                
                for i, channel in enumerate(channels):
                    progress = 20 + (70 * i / total_channels)
                    progress_dialog.update_status(f"Processing channel: {channel['name']}", progress)
                    
                    # Load surface table
                    surface_data = self.data_processor.load_surface_table(
                        channel['csv_file'],
                        channel['x_column'],
                        channel['y_column'], 
                        channel['z_column']
                    )
                    
                    # Get vehicle channel data
                    x_data = self.channel_analyzer.get_interpolated_signal_data(
                        self.vehicle_data, self.vehicle_file_path, channel['vehicle_x_channel'], target_raster
                    )
                    y_data = self.channel_analyzer.get_interpolated_signal_data(
                        self.vehicle_data, self.vehicle_file_path, channel['vehicle_y_channel'], target_raster
                    )
                    
                    # Interpolate values
                    z_interpolated = []
                    for x_val, y_val in zip(x_data, y_data):
                        z_val = self.data_processor.interpolate_z_value(
                            x_val, y_val,
                            surface_data['x_values'],
                            surface_data['y_values'],
                            surface_data['z_matrix']
                        )
                        z_interpolated.append(z_val)
                    
                    # Create calculated signal
                    signal = self.output_generator.create_calculated_signal(
                        channel, z_interpolated, surface_data['timestamps']
                    )
                    calculated_signals[channel['name']] = signal
                
                # Save output
                progress_dialog.update_status("Saving output...", 95)
                
                original_file_ext = os.path.splitext(self.vehicle_file_path)[1]
                self.file_manager.save_output(
                    calculated_signals, self.vehicle_file_path, original_file_ext,
                    vehicle_data=self.vehicle_data
                )
                
                progress_dialog.update_status("Complete!", 100)
                
                # Success
                self.root.after(0, lambda: [
                    progress_dialog.close(),
                    messagebox.showinfo("Success", f"Successfully processed {len(channels)} channels!"),
                    self.log_status(f"✅ Successfully processed {len(channels)} channels")
                ])
                
            except Exception as e:
                self.root.after(0, lambda: [
                    progress_dialog.close(),
                    messagebox.showerror("Error", f"Processing failed: {str(e)}"),
                    self.log_status(f"❌ Processing failed: {str(e)}")
                ])
        
        # Start processing in background thread
        threading.Thread(target=process_thread, daemon=True).start()
    
    def ask_for_raster(self, channel_analysis):
        """Ask user for target raster using advanced dialog."""
        dialog = AdvancedRasterDialog(self.root, channel_analysis, logger=self)
        dialog.show()
        
        # Wait for dialog to complete
        self.root.wait_window(dialog.dialog)
        
        # Return the selected raster
        return getattr(dialog, 'selected_raster', None)
    
    # Settings management
    def save_settings(self):
        """Save current settings."""
        try:
            self.settings_manager.save_settings(self)
            self.log_status("💾 Settings saved")
        except Exception as e:
            self.log_status(f"❌ Error saving settings: {str(e)}")
    
    def load_settings_on_startup(self):
        """Load settings on application startup."""
        try:
            settings = self.settings_manager.load_settings_on_startup()
            if settings:
                self.restore_settings(settings)
                self.log_status("📂 Settings loaded from startup")
        except Exception as e:
            self.log_status(f"⚠️ Could not load startup settings: {str(e)}")
    
    def save_settings_as(self):
        """Save settings to a specific file."""
        file_path = filedialog.asksaveasfilename(
            title="Save Settings As",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                self.settings_manager.save_settings_as(self, file_path)
                self.log_status(f"💾 Settings saved as: {os.path.basename(file_path)}")
                messagebox.showinfo("Success", "Settings saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
                self.log_status(f"❌ Error saving settings: {str(e)}")
    
    def load_settings_from(self):
        """Load settings from a specific file."""
        file_path = filedialog.askopenfilename(
            title="Load Settings From",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                settings = self.settings_manager.load_settings_from(file_path)
                if settings:
                    self.restore_settings(settings)
                    self.log_status(f"📂 Settings loaded from: {os.path.basename(file_path)}")
                    messagebox.showinfo("Success", "Settings loaded successfully!")
                else:
                    messagebox.showwarning("Warning", "No valid settings found in file!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
                self.log_status(f"❌ Error loading settings: {str(e)}")
    
    def quick_save_settings(self, slot):
        """Quick save settings to a slot."""
        try:
            self.settings_manager.quick_save_settings(self, slot)
            slot_name = self.settings_manager.get_slot_name(slot)
            self.log_status(f"⚡ Quick saved to {slot_name}")
        except Exception as e:
            self.log_status(f"❌ Error quick saving: {str(e)}")
    
    def quick_load_settings(self, slot):
        """Quick load settings from a slot."""
        try:
            settings = self.settings_manager.quick_load_settings(slot)
            if settings:
                self.restore_settings(settings)
                slot_name = self.settings_manager.get_slot_name(slot)
                self.log_status(f"⚡ Quick loaded from {slot_name}")
            else:
                slot_name = self.settings_manager.get_slot_name(slot)
                messagebox.showinfo("Info", f"No settings saved in {slot_name}!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
            self.log_status(f"❌ Error quick loading: {str(e)}")
    
    def rename_slot_dialog(self, slot):
        """Show dialog to rename a quick save slot."""
        current_name = self.settings_manager.get_slot_name(slot)
        
        rename_dialog = ctk.CTkToplevel(self.root)
        rename_dialog.title(f"Rename {current_name}")
        rename_dialog.geometry("400x200")
        rename_dialog.transient(self.root)
        rename_dialog.grab_set()
        
        # Center dialog
        rename_dialog.update_idletasks()
        x = (rename_dialog.winfo_screenwidth() // 2) - 200
        y = (rename_dialog.winfo_screenheight() // 2) - 100
        rename_dialog.geometry(f"400x200+{x}+{y}")
        
        # Content
        main_frame = ctk.CTkFrame(rename_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"Rename {current_name}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        new_name_var = ctk.StringVar(value=current_name)
        name_entry = ctk.CTkEntry(
            main_frame,
            textvariable=new_name_var,
            placeholder_text="Enter new name",
            width=300
        )
        name_entry.pack(pady=10)
        name_entry.focus()
        
        def confirm():
            new_name = new_name_var.get().strip()
            if new_name and new_name != current_name:
                self.settings_manager.update_slot_name(slot, new_name)
                if slot == 1:
                    self.slot_1_name_var.set(new_name)
                else:
                    self.slot_2_name_var.set(new_name)
                self.log_status(f"✏️ Renamed slot {slot} to: {new_name}")
            rename_dialog.destroy()
        
        def cancel():
            rename_dialog.destroy()
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=20)
        
        confirm_btn = ctk.CTkButton(
            button_frame,
            text="✅ Confirm",
            command=confirm,
            width=100
        )
        confirm_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="❌ Cancel",
            command=cancel,
            width=100
        )
        cancel_btn.pack(side="left", padx=5)
        
        # Bind Enter key
        name_entry.bind('<Return>', lambda e: confirm())
    
    def restore_settings(self, settings):
        """Restore application settings."""
        try:
            # Restore channels
            if 'custom_channels' in settings:
                self.channel_manager.set_all_channels(settings['custom_channels'])
                self.update_channels_display()
            
            # Restore vehicle file
            if 'vehicle_file_path' in settings and settings['vehicle_file_path']:
                self.vehicle_file_path = settings['vehicle_file_path']
                if os.path.exists(self.vehicle_file_path):
                    self.load_vehicle_file()
            
            # Restore theme
            if 'theme' in settings:
                self.theme_var.set(settings['theme'])
                self.change_theme(settings['theme'])
            
            # Restore slot names
            if 'slot_names' in settings:
                slot_names = settings['slot_names']
                if '1' in slot_names:
                    self.slot_1_name_var.set(slot_names['1'])
                if '2' in slot_names:
                    self.slot_2_name_var.set(slot_names['2'])
        
        except Exception as e:
            self.log_status(f"⚠️ Error restoring some settings: {str(e)}")
    
    def get_all_settings(self):
        """Get all current settings for saving."""
        return self.settings_manager.get_all_settings(self)
    
    # Status log functionality
    def clear_status_log(self):
        """Clear the status log."""
        self.status_log.clear()
        self.log_display.delete("0.0", "end")
        self.log_status("🗑️ Status log cleared")
    
    def log_status(self, message):
        """Add a message to the status log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Add to log list
        self.status_log.append(log_entry)
        
        # Update display
        self.log_display.insert("end", log_entry + "\n")
        self.log_display.see("end")
        
        # Limit log size
        if len(self.status_log) > 1000:
            self.status_log = self.status_log[-500:]
            # Rebuild display
            self.log_display.delete("0.0", "end")
            for entry in self.status_log:
                self.log_display.insert("end", entry + "\n")
    
    def on_closing(self):
        """Handle application closing."""
        try:
            # Auto-save settings before closing
            self.save_settings()
            self.log_status("👋 Application closing - settings saved")
        except:
            pass
        
        self.root.destroy()
    
    def run(self):
        """Start the application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    app = VehicleLogChannelAppenderModular()
    app.run()


if __name__ == "__main__":
    main()