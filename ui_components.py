"""
UI Components Module for Vehicle Log Channel Appender
Contains reusable UI components and widgets.
"""

import customtkinter as ctk
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import os


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
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack()
        
    def update_status(self, message, progress=None):
        """Update the dialog status and progress."""
        self.status_label.configure(text=message)
        if progress is not None:
            self.progress_bar.set(progress)
        self.dialog.update()
        
    def close(self):
        """Close the progress dialog."""
        self.dialog.destroy()


class AdvancedRasterDialog:
    """Advanced raster configuration dialog with channel analysis."""
    
    def __init__(self, parent, channel_analysis, logger=None):
        """Initialize the advanced raster dialog.
        
        Args:
            parent: Parent window
            channel_analysis: Dictionary with channel analysis data
            logger: Logging function
        """
        self.logger = logger if logger else lambda msg: print(msg)
        self.channel_analysis = channel_analysis
        self.result = [None]
        
        # Create raster dialog
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title('🎯 Set Time Raster - Advanced Analysis')
        self.dialog.geometry('900x800')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        self.dialog.minsize(800, 650)
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 450
        y = (self.dialog.winfo_screenheight() // 2) - 400
        self.dialog.geometry(f"900x800+{x}+{y}")
        
        # Calculate overall minimum raster
        self.overall_min_raster = 0.001  # Default fallback
        self.limiting_channel = "Unknown"
        
        if self.channel_analysis:
            min_rasters = []
            for ch_name, analysis in self.channel_analysis.items():
                if 'suggested_min_raster' in analysis:
                    min_rasters.append(analysis['suggested_min_raster'])
                    if analysis['suggested_min_raster'] == max(min_rasters):
                        self.limiting_channel = ch_name
            if min_rasters:
                self.overall_min_raster = max(min_rasters)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame,
            text="🎯 Time Raster Configuration with Channel Analysis",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Info frame
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=(0, 15))
        
        info_text = ctk.CTkLabel(
            info_frame,
            text="The vehicle channels may have different sampling rates.\n"
                 "Specify a time raster (in seconds) to resample all signals to the same time base.\n"
                 "Lower rasters provide finer resolution but require interpolation if original data is coarser.",
            font=ctk.CTkFont(size=11),
            justify="left"
        )
        info_text.pack(padx=15, pady=10)
        
        # Minimum raster warning frame
        warning_frame = ctk.CTkFrame(main_frame)
        warning_frame.pack(fill="x", pady=(0, 15))
        
        warning_label = ctk.CTkLabel(
            warning_frame,
            text=f"⚠️ Recommended minimum raster: {self.overall_min_raster:.6f} seconds ({self.overall_min_raster*1000:.2f} ms)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ff6b35"
        )
        warning_label.pack(padx=15, pady=(10, 5))
        
        limiting_label = ctk.CTkLabel(
            warning_frame,
            text=f"Limiting channel: {self.limiting_channel}",
            font=ctk.CTkFont(size=11),
            text_color="#ff9500"
        )
        limiting_label.pack(padx=15, pady=(0, 10))
        
        # Channel analysis table - collapsible
        analysis_frame = ctk.CTkFrame(main_frame)
        analysis_frame.pack(fill="x", pady=(0, 15))
        
        # Toggle button for analysis table
        analysis_header = ctk.CTkFrame(analysis_frame)
        analysis_header.pack(fill="x", padx=15, pady=(10, 5))
        
        analysis_title = ctk.CTkLabel(
            analysis_header,
            text="📊 Per-Channel Analysis",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        analysis_title.pack(side="left")
        
        # Toggle button
        self.analysis_expanded = ctk.BooleanVar(value=False)
        self.toggle_analysis_btn = ctk.CTkButton(
            analysis_header,
            text="▼ Show Details",
            command=self.toggle_analysis_table,
            width=120,
            height=25,
            font=ctk.CTkFont(size=11)
        )
        self.toggle_analysis_btn.pack(side="right")
        
        # Analysis table container (initially hidden)
        self.analysis_table_container = ctk.CTkFrame(analysis_frame)
        
        self.setup_analysis_table()
        
        # Input section
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", pady=(0, 15))
        
        input_label = ctk.CTkLabel(
            input_frame,
            text="Enter raster value (seconds):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        input_label.pack(pady=(10, 5))
        
        # Raster input
        self.raster_var = ctk.StringVar(value=str(self.overall_min_raster))
        self.raster_entry = ctk.CTkEntry(input_frame, textvariable=self.raster_var, width=200)
        self.raster_entry.pack(pady=(0, 10))
        self.raster_entry.focus()
        
        # Suggestion buttons
        suggestions_frame = ctk.CTkFrame(input_frame)
        suggestions_frame.pack(pady=(0, 10))
        
        suggestions = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
        
        # Configure grid for suggestions frame
        suggestions_frame.grid_columnconfigure(0, weight=1)
        suggestions_frame.grid_columnconfigure(1, weight=1)
        suggestions_frame.grid_columnconfigure(2, weight=1)
        
        # Title label using grid
        title_label = ctk.CTkLabel(suggestions_frame, text="Quick select:", 
                    font=ctk.CTkFont(size=11, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 5))
        
        for i, value in enumerate(suggestions):
            row = (i // 3) + 1  # Start from row 1 (row 0 is the title)
            col = i % 3
            color = "#2b7a0b" if value >= self.overall_min_raster else "#8a6914"
            
            btn = ctk.CTkButton(
                suggestions_frame,
                text=f"{value}s",
                command=lambda v=value: self.raster_var.set(str(v)),
                width=80,
                height=30,
                fg_color=color
            )
            btn.grid(row=row, column=col, padx=5, pady=2)
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        ok_btn = ctk.CTkButton(button_frame, text='✅ OK', command=self.confirm_raster, width=100)
        ok_btn.pack(side='left', padx=10)
        
        cancel_btn = ctk.CTkButton(button_frame, text='❌ Cancel', command=self.cancel_raster, width=100)
        cancel_btn.pack(side='left', padx=10)
        
        self.raster_entry.bind('<Return>', lambda e: self.confirm_raster())
        
    def setup_analysis_table(self):
        """Setup the channel analysis table."""
        # Create treeview for channel analysis
        analysis_tree_frame = ctk.CTkFrame(self.analysis_table_container)
        analysis_tree_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        columns = ("Channel", "Min Interval", "Avg Interval", "Suggested Min Raster", "Samples", "Status")
        self.analysis_tree = ttk.Treeview(analysis_tree_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        for col in columns:
            self.analysis_tree.heading(col, text=col)
            self.analysis_tree.column(col, width=120)
        
        # Populate tree with color indicators
        for ch_name, analysis in self.channel_analysis.items():
            if 'error' in analysis:
                # Red for errors
                self.analysis_tree.insert("", "end", values=(
                    ch_name, "Error", "Error", "Error", "Error", "❌ " + analysis['error']
                ), tags=("error",))
            elif 'note' in analysis:
                # Yellow for CSV files
                self.analysis_tree.insert("", "end", values=(
                    ch_name, "N/A", "N/A", "N/A", analysis.get('sample_count', 'N/A'), "⚠️ " + analysis['note']
                ), tags=("warning",))
            else:
                # Green for good channels
                status = "✅ Good"
                if analysis.get('suggested_min_raster', 0) > 0.01:  # Above 10ms might be concerning
                    status = "⚠️ Low rate"
                
                self.analysis_tree.insert("", "end", values=(
                    ch_name,
                    f"{analysis['min_interval']:.6f}s",
                    f"{analysis['avg_interval']:.6f}s", 
                    f"{analysis['suggested_min_raster']:.6f}s",
                    analysis['sample_count'],
                    status
                ), tags=("good",))
        
        # Configure row colors with better contrast
        self.analysis_tree.tag_configure("error", background="#ffcccc", foreground="#000000")
        self.analysis_tree.tag_configure("warning", background="#ffeaa7", foreground="#2d3436")  
        self.analysis_tree.tag_configure("good", background="#d4edda", foreground="#000000")
        
        # Add scrollbar
        tree_scroll = ttk.Scrollbar(analysis_tree_frame, orient="vertical", command=self.analysis_tree.yview)
        self.analysis_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.analysis_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
    def toggle_analysis_table(self):
        """Toggle the visibility of the analysis table."""
        if self.analysis_expanded.get():
            # Hide table
            self.analysis_table_container.pack_forget()
            self.toggle_analysis_btn.configure(text="▼ Show Details")
            self.analysis_expanded.set(False)
        else:
            # Show table
            self.analysis_table_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            self.toggle_analysis_btn.configure(text="▲ Hide Details")
            self.analysis_expanded.set(True)
    
    def confirm_raster(self):
        """Confirm the raster selection."""
        try:
            raster_value = float(self.raster_var.get())
            if raster_value <= 0:
                messagebox.showerror('Error', 'Raster value must be positive!')
                return
            self.result[0] = raster_value
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror('Error', 'Please enter a valid number!')
    
    def cancel_raster(self):
        """Cancel the raster selection."""
        self.dialog.destroy()
    
    def show(self):
        """Show the dialog and return the result."""
        self.dialog.wait_window()
        return self.result[0]


class ExcelFilterDialog:
    """Excel-like filter dialog for column filtering."""
    
    def __init__(self, parent, column_name, unique_values, current_filter, logger=None):
        """Initialize the Excel filter dialog.
        
        Args:
            parent: Parent window
            column_name: Name of the column to filter
            unique_values: List of unique values in the column
            current_filter: Current filter configuration
            logger: Logging function
        """
        self.logger = logger if logger else lambda msg: print(msg)
        self.column_name = column_name
        self.unique_values = unique_values
        self.current_filter = current_filter
        self.result = [None]
        
        # Create filter dialog
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f'🔽 Filter: {column_name}')
        self.dialog.geometry('450x700')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        self.dialog.minsize(400, 600)
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 225
        y = (self.dialog.winfo_screenheight() // 2) - 350
        self.dialog.geometry(f"450x700+{x}+{y}")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        # Create main scrollable frame
        main_scroll_frame = ctk.CTkScrollableFrame(self.dialog)
        main_scroll_frame.pack(fill="both", expand=True, padx=15, pady=(15, 5))
        
        # Fixed button frame at bottom
        button_frame_fixed = ctk.CTkFrame(self.dialog)
        button_frame_fixed.pack(fill="x", side="bottom", padx=15, pady=(5, 15))
        
        # Title
        title_label = ctk.CTkLabel(
            main_scroll_frame,
            text=f"🔽 Filter Column: {self.column_name}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(5, 15))
        
        # Filter type selection
        filter_type_frame = ctk.CTkFrame(main_scroll_frame)
        filter_type_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(filter_type_frame, text="Filter Type:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.filter_type_var = ctk.StringVar(value=self.current_filter["filter_type"])
        
        include_radio = ctk.CTkRadioButton(
            filter_type_frame,
            text="✅ Include selected values (show only these)",
            variable=self.filter_type_var,
            value="include",
            font=ctk.CTkFont(size=11)
        )
        include_radio.pack(anchor="w", padx=20, pady=2)
        
        exclude_radio = ctk.CTkRadioButton(
            filter_type_frame,
            text="❌ Exclude selected values (hide these)",
            variable=self.filter_type_var,
            value="exclude",
            font=ctk.CTkFont(size=11)
        )
        exclude_radio.pack(anchor="w", padx=20, pady=(2, 10))
        
        # Advanced text filter section
        text_filter_frame = ctk.CTkFrame(main_scroll_frame)
        text_filter_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(text_filter_frame, text="🔍 Text Filter:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Text filter controls
        text_controls_frame = ctk.CTkFrame(text_filter_frame)
        text_controls_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Filter type dropdown
        self.text_filter_type_var = ctk.StringVar(value="contains")
        text_type_menu = ctk.CTkOptionMenu(
            text_controls_frame,
            variable=self.text_filter_type_var,
            values=["contains", "starts with", "ends with", "equals", "not contains"],
            font=ctk.CTkFont(size=10),
            width=120
        )
        text_type_menu.pack(side="left", padx=(0, 10))
        
        # Text filter entry
        self.text_filter_value_var = ctk.StringVar()
        text_filter_entry = ctk.CTkEntry(
            text_controls_frame,
            textvariable=self.text_filter_value_var,
            placeholder_text="Enter text to filter...",
            width=200
        )
        text_filter_entry.pack(side="left", fill="x", expand=True)
        
        # Apply text filter button
        apply_text_btn = ctk.CTkButton(
            text_filter_frame,
            text="Apply Text Filter",
            command=self.apply_text_filter,
            height=25,
            width=120,
            font=ctk.CTkFont(size=10)
        )
        apply_text_btn.pack(padx=10, pady=(0, 10))
        
        # Simple search within values
        search_frame = ctk.CTkFrame(main_scroll_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(search_frame, text="🔍 Quick search values:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.search_var = ctk.StringVar()
        self.search_var.trace('w', self.filter_values_list)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, placeholder_text="Type to search...")
        search_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # Values selection
        values_frame = ctk.CTkFrame(main_scroll_frame)
        values_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        ctk.CTkLabel(values_frame, text=f"Select values ({len(self.unique_values)} total):", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Control buttons
        control_frame = ctk.CTkFrame(values_frame)
        control_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        select_all_btn = ctk.CTkButton(control_frame, text="Select All", command=self.select_all, width=80, height=25)
        select_all_btn.pack(side="left", padx=(0, 5))
        
        clear_all_btn = ctk.CTkButton(control_frame, text="Clear All", command=self.clear_all, width=80, height=25)
        clear_all_btn.pack(side="left", padx=5)
        
        # Values list with scrollable frame
        self.values_container = ctk.CTkScrollableFrame(values_frame, height=300)
        self.values_container.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Store checkboxes for values
        self.value_vars = {}
        self.value_checkboxes = {}
        
        # Create checkboxes for all values
        for value in self.unique_values:
            var = ctk.BooleanVar()
            # Set initial state based on current filter
            if self.current_filter["enabled"]:
                var.set(value in self.current_filter["selected_values"])
            else:
                var.set(True)  # Select all by default if no filter
                
            self.value_vars[value] = var
            
            checkbox = ctk.CTkCheckBox(
                self.values_container,
                text=value,
                variable=var,
                font=ctk.CTkFont(size=10)
            )
            checkbox.pack(anchor="w", padx=5, pady=1)
            self.value_checkboxes[value] = checkbox
        
        # Buttons at bottom
        apply_btn = ctk.CTkButton(button_frame_fixed, text='✅ Apply Filter', command=self.apply_filter, width=120)
        apply_btn.pack(side='left', padx=(0, 10))
        
        clear_btn = ctk.CTkButton(button_frame_fixed, text='🧹 Clear Filter', command=self.clear_filter, width=120)
        clear_btn.pack(side='left', padx=10)
        
        cancel_btn = ctk.CTkButton(button_frame_fixed, text='❌ Cancel', command=self.cancel_filter, width=100)
        cancel_btn.pack(side='right')
        
    def apply_text_filter(self):
        """Apply text filter to checkbox selections."""
        filter_text = self.text_filter_value_var.get().strip().lower()
        filter_type = self.text_filter_type_var.get()
        
        if not filter_text:
            return
        
        # Clear current selections
        for var in self.value_vars.values():
            var.set(False)
        
        # Select values based on text filter
        for value in self.unique_values:
            value_lower = value.lower()
            should_select = False
            
            if filter_type == "contains" and filter_text in value_lower:
                should_select = True
            elif filter_type == "starts with" and value_lower.startswith(filter_text):
                should_select = True
            elif filter_type == "ends with" and value_lower.endswith(filter_text):
                should_select = True
            elif filter_type == "equals" and value_lower == filter_text:
                should_select = True
            elif filter_type == "not contains" and filter_text not in value_lower:
                should_select = True
            
            if should_select and value in self.value_vars:
                self.value_vars[value].set(True)
    
    def filter_values_list(self, *args):
        """Filter the values list based on search term."""
        search_term = self.search_var.get().lower()
        
        for value, checkbox in self.value_checkboxes.items():
            if not search_term or search_term in value.lower():
                checkbox.pack(anchor="w", padx=5, pady=1)
            else:
                checkbox.pack_forget()
    
    def select_all(self):
        """Select all visible values."""
        search_term = self.search_var.get().lower()
        for value, var in self.value_vars.items():
            if not search_term or search_term in value.lower():
                var.set(True)
    
    def clear_all(self):
        """Clear all visible values."""
        search_term = self.search_var.get().lower()
        for value, var in self.value_vars.items():
            if not search_term or search_term in value.lower():
                var.set(False)
    
    def apply_filter(self):
        """Apply the filter with selected values."""
        selected_values = {value for value, var in self.value_vars.items() if var.get()}
        
        filter_config = {
            "enabled": True,
            "selected_values": selected_values,
            "filter_type": self.filter_type_var.get()
        }
        
        self.result[0] = filter_config
        self.dialog.destroy()
    
    def clear_filter(self):
        """Clear the filter for this column."""
        filter_config = {
            "enabled": False,
            "selected_values": set(),
            "filter_type": "include"
        }
        
        self.result[0] = filter_config
        self.dialog.destroy()
    
    def cancel_filter(self):
        """Cancel the filter operation."""
        self.dialog.destroy()
    
    def show(self):
        """Show the dialog and return the result."""
        self.dialog.wait_window()
        return self.result[0]