"""
Vehicle Log Channel Appender - Enhanced Version

This program:
1. Allows selection of a single vehicle log file (CSV, .dat, MDF, MF4)
2. Allows creation of multiple custom channels based on X,Y coordinate interpolation from CSV surface tables
3. Interpolates Z values based on X and Y channels from vehicle log using CSV surface table
4. Creates new files containing only the calculated channels (avoiding signal processing warnings)
5. Saves and loads user settings and custom channel configurations

Author: Assistant
"""

import numpy as np
import pandas as pd
from asammdf import MDF, Signal
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from scipy.interpolate import griddata
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


class ChannelConfig:
    """Configuration for a custom channel"""
    def __init__(self, name="", csv_path="", x_channel="", y_channel="", unit="", comment=""):
        self.name = name
        self.csv_path = csv_path
        self.x_channel = x_channel
        self.y_channel = y_channel
        self.unit = unit
        self.comment = comment
    
    def to_dict(self):
        return {
            'name': self.name,
            'csv_path': self.csv_path,
            'x_channel': self.x_channel,
            'y_channel': self.y_channel,
            'unit': self.unit,
            'comment': self.comment
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class VehicleLogChannelAppender:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Enhanced Vehicle Log Channel Appender")
        self.root.geometry("1200x800")
        
        # Data storage
        self.vehicle_file_path = None
        self.vehicle_data = None
        self.available_channels = []
        self.reference_timestamps = None
        
        # Custom channels configuration
        self.custom_channels = []  # List of ChannelConfig objects
        
        # Settings file path
        self.settings_file = Path.cwd() / "channel_appender_settings.json"
        
        # UI elements that need to be accessible
        self.channels_frame = None
        self.log_text = None
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the enhanced user interface"""
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Main functionality
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Channel Processing")
        
        # Tab 2: Custom channels management
        self.channels_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.channels_tab, text="Custom Channels")
        
        self.setup_main_tab()
        self.setup_channels_tab()
        
    def setup_main_tab(self):
        """Setup the main processing tab"""
        
        # Title
        title_label = tk.Label(self.main_tab, text="Enhanced Vehicle Log Channel Appender", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Main frame with two columns
        main_frame = tk.Frame(self.main_tab)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Left column for controls
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        
        # Right column for log
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)
        
        # Vehicle file selection
        vehicle_frame = tk.LabelFrame(left_frame, text="Vehicle Log File", font=("Arial", 10, "bold"))
        vehicle_frame.pack(fill="x", pady=5)
        
        self.vehicle_file_label = tk.Label(vehicle_frame, text="No file selected", 
                                          wraplength=300, justify="left")
        self.vehicle_file_label.pack(pady=5)
        
        tk.Button(vehicle_frame, text="Select Vehicle File", 
                 command=self.select_vehicle_file, bg="lightblue").pack(pady=5)
        
        # Processing controls
        process_frame = tk.LabelFrame(left_frame, text="Processing", font=("Arial", 10, "bold"))
        process_frame.pack(fill="x", pady=5)
        
        tk.Button(process_frame, text="Process All Custom Channels", 
                 command=self.process_all_channels, bg="lightgreen", 
                 font=("Arial", 10, "bold")).pack(pady=10, fill="x")
        
        # Settings
        settings_frame = tk.LabelFrame(left_frame, text="Settings", font=("Arial", 10, "bold"))
        settings_frame.pack(fill="x", pady=5)
        
        tk.Button(settings_frame, text="Save Current Settings", 
                 command=self.save_settings, bg="lightyellow").pack(pady=5, fill="x")
        
        tk.Button(settings_frame, text="Load Settings", 
                 command=self.load_settings, bg="lightgray").pack(pady=5, fill="x")
        
        # Status log
        log_frame = tk.LabelFrame(right_frame, text="Processing Log", font=("Arial", 10, "bold"))
        log_frame.pack(fill="both", expand=True)
        
        # Create text widget with scrollbar
        log_text_frame = tk.Frame(log_frame)
        log_text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_text_frame, wrap="word", height=20)
        log_scrollbar = tk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Clear log button
        tk.Button(log_frame, text="Clear Log", command=self.clear_log, 
                 bg="lightcoral").pack(pady=5)
        
    def setup_channels_tab(self):
        """Setup the custom channels management tab"""
        
        # Title
        title_label = tk.Label(self.channels_tab, text="Custom Channels Configuration", 
                              font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Main frame
        main_frame = tk.Frame(self.channels_tab)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Channels list frame
        list_frame = tk.LabelFrame(main_frame, text="Configured Channels", font=("Arial", 10, "bold"))
        list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Treeview for channels list
        columns = ('name', 'csv_file', 'x_channel', 'y_channel', 'unit')
        self.channels_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # Define headings
        self.channels_tree.heading('name', text='Channel Name')
        self.channels_tree.heading('csv_file', text='CSV File')
        self.channels_tree.heading('x_channel', text='X Channel')
        self.channels_tree.heading('y_channel', text='Y Channel')
        self.channels_tree.heading('unit', text='Unit')
        
        # Configure column widths
        self.channels_tree.column('name', width=150)
        self.channels_tree.column('csv_file', width=200)
        self.channels_tree.column('x_channel', width=100)
        self.channels_tree.column('y_channel', width=100)
        self.channels_tree.column('unit', width=60)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.channels_tree.yview)
        self.channels_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.channels_tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        tree_scrollbar.pack(side="right", fill="y", pady=5)
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=5)
        
        tk.Button(buttons_frame, text="Add New Channel", 
                 command=self.add_new_channel, bg="lightgreen").pack(side="left", padx=5)
        
        tk.Button(buttons_frame, text="Edit Selected", 
                 command=self.edit_selected_channel, bg="lightyellow").pack(side="left", padx=5)
        
        tk.Button(buttons_frame, text="Delete Selected", 
                 command=self.delete_selected_channel, bg="lightcoral").pack(side="left", padx=5)
        
        tk.Button(buttons_frame, text="Refresh List", 
                 command=self.refresh_channels_list, bg="lightblue").pack(side="left", padx=5)
        
    def refresh_channels_list(self):
        """Refresh the channels list display"""
        # Clear existing items
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
        
        # Add all custom channels
        for i, channel in enumerate(self.custom_channels):
            csv_filename = Path(channel.csv_path).name if channel.csv_path else "No file"
            self.channels_tree.insert('', 'end', values=(
                channel.name,
                csv_filename,
                channel.x_channel,
                channel.y_channel,
                channel.unit
            ))
    
    def add_new_channel(self):
        """Add a new custom channel"""
        self.edit_channel_dialog(None)
    
    def edit_selected_channel(self):
        """Edit the selected channel"""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to edit.")
            return
        
        # Get the index of the selected item
        item_index = self.channels_tree.index(selection[0])
        if item_index < len(self.custom_channels):
            self.edit_channel_dialog(self.custom_channels[item_index])
    
    def delete_selected_channel(self):
        """Delete the selected channel"""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected channel?"):
            item_index = self.channels_tree.index(selection[0])
            if item_index < len(self.custom_channels):
                del self.custom_channels[item_index]
                self.refresh_channels_list()
    
    def edit_channel_dialog(self, channel_config):
        """Show dialog to edit channel configuration"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Channel Configuration")
        dialog.geometry("600x500")
        dialog.grab_set()
        
        # Channel name
        tk.Label(dialog, text="Channel Name:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        name_var = tk.StringVar(value=channel_config.name if channel_config else "")
        tk.Entry(dialog, textvariable=name_var, width=40).grid(row=0, column=1, padx=10, pady=5)
        
        # CSV file selection
        tk.Label(dialog, text="CSV Surface Table:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        csv_var = tk.StringVar(value=channel_config.csv_path if channel_config else "")
        csv_frame = tk.Frame(dialog)
        csv_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        csv_entry = tk.Entry(csv_frame, textvariable=csv_var, width=35)
        csv_entry.pack(side="left")
        
        def select_csv():
            filename = filedialog.askopenfilename(
                title="Select CSV Surface Table",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if filename:
                csv_var.set(filename)
        
        tk.Button(csv_frame, text="Browse", command=select_csv).pack(side="left", padx=(5, 0))
        
        # X and Y channel selection (will be populated when vehicle file is loaded)
        tk.Label(dialog, text="X Channel (e.g., RPM):", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        x_channel_var = tk.StringVar(value=channel_config.x_channel if channel_config else "")
        x_channel_combo = AutocompleteCombobox(dialog, textvariable=x_channel_var, width=37)
        x_channel_combo.grid(row=2, column=1, padx=10, pady=5)
        
        tk.Label(dialog, text="Y Channel (e.g., ETASP):", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", padx=10, pady=5)
        y_channel_var = tk.StringVar(value=channel_config.y_channel if channel_config else "")
        y_channel_combo = AutocompleteCombobox(dialog, textvariable=y_channel_var, width=37)
        y_channel_combo.grid(row=3, column=1, padx=10, pady=5)
        
        # Set available channels if vehicle file is loaded
        if self.available_channels:
            x_channel_combo.set_completion_list(self.available_channels)
            y_channel_combo.set_completion_list(self.available_channels)
        
        # Unit
        tk.Label(dialog, text="Unit:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", padx=10, pady=5)
        unit_var = tk.StringVar(value=channel_config.unit if channel_config else "")
        tk.Entry(dialog, textvariable=unit_var, width=40).grid(row=4, column=1, padx=10, pady=5)
        
        # Comment
        tk.Label(dialog, text="Comment:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="nw", padx=10, pady=5)
        comment_var = tk.StringVar(value=channel_config.comment if channel_config else "")
        comment_text = tk.Text(dialog, width=40, height=4)
        comment_text.grid(row=5, column=1, padx=10, pady=5)
        if channel_config and channel_config.comment:
            comment_text.insert("1.0", channel_config.comment)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        def save_channel():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Please enter a channel name.")
                return
            
            if not csv_var.get().strip():
                messagebox.showerror("Error", "Please select a CSV surface table file.")
                return
            
            if not x_channel_var.get().strip() or not y_channel_var.get().strip():
                messagebox.showerror("Error", "Please select both X and Y channels.")
                return
            
            new_config = ChannelConfig(
                name=name_var.get().strip(),
                csv_path=csv_var.get().strip(),
                x_channel=x_channel_var.get().strip(),
                y_channel=y_channel_var.get().strip(),
                unit=unit_var.get().strip(),
                comment=comment_text.get("1.0", tk.END).strip()
            )
            
            # Add or update the channel
            if channel_config:  # Editing existing
                index = self.custom_channels.index(channel_config)
                self.custom_channels[index] = new_config
            else:  # Adding new
                self.custom_channels.append(new_config)
            
            self.refresh_channels_list()
            dialog.destroy()
        
        tk.Button(button_frame, text="Save", command=save_channel, bg="lightgreen").pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="lightcoral").pack(side="left", padx=10)
        
    def select_vehicle_file(self):
        """Select vehicle log file"""
        filename = filedialog.askopenfilename(
            title="Select Vehicle Log File",
            filetypes=[
                ("All supported", "*.csv;*.dat;*.mdf;*.mf4"),
                ("CSV files", "*.csv"),
                ("DAT files", "*.dat"),
                ("MDF files", "*.mdf"),
                ("MF4 files", "*.mf4"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            self.vehicle_file_path = filename
            self.vehicle_file_label.config(text=f"Selected: {Path(filename).name}")
            self.load_vehicle_file()
    
    def load_vehicle_file(self):
        """Load the selected vehicle file and extract channel names"""
        try:
            file_ext = Path(self.vehicle_file_path).suffix.lower()
            
            if file_ext == '.csv':
                self.vehicle_data = pd.read_csv(self.vehicle_file_path)
                self.available_channels = list(self.vehicle_data.columns)
                self.log_status(f"CSV file loaded. Found {len(self.available_channels)} channels.")
            else:  # MDF/MF4/DAT
                self.vehicle_data = MDF(self.vehicle_file_path)
                # Get all channel names
                self.available_channels = []
                for group in self.vehicle_data.groups:
                    for channel in group.channels:
                        if channel.name not in self.available_channels:
                            self.available_channels.append(channel.name)
                
                self.log_status(f"MDF vehicle file loaded successfully. Found {len(self.available_channels)} channels.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load vehicle file: {str(e)}")
            self.log_status(f"Error loading vehicle file: {str(e)}")
    
    def process_all_channels(self):
        """Process all configured custom channels"""
        if not self.vehicle_data:
            messagebox.showerror("Error", "Please select a vehicle log file first!")
            return
        
        if not self.custom_channels:
            messagebox.showerror("Error", "No custom channels configured. Please add at least one channel in the Custom Channels tab.")
            return
        
        # Ask for output format
        output_format = self.ask_output_format()
        if output_format is None:
            return
        
        # Ask for raster if needed
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        raster = None
        if file_ext in ['.mdf', '.mf4', '.dat']:
            raster = self.ask_for_raster()
            if raster is None:  # User cancelled
                self.log_status("Processing cancelled by user.")
                return
        
        self.log_status(f"Starting processing of {len(self.custom_channels)} custom channels...")
        
        processed_channels = []
        failed_channels = []
        
        for i, channel_config in enumerate(self.custom_channels):
            try:
                self.log_status(f"Processing channel {i+1}/{len(self.custom_channels)}: {channel_config.name}")
                
                # Load CSV surface table for this channel
                surface_data = self.load_csv_surface_table(channel_config.csv_path)
                if surface_data is None:
                    failed_channels.append(f"{channel_config.name}: Failed to load CSV surface table")
                    continue
                
                # Extract data for this channel
                x_data, y_data, timestamps = self.extract_channel_data(
                    channel_config.x_channel, 
                    channel_config.y_channel, 
                    raster
                )
                
                if x_data is None or y_data is None:
                    failed_channels.append(f"{channel_config.name}: Failed to extract channel data")
                    continue
                
                # Interpolate Z values
                z_values = self.interpolate_channel_values(x_data, y_data, surface_data, channel_config.name)
                
                if z_values is None:
                    failed_channels.append(f"{channel_config.name}: Failed to interpolate values")
                    continue
                
                # Create signal
                signal = Signal(
                    samples=np.array(z_values, dtype=np.float64),
                    timestamps=timestamps,
                    name=channel_config.name,
                    unit=channel_config.unit,
                    comment=channel_config.comment or f"Interpolated from {channel_config.x_channel} and {channel_config.y_channel}"
                )
                
                processed_channels.append(signal)
                self.log_status(f"✓ Successfully processed {channel_config.name}")
                
            except Exception as e:
                failed_channels.append(f"{channel_config.name}: {str(e)}")
                self.log_status(f"✗ Failed to process {channel_config.name}: {str(e)}")
        
        if processed_channels:
            # Create output file with only the calculated channels
            self.create_output_file(processed_channels, output_format)
            
            success_msg = f"Successfully processed {len(processed_channels)} channels."
            if failed_channels:
                success_msg += f"\n{len(failed_channels)} channels failed."
            
            messagebox.showinfo("Processing Complete", success_msg)
        else:
            messagebox.showerror("Error", "No channels were successfully processed.")
        
        if failed_channels:
            self.log_status("Failed channels:")
            for failure in failed_channels:
                self.log_status(f"  - {failure}")
    
    def ask_output_format(self):
        """Ask user for output file format"""
        format_window = tk.Toplevel(self.root)
        format_window.title('Output Format')
        format_window.geometry('400x200')
        format_window.grab_set()
        
        tk.Label(format_window, text='Select Output Format', 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        format_var = tk.StringVar(value="mf4")
        
        tk.Radiobutton(format_window, text="MF4 (recommended for calculated channels)", 
                      variable=format_var, value="mf4").pack(pady=5)
        tk.Radiobutton(format_window, text="CSV (for data analysis)", 
                      variable=format_var, value="csv").pack(pady=5)
        
        result = [None]
        
        def confirm_format():
            result[0] = format_var.get()
            format_window.destroy()
        
        def cancel_format():
            result[0] = None
            format_window.destroy()
        
        button_frame = tk.Frame(format_window)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text='OK', command=confirm_format, 
                 bg='lightgreen').pack(side='left', padx=10)
        tk.Button(button_frame, text='Cancel', command=cancel_format, 
                 bg='lightcoral').pack(side='left', padx=10)
        
        format_window.wait_window()
        return result[0]
    
    def extract_channel_data(self, x_channel, y_channel, raster=None):
        """Extract data for the specified channels"""
        try:
            file_ext = Path(self.vehicle_file_path).suffix.lower()
            
            if file_ext == '.csv':
                x_data = pd.to_numeric(self.vehicle_data[x_channel], errors='coerce')
                y_data = pd.to_numeric(self.vehicle_data[y_channel], errors='coerce')
                timestamps = np.arange(len(x_data), dtype=np.float64)
            else:  # MDF/MF4/DAT
                if raster:
                    x_signal = self.vehicle_data.get(x_channel, raster=raster)
                    y_signal = self.vehicle_data.get(y_channel, raster=raster)
                else:
                    x_signal = self.vehicle_data.get(x_channel)
                    y_signal = self.vehicle_data.get(y_channel)
                
                x_data = x_signal.samples
                y_data = y_signal.samples
                timestamps = x_signal.timestamps
                
                # Ensure both signals have the same length
                if len(x_data) != len(y_data):
                    min_len = min(len(x_data), len(y_data))
                    x_data = x_data[:min_len]
                    y_data = y_data[:min_len]
                    timestamps = timestamps[:min_len]
                    self.log_status(f"Warning: Trimmed signals to {min_len} samples due to length mismatch")
            
            return x_data, y_data, timestamps
            
        except Exception as e:
            self.log_status(f"Error extracting channel data: {str(e)}")
            return None, None, None
    
    def load_csv_surface_table(self, csv_path):
        """Load and process CSV surface table"""
        try:
            if not os.path.exists(csv_path):
                self.log_status(f"CSV file not found: {csv_path}")
                return None
            
            # Read CSV file
            data = pd.read_csv(csv_path)
            
            # Extract x_values (first row, excluding first cell)
            x_values = pd.to_numeric(data.iloc[0, 1:], errors='coerce').values
            
            # Extract y_values (first column, excluding first cell)  
            y_values = pd.to_numeric(data.iloc[1:, 0], errors='coerce').values
            
            # Extract z_matrix (excluding first row and first column)
            z_matrix = data.iloc[1:, 1:].apply(pd.to_numeric, errors='coerce').values
            
            # Validation
            if x_values.shape[0] != z_matrix.shape[1]:
                raise ValueError(f"X values count ({x_values.shape[0]}) doesn't match Z matrix columns ({z_matrix.shape[1]})")
            
            if y_values.shape[0] != z_matrix.shape[0]:
                raise ValueError(f"Y values count ({y_values.shape[0]}) doesn't match Z matrix rows ({z_matrix.shape[0]})")
            
            return x_values, y_values, z_matrix
            
        except Exception as e:
            self.log_status(f"Error loading CSV surface table {csv_path}: {str(e)}")
            return None
    
    def interpolate_channel_values(self, x_data, y_data, surface_data, channel_name):
        """Interpolate Z values using surface table"""
        try:
            x_values, y_values, z_matrix = surface_data
            
            z_interpolated = []
            valid_points = 0
            total_points = len(x_data)
            
            for i, (x_val, y_val) in enumerate(zip(x_data, y_data)):
                if pd.notna(x_val) and pd.notna(y_val):
                    z_val = self.interpolate_z_value(x_val, y_val, x_values, y_values, z_matrix)
                    z_interpolated.append(z_val)
                    if not np.isnan(z_val):
                        valid_points += 1
                else:
                    z_interpolated.append(np.nan)
            
            self.log_status(f"{channel_name}: Interpolated {valid_points}/{total_points} valid points")
            return z_interpolated
            
        except Exception as e:
            self.log_status(f"Error interpolating values for {channel_name}: {str(e)}")
            return None
    
    def interpolate_z_value(self, x, y, x_values, y_values, z_matrix):
        """Interpolate a single Z value from the surface table"""
        try:
            # Check bounds
            if x < x_values.min() or x > x_values.max() or y < y_values.min() or y > y_values.max():
                return np.nan
            
            # Create coordinate arrays for interpolation
            X, Y = np.meshgrid(x_values, y_values)
            points = np.column_stack([X.ravel(), Y.ravel()])
            values = z_matrix.ravel()
            
            # Remove NaN values
            valid_mask = ~np.isnan(values)
            if not np.any(valid_mask):
                return np.nan
            
            points = points[valid_mask]
            values = values[valid_mask]
            
            # Interpolate
            result = griddata(points, values, (x, y), method='linear')
            
            return result if not np.isnan(result) else np.nan
            
        except Exception:
            return np.nan
    
    def create_output_file(self, signals, output_format):
        """Create output file with only the calculated channels"""
        try:
            base_name = Path(self.vehicle_file_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if output_format == "csv":
                output_path = Path(self.vehicle_file_path).parent / f"{base_name}_calculated_channels_{timestamp}.csv"
                
                # Create DataFrame with all signals
                data_dict = {}
                min_length = min(len(signal.samples) for signal in signals)
                
                # Add time column
                data_dict['Time'] = signals[0].timestamps[:min_length]
                
                # Add all signal data
                for signal in signals:
                    data_dict[signal.name] = signal.samples[:min_length]
                
                df = pd.DataFrame(data_dict)
                df.to_csv(output_path, index=False)
                
            else:  # MF4 format
                output_path = Path(self.vehicle_file_path).parent / f"{base_name}_calculated_channels_{timestamp}.mf4"
                
                with MDF() as new_mdf:
                    # Add all calculated signals in a single group
                    new_mdf.append(signals, comment="Calculated channels from surface table interpolation")
                    new_mdf.save(output_path, overwrite=True)
            
            self.log_status(f"Output file created: {output_path}")
            
        except Exception as e:
            self.log_status(f"Error creating output file: {str(e)}")
            raise
    
    def ask_for_raster(self):
        """Ask user for raster value for resampling"""
        raster_window = tk.Toplevel(self.root)
        raster_window.title('Set Time Raster')
        raster_window.geometry('480x320')
        raster_window.grab_set()
        
        tk.Label(raster_window, text='Time Raster Configuration', 
                font=('TkDefaultFont', 14, 'bold')).pack(pady=10)
        
        tk.Label(raster_window, text='The channels may have different sampling rates (rasters).\n'
                                    'You need to specify a time raster (in seconds) to resample all signals\n'
                                    'to the same time base for interpolation.\n\n'
                                    'Choose a raster that is appropriate for your measurement data:', 
                font=('TkDefaultFont', 10)).pack(pady=10)
        
        # Input frame
        input_frame = tk.Frame(raster_window)
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text='Raster (seconds):').grid(row=0, column=0, padx=5)
        raster_var = tk.DoubleVar(value=0.05)  # Default 50ms - good balance of resolution and performance
        raster_entry = tk.Entry(input_frame, textvariable=raster_var, width=15)
        raster_entry.grid(row=0, column=1, padx=5)
        
        # Suggested values
        suggestions_frame = tk.Frame(raster_window)
        suggestions_frame.pack(pady=10)
        
        tk.Label(suggestions_frame, text='Common values for automotive measurements:', font=('TkDefaultFont', 9)).pack()
        
        buttons_frame = tk.Frame(suggestions_frame)
        buttons_frame.pack()
        
        def set_raster(value):
            raster_var.set(value)
        
        tk.Button(buttons_frame, text='1ms (0.001)', command=lambda: set_raster(0.001), width=12).pack(side='left', padx=2)
        tk.Button(buttons_frame, text='10ms (0.01)', command=lambda: set_raster(0.01), width=12).pack(side='left', padx=2)
        tk.Button(buttons_frame, text='50ms (0.05)', command=lambda: set_raster(0.05), width=12).pack(side='left', padx=2)
        
        # Add a second row for more options
        buttons_frame2 = tk.Frame(suggestions_frame)
        buttons_frame2.pack(pady=2)
        
        tk.Button(buttons_frame2, text='20ms (0.02)', command=lambda: set_raster(0.02), width=12).pack(side='left', padx=2)
        tk.Button(buttons_frame2, text='100ms (0.1)', command=lambda: set_raster(0.1), width=12).pack(side='left', padx=2)
        tk.Button(buttons_frame2, text='200ms (0.2)', command=lambda: set_raster(0.2), width=12).pack(side='left', padx=2)
        
        # Result variable
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
        
        # Button frame
        button_frame = tk.Frame(raster_window)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text='OK', command=confirm_raster, 
                 bg='lightgreen', font=('TkDefaultFont', 10, 'bold')).pack(side='left', padx=10)
        tk.Button(button_frame, text='Cancel', command=cancel_raster, 
                 bg='lightcoral').pack(side='left', padx=10)
        
        # Focus on entry and bind Enter key
        raster_entry.focus()
        raster_entry.bind('<Return>', lambda e: confirm_raster())
        
        # Wait for window to close
        raster_window.wait_window()
        
        return result[0]
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            settings = {
                'vehicle_file_path': self.vehicle_file_path,
                'custom_channels': [channel.to_dict() for channel in self.custom_channels],
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.log_status(f"Settings saved to {self.settings_file}")
            messagebox.showinfo("Success", "Settings saved successfully!")
            
        except Exception as e:
            self.log_status(f"Error saving settings: {str(e)}")
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if not self.settings_file.exists():
                self.log_status("No settings file found. Using defaults.")
                return
            
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
            
            # Load vehicle file path
            if settings.get('vehicle_file_path') and os.path.exists(settings['vehicle_file_path']):
                self.vehicle_file_path = settings['vehicle_file_path']
                self.vehicle_file_label.config(text=f"Selected: {Path(self.vehicle_file_path).name}")
                self.load_vehicle_file()
            
            # Load custom channels
            if settings.get('custom_channels'):
                self.custom_channels = [ChannelConfig.from_dict(ch) for ch in settings['custom_channels']]
                self.refresh_channels_list()
            
            self.log_status(f"Settings loaded from {self.settings_file}")
            
        except Exception as e:
            self.log_status(f"Error loading settings: {str(e)}")
    
    def clear_log(self):
        """Clear the status log"""
        self.log_text.delete(1.0, tk.END)
    
    def log_status(self, message):
        """Add a message to the status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def run(self):
        """Start the application"""
        self.log_status("Enhanced Vehicle Log Channel Appender started.")
        self.log_status("Please select a vehicle file and configure custom channels.")
        self.root.mainloop()


def main():
    """Main function"""
    app = VehicleLogChannelAppender()
    app.run()


if __name__ == "__main__":
    main()