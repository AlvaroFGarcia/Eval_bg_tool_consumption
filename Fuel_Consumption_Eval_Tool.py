"""
Fuel Consumption Evaluation Tool

Updated Flow:
1. Select Surface Table CSV first (defines RPM/ETASP ranges)
2. Select vehicle log files (MDF/MF4/DAT)  
3. Choose between analysis or surface creation modes
4. All operations use CSV ranges to ensure consistency
5. Z parameter selection is mandatory for all vehicle file operations

Fixed Issues:
- CSV must be selected first to define ranges
- Vehicle parameters window shows CSV ranges (read-only)  
- Comparison viewer shows vehicle data with CSV as comparison
- "Show % Difference vs CSV" properly compares vehicle vs CSV data
- Removed separate "Create Surface Table from Vehicle Logs" button
"""

import numpy as np
import pandas as pd
from asammdf import MDF
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import json
import sys
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QPushButton, QColorDialog, QSlider, QCheckBox, QDoubleSpinBox, QGroupBox
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt
import os
from scipy.interpolate import RegularGridInterpolator, griddata
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import threading

# Global list to keep references to SurfaceTableViewer instances
_active_viewers = []

def seconds_to_hms(seconds):
    """Convert seconds to HH:MM:SS.mmm format"""
    if seconds < 0:
        return "00:00:00.000"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

class SurfaceTableViewer(QWidget):
    def __init__(self, surface_data, x_values, y_values, z_values, percentages=None, total_points_inside=0, total_points_all=0, comparison_percentages=None, comparison_name="Comparison"):
        super().__init__()
        self.setWindowTitle('Surface Table Viewer')
        self.resize(1600, 1000)
        
        self.x_values = x_values
        self.y_values = y_values
        self.z_values = z_values
        self.original_percentages = percentages.copy() if percentages is not None else None
        self.percentages = percentages
        self.total_points_inside = total_points_inside
        self.total_points_all = total_points_all
        
        # Comparison data
        self.comparison_percentages = comparison_percentages
        self.comparison_name = comparison_name
        self.show_comparison = comparison_percentages is not None
        self.show_percentage_diff = False
        self.use_absolute_diff = False  # Toggle between percentage and absolute difference
        
        # Color settings
        self.min_color = QColor(255, 255, 255)  # White for minimum
        self.max_color = QColor(0, 100, 255)    # Blue for maximum
        self.color_bias = 1.0  # Linear bias
        self.use_manual_range = False
        self.manual_min = 0.0
        self.manual_max = 100.0
        
        # Create main layout
        main_layout = QVBoxLayout()
        
        # Statistics panel
        stats_panel = QHBoxLayout()
        
        # Normalization controls
        norm_group = QGroupBox("Percentage Normalization")
        norm_layout = QHBoxLayout()
        
        self.normalize_inside_only = QCheckBox("Normalize (Inside bounds = 100%)")
        self.normalize_inside_only.setChecked(True)
        self.normalize_inside_only.stateChanged.connect(self.update_normalization)
        norm_layout.addWidget(self.normalize_inside_only)
        
        # Statistics display
        if total_points_all > 0:
            inside_percentage = (total_points_inside / total_points_all) * 100
            stats_label = QLabel(f"Points inside bounds: {inside_percentage:.1f}% ({total_points_inside}/{total_points_all})")
        else:
            stats_label = QLabel("No statistics available")
        norm_layout.addWidget(stats_label)
        
        norm_group.setLayout(norm_layout)
        stats_panel.addWidget(norm_group)
        
        # Comparison controls (if comparison data is available)
        if self.show_comparison:
            comparison_group = QGroupBox("Comparison Mode")
            comparison_layout = QVBoxLayout()
            
            # Main comparison toggle
            comparison_row1 = QHBoxLayout()
            self.show_diff_cb = QCheckBox(f"Show Difference vs {self.comparison_name}")
            self.show_diff_cb.stateChanged.connect(self.toggle_percentage_diff)
            comparison_row1.addWidget(self.show_diff_cb)
            comparison_layout.addLayout(comparison_row1)
            
            # Difference type toggle (only visible when comparison is enabled)
            comparison_row2 = QHBoxLayout()
            self.diff_type_cb = QCheckBox("Use Absolute Difference (instead of %)")
            self.diff_type_cb.stateChanged.connect(self.toggle_diff_type)
            self.diff_type_cb.setEnabled(False)  # Initially disabled
            comparison_row2.addWidget(self.diff_type_cb)
            comparison_layout.addLayout(comparison_row2)
            
            comparison_group.setLayout(comparison_layout)
            stats_panel.addWidget(comparison_group)
        
        main_layout.addLayout(stats_panel)
        
        # Create control panel
        control_panel = QVBoxLayout()
        
        # Color customization controls
        color_row1 = QHBoxLayout()
        color_label = QLabel("Color Settings:")
        color_row1.addWidget(color_label)
        
        self.min_color_btn = QPushButton("Min Color")
        self.min_color_btn.setStyleSheet(f"background-color: {self.min_color.name()}")
        self.min_color_btn.clicked.connect(self.choose_min_color)
        color_row1.addWidget(self.min_color_btn)
        
        self.max_color_btn = QPushButton("Max Color")
        self.max_color_btn.setStyleSheet(f"background-color: {self.max_color.name()}")
        self.max_color_btn.clicked.connect(self.choose_max_color)
        color_row1.addWidget(self.max_color_btn)
        
        color_row1.addStretch()
        control_panel.addLayout(color_row1)
        
        # Color bias control
        bias_row = QHBoxLayout()
        bias_label = QLabel("Color Bias:")
        bias_row.addWidget(bias_label)
        
        self.bias_slider = QSlider(Qt.Horizontal)
        self.bias_slider.setMinimum(1)
        self.bias_slider.setMaximum(50)
        self.bias_slider.setValue(10)  # 1.0 bias
        self.bias_slider.valueChanged.connect(self.update_color_bias)
        bias_row.addWidget(self.bias_slider)
        
        self.bias_value_label = QLabel("1.0 (Linear)")
        bias_row.addWidget(self.bias_value_label)
        
        bias_row.addStretch()
        control_panel.addLayout(bias_row)
        
        # Manual range controls
        range_row = QHBoxLayout()
        
        self.manual_range_cb = QCheckBox("Manual Min/Max:")
        self.manual_range_cb.stateChanged.connect(self.toggle_manual_range)
        range_row.addWidget(self.manual_range_cb)
        
        range_row.addWidget(QLabel("Min:"))
        self.manual_min_spin = QDoubleSpinBox()
        self.manual_min_spin.setRange(0.0, 1000.0)
        self.manual_min_spin.setValue(0.0)
        self.manual_min_spin.setEnabled(False)
        self.manual_min_spin.valueChanged.connect(self.update_manual_range)
        range_row.addWidget(self.manual_min_spin)
        
        range_row.addWidget(QLabel("Max:"))
        self.manual_max_spin = QDoubleSpinBox()
        self.manual_max_spin.setRange(0.0, 1000.0)
        self.manual_max_spin.setValue(100.0)
        self.manual_max_spin.setEnabled(False)
        self.manual_max_spin.valueChanged.connect(self.update_manual_range)
        range_row.addWidget(self.manual_max_spin)
        
        refresh_btn = QPushButton("Refresh Table")
        refresh_btn.clicked.connect(self.update_table_colors)
        range_row.addWidget(refresh_btn)
        
        range_row.addStretch()
        control_panel.addLayout(range_row)
        
        # Create horizontal layout for control panel and legend
        controls_and_legend_layout = QHBoxLayout()
        
        # Add control panel to left side
        controls_and_legend_layout.addLayout(control_panel)
        
        # Create color legend on the right side
        legend_frame = QGroupBox("Color Legend")
        legend_layout = QVBoxLayout()
        legend_layout.setContentsMargins(1, 1, 1, 1)  # Minimal padding
        legend_layout.setSpacing(0)  # No spacing
        legend_frame.setContentsMargins(1, 1, 1, 1)  # Reduce group box margins
        
        # Create legend table with gradient
        self.legend_table = QTableWidget()
        self.legend_table.setRowCount(1)
        self.legend_table.setColumnCount(11)  # 0%, 10%, 20%, ..., 100%
        self.legend_table.setMinimumHeight(30)  # Allow resizing
        self.legend_table.setMaximumHeight(200)  # Allow resizing
        self.legend_table.setMaximumWidth(600)
        self.legend_table.setMinimumWidth(400)
        
        # Hide headers and borders for clean look
        self.legend_table.horizontalHeader().setVisible(True)
        self.legend_table.verticalHeader().setVisible(False)
        self.legend_table.setShowGrid(True)
        
        # Set column widths
        for i in range(11):
            self.legend_table.setColumnWidth(i, 35)
        
        # Create legend items
        self.update_legend()
        
        legend_layout.addWidget(self.legend_table)
        legend_frame.setLayout(legend_layout)
        legend_frame.setMaximumWidth(650)
        legend_frame.setMinimumHeight(50)  # Allow panel resizing
        legend_frame.setMaximumHeight(150)  # Allow panel resizing
        
        # Add legend to right side
        controls_and_legend_layout.addWidget(legend_frame)
        
        main_layout.addLayout(controls_and_legend_layout)

        # Create table widget
        self.table = QTableWidget()
        self.table.setRowCount(len(y_values) + 1)  # +1 for header
        self.table.setColumnCount(len(x_values) + 1)  # +1 for header
        
        # Set headers
        self.table.setItem(0, 0, QTableWidgetItem('RPM\\ETASP'))
        for i, x_val in enumerate(x_values):
            header_item = QTableWidgetItem(f'{x_val:.0f}')
            header_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.table.setItem(0, i + 1, header_item)
        for i, y_val in enumerate(y_values):
            header_item = QTableWidgetItem(f'{y_val:.3f}')
            header_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.table.setItem(i + 1, 0, header_item)
        
        # Populate table
        self.populate_table()
        
        main_layout.addWidget(self.table)
        self.setLayout(main_layout)
    
    def choose_min_color(self):
        color = QColorDialog.getColor(self.min_color, self)
        if color.isValid():
            self.min_color = color
            self.min_color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.update_legend()
    
    def choose_max_color(self):
        color = QColorDialog.getColor(self.max_color, self)
        if color.isValid():
            self.max_color = color
            self.max_color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.update_legend()
    
    def update_color_bias(self):
        """Update color bias from slider value"""
        # Convert slider value (1-50) to bias (0.1-5.0)
        slider_val = self.bias_slider.value()
        if slider_val <= 10:
            # Low bias: 0.1 to 1.0
            self.color_bias = slider_val / 10.0
            bias_text = f"{self.color_bias:.1f} (Low bias)"
        elif slider_val <= 20:
            # Linear: 1.0 to 2.0
            self.color_bias = 1.0 + (slider_val - 10) / 10.0
            bias_text = f"{self.color_bias:.1f} (Linear)" if self.color_bias == 1.0 else f"{self.color_bias:.1f}"
        else:
            # High bias: 2.0 to 5.0
            self.color_bias = 2.0 + (slider_val - 20) / 10.0
            bias_text = f"{self.color_bias:.1f} (High bias)"
        
        self.bias_value_label.setText(bias_text)
        self.update_legend()
    
    def toggle_manual_range(self):
        """Toggle manual min/max range controls"""
        self.use_manual_range = self.manual_range_cb.isChecked()
        self.manual_min_spin.setEnabled(self.use_manual_range)
        self.manual_max_spin.setEnabled(self.use_manual_range)
        
        if self.use_manual_range and self.percentages is not None:
            # Set default values to current data range
            current_max = np.nanmax(self.percentages) if not np.all(np.isnan(self.percentages)) else 100.0
            self.manual_max_spin.setValue(current_max)
        
        self.update_legend()
    
    def update_manual_range(self):
        """Update manual min/max values"""
        self.manual_min = self.manual_min_spin.value()
        self.manual_max = self.manual_max_spin.value()
        self.update_legend()
    
    def update_normalization(self):
        """Update percentage normalization"""
        if self.original_percentages is None:
            return
        
        if self.normalize_inside_only.isChecked():
            # Normalize so inside points sum to 100%
            total_percentage = np.nansum(self.original_percentages)
            if total_percentage > 0:
                self.percentages = (self.original_percentages / total_percentage) * 100
            else:
                self.percentages = self.original_percentages.copy()
        else:
            # Use original percentages (may not sum to 100%)
            self.percentages = self.original_percentages.copy()
        
        self.populate_table()
        self.update_legend()
    
    def toggle_percentage_diff(self):
        """Toggle between showing main data and difference"""
        self.show_percentage_diff = self.show_diff_cb.isChecked()
        # Enable/disable the difference type toggle based on comparison state
        if hasattr(self, 'diff_type_cb'):
            self.diff_type_cb.setEnabled(self.show_percentage_diff)
        self.populate_table()
        self.update_legend()
    
    def toggle_diff_type(self):
        """Toggle between percentage and absolute difference"""
        self.use_absolute_diff = self.diff_type_cb.isChecked()
        self.populate_table()
        self.update_legend()
    
    def get_interpolated_color(self, percentage, max_percentage):
        """Get color based on percentage using interpolation between min and max colors with bias"""
        if max_percentage == 0:
            return self.min_color
        
        # Determine the range for color mapping
        if self.use_manual_range:
            min_val = self.manual_min
            max_val = self.manual_max
        else:
            min_val = 0
            max_val = max_percentage
        
        # Clamp percentage to range
        clamped_percentage = max(min_val, min(max_val, percentage))
        
        # Calculate ratio with bias
        if max_val > min_val:
            ratio = (clamped_percentage - min_val) / (max_val - min_val)
            # Apply bias (power function)
            ratio = ratio ** self.color_bias
        else:
            ratio = 0
        
        # Interpolate RGB values
        r = int(self.min_color.red() + ratio * (self.max_color.red() - self.min_color.red()))
        g = int(self.min_color.green() + ratio * (self.max_color.green() - self.min_color.green()))
        b = int(self.min_color.blue() + ratio * (self.max_color.blue() - self.min_color.blue()))
        
        return QColor(r, g, b)
    
    def get_difference_color(self, difference, max_abs_difference):
        """Get color for percentage difference (red for negative, green for positive)"""
        if max_abs_difference == 0:
            return QColor(255, 255, 255)  # White for no difference
        
        # Clamp difference to range
        clamped_diff = max(-max_abs_difference, min(max_abs_difference, difference))
        
        # Calculate ratio with bias
        ratio = abs(clamped_diff) / max_abs_difference
        ratio = ratio ** self.color_bias
        
        if clamped_diff < 0:
            # Negative difference: white to red
            r = int(255)
            g = int(255 * (1 - ratio))
            b = int(255 * (1 - ratio))
        elif clamped_diff > 0:
            # Positive difference: white to green
            r = int(255 * (1 - ratio))
            g = int(255)
            b = int(255 * (1 - ratio))
        else:
            # Zero difference: white
            r = g = b = 255
        
        return QColor(r, g, b)
    
    def populate_table(self):
        """Populate table with Z values and percentages"""
        display_data = None
        max_percentage = 0
        
        if self.show_comparison and self.show_percentage_diff:
            # Show difference (percentage or absolute)
            if self.percentages is not None and self.comparison_percentages is not None:
                # Check if we're comparing surface table values (z_values) vs percentages
                if np.array_equal(self.percentages, self.z_values):
                    # We're comparing surface table values
                    if self.use_absolute_diff:
                        # Absolute difference = main - comparison
                        display_data = self.percentages - self.comparison_percentages
                    else:
                        # Percentage difference = ((main - comparison) / comparison) * 100
                        with np.errstate(divide='ignore', invalid='ignore'):
                            display_data = np.where(
                                (self.comparison_percentages != 0) & ~np.isnan(self.comparison_percentages),
                                ((self.percentages - self.comparison_percentages) / self.comparison_percentages) * 100,
                                0
                            )
                    # For surface table differences, use a reasonable range
                    max_abs_diff = np.nanmax(np.abs(display_data[np.isfinite(display_data)])) if np.any(np.isfinite(display_data)) else 10
                    max_percentage = max_abs_diff
                else:
                    # Regular percentage-based comparison
                    if self.use_absolute_diff:
                        # Absolute difference for percentages
                        display_data = self.percentages - self.comparison_percentages
                    else:
                        # Percentage point difference (already in percentage units)
                        display_data = self.percentages - self.comparison_percentages
                    # For difference, use symmetric range around 0
                    max_abs_diff = np.nanmax(np.abs(display_data)) if not np.all(np.isnan(display_data)) else 10
                    max_percentage = max_abs_diff
            else:
                display_data = np.zeros_like(self.z_values)
        else:
            # Show main percentages
            display_data = self.percentages
            if display_data is not None:
                max_percentage = np.nanmax(display_data) if not np.all(np.isnan(display_data)) else 0
        
        for i, y_val in enumerate(self.y_values):
            for j, x_val in enumerate(self.x_values):
                z_val = self.z_values[i, j]
                
                # Create text content
                if np.isnan(z_val):
                    text = "N/A"
                else:
                    text = f'{z_val:.3f}'
                
                if display_data is not None:
                    data_val = display_data[i, j]
                    if not np.isnan(data_val):
                        if self.show_comparison and self.show_percentage_diff:
                            # Show difference with + or - sign and appropriate unit
                            if self.use_absolute_diff:
                                text += f'\n{data_val:+.2f}'
                            else:
                                text += f'\n{data_val:+.2f}%'
                        else:
                            text += f'\n{data_val:.2f}%'
                    else:
                        if self.show_comparison and self.show_percentage_diff and self.use_absolute_diff:
                            text += '\n0.00'
                        else:
                            text += '\n0.00%'
                        data_val = 0
                else:
                    data_val = 0
                
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                
                # Set color based on data
                if display_data is not None:
                    if self.show_comparison and self.show_percentage_diff:
                        # Use different color scheme for differences
                        color = self.get_difference_color(data_val, max_percentage)
                    else:
                        color = self.get_interpolated_color(data_val, max_percentage)
                    item.setBackground(color)
                    
                    # Set text color for better contrast
                    if color.lightness() < 128:
                        item.setForeground(QColor('white'))
                    else:
                        item.setForeground(QColor('black'))
                
                self.table.setItem(i + 1, j + 1, item)
    
    def update_table_colors(self):
        """Update table colors with new color scheme"""
        self.populate_table()
        self.update_legend()
    
    def update_legend(self):
        """Update the color legend based on current color settings"""
        if self.show_comparison and self.show_percentage_diff:
            # Show difference legend (symmetric around 0)
            if self.percentages is not None and self.comparison_percentages is not None:
                # Check if we're comparing surface table values
                if np.array_equal(self.percentages, self.z_values):
                    # Calculate differences for surface table comparison
                    if self.use_absolute_diff:
                        # Absolute difference
                        display_data = self.percentages - self.comparison_percentages
                    else:
                        # Percentage difference
                        with np.errstate(divide='ignore', invalid='ignore'):
                            display_data = np.where(
                                (self.comparison_percentages != 0) & ~np.isnan(self.comparison_percentages),
                                ((self.percentages - self.comparison_percentages) / self.comparison_percentages) * 100,
                                0
                            )
                    max_abs_diff = np.nanmax(np.abs(display_data[np.isfinite(display_data)])) if np.any(np.isfinite(display_data)) else 10.0
                else:
                    # Regular percentage-based comparison
                    display_data = self.percentages - self.comparison_percentages
                    max_abs_diff = np.nanmax(np.abs(display_data)) if not np.all(np.isnan(display_data)) else 10.0
            else:
                max_abs_diff = 10.0
            
            # Create legend items from -max to +max
            for i in range(11):
                diff_val = -max_abs_diff + (2 * max_abs_diff) * (i / 10.0)
                
                # Set header with difference value (with appropriate unit)
                if self.use_absolute_diff:
                    header_item = QTableWidgetItem(f'{diff_val:+.1f}')
                else:
                    header_item = QTableWidgetItem(f'{diff_val:+.1f}%')
                header_item.setFont(QFont("Arial", 8, QFont.Bold))
                self.legend_table.setHorizontalHeaderItem(i, header_item)
                
                # Create colored cell
                item = QTableWidgetItem('')
                color = self.get_difference_color(diff_val, max_abs_diff)
                item.setBackground(color)
                
                # Set text color for better contrast
                if color.lightness() < 128:
                    item.setForeground(QColor('white'))
                else:
                    item.setForeground(QColor('black'))
                
                self.legend_table.setItem(0, i, item)
        else:
            # Normal percentage legend
            # Determine the range for the legend
            if self.use_manual_range:
                min_val = self.manual_min
                max_val = self.manual_max
            else:
                if self.percentages is not None:
                    max_val = np.nanmax(self.percentages) if not np.all(np.isnan(self.percentages)) else 100.0
                else:
                    max_val = 100.0
                min_val = 0.0
            
            # Create legend items for 0%, 10%, 20%, ..., 100%
            for i in range(11):
                percentage = min_val + (max_val - min_val) * (i / 10.0)
                
                # Set header with percentage value
                header_item = QTableWidgetItem(f'{percentage:.1f}%')
                header_item.setFont(QFont("Arial", 8, QFont.Bold))
                self.legend_table.setHorizontalHeaderItem(i, header_item)
                
                # Create colored cell
                item = QTableWidgetItem('')
                color = self.get_interpolated_color(percentage, max_val)
                item.setBackground(color)
                
                # Set text color for better contrast
                if color.lightness() < 128:
                    item.setForeground(QColor('white'))
                else:
                    item.setForeground(QColor('black'))
                
                self.legend_table.setItem(0, i, item)
    
    def closeEvent(self, event):
        """Handle window close event properly"""
        global _active_viewers
        if self in _active_viewers:
            _active_viewers.remove(self)
        event.accept()

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

