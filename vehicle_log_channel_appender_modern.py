"""
Vehicle Log Channel Appender - Modern UI Version
Complete implementation with ALL features from the original

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

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark")  # Default to dark mode
ctk.set_default_color_theme("blue")  # Professional blue theme


class ModernAutocompleteCombobox(ctk.CTkComboBox):
    """A modern ComboBox with autocompletion support."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._completion_list = []
        self.bind('<KeyRelease>', self.handle_keyrelease)
    
    def set_completion_list(self, completion_list):
        """Set the list of values for autocompletion."""
        self._completion_list = sorted(completion_list, key=str.lower)
        self.configure(values=self._completion_list)
    
    def handle_keyrelease(self, event):
        """Handle key release events for autocompletion."""
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Return', 'Tab']:
            return
        
        current_text = self.get().lower()
        if not current_text:
            self.configure(values=self._completion_list)
            return
        
        # Filter matching items
        matches = [item for item in self._completion_list 
                  if item.lower().startswith(current_text)]
        
        if matches:
            self.configure(values=matches)


class ModernProgressDialog:
    """Modern progress dialog with loading animation."""
    
    def __init__(self, parent, title="Processing", message="Please wait..."):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create modern layout
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Message label
        self.message_label = ctk.CTkLabel(
            main_frame, 
            text=message,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.message_label.pack(pady=(0, 15))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(main_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))
        self.progress_bar.set(0)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Initializing...",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack()
        
    def update_progress(self, value, status=""):
        """Update progress bar and status."""
        self.progress_bar.set(value)
        if status:
            self.status_label.configure(text=status)
        self.dialog.update_idletasks()
    
    def close(self):
        """Close the dialog."""
        self.dialog.destroy()


