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
        self.root.geometry("1000x700")
        
        # Data storage
        self.vehicle_file_path = None
        self.vehicle_data = None
        self.available_channels = []
        self.custom_channels = []  # List of custom channel configurations
        self.reference_timestamps = None
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the user interface with tabbed layout"""
        
        # Title
        title_label = tk.Label(self.root, text="Vehicle Log Channel Appender", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Setup tabs
        self.setup_processing_tab()
        self.setup_custom_channels_tab()
        
        # Status/Log area (outside tabs)
        log_frame = tk.LabelFrame(self.root, text="Status Log", font=("Arial", 10, "bold"))
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Create scrollable text widget
        text_frame = tk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(text_frame, height=6, wrap=tk.WORD)
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Settings buttons
        settings_frame = tk.Frame(self.root)
        settings_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        tk.Button(settings_frame, text="Save Settings", command=self.save_settings).pack(side="left", padx=5)
        tk.Button(settings_frame, text="Load Settings", command=self.load_settings).pack(side="left", padx=5)
        
        self.log_status("Application started. Please select a vehicle file and configure custom channels.")

    def setup_processing_tab(self):
        """Setup the main processing tab"""
        self.processing_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.processing_frame, text="Processing")
        
        # Vehicle file selection
        file_frame = tk.LabelFrame(self.processing_frame, text="Vehicle Log File", 
                                  font=("Arial", 12, "bold"))
        file_frame.pack(fill="x", padx=20, pady=10)
        
        vehicle_btn_frame = tk.Frame(file_frame)
        vehicle_btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.vehicle_btn = tk.Button(vehicle_btn_frame, text="Select Vehicle File (MDF/MF4/DAT/CSV)", 
                                    command=self.select_vehicle_file, bg="lightgreen")
        self.vehicle_btn.pack(side="left")
        
        self.vehicle_status = tk.Label(vehicle_btn_frame, text="No vehicle file selected", fg="red")
        self.vehicle_status.pack(side="left", padx=10)
        
        # Processing options
        options_frame = tk.LabelFrame(self.processing_frame, text="Processing Options", 
                                     font=("Arial", 12, "bold"))
        options_frame.pack(fill="x", padx=20, pady=10)
        
        # Output format selection
        format_frame = tk.Frame(options_frame)
        format_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(format_frame, text="Output Format:", font=("Arial", 10, "bold")).pack(anchor="w")
        
        self.output_format = tk.StringVar(value="mf4")
        tk.Radiobutton(format_frame, text="MF4 (Recommended for calculated channels)", 
                      variable=self.output_format, value="mf4").pack(anchor="w", padx=20)
        tk.Radiobutton(format_frame, text="CSV (For data analysis)", 
                      variable=self.output_format, value="csv").pack(anchor="w", padx=20)
        
        # Processing section
        process_frame = tk.LabelFrame(self.processing_frame, text="Process Channels", 
                                     font=("Arial", 12, "bold"))
        process_frame.pack(fill="x", padx=20, pady=10)
        
        info_frame = tk.Frame(process_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_text = ("Configure custom channels in the 'Custom Channels' tab, then process them here.\n"
                    "The tool will create calculated channels based on surface table interpolation.")
        tk.Label(info_frame, text=info_text, font=("Arial", 9), fg="blue", justify="left").pack(anchor="w")
        
        process_btn_frame = tk.Frame(process_frame)
        process_btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.process_btn = tk.Button(process_btn_frame, text="Process All Custom Channels", 
                                    command=self.process_all_channels, bg="orange", 
                                    font=("Arial", 12, "bold"))
        self.process_btn.pack()

    def setup_custom_channels_tab(self):
        """Setup the custom channels tab with proper CSV surface table configuration"""
        self.custom_channels_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.custom_channels_frame, text="Custom Channels")
        
        # Title
        title_label = tk.Label(self.custom_channels_frame, text="Custom Channel Management", 
                              font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Add new channel section
        add_frame = tk.LabelFrame(self.custom_channels_frame, text="Add New Custom Channel", 
                                 font=("Arial", 12, "bold"))
        add_frame.pack(fill="x", padx=20, pady=10)
        
        # Channel name
        name_frame = tk.Frame(add_frame)
        name_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(name_frame, text="Channel Name:", width=18, anchor="w").pack(side="left")
        self.new_custom_name = tk.Entry(name_frame, width=30)
        self.new_custom_name.pack(side="left", padx=5)
        
        # CSV Surface Table file
        csv_frame = tk.Frame(add_frame)
        csv_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(csv_frame, text="Surface Table CSV:", width=18, anchor="w").pack(side="left")
        self.new_custom_csv = tk.Entry(csv_frame, width=40)
        self.new_custom_csv.pack(side="left", padx=5)
        tk.Button(csv_frame, text="Browse", command=self.browse_custom_csv).pack(side="left", padx=5)
        
        # CSV column configuration section
        csv_config_frame = tk.LabelFrame(add_frame, text="CSV Surface Table Configuration")
        csv_config_frame.pack(fill="x", padx=10, pady=5)
        
        # X axis column (e.g., RPM)
        x_col_frame = tk.Frame(csv_config_frame)
        x_col_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(x_col_frame, text="X-axis Column (e.g., RPM):", width=25, anchor="w").pack(side="left")
        self.new_custom_x_col = AutocompleteCombobox(x_col_frame, width=25)
        self.new_custom_x_col.pack(side="left", padx=5)
        
        # Y axis column (e.g., ETASP)
        y_col_frame = tk.Frame(csv_config_frame)
        y_col_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(y_col_frame, text="Y-axis Column (e.g., ETASP):", width=25, anchor="w").pack(side="left")
        self.new_custom_y_col = AutocompleteCombobox(y_col_frame, width=25)
        self.new_custom_y_col.pack(side="left", padx=5)
        
        # Z axis column (values)
        z_col_frame = tk.Frame(csv_config_frame)
        z_col_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(z_col_frame, text="Z-axis Column (Values):", width=25, anchor="w").pack(side="left")
        self.new_custom_z_col = AutocompleteCombobox(z_col_frame, width=25)
        self.new_custom_z_col.pack(side="left", padx=5)
        
        # Vehicle log channel selection section
        veh_config_frame = tk.LabelFrame(add_frame, text="Vehicle Log Channel Selection")
        veh_config_frame.pack(fill="x", padx=10, pady=5)
        
        # Vehicle X channel
        veh_x_frame = tk.Frame(veh_config_frame)
        veh_x_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(veh_x_frame, text="Vehicle X Channel:", width=18, anchor="w").pack(side="left")
        self.new_custom_veh_x = AutocompleteCombobox(veh_x_frame, width=30)
        self.new_custom_veh_x.pack(side="left", padx=5)
        
        # Vehicle Y channel
        veh_y_frame = tk.Frame(veh_config_frame)
        veh_y_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(veh_y_frame, text="Vehicle Y Channel:", width=18, anchor="w").pack(side="left")
        self.new_custom_veh_y = AutocompleteCombobox(veh_y_frame, width=30)
        self.new_custom_veh_y.pack(side="left", padx=5)
        
        # Units and comment
        meta_frame = tk.Frame(add_frame)
        meta_frame.pack(fill="x", padx=10, pady=5)
        
        units_frame = tk.Frame(meta_frame)
        units_frame.pack(side="left", fill="x", expand=True)
        tk.Label(units_frame, text="Units:", width=8, anchor="w").pack(side="left")
        self.new_custom_units = tk.Entry(units_frame, width=15)
        self.new_custom_units.pack(side="left", padx=5)
        
        comment_frame = tk.Frame(meta_frame)
        comment_frame.pack(side="right", fill="x", expand=True)
        tk.Label(comment_frame, text="Comment:", width=10, anchor="w").pack(side="left")
        self.new_custom_comment = tk.Entry(comment_frame, width=25)
        self.new_custom_comment.pack(side="left", padx=5)
        
        # Add button
        add_btn_frame = tk.Frame(add_frame)
        add_btn_frame.pack(fill="x", padx=10, pady=10)
        tk.Button(add_btn_frame, text="Add Custom Channel", command=self.add_custom_channel,
                 bg="lightgreen", font=("Arial", 10, "bold")).pack()
        
        # Custom channels list
        list_frame = tk.LabelFrame(self.custom_channels_frame, text="Configured Custom Channels", 
                                  font=("Arial", 12, "bold"))
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create treeview for custom channels
        columns = ("Name", "CSV File", "X Col", "Y Col", "Z Col", "Veh X", "Veh Y", "Units")
        self.custom_channels_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.custom_channels_tree.heading(col, text=col)
            self.custom_channels_tree.column(col, width=120)
        
        # Scrollbar for treeview
        tree_frame = tk.Frame(list_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.custom_channels_tree.yview)
        self.custom_channels_tree.configure(yscrollcommand=scrollbar.set)
        
        self.custom_channels_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Management buttons
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Button(btn_frame, text="Edit Selected", command=self.edit_custom_channel).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_custom_channel).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Clear All", command=self.clear_custom_channels).pack(side="left", padx=5)

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
        
        # Auto-save settings to preserve the last used configuration (before clearing)
        self.save_settings()
        
        # Clear input fields
        self.clear_custom_channel_inputs()
        
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
        # Clear existing items
        for item in self.custom_channels_tree.get_children():
            self.custom_channels_tree.delete(item)
        
        # Add current custom channels
        for channel in self.custom_channels:
            self.custom_channels_tree.insert("", "end", values=(
                channel['name'],
                os.path.basename(channel['csv_file']),
                channel['x_column'],
                channel['y_column'],
                channel['z_column'],
                channel['vehicle_x_channel'],
                channel['vehicle_y_channel'],
                channel['units']
            ))

    def edit_custom_channel(self):
        """Edit the selected custom channel"""
        selection = self.custom_channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to edit!")
            return
            
        item = selection[0]
        index = self.custom_channels_tree.index(item)
        channel = self.custom_channels[index]
        
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
        del self.custom_channels[index]
        self.refresh_custom_channels_tree()

    def delete_custom_channel(self):
        """Delete the selected custom channel"""
        selection = self.custom_channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to delete!")
            return
            
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this custom channel?"):
            item = selection[0]
            index = self.custom_channels_tree.index(item)
            del self.custom_channels[index]
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
        """Save current settings to file"""
        try:
            # Capture current form values for last channel settings
            last_channel_settings = {
                'name': self.new_custom_name.get(),
                'csv_file': self.new_custom_csv.get(),
                'x_column': self.new_custom_x_col.get(),
                'y_column': self.new_custom_y_col.get(),
                'z_column': self.new_custom_z_col.get(),
                'vehicle_x_channel': self.new_custom_veh_x.get(),
                'vehicle_y_channel': self.new_custom_veh_y.get(),
                'units': self.new_custom_units.get(),
                'comment': self.new_custom_comment.get()
            }
            
            settings = {
                'vehicle_file': self.vehicle_file_path,
                'custom_channels': self.custom_channels,
                'output_format': self.output_format.get(),
                'last_channel_settings': last_channel_settings,
                'last_updated': datetime.now().isoformat()
            }
            
            with open('channel_appender_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
                
            self.log_status("Settings saved successfully")
            
        except Exception as e:
            self.log_status(f"Error saving settings: {str(e)}")

    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('channel_appender_settings.json'):
                with open('channel_appender_settings.json', 'r') as f:
                    settings = json.load(f)
                
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

    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main function"""
    app = VehicleLogChannelAppender()
    app.run()


if __name__ == "__main__":
    main()