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
import tempfile
import shutil
from pathlib import Path

class VehicleLogChannelAppender:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vehicle Log Channel Appender")
        self.root.geometry("800x600")
        
        # Data storage
        self.vehicle_file_path = None
        self.csv_surface_path = None
        self.vehicle_data = None
        self.csv_data = None
        self.available_channels = []
        
        # Selected parameters
        self.rpm_channel = tk.StringVar()
        self.etasp_channel = tk.StringVar()
        self.new_channel_name = tk.StringVar(value="Calculated_Z")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        
        # Title
        title_label = tk.Label(self.root, text="Vehicle Log Channel Appender", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Step 1: Select CSV Surface Table
        step1_frame = tk.LabelFrame(main_frame, text="Step 1: Select CSV Surface Table", 
                                   font=("Arial", 12, "bold"))
        step1_frame.pack(fill="x", pady=5)
        
        csv_btn_frame = tk.Frame(step1_frame)
        csv_btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.csv_btn = tk.Button(csv_btn_frame, text="Select CSV Surface Table", 
                                command=self.select_csv_file, bg="lightblue")
        self.csv_btn.pack(side="left")
        
        self.csv_status = tk.Label(csv_btn_frame, text="No CSV file selected", 
                                  fg="red")
        self.csv_status.pack(side="left", padx=10)
        
        # Step 2: Select Vehicle Log File
        step2_frame = tk.LabelFrame(main_frame, text="Step 2: Select Vehicle Log File", 
                                   font=("Arial", 12, "bold"))
        step2_frame.pack(fill="x", pady=5)
        
        vehicle_btn_frame = tk.Frame(step2_frame)
        vehicle_btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.vehicle_btn = tk.Button(vehicle_btn_frame, text="Select Vehicle Log File", 
                                    command=self.select_vehicle_file, bg="lightgreen")
        self.vehicle_btn.pack(side="left")
        
        self.vehicle_status = tk.Label(vehicle_btn_frame, text="No vehicle file selected", 
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
        self.rpm_combo = ttk.Combobox(rpm_frame, textvariable=self.rpm_channel, 
                                     state="readonly", width=30)
        self.rpm_combo.pack(side="left", padx=5)
        
        # ETASP Channel selection
        etasp_frame = tk.Frame(params_frame)
        etasp_frame.pack(fill="x", pady=2)
        tk.Label(etasp_frame, text="ETASP Channel:", width=15, anchor="w").pack(side="left")
        self.etasp_combo = ttk.Combobox(etasp_frame, textvariable=self.etasp_channel, 
                                       state="readonly", width=30)
        self.etasp_combo.pack(side="left", padx=5)
        
        # New channel name
        name_frame = tk.Frame(params_frame)
        name_frame.pack(fill="x", pady=2)
        tk.Label(name_frame, text="New Channel Name:", width=15, anchor="w").pack(side="left")
        name_entry = tk.Entry(name_frame, textvariable=self.new_channel_name, width=32)
        name_entry.pack(side="left", padx=5)
        
        # Step 4: Process
        step4_frame = tk.LabelFrame(main_frame, text="Step 4: Process and Export", 
                                   font=("Arial", 12, "bold"))
        step4_frame.pack(fill="x", pady=5)
        
        process_frame = tk.Frame(step4_frame)
        process_frame.pack(pady=10)
        
        self.process_btn = tk.Button(process_frame, text="Calculate and Append Channel", 
                                    command=self.process_and_export, bg="orange", 
                                    font=("Arial", 12, "bold"))
        self.process_btn.pack()
        
        # Status text area
        status_frame = tk.LabelFrame(main_frame, text="Status Log", 
                                    font=("Arial", 12, "bold"))
        status_frame.pack(fill="both", expand=True, pady=5)
        
        self.status_text = tk.Text(status_frame, height=8, wrap="word")
        scrollbar = tk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.status_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
    def log_status(self, message):
        """Add message to status log"""
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
        
    def select_csv_file(self):
        """Select CSV surface table file"""
        file_path = filedialog.askopenfilename(
            title="Select CSV Surface Table",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                self.csv_surface_path = file_path
                self.load_csv_surface_table()
                self.csv_status.config(text=f"CSV loaded: {os.path.basename(file_path)}", fg="green")
                self.log_status(f"CSV surface table loaded: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV file: {str(e)}")
                self.log_status(f"Error loading CSV: {str(e)}")
                
    def load_csv_surface_table(self):
        """Load and parse CSV surface table"""
        try:
            # Read CSV file with headers, then handle units row if present
            df_full = pd.read_csv(self.csv_surface_path)
            
            # Try to detect format - assume first 3 columns are RPM, ETASP, Z
            if len(df_full.columns) < 3:
                raise ValueError("CSV must have at least 3 columns (RPM, ETASP, Z)")
            
            # Get first three columns
            rpm_col = df_full.columns[0]
            etasp_col = df_full.columns[1]
            z_col = df_full.columns[2]
            
            # Remove the units row if present (same logic as Fuel_Consumption_Eval_Tool)
            if len(df_full) > 0:
                # Check if the first row contains units (non-numeric data in numeric columns)
                try:
                    # Try to convert the first data row to numeric
                    pd.to_numeric(df_full.iloc[0][rpm_col])
                    pd.to_numeric(df_full.iloc[0][etasp_col]) 
                    pd.to_numeric(df_full.iloc[0][z_col])
                    # If successful, no units row to skip
                    df = df_full
                except (ValueError, TypeError):
                    # If conversion fails, skip the first row (units row)
                    df = df_full.iloc[1:].reset_index(drop=True)
            else:
                df = df_full
            
            # Extract and convert data
            rpm_data = pd.to_numeric(df[rpm_col], errors='coerce')
            etasp_data = pd.to_numeric(df[etasp_col], errors='coerce')
            z_data = pd.to_numeric(df[z_col], errors='coerce')
            
            self.csv_data = {
                'rpm': rpm_data.values,
                'etasp': etasp_data.values,
                'z': z_data.values
            }
            
            # Remove any NaN values
            valid_mask = ~(np.isnan(self.csv_data['rpm']) | 
                          np.isnan(self.csv_data['etasp']) | 
                          np.isnan(self.csv_data['z']))
            
            self.csv_data['rpm'] = self.csv_data['rpm'][valid_mask]
            self.csv_data['etasp'] = self.csv_data['etasp'][valid_mask]
            self.csv_data['z'] = self.csv_data['z'][valid_mask]
            
            self.log_status(f"CSV data loaded with {len(self.csv_data['rpm'])} valid points")
            self.log_status(f"RPM range: {self.csv_data['rpm'].min():.2f} - {self.csv_data['rpm'].max():.2f}")
            self.log_status(f"ETASP range: {self.csv_data['etasp'].min():.2f} - {self.csv_data['etasp'].max():.2f}")
            self.log_status(f"Z range: {self.csv_data['z'].min():.2f} - {self.csv_data['z'].max():.2f}")
            
        except Exception as e:
            raise Exception(f"Error parsing CSV surface table: {str(e)}")
            
    def select_vehicle_file(self):
        """Select vehicle log file"""
        file_path = filedialog.askopenfilename(
            title="Select Vehicle Log File",
            filetypes=[
                ("MDF, MF4 and DAT Files", "*.dat *.mdf *.mf4"),
                ("CSV Files", "*.csv"),
                ("DAT Files", "*.dat"),
                ("MDF Files", "*.mdf"),
                ("MF4 Files", "*.mf4"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.vehicle_file_path = file_path
                self.load_vehicle_file()
                self.vehicle_status.config(text=f"Vehicle file loaded: {os.path.basename(file_path)}", fg="green")
                self.log_status(f"Vehicle file loaded: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load vehicle file: {str(e)}")
                self.log_status(f"Error loading vehicle file: {str(e)}")
                
    def load_vehicle_file(self):
        """Load vehicle log file and get available channels"""
        file_ext = Path(self.vehicle_file_path).suffix.lower()
        
        if file_ext == '.csv':
            self.load_csv_vehicle_file()
        else:
            self.load_mdf_vehicle_file()
            
    def load_csv_vehicle_file(self):
        """Load CSV vehicle file"""
        try:
            # Read CSV file with headers, then handle units row if present (same as Fuel_Consumption_Eval_Tool)
            df_full = pd.read_csv(self.vehicle_file_path)
            
            # Remove the units row if present 
            if len(df_full) > 0:
                # Check if the first row contains units (non-numeric data)
                # Try to find at least one numeric column to test
                numeric_test_passed = False
                for col in df_full.columns:
                    try:
                        pd.to_numeric(df_full.iloc[0][col])
                        numeric_test_passed = True
                        break
                    except (ValueError, TypeError):
                        continue
                
                if numeric_test_passed:
                    # If we found numeric data in first row, no units row to skip
                    df = df_full
                else:
                    # If no numeric data found in first row, assume it's a units row and skip it
                    df = df_full.iloc[1:].reset_index(drop=True)
            else:
                df = df_full
            
            self.vehicle_data = df
            self.available_channels = list(df.columns)
            
            # Update combo boxes
            self.rpm_combo['values'] = self.available_channels
            self.etasp_combo['values'] = self.available_channels
            
            self.log_status(f"CSV vehicle file loaded with {len(df)} rows and {len(df.columns)} channels")
            self.log_status(f"Available channels: {', '.join(self.available_channels[:10])}{'...' if len(self.available_channels) > 10 else ''}")
            
        except Exception as e:
            raise Exception(f"Error loading CSV vehicle file: {str(e)}")
            
    def load_mdf_vehicle_file(self):
        """Load MDF/DAT/MF4 vehicle file"""
        try:
            mdf = MDF(self.vehicle_file_path)
            self.vehicle_data = mdf
            self.available_channels = list(mdf.channels_db.keys())
            
            # Update combo boxes
            self.rpm_combo['values'] = self.available_channels
            self.etasp_combo['values'] = self.available_channels
            
            self.log_status(f"MDF vehicle file loaded with {len(self.available_channels)} channels")
            self.log_status(f"Available channels: {', '.join(self.available_channels[:10])}{'...' if len(self.available_channels) > 10 else ''}")
            
        except Exception as e:
            raise Exception(f"Error loading MDF vehicle file: {str(e)}")
            
    def interpolate_z_values(self, rpm_values, etasp_values):
        """Interpolate Z values using CSV surface table"""
        if self.csv_data is None:
            raise ValueError("No CSV surface table loaded")
            
        try:
            # Create points for interpolation
            points = np.column_stack((self.csv_data['rpm'], self.csv_data['etasp']))
            values = self.csv_data['z']
            
            # Create target points
            target_points = np.column_stack((rpm_values, etasp_values))
            
            # Interpolate using linear method first, then nearest for NaN values
            interpolated_z = griddata(points, values, target_points, method='linear', fill_value=np.nan)
            
            # Fill NaN values with nearest neighbor interpolation
            nan_mask = np.isnan(interpolated_z)
            if np.any(nan_mask):
                interpolated_z_nearest = griddata(points, values, target_points, method='nearest')
                interpolated_z[nan_mask] = interpolated_z_nearest[nan_mask]
                
            return interpolated_z
            
        except Exception as e:
            raise Exception(f"Error during interpolation: {str(e)}")
            
    def process_and_export(self):
        """Main processing function"""
        try:
            # Validate inputs
            if not self.csv_surface_path:
                messagebox.showerror("Error", "Please select a CSV surface table first")
                return
                
            if not self.vehicle_file_path:
                messagebox.showerror("Error", "Please select a vehicle log file")
                return
                
            if not self.rpm_channel.get():
                messagebox.showerror("Error", "Please select RPM channel")
                return
                
            if not self.etasp_channel.get():
                messagebox.showerror("Error", "Please select ETASP channel")
                return
                
            if not self.new_channel_name.get():
                messagebox.showerror("Error", "Please provide a name for the new channel")
                return
                
            self.log_status("Starting processing...")
            
            # Process based on file type
            file_ext = Path(self.vehicle_file_path).suffix.lower()
            
            if file_ext == '.csv':
                self.process_csv_vehicle_file()
            else:
                self.process_mdf_vehicle_file()
                
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
            self.log_status(f"Processing failed: {str(e)}")
            
    def process_csv_vehicle_file(self):
        """Process CSV vehicle file"""
        try:
            df = self.vehicle_data.copy()
            
            # Get RPM and ETASP data
            rpm_data = df[self.rpm_channel.get()].values
            etasp_data = df[self.etasp_channel.get()].values
            
            self.log_status(f"Processing {len(rpm_data)} data points...")
            
            # Interpolate Z values
            calculated_z = self.interpolate_z_values(rpm_data, etasp_data)
            
            # Add new column
            df[self.new_channel_name.get()] = calculated_z
            
            # Save to new file
            output_path = self.get_output_path('.csv')
            df.to_csv(output_path, index=False)
            
            self.log_status(f"Successfully saved CSV file with new channel: {output_path}")
            messagebox.showinfo("Success", f"File saved successfully:\n{output_path}")
            
        except Exception as e:
            raise Exception(f"Error processing CSV file: {str(e)}")
            
    def process_mdf_vehicle_file(self):
        """Process MDF/DAT/MF4 vehicle file"""
        try:
            mdf = self.vehicle_data
            
            # Get RPM and ETASP signals
            rpm_signal = mdf.get(self.rpm_channel.get())
            etasp_signal = mdf.get(self.etasp_channel.get())
            
            self.log_status(f"Processing signals with {len(rpm_signal.samples)} RPM and {len(etasp_signal.samples)} ETASP samples...")
            
            # Create common time base
            start_time = max(rpm_signal.timestamps[0], etasp_signal.timestamps[0])
            end_time = min(rpm_signal.timestamps[-1], etasp_signal.timestamps[-1])
            
            # Use the rpm signal timestamps as base (or create regular intervals)
            if len(rpm_signal.timestamps) <= len(etasp_signal.timestamps):
                time_base = rpm_signal.timestamps
                rpm_resampled = rpm_signal.samples
                etasp_resampled = np.interp(time_base, etasp_signal.timestamps, etasp_signal.samples)
            else:
                time_base = etasp_signal.timestamps
                etasp_resampled = etasp_signal.samples
                rpm_resampled = np.interp(time_base, rpm_signal.timestamps, rpm_signal.samples)
            
            # Filter to common time range
            time_mask = (time_base >= start_time) & (time_base <= end_time)
            time_base = time_base[time_mask]
            rpm_resampled = rpm_resampled[time_mask]
            etasp_resampled = etasp_resampled[time_mask]
            
            self.log_status(f"Using {len(time_base)} synchronized time points...")
            
            # Interpolate Z values
            calculated_z = self.interpolate_z_values(rpm_resampled, etasp_resampled)
            
            # Create new signal
            new_signal = Signal(
                samples=calculated_z,
                timestamps=time_base,
                name=self.new_channel_name.get(),
                unit='units'
            )
            
            # Add signal to MDF
            mdf.append(new_signal)
            
            # Save to new file
            output_path = self.get_output_path(Path(self.vehicle_file_path).suffix)
            mdf.save(output_path, overwrite=True)
            
            self.log_status(f"Successfully saved MDF file with new channel: {output_path}")
            messagebox.showinfo("Success", f"File saved successfully:\n{output_path}")
            
            # Close the MDF file
            mdf.close()
            
        except Exception as e:
            raise Exception(f"Error processing MDF file: {str(e)}")
            
    def get_output_path(self, extension):
        """Generate output file path"""
        input_path = Path(self.vehicle_file_path)
        output_filename = f"{input_path.stem}_with_{self.new_channel_name.get()}{extension}"
        output_path = input_path.parent / output_filename
        
        # If file exists, add number suffix
        counter = 1
        while output_path.exists():
            output_filename = f"{input_path.stem}_with_{self.new_channel_name.get()}_{counter}{extension}"
            output_path = input_path.parent / output_filename
            counter += 1
            
        return str(output_path)
        
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main function"""
    app = VehicleLogChannelAppender()
    app.run()

if __name__ == "__main__":
    main()