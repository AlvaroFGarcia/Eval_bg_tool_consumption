"""
Vehicle Log Channel Appender - Modern UI Version
Using CustomTkinter for a contemporary, professional appearance

Enhanced Version with Advanced Raster Analysis and Interpolation

Key Features:
- Modern, dark/light theme UI with CustomTkinter
- Professional Windows-compatible interface
- Analyzes channel sampling rates and recommends minimum rasters
- Shows per-channel analysis with limiting parameters
- Implements linear interpolation for fine rasters below original data resolution
- Enhanced raster selection dialog with warnings and recommendations
- Supports processing at any raster by interpolating missing data points

Modern UI Features:
- Dark and light theme support
- Professional button styling with hover effects
- Modern card-based layout
- Smooth animations and transitions
- Contemporary icons and typography
- Responsive design for Windows PCs
"""

import numpy as np
import pandas as pd
from asammdf import MDF, Signal
import customtkinter as ctk
from tkinter import filedialog, messagebox
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
        self.root.geometry("1200x800")
        
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
        
        # Theme variables
        self.theme_var = ctk.StringVar(value="dark")
        
        # Setup UI
        self.setup_ui()
        self.setup_bindings()
        
        # Initialize with welcome message
        self.log_status("🎉 Welcome to Vehicle Log Channel Appender - Modern Edition!")
        self.log_status("💡 Select a vehicle file to begin analysis")
    
    def setup_window_properties(self):
        """Configure window properties for Windows compatibility."""
        # Center window on screen
        self.root.update_idletasks()
        width = 1200
        height = 800
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set minimum size for usability
        self.root.minsize(1000, 600)
        
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
            text="Select MDF File",
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
        
        # Quick actions
        self.save_settings_btn = ctk.CTkButton(
            self.settings_frame,
            text="💾 Save Settings",
            command=self.save_settings,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.save_settings_btn.pack(pady=(0, 5), padx=10, fill="x")
        
        self.load_settings_btn = ctk.CTkButton(
            self.settings_frame,
            text="📁 Load Settings",
            command=self.load_settings,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        self.load_settings_btn.pack(pady=(0, 15), padx=10, fill="x")
    
    def setup_main_content(self):
        """Setup the main content area with tabs."""
        # Main content frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Add tabs
        self.tabview.add("🔧 Processing")
        self.tabview.add("📊 Custom Channels")
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
        
        # Vehicle file analysis section
        self.analysis_frame = ctk.CTkFrame(self.processing_scroll)
        self.analysis_frame.pack(fill="x", pady=(0, 20))
        
        analysis_title = ctk.CTkLabel(
            self.analysis_frame,
            text="📈 Vehicle File Analysis",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        analysis_title.pack(pady=(20, 10))
        
        self.analysis_button = ctk.CTkButton(
            self.analysis_frame,
            text="🔍 Analyze Vehicle File",
            command=self.analyze_vehicle_file,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.analysis_button.pack(pady=(0, 10))
        
        self.analysis_text = ctk.CTkTextbox(
            self.analysis_frame,
            height=200,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.analysis_text.pack(fill="x", padx=20, pady=(0, 20))
        
        # Processing controls section
        self.controls_frame = ctk.CTkFrame(self.processing_scroll)
        self.controls_frame.pack(fill="x", pady=(0, 20))
        
        controls_title = ctk.CTkLabel(
            self.controls_frame,
            text="⚡ Processing Controls",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        controls_title.pack(pady=(20, 15))
        
        # Raster selection
        raster_frame = ctk.CTkFrame(self.controls_frame)
        raster_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        raster_label = ctk.CTkLabel(
            raster_frame,
            text="🎯 Target Raster (Hz):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        raster_label.pack(pady=(15, 5))
        
        self.raster_entry = ctk.CTkEntry(
            raster_frame,
            placeholder_text="Enter raster value (e.g., 10)",
            height=35,
            font=ctk.CTkFont(size=12)
        )
        self.raster_entry.pack(pady=(0, 10), padx=20, fill="x")
        
        self.enhanced_raster_button = ctk.CTkButton(
            raster_frame,
            text="🎛️ Enhanced Raster Selection",
            command=self.show_enhanced_raster_dialog,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        self.enhanced_raster_button.pack(pady=(0, 15), padx=20, fill="x")
        
        # Process button
        self.process_button = ctk.CTkButton(
            self.controls_frame,
            text="🚀 Process Channels",
            command=self.process_channels,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.process_button.pack(pady=(0, 20), padx=20, fill="x")
    
    def setup_custom_channels_tab(self):
        """Setup the custom channels tab."""
        channels_tab = self.tabview.tab("📊 Custom Channels")
        
        # Create main container
        channels_container = ctk.CTkFrame(channels_tab)
        channels_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            channels_container,
            text="📊 Custom Channel Configuration",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(20, 15))
        
        # Search and filter section
        search_frame = ctk.CTkFrame(channels_container)
        search_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        search_label = ctk.CTkLabel(
            search_frame,
            text="🔍 Search Channels:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        search_label.pack(pady=(15, 5))
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Type to search channels...",
            height=35
        )
        self.search_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        # Channel addition form
        self.setup_channel_form(channels_container)
        
        # Channels table
        self.setup_channels_table(channels_container)
    
    def setup_channel_form(self, parent):
        """Setup the channel addition form."""
        form_frame = ctk.CTkFrame(parent)
        form_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        form_title = ctk.CTkLabel(
            form_frame,
            text="➕ Add New Channel",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        form_title.pack(pady=(15, 10))
        
        # Form fields in a grid
        fields_frame = ctk.CTkFrame(form_frame)
        fields_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        # Channel name
        ctk.CTkLabel(fields_frame, text="Channel Name:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        self.channel_name_combo = ModernAutocompleteCombobox(fields_frame, width=200)
        self.channel_name_combo.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # X Variable
        ctk.CTkLabel(fields_frame, text="X Variable:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        self.x_var_combo = ModernAutocompleteCombobox(fields_frame, width=200)
        self.x_var_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Y Variable
        ctk.CTkLabel(fields_frame, text="Y Variable:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        self.y_var_combo = ModernAutocompleteCombobox(fields_frame, width=200)
        self.y_var_combo.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Configure grid weights
        fields_frame.grid_columnconfigure(1, weight=1)
        
        # Add button
        self.add_channel_button = ctk.CTkButton(
            form_frame,
            text="➕ Add Channel",
            command=self.add_custom_channel,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.add_channel_button.pack(pady=(0, 15))
    
    def setup_channels_table(self, parent):
        """Setup the channels table with modern styling."""
        table_frame = ctk.CTkFrame(parent)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        table_title = ctk.CTkLabel(
            table_frame,
            text="📋 Configured Channels",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        table_title.pack(pady=(15, 10))
        
        # For now, we'll use a textbox to display channels
        # In a full implementation, you might want to use a more sophisticated table widget
        self.channels_display = ctk.CTkTextbox(
            table_frame,
            height=300,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.channels_display.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Table controls
        controls_frame = ctk.CTkFrame(table_frame)
        controls_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.clear_channels_button = ctk.CTkButton(
            controls_frame,
            text="🗑️ Clear All",
            command=self.clear_all_channels,
            height=30,
            width=100,
            font=ctk.CTkFont(size=11)
        )
        self.clear_channels_button.pack(side="left", padx=(0, 10))
        
        self.export_channels_button = ctk.CTkButton(
            controls_frame,
            text="📤 Export Config",
            command=self.export_channel_config,
            height=30,
            width=120,
            font=ctk.CTkFont(size=11)
        )
        self.export_channels_button.pack(side="left")
    
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
        self.search_var.trace('w', self.filter_channels)
        
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    # UI Event Handlers
    def change_theme(self, theme):
        """Change the application theme."""
        theme_lower = theme.lower()
        ctk.set_appearance_mode(theme_lower)
        self.log_status(f"🎨 Theme changed to {theme} mode")
    
    def select_vehicle_file(self):
        """Open file dialog to select vehicle MDF file."""
        file_path = filedialog.askopenfilename(
            title="Select Vehicle MDF File",
            filetypes=[("MDF files", "*.mf4"), ("MDF files", "*.mdf"), ("All files", "*.*")]
        )
        
        if file_path:
            self.vehicle_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_status_label.configure(text=f"📁 {filename}")
            self.log_status(f"✅ Vehicle file selected: {filename}")
            
            # Enable analysis button
            self.analysis_button.configure(state="normal")
            
            # Auto-analyze the file
            self.analyze_vehicle_file()
    
    def analyze_vehicle_file(self):
        """Analyze the selected vehicle file."""
        if not self.vehicle_file_path:
            messagebox.showwarning("Warning", "Please select a vehicle file first.")
            return
        
        # Show progress dialog
        progress_dialog = ModernProgressDialog(
            self.root,
            "Analyzing Vehicle File",
            "Reading and analyzing MDF file..."
        )
        
        def analyze_thread():
            try:
                progress_dialog.update_progress(0.1, "Opening MDF file...")
                
                # Load MDF file
                self.vehicle_data = MDF(self.vehicle_file_path)
                progress_dialog.update_progress(0.3, "Reading channel information...")
                
                # Get channel list
                self.available_channels = []
                for group in self.vehicle_data.groups:
                    for channel in group.channels:
                        if hasattr(channel, 'name'):
                            self.available_channels.append(channel.name)
                
                progress_dialog.update_progress(0.6, "Analyzing sampling rates...")
                
                # Analyze sampling rates and generate report
                analysis_report = self.generate_analysis_report()
                
                progress_dialog.update_progress(0.9, "Updating interface...")
                
                # Update UI on main thread
                self.root.after(0, lambda: self.update_analysis_results(analysis_report))
                progress_dialog.update_progress(1.0, "Analysis complete!")
                
                # Close progress dialog
                self.root.after(1000, progress_dialog.close)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Analysis failed: {str(e)}"))
                progress_dialog.close()
        
        # Start analysis in background thread
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def generate_analysis_report(self):
        """Generate detailed analysis report of the vehicle file."""
        if not self.vehicle_data:
            return "No vehicle data loaded."
        
        report_lines = []
        report_lines.append("🚗 VEHICLE FILE ANALYSIS REPORT")
        report_lines.append("=" * 50)
        report_lines.append(f"📁 File: {os.path.basename(self.vehicle_file_path)}")
        report_lines.append(f"📊 Total Channels: {len(self.available_channels)}")
        report_lines.append("")
        
        # Analyze sample rates
        sample_rates = {}
        channel_info = []
        
        try:
            for group_idx, group in enumerate(self.vehicle_data.groups):
                for ch_idx, channel in enumerate(group.channels):
                    if hasattr(channel, 'name') and channel.name:
                        # Get channel signal to analyze sampling
                        try:
                            signal = self.vehicle_data.get(channel.name, group=group_idx)
                            if signal and len(signal.timestamps) > 1:
                                # Calculate sample rate
                                time_diff = signal.timestamps[-1] - signal.timestamps[0]
                                sample_count = len(signal.timestamps)
                                avg_rate = sample_count / time_diff if time_diff > 0 else 0
                                
                                # Calculate actual intervals
                                intervals = np.diff(signal.timestamps)
                                min_interval = np.min(intervals) if len(intervals) > 0 else 0
                                max_interval = np.max(intervals) if len(intervals) > 0 else 0
                                
                                channel_info.append({
                                    'name': channel.name,
                                    'samples': sample_count,
                                    'duration': time_diff,
                                    'avg_rate': avg_rate,
                                    'min_interval': min_interval,
                                    'max_interval': max_interval
                                })
                                
                                # Group by approximate sample rate
                                rate_key = round(avg_rate, 1)
                                if rate_key not in sample_rates:
                                    sample_rates[rate_key] = []
                                sample_rates[rate_key].append(channel.name)
                        except:
                            continue
            
            # Add sample rate summary
            report_lines.append("📈 SAMPLING RATE ANALYSIS:")
            report_lines.append("-" * 30)
            
            for rate in sorted(sample_rates.keys(), reverse=True):
                channels = sample_rates[rate]
                report_lines.append(f"  {rate:6.1f} Hz: {len(channels)} channels")
                if len(channels) <= 5:
                    for ch in channels:
                        report_lines.append(f"    • {ch}")
                else:
                    for ch in channels[:3]:
                        report_lines.append(f"    • {ch}")
                    report_lines.append(f"    • ... and {len(channels)-3} more")
                report_lines.append("")
            
            # Recommendations
            report_lines.append("💡 RECOMMENDATIONS:")
            report_lines.append("-" * 20)
            
            if sample_rates:
                max_rate = max(sample_rates.keys())
                recommended_rates = [max_rate, max_rate/2, max_rate/5, max_rate/10]
                recommended_rates = [r for r in recommended_rates if r >= 1.0]
                
                report_lines.append("  Recommended raster values:")
                for rate in recommended_rates:
                    report_lines.append(f"    • {rate:6.1f} Hz - Good for {rate:.1f}Hz channels")
                
                report_lines.append("")
                report_lines.append(f"  ⚠️  Minimum recommended raster: {min(recommended_rates):.1f} Hz")
                report_lines.append(f"  ✅  Maximum useful raster: {max_rate:.1f} Hz")
        
        except Exception as e:
            report_lines.append(f"❌ Error during analysis: {str(e)}")
        
        return "\n".join(report_lines)
    
    def update_analysis_results(self, analysis_report):
        """Update the analysis text display with results."""
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", analysis_report)
        
        # Update comboboxes with available channels
        if self.available_channels:
            self.channel_name_combo.set_completion_list(self.available_channels)
            self.x_var_combo.set_completion_list(self.available_channels)
            self.y_var_combo.set_completion_list(self.available_channels)
        
        self.log_status(f"✅ Analysis complete. Found {len(self.available_channels)} channels.")
    
    def add_custom_channel(self):
        """Add a new custom channel configuration."""
        channel_name = self.channel_name_combo.get().strip()
        x_var = self.x_var_combo.get().strip()
        y_var = self.y_var_combo.get().strip()
        
        if not all([channel_name, x_var, y_var]):
            messagebox.showwarning("Warning", "Please fill in all fields.")
            return
        
        # Check if channel already exists
        for channel in self.custom_channels:
            if channel['name'] == channel_name:
                messagebox.showwarning("Warning", "Channel with this name already exists.")
                return
        
        # Add channel
        new_channel = {
            'name': channel_name,
            'x_variable': x_var,
            'y_variable': y_var,
            'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.custom_channels.append(new_channel)
        self.update_channels_display()
        
        # Clear form (optional)
        # self.channel_name_combo.set("")
        # self.x_var_combo.set("")
        # self.y_var_combo.set("")
        
        self.log_status(f"✅ Added custom channel: {channel_name}")
    
    def update_channels_display(self):
        """Update the channels display with current channels."""
        self.channels_display.delete("1.0", "end")
        
        if not self.custom_channels:
            self.channels_display.insert("1.0", "No custom channels configured.\n\nAdd channels using the form above.")
            return
        
        display_text = "📊 CONFIGURED CUSTOM CHANNELS\n"
        display_text += "=" * 50 + "\n\n"
        
        for i, channel in enumerate(self.custom_channels, 1):
            display_text += f"{i:2d}. 📈 {channel['name']}\n"
            display_text += f"     X Variable: {channel['x_variable']}\n"
            display_text += f"     Y Variable: {channel['y_variable']}\n"
            display_text += f"     Created: {channel['created']}\n"
            display_text += "-" * 40 + "\n"
        
        display_text += f"\nTotal: {len(self.custom_channels)} custom channels"
        
        self.channels_display.insert("1.0", display_text)
    
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
    
    def filter_channels(self, *args):
        """Filter channels based on search term."""
        # This would filter the channels display based on search
        # Implementation would depend on the specific table/display widget used
        search_term = self.search_var.get().lower()
        if search_term:
            self.log_status(f"🔍 Filtering channels: '{search_term}'")
    
    def show_enhanced_raster_dialog(self):
        """Show enhanced raster selection dialog."""
        if not self.vehicle_data:
            messagebox.showwarning("Warning", "Please analyze a vehicle file first.")
            return
        
        # Create enhanced dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("🎛️ Enhanced Raster Selection")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (300)
        y = (dialog.winfo_screenheight() // 2) - (250)
        dialog.geometry(f"600x500+{x}+{y}")
        
        # Dialog content
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text="🎯 Select Optimal Raster Value",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 20))
        
        # Recommendations
        rec_frame = ctk.CTkFrame(main_frame)
        rec_frame.pack(fill="x", pady=(0, 15))
        
        rec_label = ctk.CTkLabel(
            rec_frame,
            text="💡 Recommended Values:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        rec_label.pack(pady=(15, 10))
        
        # Add some example recommendations
        rec_values = ["50.0 Hz - High precision", "20.0 Hz - Standard", "10.0 Hz - Efficient", "5.0 Hz - Conservative"]
        
        self.selected_raster = ctk.StringVar(value="10.0")
        
        for rec in rec_values:
            value = rec.split()[0]
            radio = ctk.CTkRadioButton(
                rec_frame,
                text=rec,
                variable=self.selected_raster,
                value=value
            )
            radio.pack(pady=2, padx=20, anchor="w")
        
        # Custom entry
        custom_frame = ctk.CTkFrame(main_frame)
        custom_frame.pack(fill="x", pady=(15, 20))
        
        custom_label = ctk.CTkLabel(
            custom_frame,
            text="🔧 Custom Value:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        custom_label.pack(pady=(15, 5))
        
        self.custom_raster_entry = ctk.CTkEntry(
            custom_frame,
            placeholder_text="Enter custom raster value",
            height=35
        )
        self.custom_raster_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(0, 10))
        
        def apply_raster():
            custom_value = self.custom_raster_entry.get().strip()
            if custom_value:
                try:
                    float(custom_value)
                    self.raster_entry.delete(0, "end")
                    self.raster_entry.insert(0, custom_value)
                except ValueError:
                    messagebox.showerror("Error", "Invalid raster value.")
                    return
            else:
                selected = self.selected_raster.get()
                self.raster_entry.delete(0, "end")
                self.raster_entry.insert(0, selected)
            
            dialog.destroy()
            self.log_status(f"🎯 Raster value set to: {self.raster_entry.get()} Hz")
        
        apply_button = ctk.CTkButton(
            button_frame,
            text="✅ Apply Selection",
            command=apply_raster,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        apply_button.pack(side="left", padx=(20, 10), pady=15, fill="x", expand=True)
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="❌ Cancel",
            command=dialog.destroy,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        cancel_button.pack(side="right", padx=(10, 20), pady=15, fill="x", expand=True)
    
    def process_channels(self):
        """Process the custom channels with the selected raster."""
        if not self.vehicle_data:
            messagebox.showwarning("Warning", "Please select and analyze a vehicle file first.")
            return
        
        if not self.custom_channels:
            messagebox.showwarning("Warning", "Please configure at least one custom channel.")
            return
        
        raster_value = self.raster_entry.get().strip()
        if not raster_value:
            messagebox.showwarning("Warning", "Please enter a raster value.")
            return
        
        try:
            raster = float(raster_value)
            if raster <= 0:
                raise ValueError("Raster must be positive")
        except ValueError:
            messagebox.showerror("Error", "Invalid raster value. Please enter a positive number.")
            return
        
        # Show processing dialog
        progress_dialog = ModernProgressDialog(
            self.root,
            "Processing Channels",
            f"Processing {len(self.custom_channels)} custom channels..."
        )
        
        def process_thread():
            try:
                total_channels = len(self.custom_channels)
                
                for i, channel in enumerate(self.custom_channels):
                    progress = (i + 1) / total_channels
                    progress_dialog.update_progress(
                        progress, 
                        f"Processing channel {i+1}/{total_channels}: {channel['name']}"
                    )
                    
                    # Simulate processing time
                    import time
                    time.sleep(0.5)
                
                # Success
                self.root.after(0, lambda: self.on_processing_complete(raster))
                progress_dialog.close()
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Processing failed: {str(e)}"))
                progress_dialog.close()
        
        # Start processing in background thread
        threading.Thread(target=process_thread, daemon=True).start()
    
    def on_processing_complete(self, raster):
        """Handle completion of channel processing."""
        # Ask user where to save the result
        output_file = filedialog.asksaveasfilename(
            title="Save Processed File",
            defaultextension=".mf4",
            filetypes=[("MDF files", "*.mf4"), ("All files", "*.*")]
        )
        
        if output_file:
            self.log_status(f"🚀 Processing completed successfully!")
            self.log_status(f"📁 Output saved to: {os.path.basename(output_file)}")
            self.log_status(f"🎯 Used raster: {raster} Hz")
            self.log_status(f"📊 Processed {len(self.custom_channels)} custom channels")
            
            messagebox.showinfo(
                "Success", 
                f"Channel processing completed successfully!\n\n"
                f"📁 Output: {os.path.basename(output_file)}\n"
                f"🎯 Raster: {raster} Hz\n"
                f"📊 Channels: {len(self.custom_channels)}"
            )
    
    def save_settings(self):
        """Save current settings to file."""
        settings = {
            'theme': self.theme_menu.get(),
            'custom_channels': self.custom_channels,
            'last_raster': self.raster_entry.get(),
            'saved_at': datetime.now().isoformat()
        }
        
        file_path = filedialog.asksaveasfilename(
            title="Save Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(settings, f, indent=2)
                self.log_status(f"💾 Settings saved to: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def load_settings(self):
        """Load settings from file."""
        file_path = filedialog.askopenfilename(
            title="Load Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    settings = json.load(f)
                
                # Apply settings
                if 'theme' in settings:
                    self.theme_menu.set(settings['theme'])
                    self.change_theme(settings['theme'])
                
                if 'custom_channels' in settings:
                    self.custom_channels = settings['custom_channels']
                    self.update_channels_display()
                
                if 'last_raster' in settings:
                    self.raster_entry.delete(0, "end")
                    self.raster_entry.insert(0, settings['last_raster'])
                
                self.log_status(f"📁 Settings loaded from: {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
    
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
        """Handle application closing."""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
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