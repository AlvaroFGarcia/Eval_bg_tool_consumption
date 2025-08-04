"""
Vehicle Log Channel Appender - Modern UI Demo
This is a demo version for testing the modern UI without heavy dependencies
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import json
from datetime import datetime
import threading
import time

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


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


class VehicleLogChannelAppenderDemo:
    def __init__(self):
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("🚗 Vehicle Log Channel Appender - Modern Edition (Demo)")
        self.root.geometry("1200x800")
        
        # Set window icon and properties
        self.setup_window_properties()
        
        # Demo data
        self.vehicle_file_path = None
        self.custom_channels = []
        self.available_channels = [
            "Engine_RPM", "Vehicle_Speed", "Throttle_Position", "Engine_Load",
            "Fuel_Flow", "Intake_Temp", "Coolant_Temp", "Oil_Pressure",
            "Brake_Pressure", "Steering_Angle", "Gear_Position", "Battery_Voltage"
        ]
        
        # UI state
        self.search_var = ctk.StringVar()
        
        # Setup UI
        self.setup_ui()
        self.setup_bindings()
        
        # Initialize with welcome message
        self.log_status("🎉 Welcome to Vehicle Log Channel Appender - Modern Edition!")
        self.log_status("💡 This is a demo version to showcase the modern UI")
    
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
            text="Modern Edition v2.0 (Demo)",
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
            text="Select MDF File (Demo)",
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
            text="🔍 Analyze Vehicle File (Demo)",
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
        
        # Add demo analysis
        demo_analysis = """🚗 DEMO VEHICLE FILE ANALYSIS REPORT
==================================================
📁 File: demo_vehicle_data.mf4
📊 Total Channels: 12

📈 SAMPLING RATE ANALYSIS:
------------------------------
  100.0 Hz: 4 channels
    • Engine_RPM
    • Vehicle_Speed
    • Throttle_Position
    • Engine_Load

   50.0 Hz: 4 channels
    • Fuel_Flow
    • Intake_Temp
    • Coolant_Temp
    • Oil_Pressure

   10.0 Hz: 4 channels
    • Brake_Pressure
    • Steering_Angle
    • Gear_Position
    • Battery_Voltage

