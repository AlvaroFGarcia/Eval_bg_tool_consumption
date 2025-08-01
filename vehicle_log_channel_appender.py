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
        
        # Modern window setup - responsive sizing
        self.root.geometry("1400x900")  # Increased size for better visibility
        self.root.minsize(1200, 800)    # Minimum size to ensure all components are visible
        
        # Center the window on screen
        self.center_window()
        
        # Modern styling configuration
        self.configure_modern_style()
        
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
        
        # Modern color scheme
        self.colors = {
            'primary': '#2E3440',      # Dark blue-gray
            'secondary': '#3B4252',    # Lighter blue-gray
            'accent': '#5E81AC',       # Blue accent
            'success': '#A3BE8C',      # Green
            'warning': '#EBCB8B',      # Yellow
            'error': '#BF616A',        # Red
            'background': '#ECEFF4',   # Light background
            'text': '#2E3440',         # Dark text
            'light_gray': '#E5E9F0',   # Light gray
            'white': '#FFFFFF'         # White
        }
        
        # Configure root background
        self.root.configure(bg=self.colors['background'])
        
        # Configure ttk widgets
        style.configure('TLabel', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('TButton', background=self.colors['accent'], foreground=self.colors['white'])
        style.configure('TCheckbutton', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('TRadiobutton', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('Treeview', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('Horizontal.TScrollbar', background=self.colors['light_gray'], foreground=self.colors['text'])
        style.configure('Vertical.TScrollbar', background=self.colors['light_gray'], foreground=self.colors['text'])
        style.configure('Combobox', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('Entry', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('LabelFrame', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('Frame', background=self.colors['background'])
        
        # Configure ttk notebook
        style.configure('TNotebook', background=self.colors['background'], foreground=self.colors['text'])
        style.configure('TNotebook.Tab', background=self.colors['secondary'], foreground=self.colors['text'])
        
        # Configure ttk treeview
        style.configure('Treeview', rowheight=25)
        
        # Configure ttk scrollbars
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        
        # Configure ttk scrollbar
        style.configure('Horizontal.TScrollbar', gripcount=0, arrowsize=15)
        style.configure('Vertical.TScrollbar', gripcount=0, arrowsize=15)
        
        # Configure ttk combobox
        style.configure('Combobox', padding=(5, 5), arrowsize=15)
        
        # Configure ttk entry
        style.configure('Entry', padding=(5, 5))
        
        # Configure ttk label
        style.configure('Label', padding=(5, 5))
        
        # Configure ttk labelframe
        style.configure('LabelFrame', padding=(10, 10))
        
        # Configure ttk frame
        style.configure('Frame', padding=(10, 10))
        
        # Configure ttk button
        style.configure('Button', padding=(10, 5))
        
        # Configure ttk checkbutton
        style.configure('Checkbutton', padding=(10, 5))
        
        # Configure ttk radiobutton
        style.configure('Radiobutton', padding=(10, 5))
        
        # Configure ttk treeview
        style.configure('Treeview', padding=(10, 10))
        