class VehicleLogChannelAppenderModern:
    def __init__(self):
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("🚗 Vehicle Log Channel Appender - Modern Edition")
        self.root.geometry("1400x900")
        
        # Set window icon and properties
        self.setup_window_properties()
        
        # Data storage
        self.vehicle_file_path = None
        self.vehicle_data = None
        self.available_channels = []
        self.custom_channels = []
        self.reference_timestamps = None
        
        # UI state
        self.search_var = ctk.StringVar()
        self.filter_vars = {}
        self.all_custom_channels = []
        self.settings_data = {}
        
        # Form variables
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
        
        # Theme variables
        self.theme_var = ctk.StringVar(value="dark")
        
        # Setup UI
        self.setup_ui()
        self.setup_bindings()
        
        # Load settings on startup
        self.load_settings_on_startup()
        
        # Initialize with welcome message
        self.log_status("🎉 Welcome to Vehicle Log Channel Appender - Modern Edition!")
        self.log_status("💡 Select a vehicle file and configure custom channels to begin")
    
    def setup_window_properties(self):
        """Configure window properties for Windows compatibility."""
        # Center window on screen
        self.root.update_idletasks()
        width = 1400
        height = 900
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
        self.sidebar_frame.grid_propagate(False)  # Prevent frame from shrinking
        
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
            text="Modern Edition v2.0",
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
        quick_frame = ctk.CTkFrame(self.settings_frame)
        quick_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        quick_label = ctk.CTkLabel(
            quick_frame,
            text="⚡ Quick Save/Load:",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        quick_label.pack(pady=(10, 5))
        
        # Initialize slot names storage
        self.slot_names = {1: "Slot 1", 2: "Slot 2", 3: "Slot 3"}
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
            name_entry.insert(0, self.slot_names[i])
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
        self.setup_complete_channel_form()
        
        # Channels table with search and filters
        self.setup_complete_channels_table()
    
    def setup_complete_channel_form(self):
        """Setup the complete channel addition form with all fields."""
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
        csv_config_frame = ctk.CTkFrame(main_form)
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
        veh_config_frame = ctk.CTkFrame(main_form)
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
        meta_frame = ctk.CTkFrame(main_form)
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
    
    def setup_complete_channels_table(self):
        """Setup the complete channels table with search, filters, and management."""
        table_frame = ctk.CTkFrame(self.channels_scroll)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 20))
        
        table_title = ctk.CTkLabel(
            table_frame,
            text="📋 Configured Custom Channels",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        table_title.pack(pady=(15, 10))
        
        # Search and filter controls
        search_frame = ctk.CTkFrame(table_frame)
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
        self.setup_filters_btn = ctk.CTkButton(
            search_controls,
            text="🎛️ Setup Filters",
            command=self.setup_filters,
            width=100,
            height=28
        )
        self.setup_filters_btn.pack(side="right", padx=5)
        
        # Create proper table display using treeview
        # Configure treeview style
        import tkinter.ttk as ttk
        style = ttk.Style()
        style.configure("Modern.Treeview", 
                       background="#212121",
                       foreground="white",
                       fieldbackground="#212121",
                       font=("Segoe UI", 10))
        style.configure("Modern.Treeview.Heading", 
                       background="#2a2a2a",
                       foreground="#ffffff",
                       relief="raised",
                       borderwidth=1,
                       font=("Segoe UI", 10, "bold"))
        style.map("Modern.Treeview.Heading",
                 background=[('active', '#3a3a3a')],
                 foreground=[('active', '#ffffff')])
        
        # Table container with proper scrollbars
        tree_container = ctk.CTkFrame(table_frame)
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
        
        # Configure columns
        column_widths = {"Name": 120, "CSV File": 150, "X Col": 80, "Y Col": 80, "Z Col": 80, 
                        "Veh X": 120, "Veh Y": 120, "Units": 60, "Comment": 150}
        
        for col in columns:
            self.channels_tree.heading(col, text=col)
            self.channels_tree.column(col, width=column_widths.get(col, 100), minwidth=60)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.channels_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.channels_tree.xview)
        
        self.channels_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout for proper alignment
        self.channels_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Table management buttons
        controls_frame = ctk.CTkFrame(table_frame)
        controls_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.edit_channel_btn = ctk.CTkButton(
            controls_frame,
            text="✏️ Edit Selected",
            command=self.edit_selected_channel,
            width=120,
            height=30
        )
        self.edit_channel_btn.pack(side="left", padx=5)
        
        self.delete_channel_btn = ctk.CTkButton(
            controls_frame,
            text="🗑️ Delete Selected",
            command=self.delete_selected_channel,
            width=120,
            height=30
        )
        self.delete_channel_btn.pack(side="left", padx=5)
        
        self.duplicate_channel_btn = ctk.CTkButton(
            controls_frame,
            text="📋 Duplicate",
            command=self.duplicate_selected_channel,
            width=100,
            height=30
        )
        self.duplicate_channel_btn.pack(side="left", padx=5)
        
        self.clear_all_btn = ctk.CTkButton(
            controls_frame,
            text="🧹 Clear All",
            command=self.clear_all_channels,
            width=100,
            height=30
        )
        self.clear_all_btn.pack(side="left", padx=5)
        
        self.export_config_btn = ctk.CTkButton(
            controls_frame,
            text="📤 Export Config",
            command=self.export_channel_config,
            width=120,
            height=30
        )
        self.export_config_btn.pack(side="right", padx=5)
    
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
    
    # UI Event Handlers
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
                self.load_vehicle_file()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load vehicle file: {str(e)}")
                self.log_status(f"❌ Error loading vehicle file: {str(e)}")
    
    def load_vehicle_file(self):
        """Load vehicle file and extract available channels."""
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        
        if file_ext == '.csv':
            self.load_csv_vehicle_file()
        elif file_ext in ['.mdf', '.mf4', '.dat']:
            self.load_mdf_vehicle_file()
        else:
            raise Exception(f"Unsupported file format: {file_ext}")
    
    def load_csv_vehicle_file(self):
        """Load CSV vehicle file."""
        try:
            df = pd.read_csv(self.vehicle_file_path)
            self.available_channels = df.columns.tolist()
            self.vehicle_data = df
            
            # Update channel comboboxes
            self.veh_x_combo.set_completion_list(self.available_channels)
            self.veh_y_combo.set_completion_list(self.available_channels)
            
            self.log_status(f"✅ CSV vehicle file loaded successfully. Found {len(self.available_channels)} channels.")
            
        except Exception as e:
            raise Exception(f"Error loading CSV vehicle file: {str(e)}")
    
    def load_mdf_vehicle_file(self):
        """Load MDF/MF4/DAT vehicle file."""
        try:
            mdf = MDF(self.vehicle_file_path)
            
            # Get available channels
            self.available_channels = []
            for group_index in range(len(mdf.groups)):
                for channel in mdf.groups[group_index].channels:
                    self.available_channels.append(channel.name)
            
            self.vehicle_data = mdf
            
            # Update channel comboboxes
            self.veh_x_combo.set_completion_list(self.available_channels)
            self.veh_y_combo.set_completion_list(self.available_channels)
            
            self.log_status(f"✅ MDF vehicle file loaded successfully. Found {len(self.available_channels)} channels.")
            
        except Exception as e:
            raise Exception(f"Error loading MDF vehicle file: {str(e)}")
    
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
                df = pd.read_csv(file_path, nrows=1)
                columns = df.columns.tolist()
                
                # Update comboboxes with available columns
                self.x_col_combo.set_completion_list(columns)
                self.y_col_combo.set_completion_list(columns)
                self.z_col_combo.set_completion_list(columns)
                
                self.log_status(f"✅ Loaded CSV columns: {', '.join(columns)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read CSV file: {str(e)}")
                self.log_status(f"❌ Error reading CSV file: {str(e)}")
    
    def add_custom_channel(self):
        """Add a new custom channel configuration."""
        channel_name = self.channel_name_var.get().strip()
        csv_file = self.csv_file_var.get().strip()
        x_col = self.x_col_var.get().strip()
        y_col = self.y_col_var.get().strip()
        z_col = self.z_col_var.get().strip()
        veh_x_channel = self.veh_x_var.get().strip()
        veh_y_channel = self.veh_y_var.get().strip()
        units = self.units_var.get().strip()
        comment = self.comment_var.get().strip()
        
        # Validation
        if not all([channel_name, csv_file, x_col, y_col, z_col, veh_x_channel, veh_y_channel]):
            messagebox.showerror("Error", "Please fill in all required fields!")
            return
            
        if not os.path.exists(csv_file):
            messagebox.showerror("Error", "CSV file does not exist!")
            return
            
        if x_col == y_col or x_col == z_col or y_col == z_col:
            messagebox.showerror("Error", "X, Y, and Z columns must be different!")
            return
        
        # Check if channel already exists
        for channel in self.custom_channels:
            if channel['name'] == channel_name:
                messagebox.showerror("Error", "Channel with this name already exists!")
                return
        
        # Create custom channel configuration
        new_channel = {
            'name': channel_name,
            'csv_file': csv_file,
            'x_column': x_col,
            'y_column': y_col,
            'z_column': z_col,
            'vehicle_x_channel': veh_x_channel,
            'vehicle_y_channel': veh_y_channel,
            'units': units,
            'comment': comment
        }
        
        # Add to the list
        self.custom_channels.append(new_channel)
        
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
        
        self.log_status(f"✅ Added custom channel: {channel_name}")
    
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
        """Update the channels display with current channels."""
        # Clear existing items
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
        
        # Populate with current channels
        for channel in self.custom_channels:
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
    
    def clear_all_channels(self):
        """Clear all custom channels after confirmation."""
        if not self.custom_channels:
            return
        
        result = messagebox.askyesno(
            "Confirm Clear",
            f"Are you sure you want to clear all {len(self.custom_channels)} custom channels?"
        )
        
        if result:
            self.custom_channels.clear()
            self.update_channels_display()
            self.log_status("🗑️ All custom channels cleared.")
    
    def on_search_change(self, *args):
        """Handle search text changes."""
        search_term = self.search_var.get().lower()
        if search_term:
            self.log_status(f"🔍 Search term: '{search_term}'")
            # Apply search filter to displayed channels
            self.apply_search_filter()
    
    def apply_search_filter(self):
        """Apply search filter to channels display."""
        search_term = self.search_var.get().lower()
        
        # Clear existing items
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
        
        # Filter and display channels
        for channel in self.custom_channels:
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
            
            # If no search term or term matches, show the channel
            if not search_term or search_term in channel_text:
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
    
    def clear_search(self):
        """Clear search field and show all channels."""
        self.search_var.set("")
        self.update_channels_display()
    
    def setup_filters(self):
        """Setup column filters dialog."""
        # For simplicity, we'll implement basic search for now
        # Could be expanded to more sophisticated filtering
        messagebox.showinfo("Filters", "Use the search box for basic filtering.\nAdvanced filters will be added in future updates.")
    
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
        channel = None
        channel_index = None
        
        for i, ch in enumerate(self.custom_channels):
            if ch['name'] == channel_name:
                channel = ch
                channel_index = i
                break
        
        if not channel:
            messagebox.showerror("Error", "Channel not found!")
            return
        
        # Fill the input fields with current values
        self.channel_name_var.set(channel['name'])
        self.csv_file_var.set(channel['csv_file'])
        
        # Load CSV columns and set values
        try:
            df = pd.read_csv(channel['csv_file'], nrows=1)
            columns = df.columns.tolist()
            
            self.x_col_combo.set_completion_list(columns)
            self.y_col_combo.set_completion_list(columns)
            self.z_col_combo.set_completion_list(columns)
            
            self.x_col_var.set(channel['x_column'])
            self.y_col_var.set(channel['y_column'])
            self.z_col_var.set(channel['z_column'])
        except Exception as e:
            self.log_status(f"⚠️ Error loading CSV columns: {str(e)}")
        
        self.veh_x_var.set(channel['vehicle_x_channel'])
        self.veh_y_var.set(channel['vehicle_y_channel'])
        self.units_var.set(channel['units'])
        self.comment_var.set(channel['comment'])
        
        # Remove the channel (will be re-added when user clicks Add)
        del self.custom_channels[channel_index]
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
            # Find and remove the channel
            for i, channel in enumerate(self.custom_channels):
                if channel['name'] == channel_name:
                    del self.custom_channels[i]
                    break
            
            self.update_channels_display()
            self.log_status(f"🗑️ Deleted channel: {channel_name}")
    
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
        for channel in self.custom_channels:
            if channel['name'] == channel_name:
                # Create a copy with modified name
                new_channel = channel.copy()
                new_channel['name'] = f"{channel['name']}_copy"
                
                # Ensure unique name
                counter = 1
                while any(ch['name'] == new_channel['name'] for ch in self.custom_channels):
                    new_channel['name'] = f"{channel['name']}_copy_{counter}"
                    counter += 1
                
                self.custom_channels.append(new_channel)
                self.update_channels_display()
                self.log_status(f"📋 Duplicated channel: {channel_name} → {new_channel['name']}")
                break
    
    def export_channel_config(self):
        """Export channel configuration to JSON."""
        if not self.custom_channels:
            messagebox.showwarning("Warning", "No channels to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Channel Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                config = {
                    'channels': self.custom_channels,
                    'exported_at': datetime.now().isoformat(),
                    'total_channels': len(self.custom_channels)
                }
                
                with open(file_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                self.log_status(f"📤 Channel configuration exported: {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration: {str(e)}")
    
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
            print(f"Interpolation error: {e}")
            return np.nan
    
    def analyze_channel_sampling_rates(self):
        """Analyze sampling rates of all channels used in custom channel configurations."""
        if not self.vehicle_data or not self.custom_channels:
            return {}
        
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        channel_analysis = {}
        
        # Get all unique channels used in custom configurations
        used_channels = set()
        for config in self.custom_channels:
            used_channels.add(config['vehicle_x_channel'])
            used_channels.add(config['vehicle_y_channel'])
        
        try:
            if file_ext in ['.mdf', '.mf4', '.dat']:
                for channel_name in used_channels:
                    try:
                        # Get channel info without raster to see original sampling
                        signal = self.vehicle_data.get(channel_name)
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
                    if channel_name in self.vehicle_data.columns:
                        channel_analysis[channel_name] = {
                            'sample_count': len(self.vehicle_data),
                            'note': 'CSV file - no timing information available'
                        }
                    else:
                        channel_analysis[channel_name] = {
                            'error': 'Channel not found in CSV'
                        }
        except Exception as e:
            self.log_status(f"❌ Error analyzing channel sampling rates: {str(e)}")
        
        return channel_analysis
    
    def ask_for_raster(self):
        """Ask user for raster value for resampling MDF files with detailed channel analysis."""
        # Create raster dialog
        raster_dialog = ctk.CTkToplevel(self.root)
        raster_dialog.title('🎯 Set Time Raster - Advanced Analysis')
        raster_dialog.geometry('900x800')
        raster_dialog.transient(self.root)
        raster_dialog.grab_set()
        raster_dialog.resizable(True, True)
        raster_dialog.minsize(800, 650)
        
        # Center dialog
        raster_dialog.update_idletasks()
        x = (raster_dialog.winfo_screenwidth() // 2) - 450
        y = (raster_dialog.winfo_screenheight() // 2) - 400
        raster_dialog.geometry(f"900x800+{x}+{y}")
        
        main_frame = ctk.CTkFrame(raster_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text="🎯 Time Raster Configuration with Channel Analysis",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Analyze channels first
        self.log_status("🔍 Analyzing channel sampling rates...")
        channel_analysis = self.analyze_channel_sampling_rates()
        
        # Calculate overall minimum raster
        overall_min_raster = 0.001  # Default fallback
        limiting_channel = "Unknown"
        
        if channel_analysis:
            min_rasters = []
            for ch_name, analysis in channel_analysis.items():
                if 'suggested_min_raster' in analysis:
                    min_rasters.append(analysis['suggested_min_raster'])
                    if analysis['suggested_min_raster'] == max(min_rasters):
                        limiting_channel = ch_name
            if min_rasters:
                overall_min_raster = max(min_rasters)
        
        # Info frame with better layout
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=(0, 15))
        
        info_text = ctk.CTkLabel(
            info_frame,
            text="The vehicle channels may have different sampling rates.\n"
                 "Specify a time raster (in seconds) to resample all signals to the same time base.\n"
                 "Lower rasters provide finer resolution but require interpolation if original data is coarser.",
            font=ctk.CTkFont(size=11),
            justify="left"
        )
        info_text.pack(padx=15, pady=10)
        
        # Minimum raster warning frame
        warning_frame = ctk.CTkFrame(main_frame)
        warning_frame.pack(fill="x", pady=(0, 15))
        
        warning_label = ctk.CTkLabel(
            warning_frame,
            text=f"⚠️ Recommended minimum raster: {overall_min_raster:.6f} seconds ({overall_min_raster*1000:.2f} ms)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ff6b35"
        )
        warning_label.pack(padx=15, pady=(10, 5))
        
        limiting_label = ctk.CTkLabel(
            warning_frame,
            text=f"Limiting channel: {limiting_channel}",
            font=ctk.CTkFont(size=11),
            text_color="#ff9500"
        )
        limiting_label.pack(padx=15, pady=(0, 10))
        
        # Channel analysis table - collapsible
        analysis_frame = ctk.CTkFrame(main_frame)
        analysis_frame.pack(fill="x", pady=(0, 15))
        
        # Toggle button for analysis table
        analysis_header = ctk.CTkFrame(analysis_frame)
        analysis_header.pack(fill="x", padx=15, pady=(10, 5))
        
        analysis_title = ctk.CTkLabel(
            analysis_header,
            text="📊 Per-Channel Analysis",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        analysis_title.pack(side="left")
        
        # Toggle button
        analysis_expanded = ctk.BooleanVar(value=False)
        toggle_analysis_btn = ctk.CTkButton(
            analysis_header,
            text="▼ Show Details",
            command=lambda: toggle_analysis_table(),
            width=120,
            height=25,
            font=ctk.CTkFont(size=11)
        )
        toggle_analysis_btn.pack(side="right")
        
        # Analysis table container (initially hidden)
        analysis_table_container = ctk.CTkFrame(analysis_frame)
        # Don't pack initially - will be shown when button is clicked
        
        def toggle_analysis_table():
            if analysis_expanded.get():
                # Hide table
                analysis_table_container.pack_forget()
                toggle_analysis_btn.configure(text="▼ Show Details")
                analysis_expanded.set(False)
                analysis_frame.configure(height=50)
            else:
                # Show table
                analysis_table_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
                toggle_analysis_btn.configure(text="▲ Hide Details")
                analysis_expanded.set(True)
                analysis_frame.pack_configure(fill="both", expand=True)
        
        # Create treeview for channel analysis
        import tkinter.ttk as ttk
        analysis_tree_frame = ctk.CTkFrame(analysis_table_container)
        analysis_tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        columns = ("Channel", "Min Interval", "Avg Interval", "Suggested Min Raster", "Samples", "Status")
        analysis_tree = ttk.Treeview(analysis_tree_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        for col in columns:
            analysis_tree.heading(col, text=col)
            analysis_tree.column(col, width=120)
        
        # Populate tree with color indicators
        for ch_name, analysis in channel_analysis.items():
            if 'error' in analysis:
                # Red for errors
                analysis_tree.insert("", "end", values=(
                    ch_name, "Error", "Error", "Error", "Error", "❌ " + analysis['error']
                ), tags=("error",))
            elif 'note' in analysis:
                # Yellow for CSV files
                analysis_tree.insert("", "end", values=(
                    ch_name, "N/A", "N/A", "N/A", analysis.get('sample_count', 'N/A'), "⚠️ " + analysis['note']
                ), tags=("warning",))
            else:
                # Green for good channels
                status = "✅ Good"
                if analysis.get('suggested_min_raster', 0) > 0.01:  # Above 10ms might be concerning
                    status = "⚠️ Low rate"
                
                analysis_tree.insert("", "end", values=(
                    ch_name,
                    f"{analysis['min_interval']:.6f}s",
                    f"{analysis['avg_interval']:.6f}s", 
                    f"{analysis['suggested_min_raster']:.6f}s",
                    analysis['sample_count'],
                    status
                ), tags=("good",))
        
        # Configure row colors with better contrast
        analysis_tree.tag_configure("error", background="#ffcccc", foreground="#000000")
        analysis_tree.tag_configure("warning", background="#ffeaa7", foreground="#2d3436")  
        analysis_tree.tag_configure("good", background="#d4edda", foreground="#000000")
        
        # Add scrollbar
        tree_scroll = ttk.Scrollbar(analysis_tree_frame, orient="vertical", command=analysis_tree.yview)
        analysis_tree.configure(yscrollcommand=tree_scroll.set)
        
        analysis_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        # Input section
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", pady=(0, 15))
        
        input_label = ctk.CTkLabel(
            input_frame,
            text="Enter raster value (seconds):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        input_label.pack(pady=(10, 5))
        
        raster_var = ctk.StringVar(value=str(overall_min_raster))
        raster_entry = ctk.CTkEntry(
            input_frame,
            textvariable=raster_var,
            placeholder_text="Enter raster in seconds",
            font=ctk.CTkFont(size=12),
            width=200
        )
        raster_entry.pack(pady=(0, 10))
        
        # Status label for live feedback
        status_label = ctk.CTkLabel(
            input_frame,
            text="✅ Good choice - within recommended range.",
            font=ctk.CTkFont(size=10),
            text_color="#28a745"
        )
        status_label.pack(pady=(0, 10))
        
        def update_status():
            try:
                value = float(raster_var.get())
                if value < overall_min_raster:
                    status_label.configure(text=f"⚠️ Below recommended minimum ({overall_min_raster:.6f}s). Interpolation will be used.", 
                                         text_color="#ff6b35")
                elif value > overall_min_raster * 10:
                    status_label.configure(text="⚠️ Very large raster - may lose detail.", 
                                         text_color="#ff9500")
                else:
                    status_label.configure(text="✅ Good choice - within recommended range.", 
                                         text_color="#28a745")
            except ValueError:
                status_label.configure(text="❌ Invalid number format.", 
                                     text_color="#dc3545")
        
        raster_var.trace('w', lambda *args: update_status())
        
        # Quick selection buttons
        quick_frame = ctk.CTkFrame(main_frame)
        quick_frame.pack(fill="x", pady=(0, 15))
        
        quick_label = ctk.CTkLabel(
            quick_frame,
            text="⚡ Quick Selection:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        quick_label.pack(pady=(10, 5))
        
        button_container = ctk.CTkFrame(quick_frame)
        button_container.pack(pady=(0, 10))
        
        # Suggested values with color coding
        suggested_values = [
            (overall_min_raster, "Recommended", "#28a745"),
            (0.001, "1ms", "#17a2b8" if 0.001 >= overall_min_raster else "#ffc107"),
            (0.01, "10ms", "#17a2b8" if 0.01 >= overall_min_raster else "#ffc107"),
            (0.02, "20ms", "#17a2b8" if 0.02 >= overall_min_raster else "#ffc107"),
            (0.05, "50ms", "#17a2b8" if 0.05 >= overall_min_raster else "#ffc107"),
            (0.1, "100ms", "#17a2b8" if 0.1 >= overall_min_raster else "#ffc107")
        ]
        
        for value, label, color in suggested_values:
            btn = ctk.CTkButton(
                button_container,
                text=f"{label}\n({value}s)",
                command=lambda v=value: raster_var.set(str(v)),
                width=80,
                height=40,
                font=ctk.CTkFont(size=10),
                fg_color=color
            )
            btn.pack(side="left", padx=3, pady=5)
        
        result = [None]
        
        def confirm_raster():
            try:
                raster_value = float(raster_var.get())
                if raster_value <= 0:
                    messagebox.showerror('Error', 'Raster value must be positive!')
                    return
                result[0] = raster_value
                raster_dialog.destroy()
            except ValueError:
                messagebox.showerror('Error', 'Please enter a valid number!')
        
        def cancel_raster():
            result[0] = None
            raster_dialog.destroy()
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=15)
        
        ok_btn = ctk.CTkButton(
            button_frame,
            text='✅ OK',
            command=confirm_raster,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=100,
            height=35
        )
        ok_btn.pack(side='left', padx=10)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text='❌ Cancel',
            command=cancel_raster,
            width=100,
            height=35
        )
        cancel_btn.pack(side='left', padx=10)
        
        raster_entry.focus()
        raster_dialog.wait_window()
        return result[0]
    
    def get_interpolated_signal_data(self, channel_name, target_raster):
        """Get signal data with interpolation if needed for target raster."""
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        
        if file_ext == '.csv':
            # For CSV files, just return the data as-is
            data = pd.to_numeric(self.vehicle_data[channel_name], errors='coerce')
            timestamps = np.arange(len(data), dtype=np.float64) * target_raster
            return data.values, timestamps
        
        # For MDF files, try to get data at target raster first
        try:
            signal = self.vehicle_data.get(channel_name, raster=target_raster)
            if signal is not None and len(signal.samples) > 0:
                self.log_status(f"✅ Direct raster extraction successful for {channel_name}: {len(signal.samples)} samples")
                return signal.samples, signal.timestamps
        except Exception as e:
            # If raster-based extraction fails, fall back to interpolation
            self.log_status(f"⚠️ Direct raster extraction failed for {channel_name}, using interpolation: {str(e)}")
            pass
        
        # Fallback: get original signal and interpolate
        try:
            original_signal = self.vehicle_data.get(channel_name)
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
            
            self.log_status(f"🔄 Interpolated {channel_name}: {len(original_signal.samples)} -> {len(interpolated_samples)} samples")
            return interpolated_samples, target_timestamps
            
        except Exception as e:
            raise Exception(f"Failed to get data for {channel_name}: {str(e)}")
    
    def process_all_channels(self):
        """Process all configured custom channels."""
        if not self.vehicle_data:
            messagebox.showerror("Error", "Please select a vehicle file first!")
            return
            
        if not self.custom_channels:
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
            for i, channel_config in enumerate(self.custom_channels):
                self.log_status(f"⚙️ Processing channel {i+1}/{len(self.custom_channels)}: {channel_config['name']}")
                
                # Load surface table
                try:
                    x_values, y_values, z_matrix = self.load_surface_table(
                        channel_config['csv_file'],
                        channel_config['x_column'],
                        channel_config['y_column'], 
                        channel_config['z_column']
                    )
                    self.log_status(f"✅ Surface table loaded for {channel_config['name']}")
                except Exception as e:
                    self.log_status(f"❌ Error loading surface table for {channel_config['name']}: {str(e)}")
                    continue
                
                # Extract vehicle data with interpolation support
                try:
                    if file_ext == '.csv':
                        x_data = pd.to_numeric(self.vehicle_data[channel_config['vehicle_x_channel']], errors='coerce')
                        y_data = pd.to_numeric(self.vehicle_data[channel_config['vehicle_y_channel']], errors='coerce')
                        timestamps = np.arange(len(x_data), dtype=np.float64) * (raster or 0.01)
                    else:  # MDF files
                        # Use interpolation-capable method
                        x_data, x_timestamps = self.get_interpolated_signal_data(channel_config['vehicle_x_channel'], raster)
                        y_data, y_timestamps = self.get_interpolated_signal_data(channel_config['vehicle_y_channel'], raster)
                        
                        # Align timestamps - use the shorter range
                        min_length = min(len(x_data), len(y_data))
                        x_data = x_data[:min_length]
                        y_data = y_data[:min_length]
                        timestamps = x_timestamps[:min_length]
                        
                        if len(x_data) != len(y_data):
                            raise Exception(f"Channel length mismatch after interpolation: {len(x_data)} vs {len(y_data)}")
                        
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
                            z_val = self.interpolate_z_value(x_val, y_val, x_values, y_values, z_matrix)
                            z_interpolated.append(z_val)
                            if not np.isnan(z_val):
                                valid_points += 1
                        else:
                            z_interpolated.append(np.nan)
                    
                    self.log_status(f"✅ Interpolated {valid_points}/{len(z_interpolated)} valid points for {channel_config['name']}")
                    
                    # Create signal for MDF output
                    if self.output_format_var.get() == "mf4" and file_ext != '.csv':
                        # Generate comment with all variables used
                        csv_filename = os.path.basename(channel_config['csv_file'])
                        final_comment = (
                            f"Channel generated from CSV surface table '{csv_filename}' "
                            f"using X-axis: {channel_config['x_column']} (vehicle: {channel_config['vehicle_x_channel']}), "
                            f"Y-axis: {channel_config['y_column']} (vehicle: {channel_config['vehicle_y_channel']}), "
                            f"Z-values: {channel_config['z_column']}."
                        )
                        
                        # Add user comment if provided
                        if channel_config['comment'].strip():
                            final_comment += f" User comment: {channel_config['comment']}"
                        
                        signal = Signal(
                            samples=np.array(z_interpolated, dtype=np.float64),
                            timestamps=timestamps,
                            name=channel_config['name'],
                            unit=channel_config['units'],
                            comment=final_comment
                        )
                        calculated_signals.append(signal)
                    
                    # Store for CSV output
                    if file_ext == '.csv' or self.output_format_var.get() == "csv":
                        if file_ext == '.csv':
                            # Add to existing dataframe
                            self.vehicle_data[channel_config['name']] = z_interpolated
                        else:
                            # Create new dataframe for CSV export
                            if not hasattr(self, 'csv_export_data'):
                                self.csv_export_data = pd.DataFrame()
                                self.csv_export_data['Time'] = timestamps
                            self.csv_export_data[channel_config['name']] = z_interpolated
                            
                except Exception as e:
                    self.log_status(f"❌ Error interpolating {channel_config['name']}: {str(e)}")
                    continue
            
            # Save output
            self.save_output(calculated_signals, file_ext)
            
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
            self.log_status(f"❌ Processing error: {str(e)}")
    
    def save_output(self, calculated_signals, original_file_ext):
        """Save the output in the selected format."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(self.vehicle_file_path).stem
        output_dir = Path(self.vehicle_file_path).parent
        
        try:
            if self.output_format_var.get() == "mf4" and original_file_ext != '.csv':
                # Save as MF4 with calculated channels only
                output_path = output_dir / f"{base_name}_calculated_channels_{timestamp}.mf4"
                
                with MDF() as new_mdf:
                    if calculated_signals:
                        new_mdf.append(calculated_signals, comment="Calculated channels from surface table interpolation")
                        new_mdf.save(output_path, overwrite=True)
                        self.log_status(f"✅ MF4 file saved: {output_path}")
                    else:
                        self.log_status("❌ No calculated signals to save")
                        
            if self.output_format_var.get() == "csv" or original_file_ext == '.csv':
                # Save as CSV
                output_path = output_dir / f"{base_name}_with_calculated_channels_{timestamp}.csv"
                
                if original_file_ext == '.csv':
                    # Save updated original dataframe
                    self.vehicle_data.to_csv(output_path, index=False)
                else:
                    # Save calculated channels dataframe
                    if hasattr(self, 'csv_export_data'):
                        self.csv_export_data.to_csv(output_path, index=False)
                    
                self.log_status(f"✅ CSV file saved: {output_path}")
                
            messagebox.showinfo("Success", f"Processing completed successfully!\nCreated {len(calculated_signals)} calculated channels.")
            
        except Exception as e:
            self.log_status(f"❌ Error saving output: {str(e)}")
            raise
    
    def save_settings(self):
        """Auto-save current settings to default file."""
        try:
            settings = self.get_all_settings()
            with open('channel_appender_settings_modern.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.log_status(f"❌ Error auto-saving settings: {str(e)}")
    
    def load_settings_on_startup(self):
        """Load settings from default file on startup."""
        try:
            if os.path.exists('channel_appender_settings_modern.json'):
                with open('channel_appender_settings_modern.json', 'r') as f:
                    settings = json.load(f)
                self.restore_settings(settings)
                self.log_status("✅ Previous settings loaded automatically")
        except Exception as e:
            self.log_status(f"⚠️ Could not load previous settings: {str(e)}")
    
    def save_settings_as(self):
        """Save settings to a new file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        num_channels = len(self.custom_channels)
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
            try:
                settings = self.get_all_settings()
                settings['description'] = f"Settings saved on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} with {num_channels} custom channels"
                
                with open(file_path, 'w') as f:
                    json.dump(settings, f, indent=2)
                self.log_status(f"✅ Settings saved to {os.path.basename(file_path)}")
                messagebox.showinfo("Settings Saved", f"Settings saved successfully to:\n{os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
                self.log_status(f"❌ Error saving settings: {str(e)}")
    
    def load_settings_from(self):
        """Load settings from a file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Settings From"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    settings = json.load(f)
                
                # Show preview of what will be loaded
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
                    self.log_status(f"✅ Settings loaded from {os.path.basename(file_path)}")
                    messagebox.showinfo("Settings Loaded", f"Settings loaded successfully!\n{num_channels} custom channels restored.")
                else:
                    self.log_status("⚠️ Settings load cancelled by user")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
                self.log_status(f"❌ Error loading settings: {str(e)}")
    
    def quick_save_settings(self, slot):
        """Quick save settings to a numbered slot."""
        try:
            settings = self.get_all_settings()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            num_channels = len(self.custom_channels)
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            
            settings['description'] = f"Quick save slot {slot} ({slot_name}) - {timestamp} ({num_channels} channels)"
            settings['slot_name'] = slot_name
            
            filename = f"quick_save_slot_{slot}_modern.json"
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.log_status(f"✅ Quick saved to slot {slot} ({slot_name}): {num_channels} channels")
            
        except Exception as e:
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            self.log_status(f"❌ Error quick saving to slot {slot} ({slot_name}): {str(e)}")
    
    def quick_load_settings(self, slot):
        """Quick load settings from a numbered slot."""
        filename = f"quick_save_slot_{slot}_modern.json"
        
        if not os.path.exists(filename):
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            self.log_status(f"⚠️ Quick save slot {slot} ({slot_name}) is empty")
            return
        
        try:
            with open(filename, 'r') as f:
                settings = json.load(f)
            
            num_channels = len(settings.get('custom_channels', []))
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            
            # Quick load without confirmation for faster workflow
            self.restore_settings(settings)
            self.log_status(f"✅ Quick loaded from slot {slot} ({slot_name}): {num_channels} channels")
            
        except Exception as e:
            slot_name = self.slot_names.get(slot, f"Slot {slot}")
            self.log_status(f"❌ Error quick loading from slot {slot} ({slot_name}): {str(e)}")
    
    def update_slot_name(self, slot, event):
        """Update slot name when entry is modified."""
        new_name = self.slot_name_entries[slot].get().strip()
        if new_name:
            self.slot_names[slot] = new_name
        else:
            self.slot_names[slot] = f"Slot {slot}"
    
    def rename_slot_dialog(self, slot):
        """Open dialog to rename a slot."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Rename Slot {slot}")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create layout
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Label
        label = ctk.CTkLabel(
            main_frame,
            text=f"Enter new name for Slot {slot}:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        label.pack(pady=(0, 10))
        
        # Entry
        name_var = ctk.StringVar(value=self.slot_names[slot])
        entry = ctk.CTkEntry(
            main_frame,
            textvariable=name_var,
            width=200,
            font=ctk.CTkFont(size=11)
        )
        entry.pack(pady=(0, 15))
        entry.focus()
        entry.select_range(0, 'end')
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack()
        
        def confirm():
            new_name = name_var.get().strip()
            if new_name:
                self.slot_names[slot] = new_name
                self.slot_name_entries[slot].delete(0, 'end')
                self.slot_name_entries[slot].insert(0, new_name)
                self.log_status(f"✅ Renamed slot {slot} to '{new_name}'")
            dialog.destroy()
        
        def cancel():
            dialog.destroy()
        
        ok_btn = ctk.CTkButton(
            button_frame,
            text="OK",
            command=confirm,
            width=60
        )
        ok_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=cancel,
            width=60
        )
        cancel_btn.pack(side="left", padx=5)
        
        # Bind Enter key
        entry.bind('<Return>', lambda e: confirm())
    
    def get_all_settings(self):
        """Get all current settings in a single dictionary."""
        return {
            'vehicle_file': self.vehicle_file_path,
            'custom_channels': self.custom_channels,
            'output_format': self.output_format_var.get(),
            'theme': self.theme_menu.get(),
            'slot_names': self.slot_names,
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
            },
            'saved_at': datetime.now().isoformat()
        }
    
    def restore_settings(self, settings):
        """Restore settings from dictionary."""
        try:
            # Restore custom channels
            if 'custom_channels' in settings:
                self.custom_channels = settings['custom_channels']
                self.update_channels_display()
            
            # Restore output format
            if 'output_format' in settings:
                self.output_format_var.set(settings['output_format'])
            
            # Restore theme
            if 'theme' in settings:
                self.theme_menu.set(settings['theme'])
                self.change_theme(settings['theme'])
            
            # Restore slot names
            if 'slot_names' in settings:
                self.slot_names.update(settings['slot_names'])
                for slot, name in self.slot_names.items():
                    if slot in self.slot_name_entries:
                        self.slot_name_entries[slot].delete(0, 'end')
                        self.slot_name_entries[slot].insert(0, name)
            
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
                
                # If CSV file exists, load its columns
                csv_file = form.get('csv_file', '')
                if csv_file and os.path.exists(csv_file):
                    try:
                        df = pd.read_csv(csv_file, nrows=1)
                        columns = df.columns.tolist()
                        self.x_col_combo.set_completion_list(columns)
                        self.y_col_combo.set_completion_list(columns)
                        self.z_col_combo.set_completion_list(columns)
                    except Exception as e:
                        self.log_status(f"⚠️ Could not reload CSV columns: {str(e)}")
            
            # Restore vehicle file if it exists
            if 'vehicle_file' in settings and settings['vehicle_file']:
                if os.path.exists(settings['vehicle_file']):
                    self.vehicle_file_path = settings['vehicle_file']
                    filename = os.path.basename(self.vehicle_file_path)
                    self.file_status_label.configure(text=f"📁 {filename}")
                    try:
                        self.load_vehicle_file()
                    except Exception as e:
                        self.log_status(f"⚠️ Could not reload vehicle file: {str(e)}")
                        
        except Exception as e:
            self.log_status(f"❌ Error restoring settings: {str(e)}")
    
    def clear_status_log(self):
        """Clear the status log."""
        self.status_text.delete("1.0", "end")
        self.log_status("🧹 Status log cleared.")
    
    def log_status(self, message):
        """Add a message to the status log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.status_text.insert("end", formatted_message)
        self.status_text.see("end")
    
    def on_closing(self):
        """Handle application closing with save options."""
        num_channels = len(self.custom_channels)
        
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
        app = VehicleLogChannelAppenderModern()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {e}")
        input("Press Enter to continue...")


if __name__ == "__main__":
    main()