# Removed create_surface_from_logs - now integrated into main flow

# Removed select_surface_parameters - replaced with select_vehicle_parameters that uses CSV ranges

def process_surface_creation_from_logs(mdf_file_paths, rpm_channel, etasp_channel, z_param_channel,
                                      rpm_params, etasp_params, raster_value, filters, csv_surface_data=None):
    """Process vehicle log files to create averaged surface table"""
    
    # Unpack parameters
    rpm_min, rpm_max, rpm_intervals = rpm_params
    etasp_min, etasp_max, etasp_intervals = etasp_params
    
    # Create grid
    x_values = np.linspace(rpm_min, rpm_max, rpm_intervals + 1)
    y_values = np.linspace(etasp_min, etasp_max, etasp_intervals + 1)
    
    # Initialize accumulation arrays
    z_sum_matrix = np.zeros((len(y_values), len(x_values)))
    count_matrix = np.zeros((len(y_values), len(x_values)))
    
    total_data_points = 0
    files_processed = 0
    
    # Progress window
    progress_window = tk.Toplevel()
    progress_window.title('Processing Vehicle Logs')
    progress_window.geometry('400x150')
    progress_window.grab_set()  # Make it modal
    
    progress_label = tk.Label(progress_window, text='Processing files...')
    progress_label.pack(pady=10)
    
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=len(mdf_file_paths))
    progress_bar.pack(pady=10, padx=20, fill='x')
    
    file_label = tk.Label(progress_window, text='')
    file_label.pack(pady=5)
    
    progress_window.update()
    
    try:
        for i, file_path in enumerate(mdf_file_paths):
            file_label.config(text=f'Processing: {os.path.basename(file_path)}')
            progress_window.update()
            
            try:
                # Process single file
                file_z_sum, file_count, file_data_points = process_single_file_for_surface(
                    file_path, rpm_channel, etasp_channel, z_param_channel,
                    x_values, y_values, raster_value, filters
                )
                
                # Accumulate results
                z_sum_matrix += file_z_sum
                count_matrix += file_count
                total_data_points += file_data_points
                files_processed += 1
                
            except Exception as e:
                print(f"Warning: Failed to process {os.path.basename(file_path)}: {e}")
                continue
            
            progress_var.set(i + 1)
            progress_window.update()
        
        progress_window.destroy()
        
        if files_processed == 0:
            messagebox.showerror('Error', 'No files could be processed successfully!')
            return
        
        # Calculate averaged surface table
        z_averaged_matrix = np.zeros_like(z_sum_matrix)
        
        # Avoid division by zero
        valid_mask = count_matrix > 0
        z_averaged_matrix[valid_mask] = z_sum_matrix[valid_mask] / count_matrix[valid_mask]
        z_averaged_matrix[~valid_mask] = np.nan
        
        # Show results
        show_surface_creation_results(x_values, y_values, z_averaged_matrix, count_matrix,
                                    total_data_points, files_processed, z_param_channel, csv_surface_data)
        
    except Exception as e:
        progress_window.destroy()
        messagebox.showerror('Error', f'Failed to process files: {e}')

