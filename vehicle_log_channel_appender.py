"""
Vehicle Log Channel Appender - Multi-Channel Tool

Enhanced Version with Advanced Raster Analysis and Interpolation

Key Features:
- Analyzes channel sampling rates and recommends minimum rasters
- Shows per-channel analysis with limiting parameters
- Implements linear interpolation for fine rasters below original data resolution
- Enhanced raster selection dialog with warnings and recommendations
- Supports processing at any raster by interpolating missing data points

Recent Improvements:
- Fixed issue where lower rasters wouldn't generate channels
- Added automatic interpolation when target raster is finer than source data
- Enhanced raster dialog shows recommended minimum and per-channel analysis
- Better error handling and user feedback during processing
- Fixed scrollbar alignment in Custom Channels table
- Added search functionality for table variables
- Added column filters for better data management
- Preserved form settings after adding channels for faster workflow
- Enhanced settings management with user-defined save/load options
"""

import numpy as np
import pandas as pd
from asammdf import MDF, Signal
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from scipy.interpolate import griddata, interp1d
import tempfile
import shutil
from pathlib import Path
import json
from datetime import datetime


class AutocompleteCombobox(ttk.Combobox):
    """A Combobox with autocompletion support."""
    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=str.lower)
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self['values'] = self._completion_list
        self.bind('<KeyRelease>', self.handle_keyrelease)

    def autocomplete(self, delta=0):
        if delta:
            self.delete(self.position, tk.END)
        else:
            self.position = len(self.get())

        _hits = []
        for element in self._completion_list:
            if element.lower().startswith(self.get().lower()):
                _hits.append(element)

        if _hits != self._hits:
            self._hit_index = 0
            self._hits = _hits

        if self._hits:
            self.delete(0, tk.END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(self.position, tk.END)

    def handle_keyrelease(self, event):
        if event.keysym == "BackSpace":
            self.position = self.index(tk.END)
        if event.keysym == "Left":
            self.position -= 1
        if event.keysym == "Right":
            self.position = self.index(tk.END)
        if len(event.keysym) == 1:
            self.autocomplete()


class VehicleLogChannelAppender:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vehicle Log Channel Appender - Multi-Channel Tool")
        
        # Set modern styling and responsive window sizing
        self.setup_modern_styling()
        self.setup_responsive_window()
        
        # Data storage
        self.vehicle_file_path = None
        self.vehicle_data = None
        self.available_channels = []
        self.custom_channels = []  # List of custom channel configurations
        self.reference_timestamps = None
        
        # Search and filter variables
        self.search_var = tk.StringVar()
        self.filter_vars = {}
        self.all_custom_channels = []  # Store all channels for filtering
        
        # Tooltip window reference
        self.tooltip_window = None
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_modern_styling(self):
        """Setup modern color scheme and styling"""
        # Modern color palette
        self.colors = {
            'primary': '#2E86AB',      # Blue
            'secondary': '#A23B72',    # Purple  
            'success': '#43AA8B',      # Green
            'warning': '#F18F01',      # Orange
            'danger': '#C73E1D',       # Red
            'light': '#F8F9FA',        # Light gray
            'dark': '#343A40',         # Dark gray
            'white': '#FFFFFF',
            'background': '#F5F5F5',   # Light background
            'card': '#FFFFFF',         # Card background
            'border': '#DEE2E6'        # Border color
        }
        
        # Configure ttk styles for modern look
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure modern notebook style
        style.configure('Modern.TNotebook', background=self.colors['background'])
        style.configure('Modern.TNotebook.Tab', 
                       padding=[20, 12], 
                       font=('Segoe UI', 11, 'bold'))
        
        # Configure modern frame style
        style.configure('Modern.TFrame', background=self.colors['card'])
        
        # Set root window styling
        self.root.configure(bg=self.colors['background'])
    
    def setup_responsive_window(self):
        """Setup responsive window with proper constraints"""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate responsive window size (80% of screen, but with limits)
        min_width, min_height = 1000, 700
        max_width, max_height = 1600, 1200
        
        window_width = max(min_width, min(max_width, int(screen_width * 0.8)))
        window_height = max(min_height, min(max_height, int(screen_height * 0.8)))
        
        # Center window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(min_width, min_height)
        self.root.maxsize(max_width, max_height)
        
        # Allow window to be resizable
        self.root.resizable(True, True)
        
        # Configure grid weight for responsive behavior
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
    def setup_ui(self):
        """Setup the user interface with modern tabbed layout"""
        
        # Create main container with padding
        main_container = tk.Frame(self.root, bg=self.colors['background'])
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Modern title with better styling
        title_frame = tk.Frame(main_container, bg=self.colors['background'])
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_label = tk.Label(title_frame, 
                              text="🚗 Vehicle Log Channel Appender", 
                              font=("Segoe UI", 20, "bold"),
                              fg=self.colors['dark'],
                              bg=self.colors['background'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, 
                                 text="Multi-Channel Analysis Tool with Surface Table Interpolation", 
                                 font=("Segoe UI", 11),
                                 fg=self.colors['secondary'],
                                 bg=self.colors['background'])
        subtitle_label.pack(pady=(5, 0))
        
        # Create modern notebook for tabs
        self.notebook = ttk.Notebook(main_container, style='Modern.TNotebook')
        self.notebook.pack(fill="both", expand=True, pady=(0, 15))
        
        # Setup tabs
        self.setup_processing_tab()
        self.setup_custom_channels_tab()
        
        # Modern Status/Log area
        log_frame = tk.LabelFrame(main_container, 
                                 text="📊 Status Log", 
                                 font=("Segoe UI", 12, "bold"),
                                 fg=self.colors['dark'],
                                 bg=self.colors['background'],
                                 bd=2,
                                 relief="groove")
        log_frame.pack(fill="x", pady=(0, 15))
        
        # Create scrollable text widget with modern styling
        text_frame = tk.Frame(log_frame, bg=self.colors['card'])
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.log_text = tk.Text(text_frame, 
                               height=6, 
                               wrap=tk.WORD,
                               font=("Segoe UI", 10),
                               bg=self.colors['white'],
                               fg=self.colors['dark'],
                               bd=1,
                               relief="solid",
                               selectbackground=self.colors['primary'],
                               selectforeground=self.colors['white'])
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Modern Settings section
        settings_frame = tk.Frame(main_container, bg=self.colors['background'])
        settings_frame.pack(fill="x", pady=(0, 10))
        
        # Create card-style container for settings
        settings_card = tk.Frame(settings_frame, 
                                bg=self.colors['card'],
                                bd=1,
                                relief="solid")
        settings_card.pack(fill="x", padx=5, pady=5)
        
        # Auto-save status with modern styling
        status_frame = tk.Frame(settings_card, bg=self.colors['card'])
        status_frame.pack(side="left", fill="x", expand=True, padx=15, pady=10)
        
        tk.Label(status_frame, 
                text="🔄 Auto-save: ON", 
                font=("Segoe UI", 10, "bold"), 
                fg=self.colors['success'],
                bg=self.colors['card']).pack(side="left", padx=5)
        tk.Label(status_frame, 
                text="●", 
                font=("Segoe UI", 14), 
                fg=self.colors['success'],
                bg=self.colors['card']).pack(side="left")
        
        # Main settings buttons with modern styling
        main_settings_frame = tk.Frame(settings_card, bg=self.colors['card'])
        main_settings_frame.pack(side="right", padx=15, pady=10)
        
        self.create_modern_button(main_settings_frame, 
                                 "💾 Save Settings As...", 
                                 self.save_settings_as, 
                                 self.colors['success']).pack(side="left", padx=3)
        self.create_modern_button(main_settings_frame, 
                                 "📁 Load Settings From...", 
                                 self.load_settings_from, 
                                                                   self.colors['primary']).pack(side="left", padx=3)
        
        # Modern Quick save/load section
        quick_frame = tk.Frame(settings_card, bg=self.colors['card'])
        quick_frame.pack(side="right", padx=(15, 15), pady=10)
        
        tk.Label(quick_frame, 
                text="⚡ Quick:", 
                font=("Segoe UI", 10, "bold"),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left", padx=(0, 10))
        
        # Store references to quick save/load buttons for updating indicators
        self.quick_save_buttons = {}
        self.quick_load_buttons = {}
        
        # Quick save slots (1-3) with modern styling
        for i in range(1, 4):
            btn_frame = tk.Frame(quick_frame, bg=self.colors['card'])
            btn_frame.pack(side="left", padx=3)
            
            # Check if slot has data
            slot_has_data = os.path.exists(f"quick_save_slot_{i}.json")
            save_color = self.colors['success'] if not slot_has_data else self.colors['warning']
            load_color = self.colors['primary'] if slot_has_data else self.colors['light']
            
            # Save button with modern styling
            save_btn = self.create_mini_button(btn_frame, f"S{i}", 
                                             lambda slot=i: self.quick_save_settings(slot), 
                                             save_color)
            save_btn.pack(side="top", pady=1)
            self.quick_save_buttons[i] = save_btn
            
            # Load button with modern styling
            load_btn = self.create_mini_button(btn_frame, f"L{i}", 
                                             lambda slot=i: self.quick_load_settings(slot), 
                                             load_color)
            load_btn.pack(side="top", pady=1)
            self.quick_load_buttons[i] = load_btn
            
            # Add tooltip effect on hover
            self.add_slot_tooltip(save_btn, load_btn, i)
        
        # Reset button with modern styling
        self.create_modern_button(main_settings_frame, 
                                 "🔄 Reset", 
                                 self.reset_to_defaults, 
                                 self.colors['warning']).pack(side="left", padx=3)
        
        self.log_status("🚀 Application started. Please select a vehicle file and configure custom channels.")

    def create_modern_button(self, parent, text, command, bg_color, width=None, height=None):
        """Create a modern styled button"""
        return tk.Button(parent,
                        text=text,
                        command=command,
                        bg=bg_color,
                        fg=self.colors['white'],
                        font=("Segoe UI", 10, "bold"),
                        relief="flat",
                        bd=0,
                        padx=15,
                        pady=8,
                        cursor="hand2",
                        activebackground=self.darken_color(bg_color),
                        activeforeground=self.colors['white'],
                        width=width,
                        height=height)
    
    def create_mini_button(self, parent, text, command, bg_color):
        """Create a small modern styled button for quick actions"""
        return tk.Button(parent,
                        text=text,
                        command=command,
                        bg=bg_color,
                        fg=self.colors['white'],
                        font=("Segoe UI", 8, "bold"),
                        relief="flat",
                        bd=0,
                        width=3,
                        height=1,
                        cursor="hand2",
                        activebackground=self.darken_color(bg_color),
                        activeforeground=self.colors['white'])
    
    def darken_color(self, color):
        """Darken a hex color by 20% for hover effects"""
        # Simple darkening - remove the # and convert to RGB
        if color.startswith('#'):
            color = color[1:]
        
        # Convert hex to RGB
        r = int(color[0:2], 16)
        g = int(color[2:4], 16) 
        b = int(color[4:6], 16)
        
        # Darken by 20%
        r = int(r * 0.8)
        g = int(g * 0.8)
        b = int(b * 0.8)
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def setup_processing_tab(self):
        """Setup the main processing tab with modern styling"""
        self.processing_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(self.processing_frame, text="🔧 Processing")
        
        # Create scrollable container for the processing tab
        canvas = tk.Canvas(self.processing_frame, bg=self.colors['background'])
        scrollbar = ttk.Scrollbar(self.processing_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['background'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Vehicle file selection with modern card design
        file_card = tk.LabelFrame(scrollable_frame, 
                                 text="📁 Vehicle Log File", 
                                 font=("Segoe UI", 14, "bold"),
                                 fg=self.colors['dark'],
                                 bg=self.colors['card'],
                                 bd=2,
                                 relief="groove")
        file_card.pack(fill="x", padx=25, pady=15)
        
        vehicle_btn_frame = tk.Frame(file_card, bg=self.colors['card'])
        vehicle_btn_frame.pack(fill="x", padx=20, pady=20)
        
        # Modern file selection button
        self.vehicle_btn = self.create_modern_button(vehicle_btn_frame, 
                                                    "📂 Select Vehicle File (MDF/MF4/DAT/CSV)", 
                                                    self.select_vehicle_file, 
                                                    self.colors['primary'],
                                                    width=35)
        self.vehicle_btn.pack(anchor="w")
        
        # Status label with modern styling
        status_frame = tk.Frame(vehicle_btn_frame, bg=self.colors['card'])
        status_frame.pack(fill="x", pady=(15, 0))
        
        self.vehicle_status = tk.Label(status_frame, 
                                      text="❌ No vehicle file selected", 
                                      fg=self.colors['danger'],
                                      bg=self.colors['card'],
                                      font=("Segoe UI", 11))
        self.vehicle_status.pack(anchor="w")
        
        # Modern Processing options
        options_card = tk.LabelFrame(scrollable_frame, 
                                   text="⚙️ Processing Options", 
                                   font=("Segoe UI", 14, "bold"),
                                   fg=self.colors['dark'],
                                   bg=self.colors['card'],
                                   bd=2,
                                   relief="groove")
        options_card.pack(fill="x", padx=25, pady=15)
        
        # Output format selection with modern styling
        format_container = tk.Frame(options_card, bg=self.colors['card'])
        format_container.pack(fill="x", padx=20, pady=20)
        
        format_title = tk.Label(format_container, 
                               text="📊 Output Format:", 
                               font=("Segoe UI", 12, "bold"),
                               fg=self.colors['dark'],
                               bg=self.colors['card'])
        format_title.pack(anchor="w", pady=(0, 10))
        
        self.output_format = tk.StringVar(value="mf4")
        
        # Modern radio buttons
        format_frame = tk.Frame(format_container, bg=self.colors['card'])
        format_frame.pack(fill="x", padx=20)
        
        mf4_radio = tk.Radiobutton(format_frame, 
                                  text="🔧 MF4 (Recommended for calculated channels)", 
                                  variable=self.output_format, 
                                  value="mf4",
                                  font=("Segoe UI", 11),
                                  bg=self.colors['card'],
                                  fg=self.colors['dark'],
                                  selectcolor=self.colors['primary'],
                                  activebackground=self.colors['card'])
        mf4_radio.pack(anchor="w", pady=3)
        
        csv_radio = tk.Radiobutton(format_frame, 
                                  text="📈 CSV (For data analysis)", 
                                  variable=self.output_format, 
                                  value="csv",
                                  font=("Segoe UI", 11),
                                  bg=self.colors['card'],
                                  fg=self.colors['dark'],
                                  selectcolor=self.colors['primary'],
                                  activebackground=self.colors['card'])
        csv_radio.pack(anchor="w", pady=3)
        
        # Modern Processing section
        process_card = tk.LabelFrame(scrollable_frame, 
                                   text="🚀 Process Channels", 
                                   font=("Segoe UI", 14, "bold"),
                                   fg=self.colors['dark'],
                                   bg=self.colors['card'],
                                   bd=2,
                                   relief="groove")
        process_card.pack(fill="x", padx=25, pady=15)
        
        info_container = tk.Frame(process_card, bg=self.colors['card'])
        info_container.pack(fill="x", padx=20, pady=20)
        
        # Modern info section with icon
        info_text = ("💡 Configure custom channels in the 'Custom Channels' tab, then process them here.\n"
                    "🔄 The tool will create calculated channels based on surface table interpolation.")
        info_label = tk.Label(info_container, 
                             text=info_text, 
                             font=("Segoe UI", 11), 
                             fg=self.colors['primary'],
                             bg=self.colors['card'],
                             justify="left",
                             wraplength=600)
        info_label.pack(anchor="w", pady=(0, 20))
        
        # Modern process button
        process_btn_frame = tk.Frame(info_container, bg=self.colors['card'])
        process_btn_frame.pack(fill="x")
        
        self.process_btn = self.create_modern_button(process_btn_frame, 
                                                    "🚀 Process All Custom Channels", 
                                                    self.process_all_channels, 
                                                    self.colors['warning'],
                                                    width=30,
                                                    height=2)
        self.process_btn.pack(pady=10)

    def setup_custom_channels_tab(self):
        """Setup the custom channels tab with modern design and enhanced functionality"""
        self.custom_channels_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(self.custom_channels_frame, text="⚙️ Custom Channels")
        
        # Create scrollable container for the custom channels tab
        canvas2 = tk.Canvas(self.custom_channels_frame, bg=self.colors['background'])
        scrollbar2 = ttk.Scrollbar(self.custom_channels_frame, orient="vertical", command=canvas2.yview)
        scrollable_frame2 = tk.Frame(canvas2, bg=self.colors['background'])
        
        scrollable_frame2.bind(
            "<Configure>",
            lambda e: canvas2.configure(scrollregion=canvas2.bbox("all"))
        )
        
        canvas2.create_window((0, 0), window=scrollable_frame2, anchor="nw")
        canvas2.configure(yscrollcommand=scrollbar2.set)
        
        canvas2.pack(side="left", fill="both", expand=True)
        scrollbar2.pack(side="right", fill="y")
        
        # Modern title section
        title_container = tk.Frame(scrollable_frame2, bg=self.colors['background'])
        title_container.pack(fill="x", padx=25, pady=(15, 0))
        
        title_label = tk.Label(title_container, 
                              text="⚙️ Custom Channel Management", 
                              font=("Segoe UI", 18, "bold"),
                              fg=self.colors['dark'],
                              bg=self.colors['background'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_container,
                                 text="Create and manage custom calculated channels with surface table interpolation",
                                 font=("Segoe UI", 11),
                                 fg=self.colors['secondary'],
                                 bg=self.colors['background'])
        subtitle_label.pack(pady=(5, 15))
        
        # Modern Add new channel section
        add_card = tk.LabelFrame(scrollable_frame2, 
                                text="➕ Add New Custom Channel", 
                                font=("Segoe UI", 14, "bold"),
                                fg=self.colors['dark'],
                                bg=self.colors['card'],
                                bd=2,
                                relief="groove")
        add_card.pack(fill="x", padx=25, pady=15)
        
        # Main form container
        form_container = tk.Frame(add_card, bg=self.colors['card'])
        form_container.pack(fill="x", padx=20, pady=20)
        
        # Modern Channel name field
        name_frame = tk.Frame(form_container, bg=self.colors['card'])
        name_frame.pack(fill="x", pady=8)
        tk.Label(name_frame, 
                text="📝 Channel Name:", 
                width=20, 
                anchor="w",
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_name = tk.Entry(name_frame, 
                                       width=30,
                                       font=("Segoe UI", 11),
                                       bd=1,
                                       relief="solid")
        self.new_custom_name.pack(side="left", padx=10)
        
        # Modern CSV Surface Table file field
        csv_frame = tk.Frame(form_container, bg=self.colors['card'])
        csv_frame.pack(fill="x", pady=8)
        tk.Label(csv_frame, 
                text="📊 Surface Table CSV:", 
                width=20, 
                anchor="w",
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_csv = tk.Entry(csv_frame, 
                                      width=35,
                                      font=("Segoe UI", 11),
                                      bd=1,
                                      relief="solid")
        self.new_custom_csv.pack(side="left", padx=10)
        browse_btn = self.create_modern_button(csv_frame, 
                                              "📁 Browse", 
                                              self.browse_custom_csv, 
                                              self.colors['secondary'])
        browse_btn.pack(side="left", padx=5)
        
        # Modern CSV column configuration section
        csv_config_card = tk.LabelFrame(form_container, 
                                       text="📋 CSV Surface Table Configuration",
                                       font=("Segoe UI", 12, "bold"),
                                       fg=self.colors['dark'],
                                       bg=self.colors['card'],
                                       bd=1,
                                       relief="solid")
        csv_config_card.pack(fill="x", pady=15)
        
        csv_config_inner = tk.Frame(csv_config_card, bg=self.colors['card'])
        csv_config_inner.pack(fill="x", padx=15, pady=15)
        
        # Modern X axis column field
        x_col_frame = tk.Frame(csv_config_inner, bg=self.colors['card'])
        x_col_frame.pack(fill="x", pady=5)
        tk.Label(x_col_frame, 
                text="📊 X-axis Column (e.g., RPM):", 
                width=28, 
                anchor="w",
                font=("Segoe UI", 10),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_x_col = AutocompleteCombobox(x_col_frame, 
                                                    width=25,
                                                    font=("Segoe UI", 10))
        self.new_custom_x_col.pack(side="left", padx=5)
        
        # Modern Y axis column field
        y_col_frame = tk.Frame(csv_config_inner, bg=self.colors['card'])
        y_col_frame.pack(fill="x", pady=5)
        tk.Label(y_col_frame, 
                text="📈 Y-axis Column (e.g., ETASP):", 
                width=28, 
                anchor="w",
                font=("Segoe UI", 10),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_y_col = AutocompleteCombobox(y_col_frame, 
                                                    width=25,
                                                    font=("Segoe UI", 10))
        self.new_custom_y_col.pack(side="left", padx=5)
        
        # Modern Z axis column field
        z_col_frame = tk.Frame(csv_config_inner, bg=self.colors['card'])
        z_col_frame.pack(fill="x", pady=5)
        tk.Label(z_col_frame, 
                text="📋 Z-axis Column (Values):", 
                width=28, 
                anchor="w",
                font=("Segoe UI", 10),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_z_col = AutocompleteCombobox(z_col_frame, 
                                                    width=25,
                                                    font=("Segoe UI", 10))
        self.new_custom_z_col.pack(side="left", padx=5)
        
        # Modern Vehicle log channel selection section
        veh_config_card = tk.LabelFrame(form_container, 
                                       text="🚗 Vehicle Log Channel Selection",
                                       font=("Segoe UI", 12, "bold"),
                                       fg=self.colors['dark'],
                                       bg=self.colors['card'],
                                       bd=1,
                                       relief="solid")
        veh_config_card.pack(fill="x", pady=15)
        
        veh_config_inner = tk.Frame(veh_config_card, bg=self.colors['card'])
        veh_config_inner.pack(fill="x", padx=15, pady=15)
        
        # Modern Vehicle X channel field
        veh_x_frame = tk.Frame(veh_config_inner, bg=self.colors['card'])
        veh_x_frame.pack(fill="x", pady=5)
        tk.Label(veh_x_frame, 
                text="🔧 Vehicle X Channel:", 
                width=20, 
                anchor="w",
                font=("Segoe UI", 10),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_veh_x = AutocompleteCombobox(veh_x_frame, 
                                                    width=30,
                                                    font=("Segoe UI", 10))
        self.new_custom_veh_x.pack(side="left", padx=5)
        
        # Modern Vehicle Y channel field
        veh_y_frame = tk.Frame(veh_config_inner, bg=self.colors['card'])
        veh_y_frame.pack(fill="x", pady=5)
        tk.Label(veh_y_frame, 
                text="📊 Vehicle Y Channel:", 
                width=20, 
                anchor="w",
                font=("Segoe UI", 10),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_veh_y = AutocompleteCombobox(veh_y_frame, 
                                                    width=30,
                                                    font=("Segoe UI", 10))
        self.new_custom_veh_y.pack(side="left", padx=5)
        
        # Modern Units and comment section
        meta_container = tk.Frame(form_container, bg=self.colors['card'])
        meta_container.pack(fill="x", pady=15)
        
        meta_frame = tk.Frame(meta_container, bg=self.colors['card'])
        meta_frame.pack(fill="x")
        
        # Units field
        units_frame = tk.Frame(meta_frame, bg=self.colors['card'])
        units_frame.pack(side="left", fill="x", expand=True)
        tk.Label(units_frame, 
                text="📏 Units:", 
                width=10, 
                anchor="w",
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_units = tk.Entry(units_frame, 
                                        width=15,
                                        font=("Segoe UI", 11),
                                        bd=1,
                                        relief="solid")
        self.new_custom_units.pack(side="left", padx=5)
        
        # Comment field
        comment_frame = tk.Frame(meta_frame, bg=self.colors['card'])
        comment_frame.pack(side="right", fill="x", expand=True)
        tk.Label(comment_frame, 
                text="💬 Comment:", 
                width=12, 
                anchor="w",
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_comment = tk.Entry(comment_frame, 
                                          width=25,
                                          font=("Segoe UI", 11),
                                          bd=1,
                                          relief="solid")
        self.new_custom_comment.pack(side="left", padx=5)
        
        # Modern Add button and preserve settings section
        add_btn_container = tk.Frame(form_container, bg=self.colors['card'])
        add_btn_container.pack(fill="x", pady=20)
        
        # Checkbox with modern styling
        checkbox_frame = tk.Frame(add_btn_container, bg=self.colors['card'])
        checkbox_frame.pack(side="left")
        
        self.preserve_settings = tk.BooleanVar(value=True)
        preserve_cb = tk.Checkbutton(checkbox_frame, 
                                    text="💾 Keep settings after adding channel", 
                                    variable=self.preserve_settings, 
                                    font=("Segoe UI", 10),
                                    bg=self.colors['card'],
                                    fg=self.colors['dark'],
                                    selectcolor=self.colors['success'],
                                    activebackground=self.colors['card'])
        preserve_cb.pack(side="left")
        
        # Modern add button
        add_btn_frame = tk.Frame(add_btn_container, bg=self.colors['card'])
        add_btn_frame.pack(side="right")
        
        add_btn = self.create_modern_button(add_btn_frame, 
                                           "➕ Add Custom Channel", 
                                           self.add_custom_channel,
                                           self.colors['success'],
                                           width=20)
        add_btn.pack()
        
        # Modern Custom channels list with search and filters
        list_card = tk.LabelFrame(scrollable_frame2, 
                                 text="📋 Configured Custom Channels", 
                                 font=("Segoe UI", 14, "bold"),
                                 fg=self.colors['dark'],
                                 bg=self.colors['card'],
                                 bd=2,
                                 relief="groove")
        list_card.pack(fill="both", expand=True, padx=25, pady=15)
        
        # Modern Search and filter section
        search_filter_container = tk.Frame(list_card, bg=self.colors['card'])
        search_filter_container.pack(fill="x", padx=15, pady=15)
        
        # Modern Search functionality
        search_frame = tk.Frame(search_filter_container, bg=self.colors['card'])
        search_frame.pack(side="left", fill="x", expand=True)
        
        tk.Label(search_frame, 
                text="🔍 Search:", 
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left", padx=5)
        search_entry = tk.Entry(search_frame, 
                               textvariable=self.search_var, 
                               width=30,
                               font=("Segoe UI", 11),
                               bd=1,
                               relief="solid")
        search_entry.pack(side="left", padx=5)
        search_entry.bind('<KeyRelease>', self.on_search_change)
        
        clear_search_btn = self.create_modern_button(search_frame, 
                                                    "✖️ Clear", 
                                                    self.clear_search, 
                                                    self.colors['danger'])
        clear_search_btn.pack(side="left", padx=5)
        
        # Modern Filter controls
        filter_frame = tk.Frame(search_filter_container, bg=self.colors['card'])
        filter_frame.pack(side="right")
        
        tk.Label(filter_frame, 
                text="🎛️ Filters:", 
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left", padx=5)
        setup_filters_btn = self.create_modern_button(filter_frame, 
                                                     "⚙️ Setup", 
                                                     self.setup_filters, 
                                                     self.colors['primary'])
        setup_filters_btn.pack(side="left", padx=2)
        clear_filters_btn = self.create_modern_button(filter_frame, 
                                                     "🧹 Clear", 
                                                     self.clear_filters, 
                                                     self.colors['secondary'])
        clear_filters_btn.pack(side="left", padx=2)
        
        # Modern table container with proper scrollbars
        tree_container = tk.Frame(list_card, bg=self.colors['card'])
        tree_container.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Configure grid for proper scrollbar alignment
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Create modern treeview for custom channels
        columns = ("Name", "CSV File", "X Col", "Y Col", "Z Col", "Veh X", "Veh Y", "Units")
        style = ttk.Style()
        style.configure("Custom.Treeview", 
                       background=self.colors['white'],
                       foreground=self.colors['dark'],
                       fieldbackground=self.colors['white'],
                       font=("Segoe UI", 10))
        style.configure("Custom.Treeview.Heading", 
                       background=self.colors['primary'],
                       foreground=self.colors['white'],
                       font=("Segoe UI", 10, "bold"))
        
        self.custom_channels_tree = ttk.Treeview(tree_container, 
                                               columns=columns, 
                                               show="headings", 
                                               height=10,
                                               style="Custom.Treeview")
        
        for col in columns:
            self.custom_channels_tree.heading(col, text=col)
            self.custom_channels_tree.column(col, width=130, minwidth=100)
        
        # Modern scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.custom_channels_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.custom_channels_tree.xview)
        
        self.custom_channels_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout for proper alignment
        self.custom_channels_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Modern Management buttons
        btn_container = tk.Frame(list_card, bg=self.colors['card'])
        btn_container.pack(fill="x", padx=15, pady=10)
        
        edit_btn = self.create_modern_button(btn_container, 
                                           "✏️ Edit Selected", 
                                           self.edit_custom_channel, 
                                           self.colors['primary'])
        edit_btn.pack(side="left", padx=5)
        
        delete_btn = self.create_modern_button(btn_container, 
                                             "🗑️ Delete Selected", 
                                             self.delete_custom_channel, 
                                             self.colors['danger'])
        delete_btn.pack(side="left", padx=5)
        
        clear_all_btn = self.create_modern_button(btn_container, 
                                                 "🧹 Clear All", 
                                                 self.clear_custom_channels, 
                                                 self.colors['warning'])
        clear_all_btn.pack(side="left", padx=5)
        
        # Initialize filter variables
        for col in columns:
            self.filter_vars[col] = tk.StringVar()

    def on_search_change(self, event=None):
        """Handle search text changes"""
        self.apply_search_and_filters()
    
    def clear_search(self):
        """Clear search field"""
        self.search_var.set("")
        self.apply_search_and_filters()
    
    def setup_filters(self):
        """Open filter setup dialog"""
        filter_window = tk.Toplevel(self.root)
        filter_window.title("Column Filters")
        filter_window.geometry("400x500")
        filter_window.grab_set()
        
        tk.Label(filter_window, text="Set filters for each column:", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Create filter controls for each column
        filter_frame = tk.Frame(filter_window)
        filter_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ("Name", "CSV File", "X Col", "Y Col", "Z Col", "Veh X", "Veh Y", "Units")
        
        for i, col in enumerate(columns):
            col_frame = tk.Frame(filter_frame)
            col_frame.pack(fill="x", pady=5)
            
            tk.Label(col_frame, text=f"{col}:", width=12, anchor="w").pack(side="left")
            entry = tk.Entry(col_frame, textvariable=self.filter_vars[col], width=30)
            entry.pack(side="left", padx=5)
            entry.bind('<KeyRelease>', lambda e: self.apply_search_and_filters())
        
        # Buttons
        btn_frame = tk.Frame(filter_window)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Apply Filters", 
                 command=lambda: [self.apply_search_and_filters(), filter_window.destroy()], 
                 bg="lightgreen").pack(side="left", padx=10)
        tk.Button(btn_frame, text="Clear All", 
                 command=self.clear_filters, bg="lightgray").pack(side="left", padx=10)
        tk.Button(btn_frame, text="Close", 
                 command=filter_window.destroy).pack(side="left", padx=10)
    
    def clear_filters(self):
        """Clear all column filters"""
        for var in self.filter_vars.values():
            var.set("")
        self.apply_search_and_filters()
    
    def apply_search_and_filters(self):
        """Apply search and filter criteria to the table"""
        # Clear existing items
        for item in self.custom_channels_tree.get_children():
            self.custom_channels_tree.delete(item)
        
        search_term = self.search_var.get().lower()
        
        # Filter channels based on search and filter criteria
        for channel in self.custom_channels:
            # Check search term (searches across all fields)
            channel_text = ' '.join([
                channel.get('name', ''),
                os.path.basename(channel.get('csv_file', '')),
                channel.get('x_column', ''),
                channel.get('y_column', ''),
                channel.get('z_column', ''),
                channel.get('vehicle_x_channel', ''),
                channel.get('vehicle_y_channel', ''),
                channel.get('units', '')
            ]).lower()
            
            if search_term and search_term not in channel_text:
                continue
            
            # Check column filters
            channel_values = [
                channel.get('name', ''),
                os.path.basename(channel.get('csv_file', '')),
                channel.get('x_column', ''),
                channel.get('y_column', ''),
                channel.get('z_column', ''),
                channel.get('vehicle_x_channel', ''),
                channel.get('vehicle_y_channel', ''),
                channel.get('units', '')
            ]
            
            columns = ("Name", "CSV File", "X Col", "Y Col", "Z Col", "Veh X", "Veh Y", "Units")
            filter_passed = True
            
            for i, col in enumerate(columns):
                filter_text = self.filter_vars[col].get().lower()
                if filter_text and filter_text not in channel_values[i].lower():
                    filter_passed = False
                    break
            
            if filter_passed:
                self.custom_channels_tree.insert("", "end", values=channel_values)

    def browse_custom_csv(self):
        """Browse for CSV surface table file and load its columns"""
        file_path = filedialog.askopenfilename(
            title="Select Surface Table CSV File",
            filetypes=[("CSV Files", "*.csv")]
        )
        
        if file_path:
            self.new_custom_csv.delete(0, tk.END)
            self.new_custom_csv.insert(0, file_path)
            
            # Load CSV columns for selection
            try:
                df = pd.read_csv(file_path, nrows=1)
                columns = df.columns.tolist()
                
                # Update comboboxes with available columns
                self.new_custom_x_col.set_completion_list(columns)
                self.new_custom_y_col.set_completion_list(columns)
                self.new_custom_z_col.set_completion_list(columns)
                
                self.log_status(f"Loaded CSV columns: {', '.join(columns)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read CSV file: {str(e)}")
                self.log_status(f"Error reading CSV file: {str(e)}")

    def add_custom_channel(self):
        """Add a new custom channel configuration"""
        name = self.new_custom_name.get().strip()
        csv_file = self.new_custom_csv.get().strip()
        x_col = self.new_custom_x_col.get()
        y_col = self.new_custom_y_col.get()
        z_col = self.new_custom_z_col.get()
        veh_x = self.new_custom_veh_x.get()
        veh_y = self.new_custom_veh_y.get()
        units = self.new_custom_units.get().strip()
        comment = self.new_custom_comment.get().strip()
        
        # Validation
        if not all([name, csv_file, x_col, y_col, z_col, veh_x, veh_y]):
            messagebox.showerror("Error", "Please fill in all required fields!")
            return
            
        if not os.path.exists(csv_file):
            messagebox.showerror("Error", "CSV file does not exist!")
            return
            
        if x_col == y_col or x_col == z_col or y_col == z_col:
            messagebox.showerror("Error", "X, Y, and Z columns must be different!")
            return
        
        # Create custom channel configuration
        custom_channel = {
            'name': name,
            'csv_file': csv_file,
            'x_column': x_col,
            'y_column': y_col,
            'z_column': z_col,
            'vehicle_x_channel': veh_x,
            'vehicle_y_channel': veh_y,
            'units': units,
            'comment': comment
        }
        
        # Add to the list
        self.custom_channels.append(custom_channel)
        
        # Update treeview
        self.refresh_custom_channels_tree()
        
        # Auto-save settings to preserve the configuration
        self.save_settings()
        
        # Clear input fields only if preserve_settings is False
        if not self.preserve_settings.get():
            self.clear_custom_channel_inputs()
        else:
            # Just clear the name field for the next channel
            self.new_custom_name.delete(0, tk.END)
        
        self.log_status(f"Added custom channel: {name}")

    def clear_custom_channel_inputs(self):
        """Clear all custom channel input fields"""
        self.new_custom_name.delete(0, tk.END)
        self.new_custom_csv.delete(0, tk.END)
        self.new_custom_x_col.set('')
        self.new_custom_y_col.set('')
        self.new_custom_z_col.set('')
        self.new_custom_veh_x.set('')
        self.new_custom_veh_y.set('')
        self.new_custom_units.delete(0, tk.END)
        self.new_custom_comment.delete(0, tk.END)

    def refresh_custom_channels_tree(self):
        """Refresh the custom channels tree view"""
        # Store current search and filter state
        current_search = self.search_var.get()
        current_filters = {col: var.get() for col, var in self.filter_vars.items()}
        
        # Apply search and filters
        self.apply_search_and_filters()

    def edit_custom_channel(self):
        """Edit the selected custom channel"""
        selection = self.custom_channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to edit!")
            return
            
        item = selection[0]
        values = self.custom_channels_tree.item(item)['values']
        
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
        self.new_custom_name.delete(0, tk.END)
        self.new_custom_name.insert(0, channel['name'])
        
        self.new_custom_csv.delete(0, tk.END)
        self.new_custom_csv.insert(0, channel['csv_file'])
        
        # Load CSV columns and set values
        try:
            df = pd.read_csv(channel['csv_file'], nrows=1)
            columns = df.columns.tolist()
            
            self.new_custom_x_col.set_completion_list(columns)
            self.new_custom_y_col.set_completion_list(columns)
            self.new_custom_z_col.set_completion_list(columns)
            
            self.new_custom_x_col.set(channel['x_column'])
            self.new_custom_y_col.set(channel['y_column'])
            self.new_custom_z_col.set(channel['z_column'])
        except Exception as e:
            self.log_status(f"Error loading CSV columns: {str(e)}")
        
        self.new_custom_veh_x.set(channel['vehicle_x_channel'])
        self.new_custom_veh_y.set(channel['vehicle_y_channel'])
        
        self.new_custom_units.delete(0, tk.END)
        self.new_custom_units.insert(0, channel['units'])
        
        self.new_custom_comment.delete(0, tk.END)
        self.new_custom_comment.insert(0, channel['comment'])
        
        # Remove the channel (will be re-added when user clicks Add)
        del self.custom_channels[channel_index]
        self.refresh_custom_channels_tree()

    def delete_custom_channel(self):
        """Delete the selected custom channel"""
        selection = self.custom_channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to delete!")
            return
            
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this custom channel?"):
            item = selection[0]
            values = self.custom_channels_tree.item(item)['values']
            channel_name = values[0]
            
            # Find and remove the channel
            for i, channel in enumerate(self.custom_channels):
                if channel['name'] == channel_name:
                    del self.custom_channels[i]
                    break
            
            self.refresh_custom_channels_tree()
            self.log_status("Custom channel deleted")

    def clear_custom_channels(self):
        """Clear all custom channels"""
        if self.custom_channels and messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all custom channels?"):
            self.custom_channels.clear()
            self.refresh_custom_channels_tree()
            self.log_status("All custom channels cleared")

    def select_vehicle_file(self):
        """Select vehicle log file"""
        file_path = filedialog.askopenfilename(
            title="Select Vehicle Log File",
            filetypes=[
                ("All Supported", "*.csv *.dat *.mdf *.mf4"),
                ("CSV Files", "*.csv"),
                ("DAT Files", "*.dat"),
                ("MDF Files", "*.mdf"),
                ("MF4 Files", "*.mf4")
            ]
        )
        
        if not file_path:
            return
            
        self.vehicle_file_path = file_path
        self.vehicle_status.config(text=f"Selected: {os.path.basename(file_path)}", fg="green")
        self.log_status(f"Selected vehicle file: {os.path.basename(file_path)}")
        
        try:
            self.load_vehicle_file()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load vehicle file: {str(e)}")
            self.log_status(f"Error loading vehicle file: {str(e)}")

    def load_vehicle_file(self):
        """Load vehicle file and extract available channels"""
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        
        if file_ext == '.csv':
            self.load_csv_vehicle_file()
        elif file_ext in ['.mdf', '.mf4', '.dat']:
            self.load_mdf_vehicle_file()
        else:
            raise Exception(f"Unsupported file format: {file_ext}")

    def load_csv_vehicle_file(self):
        """Load CSV vehicle file"""
        try:
            df = pd.read_csv(self.vehicle_file_path)
            self.available_channels = df.columns.tolist()
            self.vehicle_data = df
            
            # Update channel comboboxes
            if hasattr(self, 'new_custom_veh_x'):
                self.new_custom_veh_x.set_completion_list(self.available_channels)
                self.new_custom_veh_y.set_completion_list(self.available_channels)
            
            self.log_status(f"CSV vehicle file loaded successfully. Found {len(self.available_channels)} channels.")
            
        except Exception as e:
            raise Exception(f"Error loading CSV vehicle file: {str(e)}")

    def load_mdf_vehicle_file(self):
        """Load MDF/MF4/DAT vehicle file"""
        try:
            mdf = MDF(self.vehicle_file_path)
            
            # Get available channels
            self.available_channels = []
            for group_index in range(len(mdf.groups)):
                for channel in mdf.groups[group_index].channels:
                    self.available_channels.append(channel.name)
            
            self.vehicle_data = mdf
            
            # Update channel comboboxes
            if hasattr(self, 'new_custom_veh_x'):
                self.new_custom_veh_x.set_completion_list(self.available_channels)
                self.new_custom_veh_y.set_completion_list(self.available_channels)
            
            self.log_status(f"MDF vehicle file loaded successfully. Found {len(self.available_channels)} channels.")
            
        except Exception as e:
            raise Exception(f"Error loading MDF vehicle file: {str(e)}")

    def load_surface_table(self, csv_file_path, x_col, y_col, z_col):
        """Load surface table from CSV file"""
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
        """Interpolate Z value for given RPM and ETASP using bilinear interpolation"""
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
        """Analyze sampling rates of all channels used in custom channel configurations"""
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
            self.log_status(f"Error analyzing channel sampling rates: {str(e)}")
        
        return channel_analysis

    def get_interpolated_signal_data(self, channel_name, target_raster):
        """Get signal data with interpolation if needed for target raster"""
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
                self.log_status(f"Direct raster extraction successful for {channel_name}: {len(signal.samples)} samples")
                return signal.samples, signal.timestamps
        except Exception as e:
            # If raster-based extraction fails, fall back to interpolation
            self.log_status(f"Direct raster extraction failed for {channel_name}, using interpolation: {str(e)}")
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
            
            self.log_status(f"Interpolated {channel_name}: {len(original_signal.samples)} -> {len(interpolated_samples)} samples")
            return interpolated_samples, target_timestamps
            
        except Exception as e:
            raise Exception(f"Failed to get data for {channel_name}: {str(e)}")

    def ask_for_raster(self):
        """Ask user for raster value for resampling MDF files with detailed channel analysis"""
        raster_window = tk.Toplevel(self.root)
        raster_window.title('Set Time Raster - Advanced Analysis')
        raster_window.geometry('800x600')
        raster_window.grab_set()
        
        tk.Label(raster_window, text='Time Raster Configuration with Channel Analysis', 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Analyze channels first
        self.log_status("Analyzing channel sampling rates...")
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
        
        # Info frame
        info_frame = tk.LabelFrame(raster_window, text="Raster Information", font=('Arial', 12, 'bold'))
        info_frame.pack(fill="x", padx=20, pady=10)
        
        info_text = ('The vehicle channels may have different sampling rates.\n'
                    'Specify a time raster (in seconds) to resample all signals to the same time base.\n'
                    'Lower rasters provide finer resolution but require interpolation if original data is coarser.')
        tk.Label(info_frame, text=info_text, font=('Arial', 10), justify="left").pack(anchor="w", padx=10, pady=5)
        
        # Overall minimum raster display
        min_raster_frame = tk.LabelFrame(raster_window, text="Recommended Minimum Raster", 
                                        font=('Arial', 12, 'bold'), fg="red")
        min_raster_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(min_raster_frame, 
                text=f"Overall Minimum Raster: {overall_min_raster:.6f} seconds ({overall_min_raster*1000:.2f} ms)",
                font=('Arial', 11, 'bold'), fg="red").pack(anchor="w", padx=10, pady=2)
        tk.Label(min_raster_frame, 
                text=f"Limiting Channel: {limiting_channel}",
                font=('Arial', 10), fg="darkred").pack(anchor="w", padx=10, pady=2)
        tk.Label(min_raster_frame, 
                text="Values below this may require interpolation and could affect accuracy.",
                font=('Arial', 9), fg="darkred").pack(anchor="w", padx=10, pady=2)
        
        # Channel details frame (optional window)
        details_btn_frame = tk.Frame(raster_window)
        details_btn_frame.pack(fill="x", padx=20, pady=5)
        
        def show_channel_details():
            detail_window = tk.Toplevel(raster_window)
            detail_window.title('Channel Analysis Details')
            detail_window.geometry('700x400')
            
            # Create treeview for channel details
            columns = ("Channel", "Min Interval", "Avg Interval", "Suggested Min Raster", "Samples", "Status")
            tree = ttk.Treeview(detail_window, columns=columns, show="headings", height=15)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=110)
            
            # Populate tree with channel analysis
            for ch_name, analysis in channel_analysis.items():
                if 'error' in analysis:
                    tree.insert("", "end", values=(
                        ch_name, "Error", "Error", "Error", "Error", analysis['error']
                    ))
                elif 'note' in analysis:
                    tree.insert("", "end", values=(
                        ch_name, "N/A", "N/A", "N/A", analysis.get('sample_count', 'N/A'), analysis['note']
                    ))
                else:
                    tree.insert("", "end", values=(
                        ch_name,
                        f"{analysis['min_interval']:.6f}s",
                        f"{analysis['avg_interval']:.6f}s", 
                        f"{analysis['suggested_min_raster']:.6f}s",
                        analysis['sample_count'],
                        "OK"
                    ))
            
            tree.pack(fill="both", expand=True, padx=10, pady=10)
            
        tk.Button(details_btn_frame, text="Show Channel Analysis Details", 
                 command=show_channel_details, bg="lightblue").pack(side="right")
        
        # Input frame
        input_frame = tk.LabelFrame(raster_window, text="Set Raster Value", font=('Arial', 12, 'bold'))
        input_frame.pack(fill="x", padx=20, pady=10)
        
        raster_input_frame = tk.Frame(input_frame)
        raster_input_frame.pack(pady=10)
        
        tk.Label(raster_input_frame, text='Raster (seconds):', font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5)
        raster_var = tk.DoubleVar(value=overall_min_raster)
        raster_entry = tk.Entry(raster_input_frame, textvariable=raster_var, width=15, font=('Arial', 10))
        raster_entry.grid(row=0, column=1, padx=5)
        
        # Add button to set recommended minimum
        tk.Button(raster_input_frame, text="Use Recommended", 
                 command=lambda: raster_var.set(overall_min_raster), 
                 bg="lightgreen").grid(row=0, column=2, padx=10)
        
        # Suggested values
        suggestions_frame = tk.LabelFrame(raster_window, text="Common Raster Values", font=('Arial', 11, 'bold'))
        suggestions_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(suggestions_frame, text='Quick selection for automotive measurements:', 
                font=('Arial', 9)).pack(pady=5)
        
        buttons_frame = tk.Frame(suggestions_frame)
        buttons_frame.pack(pady=5)
        
        def set_raster(value):
            raster_var.set(value)
            # Show warning if below recommended minimum
            if value < overall_min_raster:
                warning_label.config(text=f"⚠️ Warning: Below recommended minimum ({overall_min_raster:.6f}s). Interpolation will be used.", 
                                   fg="orange")
            else:
                warning_label.config(text="✅ Good choice - within recommended range.", fg="green")
        
        for value, label in [(0.001, '1ms'), (0.01, '10ms'), (0.02, '20ms'), 
                            (0.05, '50ms'), (0.1, '100ms'), (0.2, '200ms')]:
            btn_color = "lightgreen" if value >= overall_min_raster else "lightyellow"
            tk.Button(buttons_frame, text=f'{label}\n({value}s)', 
                     command=lambda v=value: set_raster(v), width=8, height=2,
                     bg=btn_color).pack(side='left', padx=2)
        
        # Warning label
        warning_label = tk.Label(suggestions_frame, text="", font=('Arial', 9))
        warning_label.pack(pady=5)
        
        # Initialize warning
        set_raster(raster_var.get())
        
        result = [None]
        
        def confirm_raster():
            try:
                raster_value = raster_var.get()
                if raster_value <= 0:
                    messagebox.showerror('Error', 'Raster value must be positive!')
                    return
                result[0] = raster_value
                raster_window.destroy()
            except tk.TclError:
                messagebox.showerror('Error', 'Please enter a valid number!')
        
        def cancel_raster():
            result[0] = None
            raster_window.destroy()
        
        button_frame = tk.Frame(raster_window)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text='OK', command=confirm_raster, 
                 bg='lightgreen', font=('Arial', 10, 'bold')).pack(side='left', padx=10)
        tk.Button(button_frame, text='Cancel', command=cancel_raster, 
                 bg='lightcoral').pack(side='left', padx=10)
        
        raster_entry.focus()
        raster_entry.bind('<Return>', lambda e: confirm_raster())
        
        raster_window.wait_window()
        return result[0]

    def process_all_channels(self):
        """Process all configured custom channels"""
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
                self.log_status("Processing cancelled by user.")
                return
        
        try:
            self.log_status("Starting processing of all custom channels...")
            
            # Process each custom channel
            calculated_signals = []
            for i, channel_config in enumerate(self.custom_channels):
                self.log_status(f"Processing channel {i+1}/{len(self.custom_channels)}: {channel_config['name']}")
                
                # Load surface table
                try:
                    x_values, y_values, z_matrix = self.load_surface_table(
                        channel_config['csv_file'],
                        channel_config['x_column'],
                        channel_config['y_column'], 
                        channel_config['z_column']
                    )
                    self.log_status(f"Surface table loaded for {channel_config['name']}")
                except Exception as e:
                    self.log_status(f"Error loading surface table for {channel_config['name']}: {str(e)}")
                    continue
                
                # Extract vehicle data with interpolation support
                try:
                    if file_ext == '.csv':
                        x_data = pd.to_numeric(self.vehicle_data[channel_config['vehicle_x_channel']], errors='coerce')
                        y_data = pd.to_numeric(self.vehicle_data[channel_config['vehicle_y_channel']], errors='coerce')
                        timestamps = np.arange(len(x_data), dtype=np.float64) * raster
                    else:  # MDF files
                        # Use new interpolation-capable method
                        x_data, x_timestamps = self.get_interpolated_signal_data(channel_config['vehicle_x_channel'], raster)
                        y_data, y_timestamps = self.get_interpolated_signal_data(channel_config['vehicle_y_channel'], raster)
                        
                        # Align timestamps - use the shorter range
                        min_length = min(len(x_data), len(y_data))
                        x_data = x_data[:min_length]
                        y_data = y_data[:min_length]
                        timestamps = x_timestamps[:min_length]
                        
                        if len(x_data) != len(y_data):
                            raise Exception(f"Channel length mismatch after interpolation: {len(x_data)} vs {len(y_data)}")
                        
                    self.log_status(f"Vehicle data extracted for {channel_config['name']}: {len(x_data)} samples")
                    
                except Exception as e:
                    self.log_status(f"Error extracting vehicle data for {channel_config['name']}: {str(e)}")
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
                    
                    self.log_status(f"Interpolated {valid_points}/{len(z_interpolated)} valid points for {channel_config['name']}")
                    
                    # Create signal for MDF output
                    if self.output_format.get() == "mf4" and file_ext != '.csv':
                        # Generate pre-formed comment with all variables used
                        csv_filename = os.path.basename(channel_config['csv_file'])
                        pre_formed_comment = (
                            f"Channel generated from CSV surface table '{csv_filename}' "
                            f"using X-axis: {channel_config['x_column']} (vehicle: {channel_config['vehicle_x_channel']}), "
                            f"Y-axis: {channel_config['y_column']} (vehicle: {channel_config['vehicle_y_channel']}), "
                            f"Z-values: {channel_config['z_column']}. "
                        )
                        
                        # Combine with user comment if provided
                        final_comment = pre_formed_comment
                        if channel_config['comment'].strip():
                            final_comment += f"User comment: {channel_config['comment']}"
                        
                        signal = Signal(
                            samples=np.array(z_interpolated, dtype=np.float64),
                            timestamps=timestamps,
                            name=channel_config['name'],
                            unit=channel_config['units'],
                            comment=final_comment
                        )
                        calculated_signals.append(signal)
                    
                    # Store for CSV output
                    if file_ext == '.csv' or self.output_format.get() == "csv":
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
                    self.log_status(f"Error interpolating {channel_config['name']}: {str(e)}")
                    continue
            
            # Save output
            self.save_output(calculated_signals, file_ext)
            
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
            self.log_status(f"Processing error: {str(e)}")

    def save_output(self, calculated_signals, original_file_ext):
        """Save the output in the selected format"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(self.vehicle_file_path).stem
        output_dir = Path(self.vehicle_file_path).parent
        
        try:
            if self.output_format.get() == "mf4" and original_file_ext != '.csv':
                # Save as MF4 with calculated channels only
                output_path = output_dir / f"{base_name}_calculated_channels_{timestamp}.mf4"
                
                with MDF() as new_mdf:
                    if calculated_signals:
                        new_mdf.append(calculated_signals, comment="Calculated channels from surface table interpolation")
                        new_mdf.save(output_path, overwrite=True)
                        self.log_status(f"✅ MF4 file saved: {output_path}")
                    else:
                        self.log_status("❌ No calculated signals to save")
                        
            if self.output_format.get() == "csv" or original_file_ext == '.csv':
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
        """Auto-save current settings to default file"""
        try:
            settings = self.get_all_settings()
            with open('channel_appender_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.log_status(f"Error auto-saving settings: {str(e)}")

    def load_settings(self):
        """Load settings from default file"""
        try:
            if os.path.exists('channel_appender_settings.json'):
                with open('channel_appender_settings.json', 'r') as f:
                    settings = json.load(f)
                self.restore_settings(settings)
        except Exception as e:
            self.log_status(f"Error loading settings: {str(e)}")

    def restore_last_channel_settings(self, last_settings):
        """Restore the last channel creation settings"""
        try:
            # Restore form fields
            self.new_custom_name.delete(0, tk.END)
            if last_settings.get('name'):
                self.new_custom_name.insert(0, last_settings['name'])
            
            self.new_custom_csv.delete(0, tk.END)
            if last_settings.get('csv_file'):
                self.new_custom_csv.insert(0, last_settings['csv_file'])
                
                # If CSV file exists, load its columns
                if os.path.exists(last_settings['csv_file']):
                    try:
                        df = pd.read_csv(last_settings['csv_file'], nrows=1)
                        columns = df.columns.tolist()
                        
                        # Update comboboxes with available columns
                        self.new_custom_x_col.set_completion_list(columns)
                        self.new_custom_y_col.set_completion_list(columns)
                        self.new_custom_z_col.set_completion_list(columns)
                        
                        # Set the previously selected columns
                        if last_settings.get('x_column'):
                            self.new_custom_x_col.set(last_settings['x_column'])
                        if last_settings.get('y_column'):
                            self.new_custom_y_col.set(last_settings['y_column'])
                        if last_settings.get('z_column'):
                            self.new_custom_z_col.set(last_settings['z_column'])
                            
                    except Exception as e:
                        self.log_status(f"Warning: Could not reload CSV columns: {str(e)}")
            
            # Restore vehicle channel selections
            if last_settings.get('vehicle_x_channel'):
                self.new_custom_veh_x.set(last_settings['vehicle_x_channel'])
            if last_settings.get('vehicle_y_channel'):
                self.new_custom_veh_y.set(last_settings['vehicle_y_channel'])
            
            # Restore units and comment
            self.new_custom_units.delete(0, tk.END)
            if last_settings.get('units'):
                self.new_custom_units.insert(0, last_settings['units'])
                
            self.new_custom_comment.delete(0, tk.END)
            if last_settings.get('comment'):
                self.new_custom_comment.insert(0, last_settings['comment'])
            
            self.log_status("Last channel settings restored")
            
        except Exception as e:
            self.log_status(f"Error restoring last channel settings: {str(e)}")

    def log_status(self, message):
        """Add a timestamped message to the status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()

    def on_closing(self):
        """Handle window closing event with comprehensive save options"""
        # Check if there are any custom channels that might be lost
        num_channels = len(self.custom_channels)
        
        if num_channels > 0:
            # Create custom dialog for exit options
            exit_dialog = tk.Toplevel(self.root)
            exit_dialog.title("Save Settings Before Exit?")
            exit_dialog.geometry("400x250")
            exit_dialog.grab_set()
            exit_dialog.transient(self.root)
            
            # Center the dialog
            exit_dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
            
            # Main message
            tk.Label(exit_dialog, text="Save Settings Before Exit?", 
                    font=("Arial", 14, "bold")).pack(pady=10)
            
            # Info about current state
            info_text = f"You have {num_channels} custom channel(s) configured.\nWhat would you like to do before exiting?"
            tk.Label(exit_dialog, text=info_text, font=("Arial", 10), 
                    justify="center").pack(pady=10)
            
            # Options frame
            options_frame = tk.Frame(exit_dialog)
            options_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            result = [None]  # Use list to store result from nested functions
            
            def auto_save_exit():
                result[0] = "auto_save"
                exit_dialog.destroy()
            
            def save_as_exit():
                result[0] = "save_as"
                exit_dialog.destroy()
            
            def quick_save_exit():
                result[0] = "quick_save"
                exit_dialog.destroy()
            
            def no_save_exit():
                result[0] = "no_save"
                exit_dialog.destroy()
            
            def cancel_exit():
                result[0] = "cancel"
                exit_dialog.destroy()
            
            # Button layout
            tk.Button(options_frame, text="💾 Auto-Save & Exit", command=auto_save_exit, 
                     bg="lightgreen", font=("Arial", 10, "bold")).pack(fill="x", pady=2)
            tk.Label(options_frame, text="(Save to default file)", font=("Arial", 8), 
                    fg="gray").pack()
            
            tk.Button(options_frame, text="📁 Save As... & Exit", command=save_as_exit, 
                     bg="lightblue", font=("Arial", 10)).pack(fill="x", pady=2)
            tk.Label(options_frame, text="(Choose custom filename)", font=("Arial", 8), 
                    fg="gray").pack()
            
            tk.Button(options_frame, text="⚡ Quick Save & Exit", command=quick_save_exit, 
                     bg="lightyellow", font=("Arial", 10)).pack(fill="x", pady=2)
            tk.Label(options_frame, text="(Save to slot 1)", font=("Arial", 8), 
                    fg="gray").pack()
            
            # Separator
            tk.Frame(options_frame, height=1, bg="gray").pack(fill="x", pady=5)
            
            tk.Button(options_frame, text="🚫 Exit Without Saving", command=no_save_exit, 
                     bg="lightcoral", font=("Arial", 10)).pack(fill="x", pady=2)
            
            tk.Button(options_frame, text="❌ Cancel", command=cancel_exit, 
                     bg="lightgray", font=("Arial", 10)).pack(fill="x", pady=2)
            
            # Wait for user choice
            exit_dialog.wait_window()
            
            # Process the result
            if result[0] == "auto_save":
                self.save_settings()
                self.log_status("✅ Auto-saved settings before exit")
                self.root.destroy()
            elif result[0] == "save_as":
                self.save_settings_as()
                self.root.destroy()
            elif result[0] == "quick_save":
                self.quick_save_settings(1)
                self.root.destroy()
            elif result[0] == "no_save":
                self.root.destroy()
            # If "cancel" or None, do nothing (stay open)
            
        else:
            # No custom channels, just simple confirmation
            if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
                self.root.destroy()

    def save_settings_as(self):
        """Save settings to a new file with improved default naming"""
        # Generate default filename with timestamp and configuration summary
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
        """Load settings from a file with better user feedback"""
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
                    self.log_status("Settings load cancelled by user")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
                self.log_status(f"❌ Error loading settings: {str(e)}")

    def quick_save_settings(self, slot):
        """Quick save settings to a numbered slot"""
        try:
            settings = self.get_all_settings()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            num_channels = len(self.custom_channels)
            
            settings['description'] = f"Quick save slot {slot} - {timestamp} ({num_channels} channels)"
            
            filename = f"quick_save_slot_{slot}.json"
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.log_status(f"✅ Quick saved to slot {slot} ({num_channels} channels)")
            
            # Update button indicators
            self.update_quick_save_indicators()
            
            # Brief visual feedback
            self.root.after(100, lambda: self.show_quick_feedback(f"Saved Slot {slot}!", "lightgreen"))
            
        except Exception as e:
            self.log_status(f"❌ Error quick saving to slot {slot}: {str(e)}")
            self.show_quick_feedback(f"Save Error!", "lightcoral")

    def quick_load_settings(self, slot):
        """Quick load settings from a numbered slot"""
        filename = f"quick_save_slot_{slot}.json"
        
        if not os.path.exists(filename):
            self.log_status(f"⚠️ Quick save slot {slot} is empty")
            self.show_quick_feedback(f"Slot {slot} Empty", "lightyellow")
            return
        
        try:
            with open(filename, 'r') as f:
                settings = json.load(f)
            
            num_channels = len(settings.get('custom_channels', []))
            
            # Quick load without confirmation for faster workflow
            self.restore_settings(settings)
            self.log_status(f"✅ Quick loaded from slot {slot} ({num_channels} channels)")
            
            # Update button indicators in case any changes occurred
            self.update_quick_save_indicators()
            
            # Brief visual feedback
            self.show_quick_feedback(f"Loaded Slot {slot}!", "lightblue")
            
        except Exception as e:
            self.log_status(f"❌ Error quick loading from slot {slot}: {str(e)}")
            self.show_quick_feedback(f"Load Error!", "lightcoral")

    def show_quick_feedback(self, message, color):
        """Show brief visual feedback for quick actions"""
        # Create a temporary label for feedback
        feedback_label = tk.Label(self.root, text=message, bg=color, font=("Arial", 9, "bold"))
        feedback_label.place(relx=0.5, rely=0.1, anchor="center")
        
        # Remove after 1.5 seconds
        self.root.after(1500, feedback_label.destroy)

    def reset_to_defaults(self):
        """Reset settings to default values"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset settings to default?"):
            self.custom_channels = []
            self.refresh_custom_channels_tree()
            self.log_status("Settings reset to default.")

    def get_all_settings(self):
        """Get all current settings in a single dictionary"""
        return {
            'vehicle_file': self.vehicle_file_path,
            'custom_channels': self.custom_channels,
            'output_format': self.output_format.get(),
            'last_channel_settings': {
                'name': self.new_custom_name.get(),
                'csv_file': self.new_custom_csv.get(),
                'x_column': self.new_custom_x_col.get(),
                'y_column': self.new_custom_y_col.get(),
                'z_column': self.new_custom_z_col.get(),
                'vehicle_x_channel': self.new_custom_veh_x.get(),
                'vehicle_y_channel': self.new_custom_veh_y.get(),
                'units': self.new_custom_units.get(),
                'comment': self.new_custom_comment.get()
            },
            'last_updated': datetime.now().isoformat()
        }

    def restore_settings(self, settings):
        """Restore settings from a dictionary"""
        # Load vehicle file if it exists
        if settings.get('vehicle_file') and os.path.exists(settings['vehicle_file']):
            self.vehicle_file_path = settings['vehicle_file']
            self.vehicle_status.config(text=f"Loaded: {os.path.basename(self.vehicle_file_path)}", fg="green")
            try:
                self.load_vehicle_file()
            except Exception as e:
                self.log_status(f"Error loading saved vehicle file: {str(e)}")

        # Load custom channels
        self.custom_channels = settings.get('custom_channels', [])
        self.refresh_custom_channels_tree()

        # Load output format
        if settings.get('output_format'):
            self.output_format.set(settings['output_format'])

        # Load last channel settings
        if settings.get('last_channel_settings'):
            self.restore_last_channel_settings(settings['last_channel_settings'])
            
        self.log_status("Settings loaded successfully")

    def run(self):
        """Start the application"""
        self.root.mainloop()

    def add_slot_tooltip(self, save_btn, load_btn, slot):
        """Add tooltip functionality to quick save/load buttons"""
        def show_save_tooltip(event):
            tooltip_text = f"Quick Save Slot {slot}\nSave current settings"
            self.show_tooltip(event.widget, tooltip_text)
        
        def show_load_tooltip(event):
            filename = f"quick_save_slot_{slot}.json"
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as f:
                        settings = json.load(f)
                    num_channels = len(settings.get('custom_channels', []))
                    description = settings.get('description', '')
                    tooltip_text = f"Quick Load Slot {slot}\n{num_channels} channels\n{description}"
                except:
                    tooltip_text = f"Quick Load Slot {slot}\nData available"
            else:
                tooltip_text = f"Quick Load Slot {slot}\nEmpty slot"
            self.show_tooltip(event.widget, tooltip_text)
        
        def hide_tooltip(event):
            if hasattr(self, 'tooltip_window') and self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None
        
        save_btn.bind('<Enter>', show_save_tooltip)
        save_btn.bind('<Leave>', hide_tooltip)
        load_btn.bind('<Enter>', show_load_tooltip)
        load_btn.bind('<Leave>', hide_tooltip)

    def show_tooltip(self, widget, text):
        """Show tooltip near the widget"""
        if hasattr(self, 'tooltip_window') and self.tooltip_window:
            self.tooltip_window.destroy()
        
        self.tooltip_window = tw = tk.Toplevel(widget)
        tw.wm_overrideredirect(True)
        
        # Position tooltip near the widget
        x = widget.winfo_rootx() + 25
        y = widget.winfo_rooty() + 25
        tw.geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=text, font=("Arial", 8), bg="lightyellow", 
                        relief="solid", borderwidth=1, padx=5, pady=3)
        label.pack()

    def update_quick_save_indicators(self):
        """Update the visual indicators for quick save slots"""
        for slot in range(1, 4):
            slot_has_data = os.path.exists(f"quick_save_slot_{slot}.json")
            
            if slot in self.quick_save_buttons:
                save_color = "green" if slot_has_data else "lightgreen"
                self.quick_save_buttons[slot].config(bg=save_color)
            
            if slot in self.quick_load_buttons:
                load_color = "lightblue" if slot_has_data else "lightgray"
                self.quick_load_buttons[slot].config(bg=load_color)


def main():
    """Main function"""
    app = VehicleLogChannelAppender()
    app.run()


if __name__ == "__main__":
    main()