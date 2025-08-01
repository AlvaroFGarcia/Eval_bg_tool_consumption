"""
Vehicle Log Channel Appender - Modern Enhanced Version

Enhanced Version with Modern UI Design and Responsive Layout

Key Features:
- Modern responsive UI design with proper sizing
- Improved button visibility and layout
- Scrollable areas for content that extends beyond window bounds
- Better color scheme and typography
- Adaptive layout for different window sizes
- Enhanced user experience with proper spacing and padding

UI Improvements:
- Fixed window sizing to fit standard PC resolutions
- Added scrollbars where needed
- Larger, more visible buttons
- Modern color scheme
- Responsive layout that adapts to window resizing
- Better spacing and padding throughout
- Improved readability and usability
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


class ModernVehicleLogChannelAppender:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vehicle Log Channel Appender - Modern Edition")
        
        # Modern window setup - responsive sizing for standard PC resolutions
        self.root.geometry("1400x900")  # Larger default size for better visibility
        self.root.minsize(1200, 800)    # Minimum size to ensure all components are visible
        
        # Center the window on screen
        self.center_window()
        
        # Configure modern styling
        self.configure_modern_style()
        
        # Make window resizable and responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Data storage
        self.vehicle_file_path = None
        self.vehicle_data = None
        self.available_channels = []
        self.custom_channels = []
        self.reference_timestamps = None
        
        # Search and filter variables
        self.search_var = tk.StringVar()
        self.filter_vars = {}
        self.all_custom_channels = []
        
        # Tooltip window reference
        self.tooltip_window = None
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Setup the modern UI
        self.setup_modern_ui()
        self.load_settings()
        
        # Bind resize event for responsive layout
        self.root.bind('<Configure>', self.on_window_resize)
        
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def configure_modern_style(self):
        """Configure modern styling for the application"""
        # Configure ttk styles for modern appearance
        style = ttk.Style()
        style.theme_use('clam')  # Modern theme
        
        # Modern Nordic-inspired color scheme
        self.colors = {
            'primary': '#2E3440',      # Dark blue-gray
            'secondary': '#3B4252',    # Lighter blue-gray  
            'accent': '#5E81AC',       # Blue accent
            'success': '#A3BE8C',      # Green
            'warning': '#EBCB8B',      # Yellow
            'error': '#BF616A',        # Red
            'background': '#ECEFF4',   # Light background
            'surface': '#E5E9F0',      # Surface color
            'text': '#2E3440',         # Dark text
            'text_secondary': '#4C566A', # Secondary text
            'white': '#FFFFFF'         # Pure white
        }
        
        # Configure root background
        self.root.configure(bg=self.colors['background'])
        
        # Configure ttk widgets with modern styling
        style.configure('Modern.TLabel', 
                       background=self.colors['background'], 
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10))
        
        style.configure('Title.TLabel', 
                       background=self.colors['background'], 
                       foreground=self.colors['primary'],
                       font=('Segoe UI', 16, 'bold'))
        
        style.configure('Subtitle.TLabel', 
                       background=self.colors['background'], 
                       foreground=self.colors['text'],
                       font=('Segoe UI', 12, 'bold'))
        
        style.configure('Modern.TButton', 
                       background=self.colors['accent'],
                       foreground=self.colors['white'],
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 8))
        
        style.configure('Success.TButton', 
                       background=self.colors['success'],
                       foreground=self.colors['white'],
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 8))
        
        style.configure('Warning.TButton', 
                       background=self.colors['warning'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 8))
        
        style.configure('Modern.TFrame', 
                       background=self.colors['background'],
                       relief='flat')
        
        style.configure('Card.TFrame', 
                       background=self.colors['white'],
                       relief='solid',
                       borderwidth=1)
        
        style.configure('Modern.TLabelFrame', 
                       background=self.colors['background'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 11, 'bold'),
                       relief='solid',
                       borderwidth=1)
        
        style.configure('Modern.TNotebook', 
                       background=self.colors['background'],
                       borderwidth=0)
        
        style.configure('Modern.TNotebook.Tab', 
                       background=self.colors['surface'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10, 'bold'),
                       padding=(20, 10))
        
        style.configure('Modern.Treeview', 
                       background=self.colors['white'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 9),
                       rowheight=28,
                       borderwidth=1,
                       relief='solid')
        
        style.configure('Modern.Treeview.Heading',
                       background=self.colors['surface'],
                       foreground=self.colors['primary'],
                       font=('Segoe UI', 10, 'bold'))
        
        style.configure('Modern.TCombobox', 
                       background=self.colors['white'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10),
                       padding=(8, 6))
        
        style.configure('Modern.TEntry', 
                       background=self.colors['white'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10),
                       padding=(8, 6))
        
        style.configure('Modern.TCheckbutton', 
                       background=self.colors['background'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10))
        
        style.configure('Modern.TRadiobutton', 
                       background=self.colors['background'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10))
        
        # Configure scrollbars
        style.configure('Modern.Vertical.TScrollbar', 
                       background=self.colors['surface'],
                       troughcolor=self.colors['background'],
                       arrowcolor=self.colors['text'])
        
        style.configure('Modern.Horizontal.TScrollbar', 
                       background=self.colors['surface'],
                       troughcolor=self.colors['background'],
                       arrowcolor=self.colors['text'])

    def setup_modern_ui(self):
        """Setup the modern responsive user interface"""
        
        # Create main container with scrollable content
        self.main_container = ttk.Frame(self.root, style='Modern.TFrame')
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Title section
        self.setup_title_section()
        
        # Create notebook for tabs with modern styling
        self.notebook = ttk.Notebook(self.main_container, style='Modern.TNotebook')
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=(20, 0))
        
        # Setup tabs
        self.setup_processing_tab()
        self.setup_custom_channels_tab()
        
        # Status section at bottom (fixed height)
        self.setup_status_section()
        
        # Settings section
        self.setup_settings_section()
        
    def setup_title_section(self):
        """Setup the title and description section"""
        title_frame = ttk.Frame(self.main_container, style='Modern.TFrame')
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        title_frame.grid_columnconfigure(0, weight=1)
        
        # Main title
        title_label = ttk.Label(title_frame, 
                               text="🚗 Vehicle Log Channel Appender", 
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, pady=(0, 5))
        
        # Subtitle
        subtitle_label = ttk.Label(title_frame, 
                                  text="Modern Multi-Channel Processing Tool", 
                                  style='Modern.TLabel')
        subtitle_label.grid(row=1, column=0, pady=(0, 10))
        
        # Status indicator
        self.status_indicator = ttk.Label(title_frame, 
                                         text="● Ready", 
                                         style='Modern.TLabel',
                                         foreground=self.colors['success'])
        self.status_indicator.grid(row=2, column=0)
        
    def setup_processing_tab(self):
        """Setup the main processing tab with modern layout"""
        # Create scrollable frame for the processing tab
        self.processing_canvas = tk.Canvas(self.notebook, bg=self.colors['background'], highlightthickness=0)
        self.processing_scrollbar = ttk.Scrollbar(self.notebook, orient="vertical", 
                                                 command=self.processing_canvas.yview,
                                                 style='Modern.Vertical.TScrollbar')
        self.processing_frame = ttk.Frame(self.processing_canvas, style='Modern.TFrame')
        
        self.processing_frame.bind(
            "<Configure>",
            lambda e: self.processing_canvas.configure(scrollregion=self.processing_canvas.bbox("all"))
        )
        
        self.processing_canvas.create_window((0, 0), window=self.processing_frame, anchor="nw")
        self.processing_canvas.configure(yscrollcommand=self.processing_scrollbar.set)
        
        # Pack scrollable components
        self.processing_canvas.pack(side="left", fill="both", expand=True)
        self.processing_scrollbar.pack(side="right", fill="y")
        
        # Add to notebook
        self.notebook.add(self.processing_canvas, text="📊 Processing")
        
        # Configure grid weights for responsiveness
        self.processing_frame.grid_columnconfigure(0, weight=1)
        
        # Vehicle file selection card
        self.setup_file_selection_card()
        
        # Processing options card
        self.setup_processing_options_card()
        
        # Process execution card
        self.setup_process_execution_card()
        
    def setup_file_selection_card(self):
        """Setup vehicle file selection with modern card design"""
        file_card = ttk.LabelFrame(self.processing_frame, 
                                  text="📁 Vehicle Log File Selection", 
                                  style='Modern.TLabelFrame',
                                  padding=(20, 15))
        file_card.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 15))
        file_card.grid_columnconfigure(1, weight=1)
        
        # File selection button
        self.vehicle_btn = ttk.Button(file_card, 
                                     text="📂 Select Vehicle File (MDF/MF4/DAT/CSV)", 
                                     command=self.select_vehicle_file,
                                     style='Modern.TButton')
        self.vehicle_btn.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Status label
        self.vehicle_status = ttk.Label(file_card, 
                                       text="No vehicle file selected", 
                                       style='Modern.TLabel',
                                       foreground=self.colors['text_secondary'])
        self.vehicle_status.grid(row=1, column=0, columnspan=2, sticky="w")
        
    def setup_processing_options_card(self):
        """Setup processing options with modern card design"""
        options_card = ttk.LabelFrame(self.processing_frame, 
                                     text="⚙️ Processing Options", 
                                     style='Modern.TLabelFrame',
                                     padding=(20, 15))
        options_card.grid(row=1, column=0, sticky="ew", padx=20, pady=15)
        options_card.grid_columnconfigure(0, weight=1)
        
        # Output format section
        format_frame = ttk.Frame(options_card, style='Modern.TFrame')
        format_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        format_label = ttk.Label(format_frame, 
                                text="Output Format:", 
                                style='Subtitle.TLabel')
        format_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        self.output_format = tk.StringVar(value="mf4")
        
        mf4_radio = ttk.Radiobutton(format_frame, 
                                   text="📊 MF4 (Recommended for calculated channels)", 
                                   variable=self.output_format, 
                                   value="mf4",
                                   style='Modern.TRadiobutton')
        mf4_radio.grid(row=1, column=0, sticky="w", padx=20, pady=2)
        
        csv_radio = ttk.Radiobutton(format_frame, 
                                   text="📈 CSV (For data analysis)", 
                                   variable=self.output_format, 
                                   value="csv",
                                   style='Modern.TRadiobutton')
        csv_radio.grid(row=2, column=0, sticky="w", padx=20, pady=2)
        
    def setup_process_execution_card(self):
        """Setup process execution with modern card design"""
        process_card = ttk.LabelFrame(self.processing_frame, 
                                     text="🚀 Execute Processing", 
                                     style='Modern.TLabelFrame',
                                     padding=(20, 15))
        process_card.grid(row=2, column=0, sticky="ew", padx=20, pady=15)
        process_card.grid_columnconfigure(0, weight=1)
        
        # Info text
        info_text = ("Configure custom channels in the 'Custom Channels' tab, then process them here.\n"
                    "The tool will create calculated channels based on surface table interpolation.")
        info_label = ttk.Label(process_card, 
                              text=info_text, 
                              style='Modern.TLabel',
                              justify="left")
        info_label.grid(row=0, column=0, sticky="w", pady=(0, 15))
        
        # Process button
        self.process_btn = ttk.Button(process_card, 
                                     text="🚀 Process All Custom Channels", 
                                     command=self.process_all_channels,
                                     style='Success.TButton')
        self.process_btn.grid(row=1, column=0, pady=10)
        
    def setup_custom_channels_tab(self):
        """Setup the custom channels tab with modern scrollable layout"""
        # Create scrollable frame for the custom channels tab
        self.channels_canvas = tk.Canvas(self.notebook, bg=self.colors['background'], highlightthickness=0)
        self.channels_scrollbar = ttk.Scrollbar(self.notebook, orient="vertical", 
                                               command=self.channels_canvas.yview,
                                               style='Modern.Vertical.TScrollbar')
        self.custom_channels_frame = ttk.Frame(self.channels_canvas, style='Modern.TFrame')
        
        self.custom_channels_frame.bind(
            "<Configure>",
            lambda e: self.channels_canvas.configure(scrollregion=self.channels_canvas.bbox("all"))
        )
        
        self.channels_canvas.create_window((0, 0), window=self.custom_channels_frame, anchor="nw")
        self.channels_canvas.configure(yscrollcommand=self.channels_scrollbar.set)
        
        # Pack scrollable components
        self.channels_canvas.pack(side="left", fill="both", expand=True)
        self.channels_scrollbar.pack(side="right", fill="y")
        
        # Add to notebook
        self.notebook.add(self.channels_canvas, text="🔧 Custom Channels")
        
        # Configure grid weights
        self.custom_channels_frame.grid_columnconfigure(0, weight=1)
        
        # Setup channel configuration sections
        self.setup_add_channel_card()
        self.setup_channels_list_card()
        
    def setup_add_channel_card(self):
        """Setup add new channel card with modern design"""
        add_card = ttk.LabelFrame(self.custom_channels_frame, 
                                 text="➕ Add New Custom Channel", 
                                 style='Modern.TLabelFrame',
                                 padding=(20, 15))
        add_card.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 15))
        add_card.grid_columnconfigure(1, weight=1)
        
        # Channel name
        name_label = ttk.Label(add_card, text="Channel Name:", style='Modern.TLabel')
        name_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.new_custom_name = ttk.Entry(add_card, style='Modern.TEntry', width=30)
        self.new_custom_name.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))
        
        # CSV Surface Table file
        csv_label = ttk.Label(add_card, text="Surface Table CSV:", style='Modern.TLabel')
        csv_label.grid(row=1, column=0, sticky="w", pady=(0, 10))
        
        csv_frame = ttk.Frame(add_card, style='Modern.TFrame')
        csv_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))
        csv_frame.grid_columnconfigure(0, weight=1)
        
        self.new_custom_csv = ttk.Entry(csv_frame, style='Modern.TEntry')
        self.new_custom_csv.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        csv_browse_btn = ttk.Button(csv_frame, text="📁 Browse", 
                                   command=self.browse_custom_csv,
                                   style='Modern.TButton')
        csv_browse_btn.grid(row=0, column=1)
        
        # CSV Configuration section
        csv_config_card = ttk.LabelFrame(add_card, 
                                        text="📊 CSV Surface Table Configuration", 
                                        style='Modern.TLabelFrame',
                                        padding=(15, 10))
        csv_config_card.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15, 10))
        csv_config_card.grid_columnconfigure(1, weight=1)
        
        # X, Y, Z columns
        x_label = ttk.Label(csv_config_card, text="X-axis Column (e.g., RPM):", style='Modern.TLabel')
        x_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.new_custom_x_col = AutocompleteCombobox(csv_config_card, width=25)
        self.new_custom_x_col.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 8))
        
        y_label = ttk.Label(csv_config_card, text="Y-axis Column (e.g., ETASP):", style='Modern.TLabel')
        y_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.new_custom_y_col = AutocompleteCombobox(csv_config_card, width=25)
        self.new_custom_y_col.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 8))
        
        z_label = ttk.Label(csv_config_card, text="Z-axis Column (Values):", style='Modern.TLabel')
        z_label.grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.new_custom_z_col = AutocompleteCombobox(csv_config_card, width=25)
        self.new_custom_z_col.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(0, 8))
        
        # Vehicle Channel Selection section
        veh_config_card = ttk.LabelFrame(add_card, 
                                        text="🚗 Vehicle Log Channel Selection", 
                                        style='Modern.TLabelFrame',
                                        padding=(15, 10))
        veh_config_card.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 15))
        veh_config_card.grid_columnconfigure(1, weight=1)
        
        veh_x_label = ttk.Label(veh_config_card, text="Vehicle X Channel:", style='Modern.TLabel')
        veh_x_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.new_custom_veh_x = AutocompleteCombobox(veh_config_card, width=30)
        self.new_custom_veh_x.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 8))
        
        veh_y_label = ttk.Label(veh_config_card, text="Vehicle Y Channel:", style='Modern.TLabel')
        veh_y_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.new_custom_veh_y = AutocompleteCombobox(veh_config_card, width=30)
        self.new_custom_veh_y.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 8))
        
        # Units and comment
        meta_frame = ttk.Frame(add_card, style='Modern.TFrame')
        meta_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        meta_frame.grid_columnconfigure(1, weight=1)
        meta_frame.grid_columnconfigure(3, weight=1)
        
        units_label = ttk.Label(meta_frame, text="Units:", style='Modern.TLabel')
        units_label.grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.new_custom_units = ttk.Entry(meta_frame, style='Modern.TEntry', width=15)
        self.new_custom_units.grid(row=0, column=1, sticky="ew", padx=(0, 20))
        
        comment_label = ttk.Label(meta_frame, text="Comment:", style='Modern.TLabel')
        comment_label.grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.new_custom_comment = ttk.Entry(meta_frame, style='Modern.TEntry', width=25)
        self.new_custom_comment.grid(row=0, column=3, sticky="ew")
        
        # Add button and preserve settings
        add_btn_frame = ttk.Frame(add_card, style='Modern.TFrame')
        add_btn_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        add_btn_frame.grid_columnconfigure(1, weight=1)
        
        self.preserve_settings = tk.BooleanVar(value=True)
        preserve_check = ttk.Checkbutton(add_btn_frame, 
                                        text="Keep settings after adding channel", 
                                        variable=self.preserve_settings,
                                        style='Modern.TCheckbutton')
        preserve_check.grid(row=0, column=0, sticky="w")
        
        add_btn = ttk.Button(add_btn_frame, 
                            text="➕ Add Custom Channel", 
                            command=self.add_custom_channel,
                            style='Success.TButton')
        add_btn.grid(row=0, column=2, sticky="e")
        
    def setup_channels_list_card(self):
        """Setup configured channels list with modern design"""
        list_card = ttk.LabelFrame(self.custom_channels_frame, 
                                  text="📋 Configured Custom Channels", 
                                  style='Modern.TLabelFrame',
                                  padding=(20, 15))
        list_card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(15, 20))
        list_card.grid_rowconfigure(2, weight=1)
        list_card.grid_columnconfigure(0, weight=1)
        
        # Search and filter section
        search_frame = ttk.Frame(list_card, style='Modern.TFrame')
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        search_frame.grid_columnconfigure(1, weight=1)
        
        search_label = ttk.Label(search_frame, text="🔍 Search:", style='Modern.TLabel')
        search_label.grid(row=0, column=0, sticky="w")
        
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, 
                                style='Modern.TEntry', width=30)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(10, 10))
        search_entry.bind('<KeyRelease>', self.on_search_change)
        
        clear_btn = ttk.Button(search_frame, text="🗑️ Clear", 
                              command=self.clear_search,
                              style='Modern.TButton')
        clear_btn.grid(row=0, column=2, padx=(0, 10))
        
        filters_btn = ttk.Button(search_frame, text="🔧 Filters", 
                                command=self.setup_filters,
                                style='Modern.TButton')
        filters_btn.grid(row=0, column=3)
        
        # Create scrollable treeview container
        tree_container = ttk.Frame(list_card, style='Modern.TFrame')
        tree_container.grid(row=2, column=0, sticky="nsew", pady=(15, 0))
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Create treeview with modern styling
        columns = ("Name", "CSV File", "X Col", "Y Col", "Z Col", "Veh X", "Veh Y", "Units")
        self.custom_channels_tree = ttk.Treeview(tree_container, 
                                                columns=columns, 
                                                show="headings",
                                                style='Modern.Treeview',
                                                height=10)
        
        # Configure column widths
        column_widths = {"Name": 120, "CSV File": 150, "X Col": 80, "Y Col": 80, 
                        "Z Col": 80, "Veh X": 120, "Veh Y": 120, "Units": 80}
        
        for col in columns:
            self.custom_channels_tree.heading(col, text=col)
            self.custom_channels_tree.column(col, width=column_widths.get(col, 100))
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", 
                                   command=self.custom_channels_tree.yview,
                                   style='Modern.Vertical.TScrollbar')
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", 
                                   command=self.custom_channels_tree.xview,
                                   style='Modern.Horizontal.TScrollbar')
        
        self.custom_channels_tree.configure(yscrollcommand=v_scrollbar.set, 
                                           xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.custom_channels_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Management buttons
        btn_frame = ttk.Frame(list_card, style='Modern.TFrame')
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(15, 0))
        
        edit_btn = ttk.Button(btn_frame, text="✏️ Edit Selected", 
                             command=self.edit_custom_channel,
                             style='Modern.TButton')
        edit_btn.pack(side="left", padx=(0, 10))
        
        delete_btn = ttk.Button(btn_frame, text="🗑️ Delete Selected", 
                               command=self.delete_custom_channel,
                               style='Warning.TButton')
        delete_btn.pack(side="left", padx=(0, 10))
        
        clear_all_btn = ttk.Button(btn_frame, text="🧹 Clear All", 
                                  command=self.clear_custom_channels,
                                  style='Warning.TButton')
        clear_all_btn.pack(side="left")
        
        # Initialize filter variables
        for col in columns:
            self.filter_vars[col] = tk.StringVar()
            
    def setup_status_section(self):
        """Setup status log section with modern design"""
        status_card = ttk.LabelFrame(self.main_container, 
                                    text="📄 Status Log", 
                                    style='Modern.TLabelFrame',
                                    padding=(20, 15))
        status_card.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        status_card.grid_rowconfigure(0, weight=1)
        status_card.grid_columnconfigure(0, weight=1)
        
        # Create scrollable text widget
        text_container = ttk.Frame(status_card, style='Modern.TFrame')
        text_container.grid(row=0, column=0, sticky="nsew")
        text_container.grid_rowconfigure(0, weight=1)
        text_container.grid_columnconfigure(0, weight=1)
        
        self.log_text = tk.Text(text_container, 
                               height=6, 
                               wrap=tk.WORD,
                               bg=self.colors['white'],
                               fg=self.colors['text'],
                               font=('Consolas', 9),
                               relief='solid',
                               borderwidth=1)
        
        log_scrollbar = ttk.Scrollbar(text_container, orient="vertical", 
                                     command=self.log_text.yview,
                                     style='Modern.Vertical.TScrollbar')
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        
    def setup_settings_section(self):
        """Setup settings management section with modern design"""
        settings_card = ttk.Frame(self.main_container, style='Modern.TFrame')
        settings_card.grid(row=3, column=0, sticky="ew", pady=(15, 0))
        settings_card.grid_columnconfigure(1, weight=1)
        
        # Auto-save indicator
        auto_save_frame = ttk.Frame(settings_card, style='Modern.TFrame')
        auto_save_frame.grid(row=0, column=0, sticky="w")
        
        auto_save_label = ttk.Label(auto_save_frame, 
                                   text="💾 Auto-save: ON", 
                                   style='Modern.TLabel',
                                   foreground=self.colors['success'])
        auto_save_label.pack(side="left", padx=(0, 5))
        
        auto_indicator = ttk.Label(auto_save_frame, 
                                  text="●", 
                                  style='Modern.TLabel',
                                  foreground=self.colors['success'])
        auto_indicator.pack(side="left")
        
        # Settings buttons
        settings_btn_frame = ttk.Frame(settings_card, style='Modern.TFrame')
        settings_btn_frame.grid(row=0, column=2, sticky="e")
        
        save_as_btn = ttk.Button(settings_btn_frame, 
                                text="💾 Save Settings As...", 
                                command=self.save_settings_as,
                                style='Success.TButton')
        save_as_btn.pack(side="left", padx=(0, 10))
        
        load_btn = ttk.Button(settings_btn_frame, 
                             text="📁 Load Settings From...", 
                             command=self.load_settings_from,
                             style='Modern.TButton')
        load_btn.pack(side="left", padx=(0, 10))
        
        reset_btn = ttk.Button(settings_btn_frame, 
                              text="🔄 Reset", 
                              command=self.reset_to_defaults,
                              style='Warning.TButton')
        reset_btn.pack(side="left")
        
        # Store references for quick save/load functionality
        self.quick_save_buttons = {}
        self.quick_load_buttons = {}
        
        # Quick save/load section
        quick_frame = ttk.Frame(settings_card, style='Modern.TFrame')
        quick_frame.grid(row=0, column=1, sticky="e", padx=(10, 10))
        
        quick_label = ttk.Label(quick_frame, text="Quick:", style='Modern.TLabel')
        quick_label.pack(side="left", padx=(0, 10))
        
        for i in range(1, 4):
            slot_frame = ttk.Frame(quick_frame, style='Modern.TFrame')
            slot_frame.pack(side="left", padx=2)
            
            slot_has_data = os.path.exists(f"quick_save_slot_{i}.json")
            save_style = 'Success.TButton' if not slot_has_data else 'Modern.TButton'
            load_style = 'Modern.TButton' if slot_has_data else 'Warning.TButton'
            
            save_btn = ttk.Button(slot_frame, 
                                 text=f"S{i}", 
                                 command=lambda slot=i: self.quick_save_settings(slot),
                                 style=save_style,
                                 width=3)
            save_btn.pack(side="top", pady=(0, 2))
            self.quick_save_buttons[i] = save_btn
            
            load_btn = ttk.Button(slot_frame, 
                                 text=f"L{i}", 
                                 command=lambda slot=i: self.quick_load_settings(slot),
                                 style=load_style,
                                 width=3)
            load_btn.pack(side="top")
            self.quick_load_buttons[i] = load_btn
            
            self.add_slot_tooltip(save_btn, load_btn, i)
        
        # Log initial status
        self.log_status("🚀 Modern Vehicle Log Channel Appender started successfully!")
        self.log_status("Please select a vehicle file and configure custom channels.")
        
    def on_window_resize(self, event):
        """Handle window resize events for responsive layout"""
        if event.widget == self.root:
            # Update canvas scroll regions
            if hasattr(self, 'processing_canvas'):
                self.processing_canvas.configure(scrollregion=self.processing_canvas.bbox("all"))
            if hasattr(self, 'channels_canvas'):
                self.channels_canvas.configure(scrollregion=self.channels_canvas.bbox("all"))
    
    # Placeholder methods for functionality (to be implemented)
    def select_vehicle_file(self):
        """Select vehicle log file"""
        self.log_status("🔍 File selection not yet implemented in this demo")
        
    def browse_custom_csv(self):
        """Browse for CSV surface table file"""
        self.log_status("📁 CSV browsing not yet implemented in this demo")
        
    def add_custom_channel(self):
        """Add a new custom channel configuration"""
        self.log_status("➕ Add channel functionality not yet implemented in this demo")
        
    def edit_custom_channel(self):
        """Edit the selected custom channel"""
        self.log_status("✏️ Edit channel functionality not yet implemented in this demo")
        
    def delete_custom_channel(self):
        """Delete the selected custom channel"""
        self.log_status("🗑️ Delete channel functionality not yet implemented in this demo")
        
    def clear_custom_channels(self):
        """Clear all custom channels"""
        self.log_status("🧹 Clear all functionality not yet implemented in this demo")
        
    def process_all_channels(self):
        """Process all configured custom channels"""
        self.log_status("🚀 Channel processing not yet implemented in this demo")
        
    def on_search_change(self, event=None):
        """Handle search text changes"""
        self.log_status(f"🔍 Searching for: {self.search_var.get()}")
        
    def clear_search(self):
        """Clear search field"""
        self.search_var.set("")
        self.log_status("🗑️ Search cleared")
        
    def setup_filters(self):
        """Open filter setup dialog"""
        self.log_status("🔧 Filter setup not yet implemented in this demo")
        
    def save_settings_as(self):
        """Save settings to a new file"""
        self.log_status("💾 Save settings not yet implemented in this demo")
        
    def load_settings_from(self):
        """Load settings from a file"""
        self.log_status("📁 Load settings not yet implemented in this demo")
        
    def reset_to_defaults(self):
        """Reset settings to default values"""
        self.log_status("🔄 Reset to defaults not yet implemented in this demo")
        
    def quick_save_settings(self, slot):
        """Quick save settings to a numbered slot"""
        self.log_status(f"💾 Quick save to slot {slot} not yet implemented in this demo")
        
    def quick_load_settings(self, slot):
        """Quick load settings from a numbered slot"""
        self.log_status(f"📁 Quick load from slot {slot} not yet implemented in this demo")
        
    def load_settings(self):
        """Load settings from default file"""
        self.log_status("📁 Loading default settings...")
        
    def add_slot_tooltip(self, save_btn, load_btn, slot):
        """Add tooltip functionality to quick save/load buttons"""
        # Tooltip functionality placeholder
        pass
        
    def on_closing(self):
        """Handle window closing event"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit the Modern Vehicle Log Channel Appender?"):
            self.root.destroy()
    
    def log_status(self, message):
        """Add a timestamped message to the status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
        
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main function"""
    app = ModernVehicleLogChannelAppender()
    app.run()


if __name__ == "__main__":
    main()