💡 RECOMMENDATIONS:
--------------------
  Recommended raster values:
    • 100.0 Hz - Good for 100.0Hz channels
    •  50.0 Hz - Good for 50.0Hz channels  
    •  20.0 Hz - Good for 20.0Hz channels
    •  10.0 Hz - Good for 10.0Hz channels

  ⚠️  Minimum recommended raster: 10.0 Hz
  ✅  Maximum useful raster: 100.0 Hz"""
        
        self.analysis_text.insert("1.0", demo_analysis)
        
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
        self.raster_entry.insert(0, "10.0")
        
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
            text="🚀 Process Channels (Demo)",
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
        
        # Channel addition form
        form_frame = ctk.CTkFrame(channels_container)
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
        self.channel_name_combo = ctk.CTkComboBox(fields_frame, values=["Engine_Map", "Load_Map", "Efficiency_Map"], width=200)
        self.channel_name_combo.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # X Variable
        ctk.CTkLabel(fields_frame, text="X Variable:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        self.x_var_combo = ctk.CTkComboBox(fields_frame, values=self.available_channels, width=200)
        self.x_var_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Y Variable
        ctk.CTkLabel(fields_frame, text="Y Variable:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        self.y_var_combo = ctk.CTkComboBox(fields_frame, values=self.available_channels, width=200)
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
        
        # Channels display
        table_frame = ctk.CTkFrame(channels_container)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        table_title = ctk.CTkLabel(
            table_frame,
            text="📋 Configured Channels",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        table_title.pack(pady=(15, 10))
        
        self.channels_display = ctk.CTkTextbox(
            table_frame,
            height=300,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.channels_display.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Initialize with demo data
        self.update_channels_display()
    
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
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    # Event Handlers
    def change_theme(self, theme):
        """Change the application theme."""
        theme_lower = theme.lower()
        ctk.set_appearance_mode(theme_lower)
        self.log_status(f"🎨 Theme changed to {theme} mode")
    
    def select_vehicle_file(self):
        """Demo file selection."""
        self.log_status("📁 Demo: Vehicle file selected (demo_vehicle_data.mf4)")
        self.file_status_label.configure(text="📁 demo_vehicle_data.mf4")
        messagebox.showinfo("Demo Mode", "This is a demo. In the full version, you would select an actual MDF file.")
    
    def analyze_vehicle_file(self):
        """Demo analysis."""
        progress_dialog = ModernProgressDialog(
            self.root,
            "Analyzing Vehicle File",
            "Demo analysis in progress..."
        )
        
        def demo_analysis():
            for i in range(10):
                progress = (i + 1) / 10
                status = f"Step {i+1}/10: Analyzing demo data..."
                self.root.after(0, lambda p=progress, s=status: progress_dialog.update_progress(p, s))
                time.sleep(0.2)
            
            self.root.after(0, progress_dialog.close)
            self.root.after(0, lambda: self.log_status("✅ Demo analysis completed"))
        
        threading.Thread(target=demo_analysis, daemon=True).start()
    
    def add_custom_channel(self):
        """Add a demo custom channel."""
        channel_name = self.channel_name_combo.get()
        x_var = self.x_var_combo.get()
        y_var = self.y_var_combo.get()
        
        if channel_name and x_var and y_var:
            new_channel = {
                'name': channel_name,
                'x_variable': x_var,
                'y_variable': y_var,
                'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.custom_channels.append(new_channel)
            self.update_channels_display()
            self.log_status(f"✅ Added custom channel: {channel_name}")
        else:
            messagebox.showwarning("Warning", "Please fill in all fields.")
    
    def update_channels_display(self):
        """Update the channels display."""
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
    
    def show_enhanced_raster_dialog(self):
        """Show demo raster selection dialog."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("🎛️ Enhanced Raster Selection (Demo)")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (300)
        y = (dialog.winfo_screenheight() // 2) - (200)
        dialog.geometry(f"600x400+{x}+{y}")
        
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
            text="💡 Recommended Values (Demo):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        rec_label.pack(pady=(15, 10))
        
        rec_values = ["100.0 Hz - High precision", "50.0 Hz - Standard", "20.0 Hz - Efficient", "10.0 Hz - Conservative"]
        
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
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(15, 10))
        
        def apply_raster():
            selected = self.selected_raster.get()
            self.raster_entry.delete(0, "end")
            self.raster_entry.insert(0, selected)
            dialog.destroy()
            self.log_status(f"🎯 Raster value set to: {selected} Hz")
        
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
        """Demo processing."""
        if not self.custom_channels:
            messagebox.showwarning("Warning", "Please add at least one custom channel first.")
            return
        
        progress_dialog = ModernProgressDialog(
            self.root,
            "Processing Channels",
            f"Demo: Processing {len(self.custom_channels)} channels..."
        )
        
        def demo_processing():
            total_channels = len(self.custom_channels)
            
            for i, channel in enumerate(self.custom_channels):
                progress = (i + 1) / total_channels
                status = f"Processing channel {i+1}/{total_channels}: {channel['name']}"
                self.root.after(0, lambda p=progress, s=status: progress_dialog.update_progress(p, s))
                time.sleep(0.5)
            
            self.root.after(0, progress_dialog.close)
            self.root.after(0, lambda: messagebox.showinfo(
                "Demo Complete", 
                f"Demo processing completed!\n\n"
                f"📁 Would save to: demo_output.mf4\n"
                f"🎯 Raster: {self.raster_entry.get()} Hz\n"
                f"📊 Channels: {len(self.custom_channels)}"
            ))
            self.root.after(0, lambda: self.log_status("🚀 Demo processing completed successfully!"))
        
        threading.Thread(target=demo_processing, daemon=True).start()
    
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
        if messagebox.askokcancel("Quit", "Do you want to quit the demo application?"):
            self.root.destroy()
    
    def run(self):
        """Start the application."""
        self.root.mainloop()


def main():
    """Main function to run the demo application."""
    try:
        app = VehicleLogChannelAppenderDemo()
        app.run()
    except Exception as e:
        print(f"Failed to start demo application: {e}")
        input("Press Enter to continue...")


if __name__ == "__main__":
    main()