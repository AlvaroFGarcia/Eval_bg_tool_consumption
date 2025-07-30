"""
Vehicle Log Channel Appender

This program:
1. Allows selection of a single vehicle log file (CSV, .dat, MDF, MF4)
2. Allows selection of ETASP, RPM channels from the file
3. Loads a CSV surface table for Z value lookup
4. Interpolates Z values based on ETASP and RPM from vehicle log using CSV surface table
5. Appends the calculated Z channel back to the original file

Author: Assistant
"""

import numpy as np
import pandas as pd
from asammdf import MDF, Signal
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from scipy.interpolate import griddata


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
import tempfile
import shutil
from pathlib import Path
import json

class VehicleLogChannelAppender:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Fuel Consumption Evaluation Tool")
        self.root.geometry("800x600")
        
        # Data storage
        self.vehicle_file_path = None
        self.csv_surface_path = None
        self.vehicle_data = None
        self.surface_data = None  # This will store the loaded surface table (x_values, y_values, z_matrix)
        self.available_channels = []
        self.reference_timestamps = None  # Store reference timestamps for MDF files
        
        # Selected parameters
        self.rpm_channel = tk.StringVar()
        self.etasp_channel = tk.StringVar()
        self.new_channel_name = tk.StringVar(value="Calculated_Fuel_Consumption")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        
        # Title
        title_label = tk.Label(self.root, text="Fuel Consumption Evaluation Tool", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Step 1: Select CSV Surface Table
        step1_frame = tk.LabelFrame(main_frame, text="Step 1: Select Surface Table CSV (defines RPM/ETASP ranges)", 
                                   font=("Arial", 12, "bold"))
        step1_frame.pack(fill="x", pady=5)
        
        csv_btn_frame = tk.Frame(step1_frame)
        csv_btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.csv_btn = tk.Button(csv_btn_frame, text="Select Surface Table CSV File", 
                                command=self.select_csv_file, bg="lightblue")
        self.csv_btn.pack(side="left")
        
        self.csv_status = tk.Label(csv_btn_frame, text="No CSV file selected", 
                                  fg="red")
        self.csv_status.pack(side="left", padx=10)
        
        # Step 2: Select Vehicle Log File
        step2_frame = tk.LabelFrame(main_frame, text="Step 2: Select Vehicle Log Files", 
                                   font=("Arial", 12, "bold"))
        step2_frame.pack(fill="x", pady=5)
        
        vehicle_btn_frame = tk.Frame(step2_frame)
        vehicle_btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.vehicle_btn = tk.Button(vehicle_btn_frame, text="Select MDF/MF4/DAT Files", 
                                    command=self.select_vehicle_file, bg="lightgreen")
        self.vehicle_btn.pack(side="left")
        
        self.vehicle_status = tk.Label(vehicle_btn_frame, text="No MDF/MF4/DAT file selected", 
                                      fg="red")
        self.vehicle_status.pack(side="left", padx=10)
        
        # Step 3: Select Parameters
        step3_frame = tk.LabelFrame(main_frame, text="Step 3: Select Parameters", 
                                   font=("Arial", 12, "bold"))
        step3_frame.pack(fill="x", pady=5)
        
        params_frame = tk.Frame(step3_frame)
        params_frame.pack(fill="x", padx=10, pady=10)
        
        # RPM Channel selection
        rpm_frame = tk.Frame(params_frame)
        rpm_frame.pack(fill="x", pady=2)
        tk.Label(rpm_frame, text="RPM Channel:", width=15, anchor="w").pack(side="left")
        self.rpm_combo = AutocompleteCombobox(rpm_frame, textvariable=self.rpm_channel, width=30)
        self.rpm_combo.pack(side="left", padx=5)
        
        # ETASP Channel selection
        etasp_frame = tk.Frame(params_frame)
        etasp_frame.pack(fill="x", pady=2)
        tk.Label(etasp_frame, text="ETASP Channel:", width=15, anchor="w").pack(side="left")
        self.etasp_combo = AutocompleteCombobox(etasp_frame, textvariable=self.etasp_channel, width=30)
        self.etasp_combo.pack(side="left", padx=5)
        
        # New channel name
        name_frame = tk.Frame(params_frame)
        name_frame.pack(fill="x", pady=2)
        tk.Label(name_frame, text="New Channel Name:", width=15, anchor="w").pack(side="left")
        tk.Entry(name_frame, textvariable=self.new_channel_name, width=30).pack(side="left", padx=5)
        
        # Step 4: Process
        step4_frame = tk.LabelFrame(main_frame, text="Step 4: Process and Append Channel", 
                                   font=("Arial", 12, "bold"))
        step4_frame.pack(fill="x", pady=5)
        
        # Add explanation about raster handling
        info_frame = tk.Frame(step4_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_text = ("Note: For MDF/MF4/DAT files, you will be asked to specify a time raster\n"
                    "to handle different sampling rates between RPM and ETASP channels.")
        tk.Label(info_frame, text=info_text, font=("Arial", 9), fg="blue", justify="left").pack(anchor="w")
        
        process_frame = tk.Frame(step4_frame)
        process_frame.pack(fill="x", padx=10, pady=10)
        
        self.process_btn = tk.Button(process_frame, text="Process and Append Channel", 
                                    command=self.process_and_append, bg="orange", 
                                    font=("Arial", 10, "bold"))
        self.process_btn.pack()
        
        # Status/Log area
        log_frame = tk.LabelFrame(main_frame, text="Status Log", font=("Arial", 10, "bold"))
        log_frame.pack(fill="both", expand=True, pady=5)
        
        # Create scrollable text widget
        text_frame = tk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(text_frame, height=8, wrap=tk.WORD)
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.log_status("Application started. Please select a CSV surface table file.")
        
    def select_csv_file(self):
        """Select CSV surface table file and configure parameters"""
        file_path = filedialog.askopenfilename(
            title="Select Surface Table CSV File",
            filetypes=[("CSV Files", "*.csv")]
        )
        
        if not file_path:
            return
            
        self.csv_surface_path = file_path
        self.csv_status.config(text=f"CSV selected: {os.path.basename(file_path)}", fg="green")
        self.log_status(f"Selected CSV surface table: {os.path.basename(file_path)}")
        
        try:
            # Load CSV structure for column selection
            df = pd.read_csv(file_path, nrows=1)
            column_names = df.columns.tolist()
            self.surface_data = self.select_csv_surface_parameters(column_names, file_path)
            
            if self.surface_data:
                self.log_status("Surface table loaded and configured successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV file: {str(e)}")
            self.csv_status.config(text="No CSV file selected", fg="red")
            self.csv_surface_path = None
            self.log_status(f"Error loading CSV: {str(e)}")

    def select_csv_surface_parameters(self, column_names, csv_file_path):
        """Select CSV surface table parameters and load the surface data"""
        columns_window = tk.Toplevel(self.root)
        columns_window.title('Configure Surface Table CSV')
        columns_window.geometry('500x700')
        columns_window.grab_set()  # Make it modal
        
        tk.Label(columns_window, text='Configure Surface Table Parameters', 
                font=('TkDefaultFont', 14, 'bold')).pack(pady=10)
        tk.Label(columns_window, text='Select the columns for X, Y, and Z axes:', 
                font=('TkDefaultFont', 12)).pack(pady=10)
        
        # Load previous CSV column selections from config
        csv_config = {}
        if os.path.exists('fuel_config.json'):
            try:
                with open('fuel_config.json', 'r') as f:
                    config_data = json.load(f)
                    csv_config = config_data.get('csv_columns', {})
            except:
                pass
        
        # X-axis (RPM)
        tk.Label(columns_window, text='X-axis (RPM):').pack(pady=5)
        x_var = tk.StringVar()
        x_combobox = ttk.Combobox(columns_window, textvariable=x_var, values=column_names, state='readonly')
        if csv_config.get('x_column') in column_names:
            x_var.set(csv_config['x_column'])
        x_combobox.pack(pady=5)
        
        # Y-axis (ETASP)
        tk.Label(columns_window, text='Y-axis (ETASP):').pack(pady=5)
        y_var = tk.StringVar()
        y_combobox = ttk.Combobox(columns_window, textvariable=y_var, values=column_names, state='readonly')
        if csv_config.get('y_column') in column_names:
            y_var.set(csv_config['y_column'])
        y_combobox.pack(pady=5)
        
        # Z-axis (Results)
        tk.Label(columns_window, text='Z-axis (Results):').pack(pady=5)
        z_var = tk.StringVar()
        z_combobox = ttk.Combobox(columns_window, textvariable=z_var, values=column_names, state='readonly')
        if csv_config.get('z_column') in column_names:
            z_var.set(csv_config['z_column'])
        z_combobox.pack(pady=5)
        
        # Separator
        tk.Frame(columns_window, height=2, bg='gray').pack(fill='x', pady=10)
        
        # Interpolation Parameters
        tk.Label(columns_window, text='Interpolation Parameters:', 
                font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
        
        # RPM range frame
        rpm_frame = tk.Frame(columns_window)
        rpm_frame.pack(pady=5)
        
        tk.Label(rpm_frame, text='RPM Min:').grid(row=0, column=0, padx=5)
        rpm_min_var = tk.DoubleVar(value=csv_config.get('rpm_min', 1000.0))
        tk.Entry(rpm_frame, textvariable=rpm_min_var, width=10).grid(row=0, column=1, padx=5)
        
        tk.Label(rpm_frame, text='RPM Max:').grid(row=0, column=2, padx=5)
        rpm_max_var = tk.DoubleVar(value=csv_config.get('rpm_max', 4000.0))
        tk.Entry(rpm_frame, textvariable=rpm_max_var, width=10).grid(row=0, column=3, padx=5)
        
        tk.Label(rpm_frame, text='RPM Intervals:').grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        rpm_intervals_var = tk.IntVar(value=csv_config.get('rpm_intervals', 50))
        tk.Entry(rpm_frame, textvariable=rpm_intervals_var, width=10).grid(row=1, column=2, columnspan=2, padx=5, pady=5)
        
        # ETASP Interpolation Parameters
        tk.Label(columns_window, text='ETASP Parameters:', 
                font=('TkDefaultFont', 12, 'bold')).pack(pady=(15,5))
        
        # ETASP range frame
        etasp_frame = tk.Frame(columns_window)
        etasp_frame.pack(pady=5)
        
        tk.Label(etasp_frame, text='ETASP Min:').grid(row=0, column=0, padx=5)
        etasp_min_var = tk.DoubleVar(value=csv_config.get('etasp_min', 0.0))
        tk.Entry(etasp_frame, textvariable=etasp_min_var, width=10).grid(row=0, column=1, padx=5)
        
        tk.Label(etasp_frame, text='ETASP Max:').grid(row=0, column=2, padx=5)
        etasp_max_var = tk.DoubleVar(value=csv_config.get('etasp_max', 1.0))
        tk.Entry(etasp_frame, textvariable=etasp_max_var, width=10).grid(row=0, column=3, padx=5)
        
        tk.Label(etasp_frame, text='Number of Intervals:').grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        etasp_intervals_var = tk.IntVar(value=csv_config.get('etasp_intervals', 50))
        tk.Entry(etasp_frame, textvariable=etasp_intervals_var, width=10).grid(row=1, column=2, columnspan=2, padx=5, pady=5)
        
        # Auto-detect functionality
        def auto_detect_etasp_range():
            y_col = y_var.get()
            if not y_col:
                messagebox.showerror('Error', 'Please select Y-axis (ETASP) column first!')
                return
            
            try:
                df_full = pd.read_csv(csv_file_path)
                if len(df_full) > 0:
                    try:
                        pd.to_numeric(df_full.iloc[0][y_col])
                        df = df_full
                    except (ValueError, TypeError):
                        df = df_full.iloc[1:].reset_index(drop=True)
                else:
                    df = df_full
                
                etasp_data = pd.to_numeric(df[y_col], errors='coerce').dropna()
                if len(etasp_data) > 0:
                    etasp_min_var.set(round(etasp_data.min(), 3))
                    etasp_max_var.set(round(etasp_data.max(), 3))
                    messagebox.showinfo('Auto-Detect', f'ETASP range detected: {etasp_data.min():.3f} to {etasp_data.max():.3f}')
                else:
                    messagebox.showerror('Error', 'No valid ETASP data found!')
                    
            except Exception as e:
                messagebox.showerror('Error', f'Failed to auto-detect ETASP range: {e}')
        
        def auto_detect_rpm_range():
            x_col = x_var.get()
            if not x_col:
                messagebox.showerror('Error', 'Please select X-axis (RPM) column first!')
                return
            
            try:
                df_full = pd.read_csv(csv_file_path)
                if len(df_full) > 0:
                    try:
                        pd.to_numeric(df_full.iloc[0][x_col])
                        df = df_full
                    except (ValueError, TypeError):
                        df = df_full.iloc[1:].reset_index(drop=True)
                else:
                    df = df_full
                
                rpm_data = pd.to_numeric(df[x_col], errors='coerce').dropna()
                if len(rpm_data) > 0:
                    rpm_min_var.set(round(rpm_data.min(), 0))
                    rpm_max_var.set(round(rpm_data.max(), 0))
                    messagebox.showinfo('Auto-Detect', f'RPM range detected: {rpm_data.min():.0f} to {rpm_data.max():.0f}')
                else:
                    messagebox.showerror('Error', 'No valid RPM data found!')
                    
            except Exception as e:
                messagebox.showerror('Error', f'Failed to auto-detect RPM range: {e}')
        
        # Auto-detect buttons frame
        auto_detect_frame = tk.Frame(columns_window)
        auto_detect_frame.pack(pady=10)
        
        btn_auto_detect_rpm = tk.Button(auto_detect_frame, text='Auto-Detect RPM Range', command=auto_detect_rpm_range)
        btn_auto_detect_rpm.pack(side='left', padx=5)
        
        btn_auto_detect_etasp = tk.Button(auto_detect_frame, text='Auto-Detect ETASP Range', command=auto_detect_etasp_range)
        btn_auto_detect_etasp.pack(side='left', padx=5)
        
        surface_data_result = [None]  # Use list to make it mutable in nested function
        
        def confirm_csv_config():
            x_col = x_var.get()
            y_col = y_var.get()
            z_col = z_var.get()
            
            if not all([x_col, y_col, z_col]):
                messagebox.showerror('Error', 'Please select all three columns!')
                return
                
            if len(set([x_col, y_col, z_col])) != 3:
                messagebox.showerror('Error', 'Please select different columns for X, Y, and Z axes!')
                return
            
            # Get interpolation parameters
            rpm_min = rpm_min_var.get()
            rpm_max = rpm_max_var.get()
            rpm_intervals = rpm_intervals_var.get()
            etasp_min = etasp_min_var.get()
            etasp_max = etasp_max_var.get()
            etasp_intervals = etasp_intervals_var.get()
            
            # Save configuration
            config = {
                'csv_columns': {
                    'x_column': x_col,
                    'y_column': y_col,
                    'z_column': z_col,
                    'rpm_min': rpm_min,
                    'rpm_max': rpm_max,
                    'rpm_intervals': rpm_intervals,
                    'etasp_min': etasp_min,
                    'etasp_max': etasp_max,
                    'etasp_intervals': etasp_intervals
                }
            }
            
            try:
                with open('fuel_config.json', 'w') as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not save configuration: {e}")
                
            try:
                surface_data = self.load_surface_table(csv_file_path, x_col, y_col, z_col, 
                                                     rpm_min, rpm_max, rpm_intervals,
                                                     etasp_min, etasp_max, etasp_intervals)
                surface_data_result[0] = surface_data
                columns_window.destroy()
                
            except Exception as e:
                messagebox.showerror('Error', f'Failed to load surface table: {e}')
        
        # Create button frame
        button_frame = tk.Frame(columns_window)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text='Load Surface Table', command=confirm_csv_config, 
                 bg='lightgreen', font=('TkDefaultFont', 10, 'bold')).pack(side='left', padx=10)
        tk.Button(button_frame, text='Cancel', command=columns_window.destroy, 
                 bg='lightcoral').pack(side='left', padx=10)
        
        # Wait for window to close
        columns_window.wait_window()
        
        return surface_data_result[0]

    def load_surface_table(self, csv_file_path, x_col, y_col, z_col, rpm_min=None, rpm_max=None, rpm_intervals=None, etasp_min=None, etasp_max=None, etasp_intervals=None):
        """Load surface table from 3-column CSV format with optional interpolation - exact same logic as Fuel_Consumption_Eval_Tool"""
        # Read the CSV file with headers, then skip the units row (row 1)
        df_full = pd.read_csv(csv_file_path)
        
        # Remove the units row (which is the first data row after headers)
        if len(df_full) > 0:
            # Check if the first row contains units (non-numeric data in numeric columns)
            try:
                # Try to convert the first data row to numeric
                pd.to_numeric(df_full.iloc[0][x_col])
                pd.to_numeric(df_full.iloc[0][y_col]) 
                pd.to_numeric(df_full.iloc[0][z_col])
                # If successful, no units row to skip
                df = df_full
            except (ValueError, TypeError):
                # If conversion fails, skip the first row (units row)
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
                continue  # Skip invalid rows
        
        if not valid_data:
            raise ValueError("No valid data points found in CSV file")
        
        valid_data = np.array(valid_data)
        x_data = valid_data[:, 0]
        y_data = valid_data[:, 1]
        z_data = valid_data[:, 2]
        
        # Create interpolated RPM grid if parameters provided
        if rpm_min is not None and rpm_max is not None and rpm_intervals is not None:
            x_unique = np.linspace(rpm_min, rpm_max, rpm_intervals + 1)
        else:
            # Use original RPM values
            x_unique = sorted(np.unique(x_data))
        
        # Create interpolated ETASP grid if parameters provided
        if etasp_min is not None and etasp_max is not None and etasp_intervals is not None:
            y_unique = np.linspace(etasp_min, etasp_max, etasp_intervals + 1)
        else:
            # Use original ETASP values
            y_unique = sorted(np.unique(y_data))
        
        # Create meshgrid for interpolation
        X_grid, Y_grid = np.meshgrid(x_unique, y_unique)
        
        # Interpolate Z values using griddata
        try:
            # Use linear interpolation to fill the grid
            Z_grid = griddata(
                points=(x_data, y_data),
                values=z_data,
                xi=(X_grid, Y_grid),
                method='linear',
                fill_value=np.nan
            )
            
            # For points outside convex hull, try nearest neighbor
            mask_nan = np.isnan(Z_grid)
            if np.any(mask_nan):
                Z_nearest = griddata(
                    points=(x_data, y_data),
                    values=z_data,
                    xi=(X_grid, Y_grid),
                    method='nearest'
                )
                # Only fill NaN values that are close to existing data
                Z_grid[mask_nan] = Z_nearest[mask_nan]
                
        except Exception as e:
            print(f"Interpolation warning: {e}")
            # Fallback: create grid with original data points only
            Z_grid = np.full((len(y_unique), len(x_unique)), np.nan)
            for i, (x_val, y_val, z_val) in enumerate(valid_data):
                # Find closest grid point
                x_idx = np.argmin(np.abs(x_unique - x_val))
                y_idx = np.argmin(np.abs(y_unique - y_val))
                Z_grid[y_idx, x_idx] = z_val
        
        return np.array(x_unique), np.array(y_unique), Z_grid
                
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
            
        if not self.surface_data:
            messagebox.showerror("Error", "Please select and configure a surface table CSV file first!")
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
        """Load vehicle file using the exact same logic as Fuel_Consumption_Eval_Tool"""
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        
        if file_ext == '.csv':
            self.load_csv_vehicle_file()
        elif file_ext in ['.mdf', '.mf4', '.dat']:
            self.load_mdf_vehicle_file()
        else:
            raise Exception(f"Unsupported file format: {file_ext}")

    def load_csv_vehicle_file(self):
        """Load CSV vehicle file using the exact same logic as Fuel_Consumption_Eval_Tool"""
        try:
            # Read CSV file
            df = pd.read_csv(self.vehicle_file_path)
            
            # Get available channels (column names)
            self.available_channels = df.columns.tolist()
            
            # Store the dataframe
            self.vehicle_data = df
            
            # Update channel comboboxes
            self.rpm_combo.set_completion_list(self.available_channels)
            self.etasp_combo.set_completion_list(self.available_channels)
            
            self.log_status(f"CSV vehicle file loaded successfully. Found {len(self.available_channels)} channels.")
            
        except Exception as e:
            raise Exception(f"Error loading CSV vehicle file: {str(e)}")

    def load_mdf_vehicle_file(self):
        """Load MDF/MF4/DAT vehicle file using the exact same logic as Fuel_Consumption_Eval_Tool"""
        try:
            # Load MDF file
            mdf = MDF(self.vehicle_file_path)
            
            # Get available channels
            self.available_channels = []
            for group_index in range(len(mdf.groups)):
                for channel in mdf.groups[group_index].channels:
                    self.available_channels.append(channel.name)
            
            # Store the MDF object
            self.vehicle_data = mdf
            
            # Update channel comboboxes
            self.rpm_combo.set_completion_list(self.available_channels)
            self.etasp_combo.set_completion_list(self.available_channels)
            
            self.log_status(f"MDF vehicle file loaded successfully. Found {len(self.available_channels)} channels.")
            
        except Exception as e:
            raise Exception(f"Error loading MDF vehicle file: {str(e)}")
        
    def process_and_append(self):
        """Process the vehicle data and append the calculated channel"""
        if not self.surface_data:
            messagebox.showerror("Error", "Please select and configure a surface table CSV file first!")
            return
            
        if not self.vehicle_data:
            messagebox.showerror("Error", "Please select a vehicle log file!")
            return
            
        if not self.rpm_channel.get() or not self.etasp_channel.get():
            messagebox.showerror("Error", "Please select both RPM and ETASP channels!")
            return
        
        # Extract data based on file type
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        
        # For MDF files, ask user for raster to handle different sampling rates
        raster = None
        if file_ext in ['.mdf', '.mf4', '.dat']:
            raster = self.ask_for_raster()
            if raster is None:  # User cancelled
                self.log_status("Processing cancelled by user.")
                return
        
        try:
            self.log_status("Starting processing...")
            
            if file_ext == '.csv':
                rpm_data = pd.to_numeric(self.vehicle_data[self.rpm_channel.get()], errors='coerce')
                etasp_data = pd.to_numeric(self.vehicle_data[self.etasp_channel.get()], errors='coerce')
                # For CSV, use the index as timestamps (assuming they are sequential)
                self.reference_timestamps = np.arange(len(rpm_data), dtype=np.float64)
            else:  # MDF/MF4/DAT
                # Use raster to get both signals at the same time base
                if raster:
                    self.log_status(f"Resampling signals to {raster}s raster...")
                    # Get both signals with the same raster to ensure same time base
                    rpm_signal = self.vehicle_data.get(self.rpm_channel.get(), raster=raster)
                    etasp_signal = self.vehicle_data.get(self.etasp_channel.get(), raster=raster)
                    
                    self.log_status(f"RPM signal length after raster: {len(rpm_signal.samples)}")
                    self.log_status(f"ETASP signal length after raster: {len(etasp_signal.samples)}")
                else:
                    # Get signals without raster (this will likely cause the length mismatch error)
                    self.log_status("Warning: No raster specified - signals may have different lengths!")
                    rpm_signal = self.vehicle_data.get(self.rpm_channel.get())
                    etasp_signal = self.vehicle_data.get(self.etasp_channel.get())
                    
                    self.log_status(f"RPM signal length: {len(rpm_signal.samples)}")
                    self.log_status(f"ETASP signal length: {len(etasp_signal.samples)}")
                
                rpm_data = rpm_signal.samples
                etasp_data = etasp_signal.samples
                
                # Both signals should now have the same length due to raster resampling
                if len(rpm_data) != len(etasp_data):
                    if raster:
                        raise Exception(f"RPM and ETASP signals still have different lengths after resampling to {raster}s raster: RPM={len(rpm_data)}, ETASP={len(etasp_data)}. This may indicate an issue with the raster resampling.")
                    else:
                        raise Exception(f"RPM and ETASP signals have different lengths: RPM={len(rpm_data)}, ETASP={len(etasp_data)}. Please specify a raster value to resample both signals to the same time base.")
                
                # Store the timestamp information for later use
                self.reference_timestamps = rpm_signal.timestamps
                if len(self.reference_timestamps) != len(rpm_data):
                    raise Exception(f"RPM signal timestamps and samples length mismatch: timestamps={len(self.reference_timestamps)}, samples={len(rpm_data)}")
            
            # Get surface table data
            x_values, y_values, z_matrix = self.surface_data
            
            # Interpolate Z values for each point
            z_interpolated = []
            valid_points = 0
            total_points = len(rpm_data)
            
            for i, (rpm, etasp) in enumerate(zip(rpm_data, etasp_data)):
                if pd.notna(rpm) and pd.notna(etasp):
                    # Find the interpolated Z value
                    z_val = self.interpolate_z_value(rpm, etasp, x_values, y_values, z_matrix)
                    z_interpolated.append(z_val)
                    if not np.isnan(z_val):
                        valid_points += 1
                else:
                    z_interpolated.append(np.nan)
            
            # Ensure z_interpolated has the same length as the input data
            if len(z_interpolated) != total_points:
                raise Exception(f"Length mismatch: z_interpolated has {len(z_interpolated)} elements but input data has {total_points} elements")
            
            self.log_status(f"Interpolated {valid_points}/{total_points} valid points")
            self.log_status(f"Generated {len(z_interpolated)} interpolated values for {total_points} input samples")
            
            # Append the calculated channel
            self.append_calculated_channel(z_interpolated)
            
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
            self.log_status(f"Processing error: {str(e)}")
    
    def interpolate_z_value(self, rpm, etasp, x_values, y_values, z_matrix):
        """Interpolate Z value for given RPM and ETASP using bilinear interpolation"""
        try:
            # Convert to numpy arrays for easier handling
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
            # Interpolate in x direction
            z_x1 = z11 * (x2 - rpm) / (x2 - x1) + z21 * (rpm - x1) / (x2 - x1)
            z_x2 = z12 * (x2 - rpm) / (x2 - x1) + z22 * (rpm - x1) / (x2 - x1)
            
            # Interpolate in y direction
            z_interpolated = z_x1 * (y2 - etasp) / (y2 - y1) + z_x2 * (etasp - y1) / (y2 - y1)
            
            return z_interpolated
            
        except Exception as e:
            print(f"Interpolation error: {e}")
            return np.nan
    
    def append_calculated_channel(self, z_values):
        """Append the calculated channel to the original file"""
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        
        try:
            if file_ext == '.csv':
                self.append_to_csv(z_values)
            else:  # MDF/MF4/DAT
                self.append_to_mdf(z_values)
                
            self.log_status("Channel appended successfully!")
            messagebox.showinfo("Success", f"Channel '{self.new_channel_name.get()}' has been appended to the file!")
            
        except Exception as e:
            raise Exception(f"Failed to append channel: {str(e)}")
    
    def append_to_csv(self, z_values):
        """Append calculated channel to CSV file"""
        # Add the new column to the dataframe
        self.vehicle_data[self.new_channel_name.get()] = z_values
        
        # Create output filename
        base_name = Path(self.vehicle_file_path).stem
        output_path = Path(self.vehicle_file_path).parent / f"{base_name}_with_{self.new_channel_name.get()}.csv"
        
        # Save the updated dataframe
        self.vehicle_data.to_csv(output_path, index=False)
        
        self.log_status(f"Updated CSV saved as: {output_path}")
    
    def append_to_mdf(self, z_values):
        """Append calculated channel to MDF file"""
        # Use the reference timestamps stored during processing
        if self.reference_timestamps is None:
            raise Exception("Reference timestamps not available. This method should only be called for MDF files.")
        
        time_data = self.reference_timestamps
        
        # Ensure timestamps and z_values have the same length
        if len(time_data) != len(z_values):
            raise Exception(f"{self.new_channel_name.get()} samples and timestamps length mismatch ({len(z_values)} vs {len(time_data)})")
        
        # Create new signal with calculated values using the same timestamps as the input signals
        new_signal = Signal(
            samples=np.array(z_values, dtype=np.float64),
            timestamps=time_data,
            name=self.new_channel_name.get(),
            unit="",  # Add appropriate unit if needed
            comment=f"Calculated using surface table interpolation from {self.rpm_channel.get()} and {self.etasp_channel.get()}"
        )
        
        # Create output filename
        base_name = Path(self.vehicle_file_path).stem
        output_path = Path(self.vehicle_file_path).parent / f"{base_name}_with_{self.new_channel_name.get()}.mf4"
        
        # Create a new MDF file with all original signals plus the new one
        with MDF() as new_mdf:
            # Copy all original signals with the same raster as the new signal to maintain consistency
            for group_index in range(len(self.vehicle_data.groups)):
                group_signals = []
                
                # Get all channels from this group
                for channel in self.vehicle_data.groups[group_index].channels:
                    try:
                        # Get signal with the same raster as our new signal (interpolated to same time base)
                        signal = self.vehicle_data.get(channel.name, group=group_index, raster=new_signal.timestamps)
                        group_signals.append(signal)
                    except Exception as e:
                        self.log_status(f"Warning: Could not get signal {channel.name}: {str(e)}")
                        continue
                
                # Append the group with all its signals
                if group_signals:
                    new_mdf.append(group_signals, comment=f"Group {group_index} with resampled data")
            
            # Add the new calculated signal as a separate group to avoid conflicts
            new_mdf.append([new_signal], comment="Calculated fuel consumption channel")
            
            # Save the new file
            new_mdf.save(output_path, overwrite=True)
        
        self.log_status(f"Updated MDF saved as: {output_path}")
    
    def log_status(self, message):
        """Add a message to the status log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

    def ask_for_raster(self):
        """Ask user for raster value for resampling"""
        raster_window = tk.Toplevel(self.root)
        raster_window.title('Set Time Raster')
        raster_window.geometry('480x320')
        raster_window.grab_set()  # Make it modal
        
        tk.Label(raster_window, text='Time Raster Configuration', 
                font=('TkDefaultFont', 14, 'bold')).pack(pady=10)
        
        tk.Label(raster_window, text='The RPM and ETASP signals have different sampling rates (rasters).\n'
                                    'You need to specify a time raster (in seconds) to resample both signals\n'
                                    'to the same time base for interpolation.\n\n'
                                    'Choose a raster that is appropriate for your measurement data:', 
                font=('TkDefaultFont', 10)).pack(pady=10)
        
        # Input frame
        input_frame = tk.Frame(raster_window)
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text='Raster (seconds):').grid(row=0, column=0, padx=5)
        raster_var = tk.DoubleVar(value=0.01)  # Default 10ms - good for most automotive applications
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
        tk.Button(buttons_frame, text='100ms (0.1)', command=lambda: set_raster(0.1), width=12).pack(side='left', padx=2)
        
        # Add a second row for more options
        buttons_frame2 = tk.Frame(suggestions_frame)
        buttons_frame2.pack(pady=2)
        
        tk.Button(buttons_frame2, text='20ms (0.02)', command=lambda: set_raster(0.02), width=12).pack(side='left', padx=2)
        tk.Button(buttons_frame2, text='50ms (0.05)', command=lambda: set_raster(0.05), width=12).pack(side='left', padx=2)
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

def main():
    """Main function"""
    app = VehicleLogChannelAppender()
    app.run()

if __name__ == "__main__":
    main()