def process_single_file_for_surface(file_path, rpm_channel, etasp_channel, z_param_channel,
                                   x_values, y_values, raster_value, filters):
    """Process a single file for surface creation"""
    
    # Load file
    mdf = MDF(file_path)
    
    # Get signals
    rpm_signal = mdf.get(rpm_channel)
    etasp_signal = mdf.get(etasp_channel)
    z_param_signal = mdf.get(z_param_channel)
    
    # Create common time base
    start_time = max(rpm_signal.timestamps[0], etasp_signal.timestamps[0], z_param_signal.timestamps[0])
    end_time = min(rpm_signal.timestamps[-1], etasp_signal.timestamps[-1], z_param_signal.timestamps[-1])
    time_base = np.arange(start_time, end_time, raster_value)
    
    if len(time_base) == 0:
        return np.zeros((len(y_values), len(x_values))), np.zeros((len(y_values), len(x_values))), 0
    
    # Resample signals
    rpm_resampled = np.interp(time_base, rpm_signal.timestamps, rpm_signal.samples)
    etasp_resampled = np.interp(time_base, etasp_signal.timestamps, etasp_signal.samples)
    z_param_resampled = np.interp(time_base, z_param_signal.timestamps, z_param_signal.samples)
    
    # Apply filters
    mask = np.ones(len(time_base), dtype=bool)
    
    for filter_config in filters:
        try:
            filter_signal = mdf.get(filter_config['channel'])
            filter_resampled = np.interp(time_base, filter_signal.timestamps, filter_signal.samples)
            
            if filter_config['condition'] == 'within range':
                filter_mask = (filter_resampled >= filter_config['min']) & (filter_resampled <= filter_config['max'])
            else:  # outside range
                filter_mask = (filter_resampled < filter_config['min']) | (filter_resampled > filter_config['max'])
            
            mask = mask & filter_mask
        except:
            continue  # Skip invalid filters
    
    # Apply mask
    rpm_filtered = rpm_resampled[mask]
    etasp_filtered = etasp_resampled[mask]
    z_param_filtered = z_param_resampled[mask]
    
    # Check bounds and filter out invalid values
    x_min, x_max = x_values.min(), x_values.max()
    y_min, y_max = y_values.min(), y_values.max()
    
    bounds_mask = (rpm_filtered >= x_min) & (rpm_filtered <= x_max) & \
                  (etasp_filtered >= y_min) & (etasp_filtered <= y_max) & \
                  np.isfinite(z_param_filtered)  # Ensure Z values are finite
    
    rpm_bounded = rpm_filtered[bounds_mask]
    etasp_bounded = etasp_filtered[bounds_mask]
    z_param_bounded = z_param_filtered[bounds_mask]
    
    # Initialize matrices for this file
    z_sum_matrix = np.zeros((len(y_values), len(x_values)))
    count_matrix = np.zeros((len(y_values), len(x_values)))
    
    # Assign values to cells with averaging
    for i in range(len(rpm_bounded)):
        rpm_val = rpm_bounded[i]
        etasp_val = etasp_bounded[i]
        z_val = z_param_bounded[i]
        
        # Find which cell this point belongs to
        # Use grid boundaries instead of closest point for proper averaging
        x_cell_idx = np.digitize(rpm_val, x_values) - 1
        y_cell_idx = np.digitize(etasp_val, y_values) - 1
        
        # Ensure indices are within bounds
        x_cell_idx = max(0, min(x_cell_idx, len(x_values) - 1))
        y_cell_idx = max(0, min(y_cell_idx, len(y_values) - 1))
        
        # Accumulate sum and count for averaging
        z_sum_matrix[y_cell_idx, x_cell_idx] += z_val
        count_matrix[y_cell_idx, x_cell_idx] += 1
    
    mdf.close()
    
    return z_sum_matrix, count_matrix, len(rpm_bounded)

