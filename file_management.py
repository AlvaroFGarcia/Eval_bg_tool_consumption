"""
File Management Module for Vehicle Log Channel Appender
Contains all file loading, saving, and output operations.
"""

import numpy as np
import pandas as pd
from asammdf import MDF, Signal
from pathlib import Path
from datetime import datetime
import os


class FileManager:
    """Handles all file operations."""
    
    def __init__(self, logger=None):
        """Initialize the file manager.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
    
    def load_vehicle_file(self, file_path):
        """Load vehicle file and extract available channels.
        
        Returns:
            tuple: (vehicle_data, available_channels)
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.csv':
            return self._load_csv_vehicle_file(file_path)
        elif file_ext in ['.mdf', '.mf4', '.dat']:
            return self._load_mdf_vehicle_file(file_path)
        else:
            raise Exception(f"Unsupported file format: {file_ext}")
    
    def _load_csv_vehicle_file(self, file_path):
        """Load CSV vehicle file."""
        try:
            df = pd.read_csv(file_path)
            available_channels = df.columns.tolist()
            
            self.logger(f"✅ CSV vehicle file loaded successfully. Found {len(available_channels)} channels.")
            return df, available_channels
            
        except Exception as e:
            raise Exception(f"Error loading CSV vehicle file: {str(e)}")
    
    def _load_mdf_vehicle_file(self, file_path):
        """Load MDF/MF4/DAT vehicle file."""
        try:
            mdf = MDF(file_path)
            
            # Get available channels
            available_channels = []
            for group_index in range(len(mdf.groups)):
                for channel in mdf.groups[group_index].channels:
                    available_channels.append(channel.name)
            
            self.logger(f"✅ MDF vehicle file loaded successfully. Found {len(available_channels)} channels.")
            return mdf, available_channels
            
        except Exception as e:
            raise Exception(f"Error loading MDF vehicle file: {str(e)}")
    
    def save_output(self, calculated_signals, vehicle_file_path, output_format, 
                   vehicle_data=None, csv_export_data=None):
        """Save the output in the selected format.
        
        Args:
            calculated_signals: List of Signal objects for MF4 output
            vehicle_file_path: Path to original vehicle file
            output_format: "mf4" or "csv"
            vehicle_data: Original vehicle data (for CSV input files)
            csv_export_data: DataFrame for CSV export (for MDF input files)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(vehicle_file_path).stem
        output_dir = Path(vehicle_file_path).parent
        original_file_ext = Path(vehicle_file_path).suffix.lower()
        
        try:
            if output_format == "mf4" and original_file_ext != '.csv':
                # Save as MF4 with calculated channels only
                output_path = output_dir / f"{base_name}_calculated_channels_{timestamp}.mf4"
                
                with MDF() as new_mdf:
                    if calculated_signals:
                        new_mdf.append(calculated_signals, comment="Calculated channels from surface table interpolation")
                        new_mdf.save(output_path, overwrite=True)
                        self.logger(f"✅ MF4 file saved: {output_path}")
                    else:
                        self.logger("❌ No calculated signals to save")
                        
            if output_format == "csv" or original_file_ext == '.csv':
                # Save as CSV
                output_path = output_dir / f"{base_name}_with_calculated_channels_{timestamp}.csv"
                
                if original_file_ext == '.csv':
                    # Save updated original dataframe
                    vehicle_data.to_csv(output_path, index=False)
                else:
                    # Save calculated channels dataframe
                    if csv_export_data is not None:
                        csv_export_data.to_csv(output_path, index=False)
                    
                self.logger(f"✅ CSV file saved: {output_path}")
                
        except Exception as e:
            self.logger(f"❌ Error saving output: {str(e)}")
            raise
    
    def load_csv_columns(self, csv_file_path):
        """Load column names from a CSV file.
        
        Returns:
            list: Column names from the CSV file
        """
        try:
            df = pd.read_csv(csv_file_path, nrows=1)
            columns = df.columns.tolist()
            self.logger(f"✅ Loaded CSV columns: {', '.join(columns)}")
            return columns
        except Exception as e:
            self.logger(f"❌ Error reading CSV file: {str(e)}")
            raise Exception(f"Failed to read CSV file: {str(e)}")
    



class OutputGenerator:
    """Generates output files in various formats."""
    
    def __init__(self, logger=None):
        """Initialize the output generator.
        
        Args:
            logger: A callable that takes a message string for logging
        """
        self.logger = logger if logger else lambda msg: print(msg)
    
    def create_calculated_signal(self, channel_config, z_interpolated, timestamps):
        """Create a Signal object for calculated channel.
        
        Args:
            channel_config: Dictionary with channel configuration
            z_interpolated: Array of interpolated Z values
            timestamps: Array of timestamps
            
        Returns:
            Signal: asammdf Signal object
        """
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
        
        return signal
    
    def prepare_csv_export_data(self, timestamps, calculated_channels_data):
        """Prepare data for CSV export.
        
        Args:
            timestamps: Array of timestamps
            calculated_channels_data: Dict of {channel_name: values_array}
            
        Returns:
            pd.DataFrame: DataFrame ready for CSV export
        """
        export_data = pd.DataFrame()
        export_data['Time'] = timestamps
        
        for channel_name, values in calculated_channels_data.items():
            export_data[channel_name] = values
            
        return export_data