def show_surface_creation_results(x_values, y_values, z_averaged_matrix, count_matrix,
                                 total_data_points, files_processed, z_param_name, csv_surface_data=None):
    """Show results of surface table creation"""
    
    results_window = tk.Toplevel()
    results_window.title('Surface Table Creation Results')
    results_window.geometry('800x600')
    
    # Statistics frame
    stats_frame = tk.Frame(results_window)
    stats_frame.pack(fill='x', padx=10, pady=10)
    
    tk.Label(stats_frame, text='Surface Table Creation Results', font=('TkDefaultFont', 14, 'bold')).pack(anchor='w')
    tk.Label(stats_frame, text=f'Files processed: {files_processed}').pack(anchor='w')
    tk.Label(stats_frame, text=f'Total data points used: {total_data_points:,}').pack(anchor='w')
    tk.Label(stats_frame, text=f'Grid size: {len(x_values)} x {len(y_values)} = {len(x_values) * len(y_values)} cells').pack(anchor='w')
    
    # Count statistics
    cells_with_data = np.sum(count_matrix > 0)
    total_cells = count_matrix.size
    coverage_percentage = (cells_with_data / total_cells) * 100
    
    tk.Label(stats_frame, text=f'Cells with data: {cells_with_data}/{total_cells} ({coverage_percentage:.1f}%)').pack(anchor='w')
    
    if cells_with_data > 0:
        avg_points_per_cell = total_data_points / cells_with_data
        tk.Label(stats_frame, text=f'Average points per filled cell: {avg_points_per_cell:.1f}').pack(anchor='w')
    
    # Buttons frame
    buttons_frame = tk.Frame(results_window)
    buttons_frame.pack(fill='x', padx=10, pady=10)
    
    def view_surface_table_from_logs():
        """View the created surface table with comparison capability"""
        comparison_percentages = None
        comparison_name = "Comparison"
        
        # If CSV surface data is available, prepare it for comparison
        if csv_surface_data is not None:
            try:
                csv_x_values, csv_y_values, csv_z_values = csv_surface_data
                
                # Since both vehicle log and CSV use the same grid ranges, 
                # we can directly use the CSV data for comparison
                if csv_x_values.shape == x_values.shape and csv_y_values.shape == y_values.shape:
                    # Grids match exactly, use CSV data directly
                    comparison_percentages = csv_z_values
                else:
                    # Interpolate CSV data to match vehicle log grid
                    comparison_percentages = interpolate_surface_to_grid(
                        csv_x_values, csv_y_values, csv_z_values,
                        x_values, y_values
                    )
                
                comparison_name = "CSV Surface Table"
                
            except Exception as e:
                print(f"Warning: Failed to prepare CSV comparison data: {e}")
        
        show_surface_table(
            (x_values, y_values, z_averaged_matrix),
            x_values, y_values, z_averaged_matrix,
            percentages=z_averaged_matrix,  # Use Z values for comparison
            total_points_inside=total_data_points,
            total_points_all=total_data_points,
            comparison_percentages=comparison_percentages,
            comparison_name=comparison_name
        )
    
    def export_surface_table():
        """Export the surface table to CSV"""
        try:
            export_path = filedialog.asksaveasfilename(
                title='Export Surface Table',
                defaultextension='.csv',
                filetypes=[('CSV Files', '*.csv')]
            )
            
            if export_path:
                # Create export data
                export_data = []
                
                # Add header
                export_data.append(['RPM', 'ETASP', z_param_name])
                export_data.append(['rpm', '-', 'units'])  # Units row
                
                # Add data points
                for i, etasp_val in enumerate(y_values):
                    for j, rpm_val in enumerate(x_values):
                        z_val = z_averaged_matrix[i, j]
                        if not np.isnan(z_val):
                            export_data.append([rpm_val, etasp_val, z_val])
                
                # Write to CSV
                import csv
                with open(export_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows(export_data)
                
                messagebox.showinfo('Success', f'Surface table exported to:\n{export_path}')
        
        except Exception as e:
            messagebox.showerror('Error', f'Failed to export surface table: {e}')
    
    
    tk.Button(buttons_frame, text='Open Surface Table Viewer', command=view_surface_table_from_logs).pack(side='left', padx=5)
    tk.Button(buttons_frame, text='Export to CSV', command=export_surface_table).pack(side='left', padx=5)
    
    # Preview frame
    preview_frame = tk.Frame(results_window)
    preview_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    tk.Label(preview_frame, text='Surface Table Preview (first 10x10 cells):', font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')
    
    # Create preview table
    preview_table = tk.Frame(preview_frame)
    preview_table.pack(pady=5)
    
    # Show a limited preview
    max_rows = min(10, len(y_values))
    max_cols = min(10, len(x_values))
    
    for i in range(max_rows + 1):
        for j in range(max_cols + 1):
            if i == 0 and j == 0:
                text = "ETASP\\RPM"
            elif i == 0:
                text = f"{x_values[j-1]:.0f}"
            elif j == 0:
                text = f"{y_values[i-1]:.2f}"
            else:
                z_val = z_averaged_matrix[i-1, j-1]
                if np.isnan(z_val):
                    text = "-"
                else:
                    text = f"{z_val:.2f}"
            
            label = tk.Label(preview_table, text=text, relief='solid', width=8, borderwidth=1)
            label.grid(row=i, column=j, sticky='nsew')

def select_csv_for_comparison(csv_path, column_names, log_x_values, log_y_values, log_z_matrix, z_param_name):
    """Select CSV columns for comparison with log-based surface table"""
    
    comparison_window = tk.Toplevel()
    comparison_window.title('Select CSV Columns for Comparison')
    comparison_window.geometry('400x300')
    
    tk.Label(comparison_window, text='Select columns from CSV file:', font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
    
    # Column selection
    tk.Label(comparison_window, text='X-axis (RPM):').pack(anchor='w', padx=20)
    x_var = tk.StringVar()
    x_combo = ttk.Combobox(comparison_window, textvariable=x_var, values=column_names, state='readonly')
    x_combo.pack(pady=2, padx=20, fill='x')
    
    tk.Label(comparison_window, text='Y-axis (ETASP):').pack(anchor='w', padx=20)
    y_var = tk.StringVar()
    y_combo = ttk.Combobox(comparison_window, textvariable=y_var, values=column_names, state='readonly')
    y_combo.pack(pady=2, padx=20, fill='x')
    
    tk.Label(comparison_window, text='Z-axis (Value):').pack(anchor='w', padx=20)
    z_var = tk.StringVar()
    z_combo = ttk.Combobox(comparison_window, textvariable=z_var, values=column_names, state='readonly')
    z_combo.pack(pady=2, padx=20, fill='x')
    
    def perform_comparison():
        if not x_var.get() or not y_var.get() or not z_var.get():
            messagebox.showerror('Error', 'Please select all columns')
            return
        
        try:
            # Load CSV surface table
            csv_x_values, csv_y_values, csv_z_matrix = load_surface_table(
                csv_path, x_var.get(), y_var.get(), z_var.get()
            )
            
            # Interpolate CSV data to match log data grid
            csv_z_interpolated = interpolate_surface_to_grid(
                csv_x_values, csv_y_values, csv_z_matrix,
                log_x_values, log_y_values
            )
            
            # Show comparison
            show_surface_comparison(
                log_x_values, log_y_values, log_z_matrix, csv_z_interpolated,
                f"Vehicle Logs ({z_param_name})", f"CSV ({z_var.get()})"
            )
            
            comparison_window.destroy()
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to perform comparison: {e}')
    
    tk.Button(comparison_window, text='Compare', command=perform_comparison, bg='lightgreen').pack(pady=20)

def interpolate_surface_to_grid(source_x, source_y, source_z, target_x, target_y):
    """Interpolate source surface data to target grid"""
    
    # Create meshgrids
    source_X, source_Y = np.meshgrid(source_x, source_y)
    target_X, target_Y = np.meshgrid(target_x, target_y)
    
    # Flatten source data and remove NaN values
    source_points = []
    source_values = []
    
    for i in range(len(source_y)):
        for j in range(len(source_x)):
            if not np.isnan(source_z[i, j]):
                source_points.append([source_X[i, j], source_Y[i, j]])
                source_values.append(source_z[i, j])
    
    if len(source_points) == 0:
        return np.full_like(target_X, np.nan)
    
    source_points = np.array(source_points)
    source_values = np.array(source_values)
    
    # Interpolate to target grid
    try:
        target_z = griddata(
            source_points, source_values,
            (target_X, target_Y),
            method='linear',
            fill_value=np.nan
        )
        
        # Fill remaining NaN values with nearest neighbor if available
        nan_mask = np.isnan(target_z)
        if np.any(nan_mask):
            target_z_nearest = griddata(
                source_points, source_values,
                (target_X, target_Y),
                method='nearest'
            )
            target_z[nan_mask] = target_z_nearest[nan_mask]
            
    except Exception as e:
        print(f"Interpolation warning: {e}")
        target_z = np.full_like(target_X, np.nan)
    
    return target_z

def show_surface_comparison(x_values, y_values, surface1, surface2, name1, name2):
    """Show comparison between two surface tables"""
    
    # Calculate difference
    difference = surface1 - surface2
    
    # Show both surfaces and their difference with proper comparison data
    show_surface_table(
        (x_values, y_values, surface1),
        x_values, y_values, surface1,
        comparison_percentages=surface2,
        comparison_name=name2
    )

def main():
    # Initialize QApplication first to ensure proper Qt initialization on main thread
    qt_app = QApplication.instance()
    if not qt_app:
        qt_app = QApplication(sys.argv)
    
    root = tk.Tk()
    root.title('Fuel Consumption Evaluation Tool')
    root.geometry('500x400')

    mdf_file_paths = []
    csv_file_path = None
    surface_data = None

    def select_csv_file():
        nonlocal csv_file_path, surface_data
        csv_file_path = filedialog.askopenfilename(
            title='Select Surface Table CSV File',
            filetypes=[('CSV Files', '*.csv')]
        )
        if not csv_file_path:
            messagebox.showerror('Error', 'No CSV file selected!')
            return
        else:
            lbl_csv_selected.config(text=f"CSV selected: {os.path.basename(csv_file_path)}")
            # Load CSV structure for column selection
            try:
                df = pd.read_csv(csv_file_path, nrows=1)
                column_names = df.columns.tolist()
                surface_data = select_csv_surface_parameters(column_names, csv_file_path)
            except Exception as e:
                messagebox.showerror('Error', f'Failed to read CSV file: {e}')
                csv_file_path = None
                lbl_csv_selected.config(text='No CSV file selected')

    def select_mdf_files():
        nonlocal mdf_file_paths
        if not csv_file_path:
            messagebox.showerror('Error', 'Please select a Surface Table CSV file first!')
            return
            
        mdf_file_paths = filedialog.askopenfilenames(
            title='Select MDF/MF4/DAT Files',
            filetypes=[('MDF, MF4 and DAT Files', '*.dat *.mdf *.mf4'), ('DAT Files', '*.dat'), ('MDF Files', '*.mdf'), ('MF4 Files', '*.mf4')]
        )
        if not mdf_file_paths:
            messagebox.showerror('Error', 'No MDF/MF4/DAT file selected!')
            return
        else:
            lbl_mdf_selected.config(text=f"{len(mdf_file_paths)} file(s) selected")

    def proceed():
        if not csv_file_path:
            messagebox.showerror('Error', 'Please select a Surface Table CSV file first!')
            return
        if not mdf_file_paths:
            messagebox.showerror('Error', 'Please select MDF/MF4/DAT files!')
            return
        if not surface_data:
            messagebox.showerror('Error', 'Surface table CSV data not loaded properly!')
            return

        # Proceed with Z parameter selection for vehicle files
        select_vehicle_parameters(mdf_file_paths, surface_data)

    # Instructions
    tk.Label(root, text='Fuel Consumption Evaluation Tool', font=('TkDefaultFont', 16, 'bold')).pack(pady=10)
    tk.Label(root, text='Step 1: Select Surface Table CSV (defines RPM/ETASP ranges)', font=('TkDefaultFont', 10)).pack(pady=5)

    btn_select_csv = tk.Button(root, text='Select Surface Table CSV File', command=select_csv_file, bg='lightblue')
    btn_select_csv.pack(pady=10)

    lbl_csv_selected = tk.Label(root, text='No CSV file selected')
    lbl_csv_selected.pack()

    # Add separator
    tk.Frame(root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=10)

    tk.Label(root, text='Step 2: Select Vehicle Log Files', font=('TkDefaultFont', 10)).pack(pady=5)

    btn_select_mdf = tk.Button(root, text='Select MDF/MF4/DAT Files', command=select_mdf_files, bg='lightgreen')
    btn_select_mdf.pack(pady=10)

    lbl_mdf_selected = tk.Label(root, text='No MDF/MF4/DAT file selected')
    lbl_mdf_selected.pack()

    # Add separator
    tk.Frame(root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=5, pady=10)

    tk.Label(root, text='Step 3: Process and Compare', font=('TkDefaultFont', 10)).pack(pady=5)

    btn_proceed = tk.Button(root, text='Proceed to Parameter Selection', command=proceed, bg='orange', font=('TkDefaultFont', 10, 'bold'))
    btn_proceed.pack(pady=20)

    root.mainloop()

def select_csv_surface_parameters(column_names, csv_file_path):
    """Select CSV surface table parameters and load the surface data"""
    columns_window = tk.Toplevel()
    columns_window.title('Configure Surface Table CSV')
    columns_window.geometry('500x600')
    columns_window.grab_set()  # Make it modal

    tk.Label(columns_window, text='Configure Surface Table Parameters', font=('TkDefaultFont', 14, 'bold')).pack(pady=10)
    tk.Label(columns_window, text='Select the columns for X, Y, and Z axes:', font=('TkDefaultFont', 12)).pack(pady=10)

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
    tk.Label(columns_window, text='Interpolation Parameters:', font=('TkDefaultFont', 12, 'bold')).pack(pady=10)

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
    tk.Label(columns_window, text='ETASP Parameters:', font=('TkDefaultFont', 12, 'bold')).pack(pady=(15,5))

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

    # Auto-detect button
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

    # Auto-detect buttons frame
    auto_detect_frame = tk.Frame(columns_window)
    auto_detect_frame.pack(pady=10)
    
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
            messagebox.showerror('Error', 'Please select three different columns!')
            return

        try:
            rpm_min = rpm_min_var.get()
            rpm_max = rpm_max_var.get()
            rpm_intervals = rpm_intervals_var.get()
            etasp_min = etasp_min_var.get()
            etasp_max = etasp_max_var.get()
            etasp_intervals = etasp_intervals_var.get()
            
            if rpm_min >= rpm_max:
                messagebox.showerror('Error', 'RPM Min must be less than RPM Max!')
                return
            
            if etasp_min >= etasp_max:
                messagebox.showerror('Error', 'ETASP Min must be less than ETASP Max!')
                return
            
            if rpm_intervals <= 0 or etasp_intervals <= 0:
                messagebox.showerror('Error', 'Number of intervals must be positive!')
                return
            
            # Save CSV column selections to config
            config = {}
            if os.path.exists('fuel_config.json'):
                try:
                    with open('fuel_config.json', 'r') as f:
                        config = json.load(f)
                except:
                    pass
            
            config['csv_columns'] = {
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
            
            try:
                with open('fuel_config.json', 'w') as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not save configuration: {e}")
                
            surface_data = load_surface_table(csv_file_path, x_col, y_col, z_col, 
                                            rpm_min, rpm_max, rpm_intervals,
                                            etasp_min, etasp_max, etasp_intervals)
            surface_data_result[0] = surface_data
            columns_window.destroy()
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load surface table: {e}')

    # Create button frame
    button_frame = tk.Frame(columns_window)
    button_frame.pack(pady=20)

    btn_confirm = tk.Button(button_frame, text='Confirm Configuration', 
                           command=confirm_csv_config, bg='lightgreen', font=('TkDefaultFont', 10, 'bold'))
    btn_confirm.pack()

    # Wait for window to close
    columns_window.wait_window()
    
    return surface_data_result[0]

def select_vehicle_parameters(mdf_file_paths, surface_data):
    """Select parameters for vehicle log analysis using CSV surface table ranges"""
    params_window = tk.Toplevel()
    params_window.title('Vehicle Log Parameters')
    params_window.geometry('600x600')
    params_window.grab_set()  # Make it modal
    
    # Extract ranges from CSV surface data
    csv_x_values, csv_y_values, csv_z_values = surface_data
    rpm_min, rpm_max = float(csv_x_values.min()), float(csv_x_values.max())
    etasp_min, etasp_max = float(csv_y_values.min()), float(csv_y_values.max())
    
    # Load sample file to get channel names
    try:
        sample_mdf = MDF(mdf_file_paths[0])
        all_channels = list(sample_mdf.channels_db.keys())
    except Exception as e:
        messagebox.showerror('Error', f'Failed to load sample file: {e}')
        return
    
    # Load config if exists
    config = {}
    if os.path.exists('fuel_config.json'):
        try:
            with open('fuel_config.json', 'r') as f:
                config = json.load(f)
        except:
            pass
    
    # Variables for channels
    rpm_var = tk.StringVar(value=config.get('rpm_channel', ''))
    etasp_var = tk.StringVar(value=config.get('etasp_channel', ''))
    z_param_var = tk.StringVar()
    
    # Grid intervals (use CSV dimensions)
    rpm_intervals_var = tk.IntVar(value=len(csv_x_values) - 1)
    etasp_intervals_var = tk.IntVar(value=len(csv_y_values) - 1)
    
    raster_var = tk.DoubleVar(value=0.02)
    
    # Create UI
    main_frame = tk.Frame(params_window)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Title and CSV info
    tk.Label(main_frame, text='Vehicle Log Analysis Parameters', font=('TkDefaultFont', 14, 'bold')).pack(anchor='w', pady=(0, 10))
    
    # Show CSV ranges (read-only)
    csv_info_frame = tk.LabelFrame(main_frame, text='Surface Table Ranges (from CSV)', padx=10, pady=10)
    csv_info_frame.pack(fill='x', pady=(0, 15))
    
    tk.Label(csv_info_frame, text=f'RPM Range: {rpm_min:.0f} - {rpm_max:.0f} ({len(csv_x_values)} points)', 
             font=('TkDefaultFont', 10, 'bold'), fg='blue').pack(anchor='w')
    tk.Label(csv_info_frame, text=f'ETASP Range: {etasp_min:.3f} - {etasp_max:.3f} ({len(csv_y_values)} points)', 
             font=('TkDefaultFont', 10, 'bold'), fg='blue').pack(anchor='w')
    tk.Label(csv_info_frame, text='Note: Vehicle data will be interpolated to match these exact ranges', 
             font=('TkDefaultFont', 9), fg='darkgreen').pack(anchor='w')
    
    # Channel selection
    channel_frame = tk.LabelFrame(main_frame, text='Vehicle Log Channel Selection', padx=10, pady=10)
    channel_frame.pack(fill='x', pady=(0, 15))
    
    tk.Label(channel_frame, text='RPM Channel:').pack(anchor='w')
    rpm_combobox = AutocompleteCombobox(channel_frame, textvariable=rpm_var, width=60)
    rpm_combobox.set_completion_list(all_channels)
    rpm_combobox.pack(anchor='w', pady=(0, 5))
    
    tk.Label(channel_frame, text='ETASP Channel:').pack(anchor='w')
    etasp_combobox = AutocompleteCombobox(channel_frame, textvariable=etasp_var, width=60)
    etasp_combobox.set_completion_list(all_channels)
    etasp_combobox.pack(anchor='w', pady=(0, 5))
    
    tk.Label(channel_frame, text='Z Parameter Channel (for analysis):').pack(anchor='w')
    z_param_combobox = AutocompleteCombobox(channel_frame, textvariable=z_param_var, width=60)
    z_param_combobox.set_completion_list(all_channels)
    z_param_combobox.pack(anchor='w', pady=(0, 5))
    
    # Raster value
    raster_frame = tk.Frame(main_frame)
    raster_frame.pack(fill='x', pady=5)
    tk.Label(raster_frame, text='Raster Value (seconds):').pack(side='left')
    tk.Entry(raster_frame, textvariable=raster_var, width=8).pack(side='left', padx=(20, 0))
    
    # Filters section
    filters_frame = tk.LabelFrame(main_frame, text='Filters (Optional)', padx=10, pady=10)
    filters_frame.pack(fill='both', expand=True, pady=(15, 0))
    
    # Container for filter entries
    filters_container = tk.Frame(filters_frame)
    filters_container.pack(fill='both', expand=True, pady=5)
    
    # Scroll for filters
    filters_canvas = tk.Canvas(filters_container, height=120)
    filters_scrollbar = tk.Scrollbar(filters_container, orient='vertical', command=filters_canvas.yview)
    filters_scrollable_frame = tk.Frame(filters_canvas)
    
    filters_scrollable_frame.bind(
        '<Configure>',
        lambda e: filters_canvas.configure(scrollregion=filters_canvas.bbox('all'))
    )
    
    filters_canvas.create_window((0, 0), window=filters_scrollable_frame, anchor='nw')
    filters_canvas.configure(yscrollcommand=filters_scrollbar.set)
    
    filters_canvas.pack(side='left', fill='both', expand=True)
    filters_scrollbar.pack(side='right', fill='y')
    
    # Filter management
    filter_entries = []
    
    def add_filter():
        filter_frame = tk.Frame(filters_scrollable_frame)
        filter_frame.pack(fill='x', pady=2)
        
        # Channel
        tk.Label(filter_frame, text='Channel:').pack(side='left')
        channel_var = tk.StringVar()
        channel_cb = AutocompleteCombobox(filter_frame, textvariable=channel_var, width=20)
        channel_cb.set_completion_list(all_channels)
        channel_cb.pack(side='left', padx=2)
        
        # Condition
        tk.Label(filter_frame, text='Condition:').pack(side='left', padx=(5, 2))
        condition_var = tk.StringVar(value='within range')
        condition_cb = ttk.Combobox(filter_frame, textvariable=condition_var, 
                                   values=['within range', 'outside range'], 
                                   width=12, state='readonly')
        condition_cb.pack(side='left', padx=2)
        
        # Min/Max values
        tk.Label(filter_frame, text='Min:').pack(side='left', padx=(5, 2))
        min_var = tk.DoubleVar()
        min_entry = tk.Entry(filter_frame, textvariable=min_var, width=8)
        min_entry.pack(side='left', padx=2)
        
        tk.Label(filter_frame, text='Max:').pack(side='left', padx=(5, 2))
        max_var = tk.DoubleVar()
        max_entry = tk.Entry(filter_frame, textvariable=max_var, width=8)
        max_entry.pack(side='left', padx=2)
        
        # Remove button
        def remove_filter():
            filter_frame.destroy()
            filter_entries.remove(filter_entry)
        
        remove_btn = tk.Button(filter_frame, text='Remove', command=remove_filter)
        remove_btn.pack(side='left', padx=(5, 0))
        
        filter_entry = {
            'frame': filter_frame,
            'channel_var': channel_var,
            'condition_var': condition_var,
            'min_var': min_var,
            'max_var': max_var
        }
        filter_entries.append(filter_entry)
    
    add_filter_btn = tk.Button(filters_frame, text='Add Filter', command=add_filter)
    add_filter_btn.pack(pady=5)
    
    # Action buttons
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill='x', pady=20)
    
    def process_vehicle_analysis():
        # Validate inputs
        if not rpm_var.get() or not etasp_var.get() or not z_param_var.get():
            messagebox.showerror('Error', 'Please select RPM, ETASP, and Z parameter channels')
            return
        
        try:
            # Collect filter configurations
            filters = []
            for filter_entry in filter_entries:
                if filter_entry['channel_var'].get():
                    filters.append({
                        'channel': filter_entry['channel_var'].get(),
                        'condition': filter_entry['condition_var'].get(),
                        'min': filter_entry['min_var'].get(),
                        'max': filter_entry['max_var'].get()
                    })
            
            # Close window
            params_window.destroy()
            
            # Open second vehicle bundle selection
            select_second_vehicle_bundle_for_comparison(
                mdf_file_paths, surface_data,
                rpm_var.get(), etasp_var.get(), z_param_var.get(),
                raster_var.get(), filters
            )
            
        except Exception as e:
            messagebox.showerror('Error', f'Invalid parameters: {e}')
    
    def create_surface_from_vehicle():
        # Validate inputs
        if not rpm_var.get() or not etasp_var.get() or not z_param_var.get():
            messagebox.showerror('Error', 'Please select RPM, ETASP, and Z parameter channels')
            return
        
        try:
            # Collect filter configurations
            filters = []
            for filter_entry in filter_entries:
                if filter_entry['channel_var'].get():
                    filters.append({
                        'channel': filter_entry['channel_var'].get(),
                        'condition': filter_entry['condition_var'].get(),
                        'min': filter_entry['min_var'].get(),
                        'max': filter_entry['max_var'].get()
                    })
            
            # Close window
            params_window.destroy()
            
            # Process files for surface creation using CSV ranges
            process_surface_creation_with_csv_ranges(
                mdf_file_paths, surface_data,
                rpm_var.get(), etasp_var.get(), z_param_var.get(),
                raster_var.get(), filters
            )
            
        except Exception as e:
            messagebox.showerror('Error', f'Invalid parameters: {e}')
    
    tk.Button(button_frame, text='Select Second Vehicle Bundle for Comparison', 
              command=process_vehicle_analysis, bg='lightgreen', font=('TkDefaultFont', 10, 'bold')).pack(side='left', padx=10)
    tk.Button(button_frame, text='Create Surface Table from Vehicle Logs', 
              command=create_surface_from_vehicle, bg='lightblue', font=('TkDefaultFont', 10, 'bold')).pack(side='right', padx=10)

def select_second_vehicle_bundle_for_comparison(first_bundle_paths, surface_data, rpm_channel, etasp_channel, z_param_channel, raster_value, filters):
    """Select a second vehicle log bundle for comparison with the first bundle"""
    
    selection_window = tk.Toplevel()
    selection_window.title('Select Second Vehicle Bundle for Comparison')
    selection_window.geometry('600x400')
    selection_window.grab_set()  # Make it modal
    
    tk.Label(selection_window, text='Select Second Vehicle Log Bundle for Comparison', font=('TkDefaultFont', 14, 'bold')).pack(pady=10)
    tk.Label(selection_window, text=f'First bundle: {len(first_bundle_paths)} files selected', font=('TkDefaultFont', 10)).pack(pady=5)
    
    second_bundle_paths = []
    
    def select_second_bundle():
        nonlocal second_bundle_paths
        file_paths = filedialog.askopenfilenames(
            title='Select Second Vehicle Log Bundle (MDF/MF4/DAT Files)',
            filetypes=[
                ('MDF Files', '*.mdf'),
                ('MF4 Files', '*.mf4'),
                ('DAT Files', '*.dat'),
                ('All Supported', '*.mdf;*.mf4;*.dat'),
                ('All Files', '*.*')
            ]
        )
        if file_paths:
            second_bundle_paths = list(file_paths)
            lbl_second_bundle.config(text=f'Second bundle: {len(second_bundle_paths)} files selected')
            btn_compare.config(state='normal')
    
    btn_select_second = tk.Button(selection_window, text='Select Second Vehicle Bundle', 
                                  command=select_second_bundle, bg='lightblue')
    btn_select_second.pack(pady=10)
    
    lbl_second_bundle = tk.Label(selection_window, text='No second bundle selected')
    lbl_second_bundle.pack(pady=5)
    
    # Instructions
    instructions_frame = tk.LabelFrame(selection_window, text='Instructions', padx=10, pady=10)
    instructions_frame.pack(fill='x', padx=20, pady=20)
    
    tk.Label(instructions_frame, text='• Select a second set of vehicle log files to compare with the first set').pack(anchor='w')
    tk.Label(instructions_frame, text='• Both bundles will be processed using the same CSV ranges for RPM and ETASP').pack(anchor='w') 
    tk.Label(instructions_frame, text='• The comparison will show the difference between the two vehicle bundles').pack(anchor='w')
    tk.Label(instructions_frame, text='• Both bundles will also be compared individually against the CSV surface table').pack(anchor='w')
    
    def perform_comparison():
        if not second_bundle_paths:
            messagebox.showerror('Error', 'Please select a second vehicle bundle!')
            return
        
        try:
            selection_window.destroy()
            
            # Process both bundles using CSV ranges and compare them
            process_two_vehicle_bundles_comparison(
                first_bundle_paths, second_bundle_paths, surface_data,
                rpm_channel, etasp_channel, z_param_channel,
                raster_value, filters
            )
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to perform comparison: {e}')
    
    # Buttons frame
    buttons_frame = tk.Frame(selection_window)
    buttons_frame.pack(pady=20)
    
    btn_compare = tk.Button(buttons_frame, text='Compare Vehicle Bundles', 
                           command=perform_comparison, bg='lightgreen', 
                           font=('TkDefaultFont', 10, 'bold'), state='disabled')
    btn_compare.pack(side='left', padx=10)
    
    btn_cancel = tk.Button(buttons_frame, text='Cancel', 
                          command=selection_window.destroy, bg='lightcoral')
    btn_cancel.pack(side='right', padx=10)

def select_csv_columns(column_names, csv_file_path, mdf_file_paths):
    columns_window = tk.Toplevel()
    columns_window.title('Select CSV Columns and Interpolation Parameters')
    columns_window.geometry('500x500')

    tk.Label(columns_window, text='Select the columns for X, Y, and Z axes:', font=('TkDefaultFont', 12, 'bold')).pack(pady=10)

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
    # Set previous selection if available and still in columns
    if csv_config.get('x_column') in column_names:
        x_var.set(csv_config['x_column'])
    x_combobox.pack(pady=5)

    # Y-axis (ETASP)
    tk.Label(columns_window, text='Y-axis (ETASP):').pack(pady=5)
    y_var = tk.StringVar()
    y_combobox = ttk.Combobox(columns_window, textvariable=y_var, values=column_names, state='readonly')
    # Set previous selection if available and still in columns
    if csv_config.get('y_column') in column_names:
        y_var.set(csv_config['y_column'])
    y_combobox.pack(pady=5)

    # Z-axis (Results)
    tk.Label(columns_window, text='Z-axis (Results):').pack(pady=5)
    z_var = tk.StringVar()
    z_combobox = ttk.Combobox(columns_window, textvariable=z_var, values=column_names, state='readonly')
    # Set previous selection if available and still in columns
    if csv_config.get('z_column') in column_names:
        z_var.set(csv_config['z_column'])
    z_combobox.pack(pady=5)

    # Separator
    tk.Frame(columns_window, height=2, bg='gray').pack(fill='x', pady=10)

    # ETASP Interpolation Parameters
    tk.Label(columns_window, text='ETASP Interpolation Parameters:', font=('TkDefaultFont', 12, 'bold')).pack(pady=10)

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

    # Auto-detect button
    def auto_detect_etasp_range():
        y_col = y_var.get()
        if not y_col:
            messagebox.showerror('Error', 'Please select Y-axis (ETASP) column first!')
            return
        
        try:
            # Read CSV to get ETASP range
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

    btn_auto_detect = tk.Button(columns_window, text='Auto-Detect ETASP Range', command=auto_detect_etasp_range)
    btn_auto_detect.pack(pady=10)

    def view_surface_table():
        x_col = x_var.get()
        y_col = y_var.get()
        z_col = z_var.get()
        
        if not all([x_col, y_col, z_col]):
            messagebox.showerror('Error', 'Please select all three columns!')
            return
            
        try:
            etasp_min = etasp_min_var.get()
            etasp_max = etasp_max_var.get()
            etasp_intervals = etasp_intervals_var.get()
            
            if etasp_min >= etasp_max:
                messagebox.showerror('Error', 'ETASP Min must be less than ETASP Max!')
                return
            
            if etasp_intervals <= 0:
                messagebox.showerror('Error', 'Number of intervals must be positive!')
                return
            
            # Save CSV column selections to config (also for view operation)
            config = {}
            if os.path.exists('fuel_config.json'):
                try:
                    with open('fuel_config.json', 'r') as f:
                        config = json.load(f)
                except:
                    pass
            
            config['csv_columns'] = {
                'x_column': x_col,
                'y_column': y_col,
                'z_column': z_col,
                'etasp_min': etasp_min,
                'etasp_max': etasp_max,
                'etasp_intervals': etasp_intervals
            }
            
            try:
                with open('fuel_config.json', 'w') as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not save configuration: {e}")
                
            surface_data = load_surface_table(csv_file_path, x_col, y_col, z_col, 
                                            etasp_min, etasp_max, etasp_intervals)
            x_values, y_values, z_values = surface_data
            show_surface_table(surface_data, x_values, y_values, z_values, None, 0, 0)
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load surface table: {e}')

    def confirm_columns():
        x_col = x_var.get()
        y_col = y_var.get()
        z_col = z_var.get()
        
        if not all([x_col, y_col, z_col]):
            messagebox.showerror('Error', 'Please select all three columns!')
            return
            
        if len(set([x_col, y_col, z_col])) != 3:
            messagebox.showerror('Error', 'Please select three different columns!')
            return

        try:
            etasp_min = etasp_min_var.get()
            etasp_max = etasp_max_var.get()
            etasp_intervals = etasp_intervals_var.get()
            
            if etasp_min >= etasp_max:
                messagebox.showerror('Error', 'ETASP Min must be less than ETASP Max!')
                return
            
            if etasp_intervals <= 0:
                messagebox.showerror('Error', 'Number of intervals must be positive!')
                return
            
            # Save CSV column selections to config
            config = {}
            if os.path.exists('fuel_config.json'):
                try:
                    with open('fuel_config.json', 'r') as f:
                        config = json.load(f)
                except:
                    pass
            
            config['csv_columns'] = {
                'x_column': x_col,
                'y_column': y_col,
                'z_column': z_col,
                'etasp_min': etasp_min,
                'etasp_max': etasp_max,
                'etasp_intervals': etasp_intervals
            }
            
            try:
                with open('fuel_config.json', 'w') as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not save configuration: {e}")
                
            surface_data = load_surface_table(csv_file_path, x_col, y_col, z_col, 
                                            etasp_min, etasp_max, etasp_intervals)
            columns_window.destroy()
            select_raster_and_channels(surface_data, mdf_file_paths)
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load surface table: {e}')

    # Create button frame for better layout
    button_frame = tk.Frame(columns_window)
    button_frame.pack(pady=20)

    # Optional button to view surface table
    btn_view_table = tk.Button(button_frame, text='View Surface Table (Optional)', 
                              command=view_surface_table, bg='lightblue')
    btn_view_table.pack(side='left', padx=10)

    # Main button to proceed
    btn_confirm = tk.Button(button_frame, text='Continue to Next Step', 
                           command=confirm_columns, bg='lightgreen', font=('TkDefaultFont', 10, 'bold'))
    btn_confirm.pack(side='right', padx=10)

def load_surface_table(csv_file_path, x_col, y_col, z_col, rpm_min=None, rpm_max=None, rpm_intervals=None, etasp_min=None, etasp_max=None, etasp_intervals=None):
    """Load surface table from 3-column CSV format with optional interpolation"""
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

def show_surface_table(surface_data, x_values, y_values, z_values, percentages=None, total_points_inside=0, total_points_all=0, comparison_percentages=None, comparison_name="Comparison"):
    """Show surface table in PyQt5 window"""
    global _active_viewers
    
    # Get or create QApplication instance on main thread
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    viewer = SurfaceTableViewer(surface_data, x_values, y_values, z_values, percentages, total_points_inside, total_points_all, comparison_percentages, comparison_name)
    
    # Keep reference to prevent garbage collection
    _active_viewers.append(viewer)
    viewer.show()
    
    # Don't call app.exec_() as it would block the main thread
    # Let the existing event loop handle the window

def select_raster_and_channels(surface_data, mdf_file_paths):
    raster_window = tk.Toplevel()
    raster_window.title('Select Raster')
    raster_window.geometry('300x200')

    tk.Label(raster_window, text='Select Raster Value (seconds):').pack(pady=10)

    default_rasters = ['0.001', '0.02', '0.05', '0.1', 'Custom']
    raster_var = tk.StringVar(value=default_rasters[0])

    raster_combobox = ttk.Combobox(raster_window, values=default_rasters, textvariable=raster_var, state='readonly')
    raster_combobox.pack(pady=5)

    custom_raster_entry = tk.Entry(raster_window)
    custom_raster_entry.pack(pady=5)
    custom_raster_entry.configure(state='disabled')

    def on_raster_selection(event):
        selected = raster_var.get()
        if selected == 'Custom':
            custom_raster_entry.configure(state='normal')
        else:
            custom_raster_entry.delete(0, tk.END)
            custom_raster_entry.configure(state='disabled')

    raster_combobox.bind('<<ComboboxSelected>>', on_raster_selection)

    def confirm_raster():
        selected = raster_var.get()
        if selected == 'Custom':
            raster_value = custom_raster_entry.get()
        else:
            raster_value = selected

        try:
            raster_value = float(raster_value)
            if raster_value <= 0:
                raise ValueError
            raster_window.destroy()
            select_channels_and_filters(surface_data, raster_value, mdf_file_paths)
        except ValueError:
            messagebox.showerror('Error', 'Please enter a valid positive number for raster.')

    btn_confirm = tk.Button(raster_window, text='Confirm', command=confirm_raster)
    btn_confirm.pack(pady=10)

def select_channels_and_filters(surface_data, raster_value, mdf_file_paths):
    channels_window = tk.Toplevel()
    channels_window.title('Select Channels and Filters')
    channels_window.geometry('800x600')

    # Load sample file to get channel names
    try:
        sample_mdf = MDF(mdf_file_paths[0])
        all_channels = list(sample_mdf.channels_db.keys())
    except Exception as e:
        messagebox.showerror('Error', f'Failed to load sample file: {e}')
        return

    # Variables for required channels
    rpm_var = tk.StringVar()
    etasp_var = tk.StringVar()

    # Try to load previous selections
    config = {}
    if os.path.exists('fuel_config.json'):
        with open('fuel_config.json', 'r') as f:
            config = json.load(f)
            rpm_var.set(config.get('rpm_channel', ''))
            etasp_var.set(config.get('etasp_channel', ''))

    # Channel selection frame
    channel_frame = tk.Frame(channels_window)
    channel_frame.pack(fill='x', padx=10, pady=10)

    tk.Label(channel_frame, text='Required Channels', font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')

    tk.Label(channel_frame, text='RPM Channel:').pack(anchor='w', pady=2)
    rpm_combobox = AutocompleteCombobox(channel_frame, textvariable=rpm_var, width=50)
    rpm_combobox.set_completion_list(all_channels)
    rpm_combobox.pack(anchor='w', pady=2)

    tk.Label(channel_frame, text='ETASP Channel:').pack(anchor='w', pady=2)
    etasp_combobox = AutocompleteCombobox(channel_frame, textvariable=etasp_var, width=50)
    etasp_combobox.set_completion_list(all_channels)
    etasp_combobox.pack(anchor='w', pady=2)

    # Filters frame
    filters_frame = tk.Frame(channels_window)
    filters_frame.pack(fill='both', expand=True, padx=10, pady=10)

    tk.Label(filters_frame, text='Filters', font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')

    # Scrollable frame for filters
    canvas = tk.Canvas(filters_frame)
    scrollbar = tk.Scrollbar(filters_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Store filter information
    filters_list = []

    def add_filter():
        filter_frame = tk.Frame(scrollable_frame, relief='raised', borderwidth=1)
        filter_frame.pack(fill='x', pady=5, padx=5)

        filter_info = {
            'frame': filter_frame,
            'channel_var': tk.StringVar(),
            'condition_var': tk.StringVar(value='within range'),
            'min_var': tk.DoubleVar(),
            'max_var': tk.DoubleVar(),
            'filtered_time_var': tk.StringVar(value='--:--:--.---')
        }

        # Filter row 1: Channel and condition
        row1 = tk.Frame(filter_frame)
        row1.pack(fill='x', pady=2)

        tk.Label(row1, text='Channel:').pack(side='left')
        channel_combo = AutocompleteCombobox(row1, textvariable=filter_info['channel_var'], width=30)
        channel_combo.set_completion_list(all_channels)
        channel_combo.pack(side='left', padx=5)

        tk.Label(row1, text='Condition:').pack(side='left', padx=(10, 0))
        condition_combo = ttk.Combobox(row1, textvariable=filter_info['condition_var'], 
                                     values=['within range', 'outside range'], state='readonly', width=15)
        condition_combo.pack(side='left', padx=5)

        # Filter row 2: Min/Max values and filtered time
        row2 = tk.Frame(filter_frame)
        row2.pack(fill='x', pady=2)

        tk.Label(row2, text='Min:').pack(side='left')
        tk.Entry(row2, textvariable=filter_info['min_var'], width=10).pack(side='left', padx=5)

        tk.Label(row2, text='Max:').pack(side='left', padx=(10, 0))
        tk.Entry(row2, textvariable=filter_info['max_var'], width=10).pack(side='left', padx=5)

        tk.Label(row2, text='Filtered Time:').pack(side='left', padx=(20, 0))
        tk.Label(row2, textvariable=filter_info['filtered_time_var']).pack(side='left', padx=5)

        # Remove button
        def remove_filter():
            filter_frame.destroy()
            filters_list.remove(filter_info)
            update_remaining_time()

        tk.Button(row2, text='Remove', command=remove_filter).pack(side='right', padx=5)

        # Bind events to update remaining time when values change
        def on_filter_change(*args):
            update_remaining_time()
        
        filter_info['channel_var'].trace('w', on_filter_change)
        filter_info['condition_var'].trace('w', on_filter_change)
        filter_info['min_var'].trace('w', on_filter_change)
        filter_info['max_var'].trace('w', on_filter_change)

        filters_list.append(filter_info)
        canvas.configure(scrollregion=canvas.bbox("all"))
        update_remaining_time()  # Update immediately after adding

    def calculate_filter_time():
        """Calculate filtered time for each filter based on sample file"""
        rpm_channel = rpm_var.get()
        etasp_channel = etasp_var.get()

        if not rpm_channel or not etasp_channel:
            messagebox.showwarning('Warning', 'Please select RPM and ETASP channels first.')
            return

        try:
            # Load sample file data
            mdf = MDF(mdf_file_paths[0])
            
            for filter_info in filters_list:
                channel_name = filter_info['channel_var'].get()
                if not channel_name:
                    continue

                try:
                    signal = mdf.get(channel_name)
                    condition = filter_info['condition_var'].get()
                    min_val = filter_info['min_var'].get()
                    max_val = filter_info['max_var'].get()

                    if condition == 'within range':
                        mask = (signal.samples >= min_val) & (signal.samples <= max_val)
                    else:  # outside range
                        mask = (signal.samples < min_val) | (signal.samples > max_val)

                    # Calculate time duration
                    time_step = signal.timestamps[1] - signal.timestamps[0] if len(signal.timestamps) > 1 else raster_value
                    filtered_time = np.sum(mask) * time_step
                    filter_info['filtered_time_var'].set(seconds_to_hms(filtered_time))

                except Exception as e:
                    filter_info['filtered_time_var'].set('Error')

        except Exception as e:
            messagebox.showerror('Error', f'Failed to calculate filter times: {e}')

    def update_remaining_time():
        """Calculate remaining time after all filters"""
        rpm_channel = rpm_var.get()
        etasp_channel = etasp_var.get()

        if not rpm_channel or not etasp_channel:
            remaining_time_var.set('Total remaining time: --:--:--.--- (select channels first)')
            return

        try:
            # Load sample file data
            mdf = MDF(mdf_file_paths[0])
            rpm_signal = mdf.get(rpm_channel)
            
            # Start with all points
            mask = np.ones(len(rpm_signal.samples), dtype=bool)
            
            # Apply all filters sequentially
            for filter_info in filters_list:
                channel_name = filter_info['channel_var'].get()
                if not channel_name:
                    continue

                try:
                    signal = mdf.get(channel_name)
                    condition = filter_info['condition_var'].get()
                    min_val = filter_info['min_var'].get()
                    max_val = filter_info['max_var'].get()

                    # Resample to match rpm signal length if needed
                    if len(signal.samples) != len(rpm_signal.samples):
                        signal_resampled = np.interp(rpm_signal.timestamps, signal.timestamps, signal.samples)
                    else:
                        signal_resampled = signal.samples

                    if condition == 'within range':
                        filter_mask = (signal_resampled >= min_val) & (signal_resampled <= max_val)
                    else:  # outside range
                        filter_mask = (signal_resampled < min_val) | (signal_resampled > max_val)

                    mask = mask & filter_mask

                except Exception as e:
                    continue

            # Calculate remaining time
            time_step = rpm_signal.timestamps[1] - rpm_signal.timestamps[0] if len(rpm_signal.timestamps) > 1 else raster_value
            remaining_time = np.sum(mask) * time_step
            remaining_time_var.set(f'Total remaining time: {seconds_to_hms(remaining_time)}')

        except Exception as e:
            remaining_time_var.set('Total remaining time: Error calculating')

    # Filter controls
    filter_controls = tk.Frame(filters_frame)
    filter_controls.pack(fill='x', pady=5)

    tk.Button(filter_controls, text='Add Filter', command=add_filter).pack(side='left', padx=5)
    tk.Button(filter_controls, text='Calculate Filter Times', command=calculate_filter_time).pack(side='left', padx=5)

    # Remaining time label
    remaining_time_var = tk.StringVar(value='Total remaining time: --:--:--.---')
    tk.Label(filter_controls, textvariable=remaining_time_var).pack(side='left', padx=20)

    # Pack scrollable frame
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    def confirm_channels():
        rpm_channel = rpm_var.get()
        etasp_channel = etasp_var.get()

        if not rpm_channel or not etasp_channel:
            messagebox.showerror('Error', 'Please select both RPM and ETASP channels!')
            return

        # Verify channels exist
        if rpm_channel not in all_channels or etasp_channel not in all_channels:
            messagebox.showerror('Error', 'Selected channels not found in the file!')
            return

        # Save configuration
        config = {
            'rpm_channel': rpm_channel,
            'etasp_channel': etasp_channel,
            'filters': []
        }

        for filter_info in filters_list:
            if filter_info['channel_var'].get():
                config['filters'].append({
                    'channel': filter_info['channel_var'].get(),
                    'condition': filter_info['condition_var'].get(),
                    'min': filter_info['min_var'].get(),
                    'max': filter_info['max_var'].get()
                })

        with open('fuel_config.json', 'w') as f:
            json.dump(config, f)

        channels_window.destroy()
        process_files_and_show_results(surface_data, raster_value, rpm_channel, etasp_channel, 
                                     config['filters'], mdf_file_paths)

    btn_confirm = tk.Button(channels_window, text='Confirm', command=confirm_channels)
    btn_confirm.pack(pady=10)

def process_files(surface_data, mdf_file_paths, rpm_channel, etasp_channel, raster_value, filters, z_param_channel=None):
    """Process files and return percentages without showing results window"""
    x_values, y_values, z_values = surface_data
    
    # Initialize counters
    total_point_counts = np.zeros_like(z_values)
    total_points_inside_all_files = 0
    
    for file_path in mdf_file_paths:
        try:
            result = process_single_file(file_path, surface_data, raster_value, 
                                       rpm_channel, etasp_channel, filters)
            if result:
                # Sum actual point counts (not percentages)
                total_point_counts += result['point_counts']
                total_points_inside_all_files += result['bounded_points']
        except Exception as e:
            print(f'Warning: Failed to process {os.path.basename(file_path)}: {e}')
            continue
    
    # Convert point counts to percentages
    if total_points_inside_all_files > 0:
        total_percentages = (total_point_counts / total_points_inside_all_files) * 100
    else:
        total_percentages = np.zeros_like(z_values)
    
    return total_percentages

def process_files_and_show_results(surface_data, raster_value, rpm_channel, etasp_channel, 
                                 filters, mdf_file_paths):
    """Process files and show results with surface table and percentages"""
    x_values, y_values, z_values = surface_data
    
    # Initialize counters
    total_point_counts = np.zeros_like(z_values)
    total_points_outside = 0
    total_time_outside = 0
    total_points_inside_all_files = 0
    total_points_all_files = 0
    
    results_list = []
    
    for file_path in mdf_file_paths:
        try:
            result = process_single_file(file_path, surface_data, raster_value, 
                                       rpm_channel, etasp_channel, filters)
            if result:
                results_list.append(result)
                # Sum actual point counts (not percentages)
                total_point_counts += result['point_counts']
                total_points_outside += result['points_outside']
                total_time_outside += result['time_outside']
                total_points_inside_all_files += result['bounded_points']
                total_points_all_files += result['total_points_filtered']
        except Exception as e:
            messagebox.showerror('Error', f'Failed to process {os.path.basename(file_path)}: {e}')
            continue
    
    # Convert point counts to percentages
    if total_points_inside_all_files > 0:
        total_percentages = (total_point_counts / total_points_inside_all_files) * 100
    else:
        total_percentages = np.zeros_like(z_values)
    
    # Show results
    show_results_window(surface_data, total_percentages, results_list, 
                       total_points_outside, total_time_outside, 
                       total_points_inside_all_files, total_points_all_files)

def process_single_file(file_path, surface_data, raster_value, rpm_channel, etasp_channel, filters):
    """Process a single MDF/DAT file"""
    x_values, y_values, z_values = surface_data
    
    # Load file
    mdf = MDF(file_path)
    
    # Get signals
    rpm_signal = mdf.get(rpm_channel)
    etasp_signal = mdf.get(etasp_channel)
    
    # Create common time base
    start_time = max(rpm_signal.timestamps[0], etasp_signal.timestamps[0])
    end_time = min(rpm_signal.timestamps[-1], etasp_signal.timestamps[-1])
    time_base = np.arange(start_time, end_time, raster_value)
    
    # Resample signals
    rpm_resampled = np.interp(time_base, rpm_signal.timestamps, rpm_signal.samples)
    etasp_resampled = np.interp(time_base, etasp_signal.timestamps, etasp_signal.samples)
    
    # Apply filters
    mask = np.ones(len(time_base), dtype=bool)
    
    for filter_config in filters:
        try:
            filter_signal = mdf.get(filter_config['channel'])
            filter_resampled = np.interp(time_base, filter_signal.timestamps, filter_signal.samples)
            
            if filter_config['condition'] == 'within range':
                filter_mask = (filter_resampled >= filter_config['min']) & (filter_resampled <= filter_config['max'])
            else:  # outside range
                filter_mask = (filter_resampled < filter_config['min']) | (filter_resampled > filter_config['max'])
            
            mask = mask & filter_mask
        except:
            continue  # Skip invalid filters
    
    # Apply mask
    rpm_filtered = rpm_resampled[mask]
    etasp_filtered = etasp_resampled[mask]
    time_filtered = time_base[mask]
    
    # Check bounds
    x_min, x_max = x_values.min(), x_values.max()
    y_min, y_max = y_values.min(), y_values.max()
    
    bounds_mask = (rpm_filtered >= x_min) & (rpm_filtered <= x_max) & \
                  (etasp_filtered >= y_min) & (etasp_filtered <= y_max)
    
    points_outside = np.sum(~bounds_mask)
    time_outside = points_outside * raster_value
    
    # Keep only points within bounds
    rpm_bounded = rpm_filtered[bounds_mask]
    etasp_bounded = etasp_filtered[bounds_mask]
    
    # Create point count matrix
    point_counts = np.zeros_like(z_values)
    total_bounded_points = len(rpm_bounded)
    
    if total_bounded_points > 0:
        # Assign points to cells
        for i, rpm_val in enumerate(rpm_bounded):
            etasp_val = etasp_bounded[i]
            
            # Find closest cell
            x_idx = np.argmin(np.abs(x_values - rpm_val))
            y_idx = np.argmin(np.abs(y_values - etasp_val))
            
            point_counts[y_idx, x_idx] += 1
    
    # Also create percentage matrix for individual file display
    percentage_matrix = np.zeros_like(z_values)
    if total_bounded_points > 0:
        percentage_matrix = (point_counts / total_bounded_points) * 100
    
    result = {
        'file_path': file_path,
        'percentage_matrix': percentage_matrix,
        'point_counts': point_counts,
        'total_time': len(time_filtered) * raster_value,
        'points_outside': points_outside,
        'time_outside': time_outside,
        'total_points': len(rpm_resampled),
        'total_points_filtered': len(rpm_filtered),
        'filtered_points': len(rpm_filtered),
        'bounded_points': total_bounded_points
    }
    
    return result

def show_results_window(surface_data, total_percentages, results_list, total_points_outside, total_time_outside, total_points_inside, total_points_all):
    """Show results window with surface table and statistics"""
    results_window = tk.Toplevel()
    results_window.title('Fuel Consumption Evaluation Results')
    results_window.geometry('1000x700')
    
    # Statistics frame
    stats_frame = tk.Frame(results_window)
    stats_frame.pack(fill='x', padx=10, pady=10)
    
    tk.Label(stats_frame, text='Analysis Results', font=('TkDefaultFont', 14, 'bold')).pack(anchor='w')
    tk.Label(stats_frame, text=f'Total files processed: {len(results_list)}').pack(anchor='w')
    tk.Label(stats_frame, text=f'Total points inside bounds: {total_points_inside}').pack(anchor='w')
    tk.Label(stats_frame, text=f'Total points outside surface table: {total_points_outside}').pack(anchor='w')
    tk.Label(stats_frame, text=f'Total time outside surface table: {seconds_to_hms(total_time_outside)}').pack(anchor='w')
    
    # Button to view surface table
    def view_surface_table():
        x_values, y_values, z_values = surface_data
        show_surface_table(surface_data, x_values, y_values, z_values, total_percentages, total_points_inside, total_points_all)
    
    btn_view_surface = tk.Button(stats_frame, text='View Surface Table with Percentages', 
                                command=view_surface_table)
    btn_view_surface.pack(side='left', padx=5, pady=10)
    
    # Button to add comparison data
    def add_comparison():
        select_comparison_files(surface_data, total_percentages, total_points_inside, total_points_all)
    
    btn_add_comparison = tk.Button(stats_frame, text='Add Comparison Data', 
                                  command=add_comparison, bg='lightblue')
    btn_add_comparison.pack(side='left', padx=5, pady=10)
    
    # Individual file results
    tk.Label(results_window, text='Individual File Results', font=('TkDefaultFont', 12, 'bold')).pack(anchor='w', padx=10)
    
    # Create scrollable frame for results
    canvas = tk.Canvas(results_window)
    scrollbar = tk.Scrollbar(results_window, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Display results for each file
    for result in results_list:
        file_frame = tk.Frame(scrollable_frame, relief='raised', borderwidth=1)
        file_frame.pack(fill='x', pady=5, padx=5)
        
        file_name = os.path.basename(result['file_path'])
        tk.Label(file_frame, text=f'File: {file_name}', font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        tk.Label(file_frame, text=f'Total analysis time: {seconds_to_hms(result["total_time"])}').pack(anchor='w')
        tk.Label(file_frame, text=f'Points outside bounds: {result["points_outside"]} ({seconds_to_hms(result["time_outside"])})').pack(anchor='w')
        tk.Label(file_frame, text=f'Points used in analysis: {result["bounded_points"]}').pack(anchor='w')
    
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

def select_comparison_files(surface_data, main_percentages, main_points_inside, main_points_all):
    """Select comparison files and process them"""
    comparison_window = tk.Toplevel()
    comparison_window.title('Select Comparison Files')
    comparison_window.geometry('600x500')
    
    # File selection
    comparison_files = []
    
    def select_files():
        nonlocal comparison_files
        comparison_files = filedialog.askopenfilenames(
            title='Select Comparison MDF/MF4/DAT Files',
            filetypes=[('MDF, MF4 and DAT Files', '*.dat *.mdf *.mf4'), ('DAT Files', '*.dat'), ('MDF Files', '*.mdf'), ('MF4 Files', '*.mf4')]
        )
        if comparison_files:
            lbl_files_selected.config(text=f"{len(comparison_files)} file(s) selected")
        else:
            lbl_files_selected.config(text="No files selected")
    
    tk.Label(comparison_window, text='Select Comparison Files', font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
    
    btn_select_files = tk.Button(comparison_window, text='Select MDF/MF4/DAT Files', command=select_files)
    btn_select_files.pack(pady=5)
    
    lbl_files_selected = tk.Label(comparison_window, text='No files selected')
    lbl_files_selected.pack(pady=5)
    
    # Channel selection
    tk.Label(comparison_window, text='Select Channels for Comparison', font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
    
    # Try to load existing configuration as defaults
    config = {}
    if os.path.exists('fuel_config.json'):
        try:
            with open('fuel_config.json', 'r') as f:
                config = json.load(f)
        except:
            pass
    
    # RPM Channel
    tk.Label(comparison_window, text='RPM Channel:').pack(anchor='w', padx=20)
    rpm_var = tk.StringVar(value=config.get('rpm_channel', ''))
    rpm_entry = tk.Entry(comparison_window, textvariable=rpm_var, width=50)
    rpm_entry.pack(padx=20, pady=2)
    
    # ETASP Channel
    tk.Label(comparison_window, text='ETASP Channel:').pack(anchor='w', padx=20)
    etasp_var = tk.StringVar(value=config.get('etasp_channel', ''))
    etasp_entry = tk.Entry(comparison_window, textvariable=etasp_var, width=50)
    etasp_entry.pack(padx=20, pady=2)
    
    # Raster selection
    tk.Label(comparison_window, text='Raster Value (seconds):', font=('TkDefaultFont', 10, 'bold')).pack(pady=(10, 5))
    raster_var = tk.DoubleVar(value=0.02)
    raster_frame = tk.Frame(comparison_window)
    raster_frame.pack()
    tk.Label(raster_frame, text='Raster:').pack(side='left')
    raster_entry = tk.Entry(raster_frame, textvariable=raster_var, width=10)
    raster_entry.pack(side='left', padx=5)
    
    # Filters checkboxes
    tk.Label(comparison_window, text='Apply Same Filters as Main Analysis:', font=('TkDefaultFont', 10, 'bold')).pack(pady=(10, 5))
    use_same_filters_var = tk.BooleanVar(value=True)
    tk.Checkbutton(comparison_window, text='Use same filters', variable=use_same_filters_var).pack()
    
    # Process button
    def process_comparison():
        if not comparison_files:
            messagebox.showerror('Error', 'Please select comparison files!')
            return
        
        rpm_channel = rpm_var.get().strip()
        etasp_channel = etasp_var.get().strip()
        
        if not rpm_channel or not etasp_channel:
            messagebox.showerror('Error', 'Please enter both RPM and ETASP channels!')
            return
        
        # Get filters from main config if requested
        filters = []
        if use_same_filters_var.get():
            filters = config.get('filters', [])
        
        try:
            # Get raster value
            raster_value = raster_var.get()
            if raster_value <= 0:
                messagebox.showerror('Error', 'Raster value must be positive!')
                return
            
            # Process files and show comparison
            comparison_percentages = process_comparison_files(
                comparison_files, surface_data, raster_value, 
                rpm_channel, etasp_channel, filters
            )
            
            if comparison_percentages is not None:
                comparison_window.destroy()
                
                # Show surface table with comparison
                x_values, y_values, z_values = surface_data
                comparison_name = f"Comparison ({len(comparison_files)} files)"
                show_surface_table(
                    surface_data, x_values, y_values, z_values, 
                    main_percentages, main_points_inside, main_points_all,
                    comparison_percentages, comparison_name
                )
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to process comparison files: {e}')
    
    btn_process = tk.Button(comparison_window, text='Process Comparison', 
                           command=process_comparison, bg='lightgreen')
    btn_process.pack(pady=20)

def process_comparison_files(file_paths, surface_data, raster_value, rpm_channel, etasp_channel, filters):
    """Process comparison files and return combined percentages"""
    x_values, y_values, z_values = surface_data
    
    # Initialize counters
    total_point_counts = np.zeros_like(z_values)
    total_points_inside_all_files = 0
    
    for file_path in file_paths:
        try:
            result = process_single_file(file_path, surface_data, raster_value, 
                                       rpm_channel, etasp_channel, filters)
            if result:
                # Sum actual point counts (not percentages)
                total_point_counts += result['point_counts']
                total_points_inside_all_files += result['bounded_points']
        except Exception as e:
            print(f"Warning: Failed to process {os.path.basename(file_path)}: {e}")
            continue
    
    # Convert point counts to percentages
    if total_points_inside_all_files > 0:
        total_percentages = (total_point_counts / total_points_inside_all_files) * 100
    else:
        total_percentages = np.zeros_like(z_values)
    
    return total_percentages

def process_vehicle_analysis_with_csv(mdf_file_paths, surface_data, rpm_channel, etasp_channel, z_param_channel, raster_value, filters):
    """Process vehicle files and analyze against CSV surface table"""
    
    # Extract surface data
    csv_x_values, csv_y_values, csv_z_values = surface_data
    
    # Process vehicle files using CSV ranges
    try:
        # Process files and get percentages
        total_percentages = process_files(
            surface_data,
            mdf_file_paths,
            rpm_channel,
            etasp_channel,
            raster_value,
            filters,
            z_param_channel
        )
        
        # Show comparison with vehicle data as main and CSV as comparison
        show_surface_table(
            surface_data,
            csv_x_values, csv_y_values, total_percentages,
            percentages=total_percentages,
            total_points_inside=0,  # Will be calculated properly
            total_points_all=0,     # Will be calculated properly
            comparison_percentages=csv_z_values,
            comparison_name="CSV Surface Table"
        )
        
    except Exception as e:
        messagebox.showerror('Error', f'Failed to process vehicle analysis: {e}')

def process_two_vehicle_bundles_comparison(first_bundle_paths, second_bundle_paths, surface_data, rpm_channel, etasp_channel, z_param_channel, raster_value, filters):
    """Process and compare two vehicle bundles using CSV ranges"""
    
    # Extract ranges from CSV surface data
    csv_x_values, csv_y_values, csv_z_values = surface_data
    rpm_min, rpm_max = float(csv_x_values.min()), float(csv_x_values.max())
    etasp_min, etasp_max = float(csv_y_values.min()), float(csv_y_values.max())
    
    # Create grid using CSV ranges
    x_values = csv_x_values
    y_values = csv_y_values
    
    # Progress window
    progress_window = tk.Toplevel()
    progress_window.title('Processing Vehicle Bundles for Comparison')
    progress_window.geometry('400x200')
    progress_window.grab_set()
    
    progress_label = tk.Label(progress_window, text='Processing first bundle...')
    progress_label.pack(pady=10)
    
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=2)
    progress_bar.pack(pady=10, padx=20, fill='x')
    
    progress_window.update()
    
    try:
        # Process first bundle
        first_bundle_percentages = process_files(
            surface_data,
            first_bundle_paths,
            rpm_channel,
            etasp_channel,
            raster_value,
            filters,
            z_param_channel
        )
        
        progress_var.set(1)
        progress_label.config(text='Processing second bundle...')
        progress_window.update()
        
        # Process second bundle
        second_bundle_percentages = process_files(
            surface_data,
            second_bundle_paths,
            rpm_channel,
            etasp_channel,
            raster_value,
            filters,
            z_param_channel
        )
        
        progress_var.set(2)
        progress_window.destroy()
        
        # Show comparison with first bundle as main data and second bundle as comparison
        show_surface_table(
            surface_data,
            x_values, y_values, first_bundle_percentages,
            percentages=first_bundle_percentages,
            total_points_inside=0,
            total_points_all=0,
            comparison_percentages=second_bundle_percentages,
            comparison_name="Second Vehicle Bundle"
        )
        
    except Exception as e:
        progress_window.destroy()
        messagebox.showerror('Error', f'Failed to process vehicle bundles: {e}')

def process_surface_creation_with_csv_ranges(mdf_file_paths, surface_data, rpm_channel, etasp_channel, z_param_channel, raster_value, filters):
    """Create surface table from vehicle logs using CSV ranges"""
    
    # Extract ranges from CSV surface data
    csv_x_values, csv_y_values, csv_z_values = surface_data
    rpm_min, rpm_max = float(csv_x_values.min()), float(csv_x_values.max())
    etasp_min, etasp_max = float(csv_y_values.min()), float(csv_y_values.max())
    rpm_intervals = len(csv_x_values) - 1
    etasp_intervals = len(csv_y_values) - 1
    
    # Use the existing surface creation process
    try:
        process_surface_creation_from_logs(
            mdf_file_paths,
            rpm_channel,
            etasp_channel,
            z_param_channel,
            (rpm_min, rpm_max, rpm_intervals),
            (etasp_min, etasp_max, etasp_intervals),
            raster_value,
            filters,
            csv_surface_data=surface_data  # Pass CSV data for comparison
        )
    except Exception as e:
        messagebox.showerror('Error', f'Failed to create surface table: {e}')

if __name__ == '__main__':
    main() 