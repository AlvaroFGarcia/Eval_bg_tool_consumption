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
from PyQt5.QtGui import QColor, QFont, QPainter, QLinearGradient, QRadialGradient, QPen, QBrush
from PyQt5.QtCore import Qt, QRect, QPoint
import os
from scipy.interpolate import griddata
try:
    from scipy.ndimage import gaussian_filter
    SCIPY_NDIMAGE_AVAILABLE = True
except ImportError:
    SCIPY_NDIMAGE_AVAILABLE = False
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Global list to keep references to SurfaceTableViewer instances
_active_viewers = []

class ConcentrationOverlay(QWidget):
    """Custom overlay widget for smooth concentration visualization"""
    
    def __init__(self, parent_table, surface_viewer):
        super().__init__(parent_table.viewport())
        self.parent_table = parent_table
        self.surface_viewer = surface_viewer
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(parent_table.viewport().size())
        
        # Connect to parent table signals to update position and size
        parent_table.horizontalScrollBar().valueChanged.connect(self.update_position)
        parent_table.verticalScrollBar().valueChanged.connect(self.update_position)
        
        # Store original resize event handler
        self.original_resize_event = parent_table.viewport().resizeEvent
        parent_table.viewport().resizeEvent = self.on_parent_resize
        
    def on_parent_resize(self, event):
        """Handle parent viewport resize"""
        # Call original resize event first
        if self.original_resize_event:
            self.original_resize_event(event)
        else:
            QWidget.resizeEvent(self.parent_table.viewport(), event)
        
        # Update overlay size
        self.setFixedSize(self.parent_table.viewport().size())
        self.update()
        
    def update_position(self):
        """Update overlay position when table scrolls"""
        self.update()
        
    def paintEvent(self, event):
        """Paint the concentration overlay"""
        if not self.surface_viewer.concentration_overlay_enabled or self.surface_viewer.original_percentages is None:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Get table geometry information
        table = self.parent_table
        row_count = len(self.surface_viewer.y_values)
        col_count = len(self.surface_viewer.x_values)
        
        # Calculate cell dimensions and positions
        header_width = table.columnWidth(0)
        header_height = table.rowHeight(0)
        
        # Get visible area
        scroll_x = table.horizontalScrollBar().value()
        scroll_y = table.verticalScrollBar().value()
        
        # Paint based on selected mode
        if self.surface_viewer.concentration_mode == 'scatter':
            self.paint_scatter_concentration(painter, header_width, header_height, scroll_x, scroll_y)
        else:  # gradient mode
            self.paint_interpolated_concentration(painter, header_width, header_height, scroll_x, scroll_y)
        
    def paint_interpolated_concentration(self, painter, header_width, header_height, scroll_x, scroll_y):
        """Paint smooth interpolated concentration overlay"""
        viewer = self.surface_viewer
        table = self.parent_table
        
        # Get data dimensions
        rows = len(viewer.y_values)
        cols = len(viewer.x_values)
        
        if rows == 0 or cols == 0:
            return
            
        # Calculate cell positions and sizes
        data_points = []
        values = []
        
        for i in range(rows):
            for j in range(cols):
                # Get cell geometry
                cell_x = header_width + sum(table.columnWidth(k+1) for k in range(j)) - scroll_x
                cell_y = header_height + sum(table.rowHeight(k+1) for k in range(i)) - scroll_y
                cell_width = table.columnWidth(j+1)
                cell_height = table.rowHeight(i+1)
                
                # Get concentration value
                conc_value = viewer.original_percentages[i, j] if not np.isnan(viewer.original_percentages[i, j]) else 0
                
                # Add center point of cell
                center_x = cell_x + cell_width / 2
                center_y = cell_y + cell_height / 2
                
                data_points.append((center_x, center_y))
                values.append(conc_value)
        
        if not data_points:
            return
            
        # Create a higher resolution grid for smooth interpolation
        viewport_width = self.width()
        viewport_height = self.height()
        
        # Create interpolation grid (higher resolution for smoothness)
        grid_resolution = max(4, min(8, viewport_width // 50))  # Adaptive resolution
        x_grid = np.linspace(0, viewport_width, viewport_width // grid_resolution)
        y_grid = np.linspace(0, viewport_height, viewport_height // grid_resolution)
        
        # Convert data points to arrays
        points = np.array(data_points)
        values_array = np.array(values)
        
        if len(points) < 3:  # Need at least 3 points for interpolation
            return
            
        # Create meshgrid for interpolation
        X, Y = np.meshgrid(x_grid, y_grid)
        
        try:
            # Interpolate concentration values
            Z = griddata(points, values_array, (X, Y), method='cubic', fill_value=0)
            
            # Apply blur effect by smoothing the interpolated values
            if viewer.concentration_blur_enabled and SCIPY_NDIMAGE_AVAILABLE:
                sigma = max(1.0, grid_resolution / 4)  # Adaptive blur
                Z = gaussian_filter(Z, sigma=sigma)
            
            # Normalize values
            max_conc = np.nanmax(viewer.original_percentages) if not np.all(np.isnan(viewer.original_percentages)) else 1
            if max_conc > 0:
                Z_norm = np.clip(Z / max_conc, 0, 1)
                
                # Apply intensity and gamma correction
                Z_norm = Z_norm * viewer.concentration_intensity
                Z_norm = np.power(np.clip(Z_norm, 0, 1), viewer.concentration_gamma)
            else:
                Z_norm = np.zeros_like(Z)
            
            # Paint the interpolated surface
            self.paint_gradient_surface(painter, X, Y, Z_norm, grid_resolution)
            
        except Exception as e:
            # Fallback to simple radial gradients if interpolation fails
            print(f"Interpolation failed, using fallback: {e}")
            self.paint_radial_fallback(painter, data_points, values, max_conc)
    
    def paint_gradient_surface(self, painter, X, Y, Z_norm, grid_resolution):
        """Paint the interpolated surface using simple rectangles for better performance"""
        viewer = self.surface_viewer
        
        # Get concentration colors
        min_color = viewer.concentration_colors['min_color']
        max_color = viewer.concentration_colors['max_color']
        
        height, width = Z_norm.shape
        
        # Paint using simple filled rectangles for performance
        for i in range(height - 1):
            for j in range(width - 1):
                # Get rectangle coordinates
                x1, y1 = int(X[i, j]), int(Y[i, j])
                x2, y2 = int(X[i+1, j+1]), int(Y[i+1, j+1])
                
                if x2 <= x1 or y2 <= y1:
                    continue
                
                # Get average concentration for this cell
                avg_conc = Z_norm[i, j]
                
                # Create color for this concentration level
                color = self.interpolate_concentration_color(avg_conc, min_color, max_color, viewer.concentration_transparency)
                
                if color.alpha() > 0:
                    painter.fillRect(x1, y1, x2-x1, y2-y1, color)
    
    def paint_radial_fallback(self, painter, data_points, values, max_conc):
        """Fallback method using radial gradients"""
        viewer = self.surface_viewer
        min_color = viewer.concentration_colors['min_color']
        max_color = viewer.concentration_colors['max_color']
        
        for (x, y), value in zip(data_points, values):
            if value <= 0:
                continue
                
            normalized_val = min(1.0, value / max_conc) if max_conc > 0 else 0
            color = self.interpolate_concentration_color(normalized_val, min_color, max_color, viewer.concentration_transparency)
            
            if color.alpha() > 0:
                # Create radial gradient
                radius = 30 * normalized_val  # Scale radius with concentration
                gradient = QRadialGradient(x, y, radius)
                gradient.setColorAt(0.0, color)
                
                # Fade to transparent at edges
                transparent_color = QColor(color)
                transparent_color.setAlpha(0)
                gradient.setColorAt(1.0, transparent_color)
                
                painter.fillRect(x - radius, y - radius, 2*radius, 2*radius, QBrush(gradient))
    
    def paint_scatter_concentration(self, painter, header_width, header_height, scroll_x, scroll_y):
        """Paint concentration overlay using scatter points"""
        viewer = self.surface_viewer
        table = self.parent_table
        
        # Get data dimensions
        rows = len(viewer.y_values)
        cols = len(viewer.x_values)
        
        if rows == 0 or cols == 0:
            return
        
        # Get maximum concentration for normalization
        max_conc = np.nanmax(viewer.original_percentages) if not np.all(np.isnan(viewer.original_percentages)) else 1
        if max_conc <= 0:
            return
        
        # Get concentration colors
        min_color = viewer.concentration_colors['min_color']
        max_color = viewer.concentration_colors['max_color']
        
        # For each cell with concentration data
        for i in range(rows):
            for j in range(cols):
                # Get cell geometry
                cell_x = header_width + sum(table.columnWidth(k+1) for k in range(j)) - scroll_x
                cell_y = header_height + sum(table.rowHeight(k+1) for k in range(i)) - scroll_y
                cell_width = table.columnWidth(j+1)
                cell_height = table.rowHeight(i+1)
                
                # Get concentration value
                conc_value = viewer.original_percentages[i, j] if not np.isnan(viewer.original_percentages[i, j]) else 0
                if conc_value <= 0:
                    continue
                
                # Normalize concentration value
                normalized_conc = min(1.0, conc_value / max_conc)
                
                # Apply intensity and gamma correction
                normalized_conc = normalized_conc * viewer.concentration_intensity
                normalized_conc = pow(min(1.0, normalized_conc), viewer.concentration_gamma)
                
                if normalized_conc <= 0:
                    continue
                
                # Calculate number of scatter points based on concentration and density
                base_points = max(1, int(normalized_conc * 20 * viewer.concentration_scatter_density))
                
                # Generate random points within the cell
                import random
                random.seed(hash((i, j)))  # Consistent seed for stable point positions
                
                for _ in range(base_points):
                    # Random position within cell
                    point_x = cell_x + random.random() * cell_width
                    point_y = cell_y + random.random() * cell_height
                    
                    # Skip if point is outside visible area
                    if point_x < 0 or point_y < 0 or point_x > self.width() or point_y > self.height():
                        continue
                    
                    # Create color for this point
                    color = self.interpolate_concentration_color(
                        normalized_conc, min_color, max_color, viewer.concentration_transparency
                    )
                    
                    if color.alpha() > 0:
                        # Draw point
                        painter.setPen(QPen(color, 0))
                        painter.setBrush(QBrush(color))
                        
                        # Draw circle with size based on setting
                        radius = viewer.concentration_scatter_size / 2
                        painter.drawEllipse(
                            QPoint(int(point_x), int(point_y)), 
                            int(radius), int(radius)
                        )
    
    def interpolate_concentration_color(self, normalized_value, min_color, max_color, transparency):
        """Interpolate concentration color"""
        # Apply transparency based on slider setting
        alpha = int(normalized_value * 255 * transparency)
        
        # Interpolate RGB values
        r = int(min_color.red() + (max_color.red() - min_color.red()) * normalized_value)
        g = int(min_color.green() + (max_color.green() - min_color.green()) * normalized_value)
        b = int(min_color.blue() + (max_color.blue() - min_color.blue()) * normalized_value)
        
        return QColor(r, g, b, alpha)

def seconds_to_hms(seconds):
    """Convert seconds to HH:MM:SS.mmm format"""
    if seconds < 0:
        return "00:00:00.000"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

class SurfaceTableViewer(QWidget):
    def __init__(self, surface_data, x_values, y_values, z_values, percentages=None, total_points_inside=0, total_points_all=0, comparison_percentages=None, comparison_name="Comparison", z_values_for_comparison=None):
        super().__init__()
        self.setWindowTitle('Surface Table Viewer - Enhanced Dynamic View')
        
        # Dynamic sizing based on data dimensions and screen size
        app = QApplication.instance()
        screen = app.primaryScreen().geometry()
        
        # Calculate optimal size based on data dimensions
        min_cell_width = 60
        min_cell_height = 25
        header_height = 120  # Space for controls
        
        optimal_width = min(screen.width() * 0.95, len(x_values) * min_cell_width + 200)
        optimal_height = min(screen.height() * 0.9, len(y_values) * min_cell_height + header_height + 100)
        
        self.resize(int(optimal_width), int(optimal_height))
        
        # Center window on screen
        x = (screen.width() - optimal_width) // 2
        y = (screen.height() - optimal_height) // 2
        self.move(int(x), int(y))
        
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
        
        # Z values for comparison calculations (separate from concentration percentages)
        self.z_values_for_comparison = z_values_for_comparison if z_values_for_comparison is not None else z_values
        
        # Concentration overlay settings - default to enabled for better visualization
        self.concentration_overlay_enabled = True
        self.concentration_transparency = 0.5  # Default 50% transparency
        self.concentration_blur_enabled = True
        
        # Enhanced concentration overlay settings
        self.concentration_mode = 'gradient'  # 'gradient' or 'scatter'
        self.concentration_scatter_size = 5.0  # Scatter point size
        self.concentration_scatter_density = 1.0  # Scatter point density
        self.concentration_intensity = 1.0  # Overall intensity multiplier
        self.concentration_gamma = 1.0  # Gamma correction for non-linear scaling
        self.concentration_show_metrics = True  # Show concentration metrics
        
        # Store original percentages for concentration overlay
        self.original_percentages = percentages.copy() if percentages is not None else None
        
        # Overlay widget for smooth concentration visualization
        self.concentration_overlay_widget = None
        
        # Color settings - separate for normal and comparison modes
        self.load_color_settings()  # Load saved color settings
        self.current_mode = 'normal'  # Track current mode
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
        
        # Medium color button (only visible in comparison mode)
        self.medium_color_btn = QPushButton("Medium Color")
        self.medium_color_btn.setStyleSheet(f"background-color: {self.medium_color.name()}")
        self.medium_color_btn.clicked.connect(self.choose_medium_color)
        self.medium_color_btn.setVisible(False)  # Hidden by default
        color_row1.addWidget(self.medium_color_btn)
        
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

        # Add concentration overlay controls
        self.create_concentration_controls(main_layout)

        # Create table widget with enhanced features
        self.table = QTableWidget()
        self.table.setRowCount(len(y_values) + 1)  # +1 for header
        self.table.setColumnCount(len(x_values) + 1)  # +1 for header
        
        # Enable sorting and other features
        self.table.setSortingEnabled(False)  # Disable sorting to maintain spatial layout
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        
        # Dynamic column sizing with better support for high DPI screens
        app = QApplication.instance()
        screen = app.primaryScreen()
        dpi_scale = screen.logicalDotsPerInch() / 96.0  # Standard DPI is 96
        
        # Minimum sizes adjusted for DPI and to accommodate two lines of text
        min_cell_width = max(60, int(60 * dpi_scale))
        min_cell_height = max(35, int(35 * dpi_scale))  # Increased for two lines
        max_cell_width = max(120, int(120 * dpi_scale))
        max_cell_height = max(60, int(60 * dpi_scale))
        
        optimal_cell_width = max(min_cell_width, min(max_cell_width, (self.width() - 150) // len(x_values)))
        optimal_cell_height = max(min_cell_height, min(max_cell_height, (self.height() - 200) // len(y_values)))
        
        # Set headers with better formatting
        header_font = QFont("Arial", 9, QFont.Bold)
        corner_item = QTableWidgetItem('RPM \\ ETASP')
        corner_item.setFont(header_font)
        corner_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(0, 0, corner_item)
        
        # RPM headers (horizontal)
        for i, x_val in enumerate(x_values):
            header_item = QTableWidgetItem(f'{x_val:.0f}')
            header_item.setFont(header_font)
            header_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(0, i + 1, header_item)
            self.table.setColumnWidth(i + 1, optimal_cell_width)
        
        # ETASP headers (vertical)  
        for i, y_val in enumerate(y_values):
            header_item = QTableWidgetItem(f'{y_val:.3f}')
            header_item.setFont(header_font)
            header_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i + 1, 0, header_item)
            self.table.setRowHeight(i + 1, optimal_cell_height)
        
        # Set header row and column widths
        self.table.setColumnWidth(0, 80)  # ETASP column
        self.table.setRowHeight(0, 30)    # Header row
        
        # Enable horizontal scroll bar when needed
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Populate table
        self.populate_table()
        
        main_layout.addWidget(self.table)
        self.setLayout(main_layout)
        
        # Add resize event handler for dynamic adjustment
        self.table.resizeEvent = self.on_table_resize
        
        # Enable custom painting for concentration overlay and fix rendering issues
        self.table.setMouseTracking(True)
        
        # Set viewport update mode to prevent cell disappearing during resize/scroll
        from PyQt5.QtWidgets import QAbstractItemView
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerItem)
        
        # Create concentration overlay widget
        self.concentration_overlay_widget = ConcentrationOverlay(self.table, self)
        self.concentration_overlay_widget.show()
        
        # Initialize color mode based on whether comparison data is shown initially
        if self.show_comparison and self.show_percentage_diff:
            self.apply_color_mode('comparison')
        else:
            self.apply_color_mode('normal')
            
        # Initialize concentration metrics
        if hasattr(self, 'update_concentration_metrics'):
            self.update_concentration_metrics()
    
    def load_color_settings(self):
        """Load color settings from configuration file"""
        # Default color settings for normal mode
        self.normal_colors = {
            'min_color': QColor(255, 255, 255),  # White for minimum
            'max_color': QColor(0, 100, 255),    # Blue for maximum
            'color_bias': 1.0
        }
        
        # Default color settings for comparison mode
        self.comparison_colors = {
            'min_color': QColor(255, 0, 0),      # Red for minimum
            'max_color': QColor(0, 255, 0),      # Green for maximum
            'medium_color': QColor(255, 255, 255), # White for medium
            'color_bias': 1.0
        }
        
        # Default concentration overlay colors
        self.concentration_colors = {
            'min_color': QColor(255, 255, 255, 0),    # Transparent for minimum
            'max_color': QColor(0, 100, 255, 200),    # Semi-transparent blue for maximum
        }
        
        # Enhanced concentration overlay defaults
        self.concentration_mode = 'gradient'  # 'gradient' or 'scatter'
        self.concentration_scatter_size = 5.0
        self.concentration_scatter_density = 1.0
        self.concentration_intensity = 1.0
        self.concentration_gamma = 1.0
        self.concentration_show_metrics = True
        
        # Try to load from config file
        try:
            if os.path.exists('fuel_config.json'):
                with open('fuel_config.json', 'r') as f:
                    config = json.load(f)
                
                # Load normal mode colors
                if 'surface_viewer_normal_colors' in config:
                    normal_config = config['surface_viewer_normal_colors']
                    if 'min_color' in normal_config:
                        self.normal_colors['min_color'] = QColor(normal_config['min_color'])
                    if 'max_color' in normal_config:
                        self.normal_colors['max_color'] = QColor(normal_config['max_color'])
                    if 'color_bias' in normal_config:
                        self.normal_colors['color_bias'] = normal_config['color_bias']
                
                # Load comparison mode colors
                if 'surface_viewer_comparison_colors' in config:
                    comp_config = config['surface_viewer_comparison_colors']
                    if 'min_color' in comp_config:
                        self.comparison_colors['min_color'] = QColor(comp_config['min_color'])
                    if 'max_color' in comp_config:
                        self.comparison_colors['max_color'] = QColor(comp_config['max_color'])
                    if 'medium_color' in comp_config:
                        self.comparison_colors['medium_color'] = QColor(comp_config['medium_color'])
                    if 'color_bias' in comp_config:
                        self.comparison_colors['color_bias'] = comp_config['color_bias']
                
                # Load concentration overlay settings
                if 'concentration_overlay' in config:
                    conc_config = config['concentration_overlay']
                    if 'enabled' in conc_config:
                        self.concentration_overlay_enabled = conc_config['enabled']
                    if 'transparency' in conc_config:
                        self.concentration_transparency = conc_config['transparency']
                    if 'blur_enabled' in conc_config:
                        self.concentration_blur_enabled = conc_config['blur_enabled']
                    if 'min_color' in conc_config:
                        self.concentration_colors['min_color'] = QColor(conc_config['min_color'])
                    if 'max_color' in conc_config:
                        self.concentration_colors['max_color'] = QColor(conc_config['max_color'])
                    
                    # Load enhanced concentration settings
                    if 'mode' in conc_config:
                        self.concentration_mode = conc_config['mode']
                    if 'scatter_size' in conc_config:
                        self.concentration_scatter_size = conc_config['scatter_size']
                    if 'scatter_density' in conc_config:
                        self.concentration_scatter_density = conc_config['scatter_density']
                    if 'intensity' in conc_config:
                        self.concentration_intensity = conc_config['intensity']
                    if 'gamma' in conc_config:
                        self.concentration_gamma = conc_config['gamma']
                    if 'show_metrics' in conc_config:
                        self.concentration_show_metrics = conc_config['show_metrics']
        except Exception as e:
            print(f"Warning: Could not load color settings: {e}")
        
        # Set initial colors (normal mode)
        self.apply_color_mode('normal')
    
    def apply_color_mode(self, mode):
        """Apply color settings for the specified mode"""
        self.current_mode = mode
        
        if mode == 'normal':
            self.min_color = self.normal_colors['min_color']
            self.max_color = self.normal_colors['max_color']
            self.color_bias = self.normal_colors['color_bias']
            # Medium color not used in normal mode, but set to white as default
            self.medium_color = QColor(255, 255, 255)
        else:  # comparison mode
            self.min_color = self.comparison_colors['min_color']
            self.max_color = self.comparison_colors['max_color']
            self.medium_color = self.comparison_colors['medium_color']
            self.color_bias = self.comparison_colors['color_bias']
        
        # Update UI elements
        if hasattr(self, 'min_color_btn'):
            self.min_color_btn.setStyleSheet(f"background-color: {self.min_color.name()}")
        if hasattr(self, 'max_color_btn'):
            self.max_color_btn.setStyleSheet(f"background-color: {self.max_color.name()}")
        if hasattr(self, 'medium_color_btn'):
            self.medium_color_btn.setStyleSheet(f"background-color: {self.medium_color.name()}")
        
        # Update bias slider
        if hasattr(self, 'bias_slider'):
            if self.color_bias <= 1.0:
                slider_val = int(self.color_bias * 10)
            elif self.color_bias <= 2.0:
                slider_val = int(10 + (self.color_bias - 1.0) * 10)
            else:
                slider_val = int(20 + (self.color_bias - 2.0) * 10)
            self.bias_slider.setValue(slider_val)
            self.update_bias_label()
        
        # Update table and legend
        if hasattr(self, 'table'):
            self.populate_table()
            self.update_legend()
    
    def save_color_settings(self):
        """Save current color settings to configuration file"""
        try:
            # Load existing config
            config = {}
            if os.path.exists('fuel_config.json'):
                with open('fuel_config.json', 'r') as f:
                    config = json.load(f)
            
            # Save current mode colors
            if self.current_mode == 'normal':
                config['surface_viewer_normal_colors'] = {
                    'min_color': self.min_color.name(),
                    'max_color': self.max_color.name(),
                    'color_bias': self.color_bias
                }
            else:  # comparison mode
                config['surface_viewer_comparison_colors'] = {
                    'min_color': self.min_color.name(),
                    'max_color': self.max_color.name(),
                    'medium_color': self.medium_color.name(),
                    'color_bias': self.color_bias
                }
            
            # Save concentration overlay settings
            config['concentration_overlay'] = {
                'enabled': self.concentration_overlay_enabled,
                'transparency': self.concentration_transparency,
                'blur_enabled': self.concentration_blur_enabled,
                'min_color': self.concentration_colors['min_color'].name(),
                'max_color': self.concentration_colors['max_color'].name(),
                'mode': self.concentration_mode,
                'scatter_size': self.concentration_scatter_size,
                'scatter_density': self.concentration_scatter_density,
                'intensity': self.concentration_intensity,
                'gamma': self.concentration_gamma,
                'show_metrics': self.concentration_show_metrics
            }
            
            # Write config back
            with open('fuel_config.json', 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save color settings: {e}")
    
    def create_concentration_controls(self, main_layout):
        """Create enhanced concentration overlay controls"""
        conc_group = QGroupBox("Concentration Overlay")
        conc_main_layout = QVBoxLayout()
        
        # First row: Enable/disable and mode selection
        conc_row1 = QHBoxLayout()
        
        self.concentration_enabled_cb = QCheckBox("Enable Concentration Overlay")
        self.concentration_enabled_cb.setChecked(self.concentration_overlay_enabled)
        self.concentration_enabled_cb.stateChanged.connect(self.toggle_concentration_overlay)
        conc_row1.addWidget(self.concentration_enabled_cb)
        
        # Mode selection
        conc_row1.addWidget(QLabel("Mode:"))
        from PyQt5.QtWidgets import QComboBox
        self.concentration_mode_combo = QComboBox()
        self.concentration_mode_combo.addItems(["gradient", "scatter"])
        self.concentration_mode_combo.setCurrentText(self.concentration_mode)
        self.concentration_mode_combo.currentTextChanged.connect(self.update_concentration_mode)
        conc_row1.addWidget(self.concentration_mode_combo)
        
        # Show metrics checkbox
        self.concentration_metrics_cb = QCheckBox("Show Metrics")
        self.concentration_metrics_cb.setChecked(self.concentration_show_metrics)
        self.concentration_metrics_cb.stateChanged.connect(self.toggle_concentration_metrics)
        conc_row1.addWidget(self.concentration_metrics_cb)
        
        conc_row1.addStretch()
        conc_main_layout.addLayout(conc_row1)
        
        # Second row: Basic controls
        conc_row2 = QHBoxLayout()
        
        # Transparency slider
        conc_row2.addWidget(QLabel("Transparency:"))
        self.concentration_transparency_slider = QSlider(Qt.Horizontal)
        self.concentration_transparency_slider.setMinimum(0)
        self.concentration_transparency_slider.setMaximum(100)
        self.concentration_transparency_slider.setValue(int(self.concentration_transparency * 100))
        self.concentration_transparency_slider.valueChanged.connect(self.update_concentration_transparency)
        conc_row2.addWidget(self.concentration_transparency_slider)
        
        self.concentration_transparency_label = QLabel(f"{int(self.concentration_transparency * 100)}%")
        conc_row2.addWidget(self.concentration_transparency_label)
        
        # Intensity slider
        conc_row2.addWidget(QLabel("Intensity:"))
        self.concentration_intensity_slider = QSlider(Qt.Horizontal)
        self.concentration_intensity_slider.setMinimum(10)
        self.concentration_intensity_slider.setMaximum(300)
        self.concentration_intensity_slider.setValue(int(self.concentration_intensity * 100))
        self.concentration_intensity_slider.valueChanged.connect(self.update_concentration_intensity)
        conc_row2.addWidget(self.concentration_intensity_slider)
        
        self.concentration_intensity_label = QLabel(f"{self.concentration_intensity:.1f}x")
        conc_row2.addWidget(self.concentration_intensity_label)
        
        conc_main_layout.addLayout(conc_row2)
        
        # Third row: Advanced controls
        conc_row3 = QHBoxLayout()
        
        # Gamma correction slider
        conc_row3.addWidget(QLabel("Gamma:"))
        self.concentration_gamma_slider = QSlider(Qt.Horizontal)
        self.concentration_gamma_slider.setMinimum(10)
        self.concentration_gamma_slider.setMaximum(300)
        self.concentration_gamma_slider.setValue(int(self.concentration_gamma * 100))
        self.concentration_gamma_slider.valueChanged.connect(self.update_concentration_gamma)
        conc_row3.addWidget(self.concentration_gamma_slider)
        
        self.concentration_gamma_label = QLabel(f"{self.concentration_gamma:.1f}")
        conc_row3.addWidget(self.concentration_gamma_label)
        
        # Blur toggle (for gradient mode)
        self.concentration_blur_cb = QCheckBox("Enable Blur")
        self.concentration_blur_cb.setChecked(self.concentration_blur_enabled)
        self.concentration_blur_cb.stateChanged.connect(self.toggle_concentration_blur)
        conc_row3.addWidget(self.concentration_blur_cb)
        
        conc_main_layout.addLayout(conc_row3)
        
        # Fourth row: Scatter-specific controls
        self.scatter_controls_row = QHBoxLayout()
        
        # Scatter size slider
        self.scatter_controls_row.addWidget(QLabel("Point Size:"))
        self.concentration_scatter_size_slider = QSlider(Qt.Horizontal)
        self.concentration_scatter_size_slider.setMinimum(1)
        self.concentration_scatter_size_slider.setMaximum(20)
        self.concentration_scatter_size_slider.setValue(int(self.concentration_scatter_size))
        self.concentration_scatter_size_slider.valueChanged.connect(self.update_concentration_scatter_size)
        self.scatter_controls_row.addWidget(self.concentration_scatter_size_slider)
        
        self.concentration_scatter_size_label = QLabel(f"{self.concentration_scatter_size:.0f}px")
        self.scatter_controls_row.addWidget(self.concentration_scatter_size_label)
        
        # Scatter density slider
        self.scatter_controls_row.addWidget(QLabel("Density:"))
        self.concentration_scatter_density_slider = QSlider(Qt.Horizontal)
        self.concentration_scatter_density_slider.setMinimum(10)
        self.concentration_scatter_density_slider.setMaximum(500)
        self.concentration_scatter_density_slider.setValue(int(self.concentration_scatter_density * 100))
        self.concentration_scatter_density_slider.valueChanged.connect(self.update_concentration_scatter_density)
        self.scatter_controls_row.addWidget(self.concentration_scatter_density_slider)
        
        self.concentration_scatter_density_label = QLabel(f"{self.concentration_scatter_density:.1f}x")
        self.scatter_controls_row.addWidget(self.concentration_scatter_density_label)
        
        self.scatter_controls_row.addStretch()
        
        # Create scatter controls widget and hide if in gradient mode
        self.scatter_controls_widget = QWidget()
        self.scatter_controls_widget.setLayout(self.scatter_controls_row)
        conc_main_layout.addWidget(self.scatter_controls_widget)
        
        # Fifth row: Color selection and metrics
        conc_row5 = QHBoxLayout()
        
        # Color selection buttons
        self.conc_min_color_btn = QPushButton("Min Color")
        self.conc_min_color_btn.setStyleSheet(f"background-color: {self.concentration_colors['min_color'].name()}")
        self.conc_min_color_btn.clicked.connect(self.choose_concentration_min_color)
        conc_row5.addWidget(self.conc_min_color_btn)
        
        self.conc_max_color_btn = QPushButton("Max Color")
        self.conc_max_color_btn.setStyleSheet(f"background-color: {self.concentration_colors['max_color'].name()}")
        self.conc_max_color_btn.clicked.connect(self.choose_concentration_max_color)
        conc_row5.addWidget(self.conc_max_color_btn)
        
        # Metrics display
        self.concentration_metrics_label = QLabel("Metrics: Ready")
        conc_row5.addWidget(self.concentration_metrics_label)
        
        conc_row5.addStretch()
        conc_main_layout.addLayout(conc_row5)
        
        conc_group.setLayout(conc_main_layout)
        main_layout.addWidget(conc_group)
        
        # Update visibility based on current mode
        self.update_concentration_controls_visibility()
    
    def toggle_concentration_overlay(self):
        """Toggle concentration overlay on/off"""
        self.concentration_overlay_enabled = self.concentration_enabled_cb.isChecked()
        if self.concentration_overlay_widget:
            if self.concentration_overlay_enabled:
                self.concentration_overlay_widget.show()
            else:
                self.concentration_overlay_widget.hide()
            self.concentration_overlay_widget.update()
        self.save_color_settings()
    
    def update_concentration_transparency(self):
        """Update concentration transparency from slider"""
        self.concentration_transparency = self.concentration_transparency_slider.value() / 100.0
        self.concentration_transparency_label.setText(f"{int(self.concentration_transparency * 100)}%")
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        self.update_concentration_metrics()
        self.save_color_settings()
    
    def toggle_concentration_blur(self):
        """Toggle concentration blur on/off"""
        self.concentration_blur_enabled = self.concentration_blur_cb.isChecked()
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        self.save_color_settings()
    
    def choose_concentration_min_color(self):
        """Choose concentration minimum color"""
        color = QColorDialog.getColor(self.concentration_colors['min_color'], self)
        if color.isValid():
            self.concentration_colors['min_color'] = color
            self.conc_min_color_btn.setStyleSheet(f"background-color: {color.name()}")
            if self.concentration_overlay_widget:
                self.concentration_overlay_widget.update()
            self.update_concentration_metrics()
            self.save_color_settings()
    
    def choose_concentration_max_color(self):
        """Choose concentration maximum color"""
        color = QColorDialog.getColor(self.concentration_colors['max_color'], self)
        if color.isValid():
            self.concentration_colors['max_color'] = color
            self.conc_max_color_btn.setStyleSheet(f"background-color: {color.name()}")
            if self.concentration_overlay_widget:
                self.concentration_overlay_widget.update()
            self.update_concentration_metrics()
            self.save_color_settings()
    
    def update_concentration_mode(self):
        """Update concentration overlay mode"""
        self.concentration_mode = self.concentration_mode_combo.currentText()
        self.update_concentration_controls_visibility()
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        self.save_color_settings()
    
    def update_concentration_controls_visibility(self):
        """Update visibility of mode-specific controls"""
        is_scatter = self.concentration_mode == 'scatter'
        self.scatter_controls_widget.setVisible(is_scatter)
        self.concentration_blur_cb.setVisible(not is_scatter)
    
    def toggle_concentration_metrics(self):
        """Toggle concentration metrics display"""
        self.concentration_show_metrics = self.concentration_metrics_cb.isChecked()
        self.update_concentration_metrics()
        self.save_color_settings()
    
    def update_concentration_intensity(self):
        """Update concentration intensity from slider"""
        self.concentration_intensity = self.concentration_intensity_slider.value() / 100.0
        self.concentration_intensity_label.setText(f"{self.concentration_intensity:.1f}x")
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        self.update_concentration_metrics()
        self.save_color_settings()
    
    def update_concentration_gamma(self):
        """Update concentration gamma correction from slider"""
        self.concentration_gamma = self.concentration_gamma_slider.value() / 100.0
        self.concentration_gamma_label.setText(f"{self.concentration_gamma:.1f}")
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        self.save_color_settings()
    
    def update_concentration_scatter_size(self):
        """Update scatter point size from slider"""
        self.concentration_scatter_size = float(self.concentration_scatter_size_slider.value())
        self.concentration_scatter_size_label.setText(f"{self.concentration_scatter_size:.0f}px")
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        self.save_color_settings()
    
    def update_concentration_scatter_density(self):
        """Update scatter point density from slider"""
        self.concentration_scatter_density = self.concentration_scatter_density_slider.value() / 100.0
        self.concentration_scatter_density_label.setText(f"{self.concentration_scatter_density:.1f}x")
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        self.save_color_settings()
    
    def update_concentration_metrics(self):
        """Update concentration metrics display"""
        if not self.concentration_show_metrics or self.original_percentages is None:
            self.concentration_metrics_label.setText("Metrics: Disabled")
            return
        
        try:
            # Calculate concentration statistics
            valid_data = self.original_percentages[~np.isnan(self.original_percentages)]
            if len(valid_data) == 0:
                self.concentration_metrics_label.setText("Metrics: No valid data")
                return
            
            max_concentration = np.max(valid_data)
            mean_concentration = np.mean(valid_data)
            total_time = np.sum(valid_data)
            
            # Convert to time units (assuming percentages represent time percentages)
            # Estimate based on reasonable operating time ranges
            if total_time > 0:
                # Assuming a typical test duration of 1-8 hours
                estimated_max_time_hours = max_concentration / 100.0 * 8  # Rough estimate
                estimated_total_hours = total_time / 100.0 * 8
                
                self.concentration_metrics_label.setText(
                    f"Max: {max_concentration:.1f}% (~{estimated_max_time_hours:.1f}h) | "
                    f"Avg: {mean_concentration:.1f}% | "
                    f"Total: {total_time:.1f}% (~{estimated_total_hours:.1f}h)"
                )
            else:
                self.concentration_metrics_label.setText("Metrics: No concentration data")
                
        except Exception as e:
            self.concentration_metrics_label.setText(f"Metrics: Error - {str(e)[:20]}...")
    
    def get_concentration_overlay_color(self, value, max_value):
        """Get concentration overlay color based on value"""
        if not self.concentration_overlay_enabled or max_value == 0:
            return QColor(255, 255, 255, 0)  # Fully transparent
        
        # Normalize value to 0-1 range
        normalized = min(1.0, max(0.0, value / max_value))
        
        # Interpolate between min and max colors
        min_color = self.concentration_colors['min_color']
        max_color = self.concentration_colors['max_color']
        
        # Apply transparency based on slider setting
        alpha = int(normalized * 255 * self.concentration_transparency)
        
        # Apply blur effect by smoothing the value (simple smoothing)
        if self.concentration_blur_enabled:
            # Simple smoothing: reduce sharp transitions
            normalized = normalized ** 0.7  # Soften the gradient
        
        # Interpolate RGB values
        r = int(min_color.red() + (max_color.red() - min_color.red()) * normalized)
        g = int(min_color.green() + (max_color.green() - min_color.green()) * normalized)
        b = int(min_color.blue() + (max_color.blue() - min_color.blue()) * normalized)
        
        return QColor(r, g, b, alpha)
    
    def update_bias_label(self):
        """Update the bias label text"""
        if hasattr(self, 'bias_value_label'):
            if self.color_bias <= 1.0:
                bias_text = f"{self.color_bias:.1f} (Low bias)"
            elif self.color_bias == 1.0:
                bias_text = f"{self.color_bias:.1f} (Linear)"
            elif self.color_bias <= 2.0:
                bias_text = f"{self.color_bias:.1f}"
            else:
                bias_text = f"{self.color_bias:.1f} (High bias)"
            self.bias_value_label.setText(bias_text)
    
    def choose_min_color(self):
        color = QColorDialog.getColor(self.min_color, self)
        if color.isValid():
            self.min_color = color
            self.min_color_btn.setStyleSheet(f"background-color: {color.name()}")
            # Update the appropriate color set
            if self.current_mode == 'normal':
                self.normal_colors['min_color'] = color
            else:
                self.comparison_colors['min_color'] = color
            self.save_color_settings()
            self.update_legend()
            if hasattr(self, 'concentration_canvas'):
                self.update_concentration_plot()
    
    def choose_max_color(self):
        color = QColorDialog.getColor(self.max_color, self)
        if color.isValid():
            self.max_color = color
            self.max_color_btn.setStyleSheet(f"background-color: {color.name()}")
            # Update the appropriate color set
            if self.current_mode == 'normal':
                self.normal_colors['max_color'] = color
            else:
                self.comparison_colors['max_color'] = color
            self.save_color_settings()
            self.update_legend()
            if hasattr(self, 'concentration_canvas'):
                self.update_concentration_plot()
    
    def choose_medium_color(self):
        color = QColorDialog.getColor(self.medium_color, self)
        if color.isValid():
            self.medium_color = color
            self.medium_color_btn.setStyleSheet(f"background-color: {color.name()}")
            # Medium color is only used in comparison mode
            self.comparison_colors['medium_color'] = color
            self.save_color_settings()
            self.update_legend()
            if hasattr(self, 'concentration_canvas'):
                self.update_concentration_plot()
    
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
        
        # Update the appropriate color set bias
        if self.current_mode == 'normal':
            self.normal_colors['color_bias'] = self.color_bias
        else:
            self.comparison_colors['color_bias'] = self.color_bias
        self.save_color_settings()
        self.update_legend()
        if hasattr(self, 'concentration_canvas'):
            self.update_concentration_plot()
    
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
        if hasattr(self, 'concentration_canvas'):
            self.update_concentration_plot()
    
    def update_manual_range(self):
        """Update manual min/max values"""
        self.manual_min = self.manual_min_spin.value()
        self.manual_max = self.manual_max_spin.value()
        self.update_legend()
        if hasattr(self, 'concentration_canvas'):
            self.update_concentration_plot()
    
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
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        if hasattr(self, 'concentration_canvas'):
            self.update_concentration_plot()
    
    def toggle_percentage_diff(self):
        """Toggle between showing main data and difference"""
        self.show_percentage_diff = self.show_diff_cb.isChecked()
        # Enable/disable the difference type toggle based on comparison state
        if hasattr(self, 'diff_type_cb'):
            self.diff_type_cb.setEnabled(self.show_percentage_diff)
        # Show/hide medium color button based on comparison mode
        if hasattr(self, 'medium_color_btn'):
            self.medium_color_btn.setVisible(self.show_percentage_diff)
        
        # Switch color modes based on comparison state
        if self.show_percentage_diff:
            self.apply_color_mode('comparison')
        else:
            self.apply_color_mode('normal')
        
        self.populate_table()
        self.update_legend()
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        if hasattr(self, 'concentration_canvas'):
            self.update_concentration_plot()
    
    def toggle_diff_type(self):
        """Toggle between percentage and absolute difference"""
        self.use_absolute_diff = self.diff_type_cb.isChecked()
        self.populate_table()
        self.update_legend()
        if self.concentration_overlay_widget:
            self.concentration_overlay_widget.update()
        if hasattr(self, 'concentration_canvas'):
            self.update_concentration_plot()
    
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
        """Get color for percentage difference using min/medium/max color scheme"""
        if max_abs_difference == 0:
            return self.medium_color  # Medium color for no difference
        
        # Clamp difference to range
        clamped_diff = max(-max_abs_difference, min(max_abs_difference, difference))
        
        # Calculate ratio with bias
        ratio = abs(clamped_diff) / max_abs_difference
        ratio = ratio ** self.color_bias
        
        if clamped_diff < 0:
            # Negative difference: interpolate between medium and min color
            r = int(self.medium_color.red() + ratio * (self.min_color.red() - self.medium_color.red()))
            g = int(self.medium_color.green() + ratio * (self.min_color.green() - self.medium_color.green()))
            b = int(self.medium_color.blue() + ratio * (self.min_color.blue() - self.medium_color.blue()))
        elif clamped_diff > 0:
            # Positive difference: interpolate between medium and max color
            r = int(self.medium_color.red() + ratio * (self.max_color.red() - self.medium_color.red()))
            g = int(self.medium_color.green() + ratio * (self.max_color.green() - self.medium_color.green()))
            b = int(self.medium_color.blue() + ratio * (self.max_color.blue() - self.medium_color.blue()))
        else:
            # Zero difference: medium color
            r = self.medium_color.red()
            g = self.medium_color.green()
            b = self.medium_color.blue()
        
        return QColor(r, g, b)
    
    def populate_table(self):
        """Populate table with Z values and percentages"""
        display_data = None
        max_percentage = 0
        
        if self.show_comparison and self.show_percentage_diff:
            # Show difference (percentage or absolute)
            if self.comparison_percentages is not None:
                # Check if we have Z values for comparison (surface table mode)
                if self.z_values_for_comparison is not None:
                    # We're comparing surface table Z values
                    if self.use_absolute_diff:
                        # Absolute difference = CSV - vehicle_log (using Z values)
                        display_data = self.comparison_percentages - self.z_values_for_comparison
                    else:
                        # Percentage difference = ((CSV - vehicle_log) / vehicle_log) * 100 (using Z values)
                        with np.errstate(divide='ignore', invalid='ignore'):
                            display_data = np.where(
                                (self.z_values_for_comparison != 0) & ~np.isnan(self.z_values_for_comparison),
                                ((self.comparison_percentages - self.z_values_for_comparison) / self.z_values_for_comparison) * 100,
                                0
                            )
                    # For surface table differences, use a reasonable range
                    max_abs_diff = np.nanmax(np.abs(display_data[np.isfinite(display_data)])) if np.any(np.isfinite(display_data)) else 10
                    max_percentage = max_abs_diff
                elif self.percentages is not None:
                    # Regular percentage-based comparison (fallback for backwards compatibility)
                    if self.use_absolute_diff:
                        # Absolute difference for percentages = CSV - vehicle_log
                        display_data = self.comparison_percentages - self.percentages
                    else:
                        # Percentage difference = ((CSV - vehicle_log) / vehicle_log) * 100
                        with np.errstate(divide='ignore', invalid='ignore'):
                            display_data = np.where(
                                (self.percentages != 0) & ~np.isnan(self.percentages),
                                ((self.comparison_percentages - self.percentages) / self.percentages) * 100,
                                0
                            )
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
        
        # Disable updates while populating to prevent flickering
        self.table.setUpdatesEnabled(False)
        
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
                
                # Enhanced text formatting with DPI awareness
                app = QApplication.instance()
                screen = app.primaryScreen()
                dpi_scale = screen.logicalDotsPerInch() / 96.0
                font_size = max(7, int(8 * dpi_scale))  # Scale font size with DPI
                
                font = QFont("Arial", font_size)
                if not np.isnan(z_val):
                    font.setBold(True)
                item.setFont(font)
                
                # Add tooltip with detailed information
                if display_data is not None:
                    data_val = display_data[i, j]
                    tooltip = f"RPM: {x_val:.0f}\nETASP: {y_val:.3f}\nZ Value: {z_val:.3f}"
                    if self.show_comparison and self.show_percentage_diff:
                        if self.use_absolute_diff:
                            tooltip += f"\nDifference: {data_val:+.3f}"
                        else:
                            tooltip += f"\nDifference: {data_val:+.2f}%"
                    else:
                        tooltip += f"\nPercentage: {data_val:.2f}%"
                    item.setToolTip(tooltip)
                
                # Set color based on data
                if np.isnan(z_val):
                    # N/A cells should always be white
                    item.setBackground(QColor(255, 255, 255))
                    item.setForeground(QColor('black'))
                else:
                    # Get base color 
                    if self.show_comparison and self.show_percentage_diff:
                        # Use different color scheme for differences (no concentration overlay in comparison mode)
                        color = self.get_difference_color(data_val, max_percentage)
                    elif display_data is not None:
                        # Use display data for coloring (percentages, comparison without diff, etc.)
                        color = self.get_interpolated_color(display_data[i, j], max_percentage)
                    else:
                        # Normal mode - use z_values for coloring
                        color = self.get_interpolated_color(z_val, np.nanmax(self.z_values))
                        
                    # Note: Concentration overlay is now handled by the overlay widget
                    
                    item.setBackground(color)
                    
                    # Set text color for better contrast
                    if color.lightness() < 128:
                        item.setForeground(QColor('white'))
                    else:
                        item.setForeground(QColor('black'))
                
                self.table.setItem(i + 1, j + 1, item)
        
        # Re-enable updates and force refresh
        self.table.setUpdatesEnabled(True)
        self.table.viewport().update()
        
        # Update concentration metrics
        if hasattr(self, 'update_concentration_metrics'):
            self.update_concentration_metrics()
    
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
                        # Absolute difference = CSV - vehicle_log
                        display_data = (self.comparison_percentages - self.percentages)/2
                    else:
                        # Percentage difference = ((CSV - vehicle_log) / vehicle_log) * 100
                        with np.errstate(divide='ignore', invalid='ignore'):
                            display_data = np.where(
                                (self.percentages != 0) & ~np.isnan(self.percentages),
                                ((self.comparison_percentages - self.percentages) / self.percentages) * 100,
                                0
                            )
                    max_abs_diff = np.nanmax(np.abs(display_data[np.isfinite(display_data)])) if np.any(np.isfinite(display_data)) else 10.0
                else:
                    # Regular percentage-based comparison
                    if self.use_absolute_diff:
                        # Absolute difference = CSV - vehicle_log
                        display_data = self.comparison_percentages - self.percentages
                    else:
                        # Percentage difference = ((CSV - vehicle_log) / vehicle_log) * 100
                        with np.errstate(divide='ignore', invalid='ignore'):
                            display_data = np.where(
                                (self.percentages != 0) & ~np.isnan(self.percentages),
                                ((self.comparison_percentages - self.percentages) / self.percentages) * 100,
                                0
                            )
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
    
    def on_table_resize(self, event):
        """Handle table resize for dynamic column adjustment"""
        try:
            # Call the original resize event first
            QTableWidget.resizeEvent(self.table, event)
            
            # Update overlay widget size
            if self.concentration_overlay_widget:
                self.concentration_overlay_widget.setFixedSize(self.table.viewport().size())
                self.concentration_overlay_widget.update()
            
            if hasattr(self, 'x_values') and len(self.x_values) > 0:
                # Get DPI scaling factor safely
                app = QApplication.instance()
                if app and app.primaryScreen():
                    screen = app.primaryScreen()
                    dpi_scale = screen.logicalDotsPerInch() / 96.0
                else:
                    dpi_scale = 1.0
                
                # Adjust min/max widths for DPI
                min_width = max(60, int(60 * dpi_scale))
                max_width = max(120, int(120 * dpi_scale))
                
                # Calculate available width more accurately
                total_width = self.table.width()
                etasp_column_width = self.table.columnWidth(0)
                scrollbar_width = self.table.verticalScrollBar().width() if self.table.verticalScrollBar().isVisible() else 0
                available_width = total_width - etasp_column_width - scrollbar_width - 20  # Extra margin
                
                if available_width > 0:
                    optimal_cell_width = max(min_width, min(max_width, available_width // len(self.x_values)))
                    
                    # Batch update column widths to prevent flickering
                    self.table.setUpdatesEnabled(False)
                    for i in range(1, len(self.x_values) + 1):
                        self.table.setColumnWidth(i, optimal_cell_width)
                    self.table.setUpdatesEnabled(True)
                
                # Force a repaint to prevent cell disappearance
                self.table.viewport().update()
                
        except Exception as e:
            # Ensure updates are re-enabled in case of error
            self.table.setUpdatesEnabled(True)
            print(f"Warning: Error during table resize: {e}")
    

    
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
        
        # Calculate proper concentration percentages from count matrix
        concentration_percentages = np.zeros_like(count_matrix)
        if total_data_points > 0:
            concentration_percentages = (count_matrix / total_data_points) * 100
        
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
            percentages=concentration_percentages,  # Use proper concentration percentages
            total_points_inside=total_data_points,
            total_points_all=total_data_points,
            comparison_percentages=comparison_percentages,
            comparison_name=comparison_name,
            z_values_for_comparison=z_averaged_matrix  # Pass Z values for comparison calculations
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
        comparison_name=name2,
        z_values_for_comparison=surface1  # Use surface1 Z values for comparison calculations
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
    
    # Variables for channels - now includes Z parameter from config
    rpm_var = tk.StringVar(value=config.get('rpm_channel', ''))
    etasp_var = tk.StringVar(value=config.get('etasp_channel', ''))
    z_param_var = tk.StringVar(value=config.get('z_param_channel', ''))  # Load saved Z parameter
    
    # Grid intervals (use CSV dimensions)
    rpm_intervals_var = tk.IntVar(value=len(csv_x_values) - 1)
    etasp_intervals_var = tk.IntVar(value=len(csv_y_values) - 1)
    
    raster_var = tk.DoubleVar(value=config.get('raster_value', 0.02))  # Save raster value too
    
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
    
    def add_filter(saved_filter=None):
        filter_frame = tk.Frame(filters_scrollable_frame)
        filter_frame.pack(fill='x', pady=2)
        
        # Channel
        tk.Label(filter_frame, text='Channel:').pack(side='left')
        channel_var = tk.StringVar(value=saved_filter.get('channel', '') if saved_filter else '')
        channel_cb = AutocompleteCombobox(filter_frame, textvariable=channel_var, width=20)
        channel_cb.set_completion_list(all_channels)
        channel_cb.pack(side='left', padx=2)
        
        # Condition
        tk.Label(filter_frame, text='Condition:').pack(side='left', padx=(5, 2))
        condition_var = tk.StringVar(value=saved_filter.get('condition', 'within range') if saved_filter else 'within range')
        condition_cb = ttk.Combobox(filter_frame, textvariable=condition_var, 
                                   values=['within range', 'outside range'], 
                                   width=12, state='readonly')
        condition_cb.pack(side='left', padx=2)
        
        # Min/Max values
        tk.Label(filter_frame, text='Min:').pack(side='left', padx=(5, 2))
        min_var = tk.DoubleVar(value=saved_filter.get('min', 0.0) if saved_filter else 0.0)
        min_entry = tk.Entry(filter_frame, textvariable=min_var, width=8)
        min_entry.pack(side='left', padx=2)
        
        tk.Label(filter_frame, text='Max:').pack(side='left', padx=(5, 2))
        max_var = tk.DoubleVar(value=saved_filter.get('max', 0.0) if saved_filter else 0.0)
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
    
    # Load saved filters from config
    saved_filters = config.get('filters', [])
    for saved_filter in saved_filters:
        add_filter(saved_filter)
    
    add_filter_btn = tk.Button(filters_frame, text='Add Filter', command=lambda: add_filter())
    add_filter_btn.pack(pady=5)
    
    # Function to save configuration
    def save_configuration():
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
        
        # Update config with current selections
        current_config = {}
        if os.path.exists('fuel_config.json'):
            try:
                with open('fuel_config.json', 'r') as f:
                    current_config = json.load(f)
            except:
                current_config = {}
        
        current_config.update({
            'rpm_channel': rpm_var.get(),
            'etasp_channel': etasp_var.get(),
            'z_param_channel': z_param_var.get(),  # Save Z parameter channel
            'raster_value': raster_var.get(),  # Save raster value
            'filters': filters  # Save filters setup
        })
        
        try:
            with open('fuel_config.json', 'w') as f:
                json.dump(current_config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save configuration: {e}")
    
    # Action buttons
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill='x', pady=20)
    
    def process_vehicle_points_against_csv():
        # Validate inputs - only need RPM and ETASP for this option
        if not rpm_var.get() or not etasp_var.get():
            messagebox.showerror('Error', 'Please select RPM and ETASP channels')
            return
        
        try:
            # Save configuration before processing
            save_configuration()
            
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
            
            # Process files and show surface table viewer (similar to confirm flow)
            process_files_and_show_results(
                surface_data, raster_var.get(), 
                rpm_var.get(), etasp_var.get(), 
                filters, mdf_file_paths
            )
            
        except Exception as e:
            messagebox.showerror('Error', f'Invalid parameters: {e}')
    
    def create_surface_from_vehicle():
        # Validate inputs
        if not rpm_var.get() or not etasp_var.get() or not z_param_var.get():
            messagebox.showerror('Error', 'Please select RPM, ETASP, and Z parameter channels')
            return
        
        try:
            # Save configuration before processing
            save_configuration()
            
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
    
    tk.Button(button_frame, text='Vehicle points of operations against CSV', 
              command=process_vehicle_points_against_csv, bg='lightgreen', font=('TkDefaultFont', 10, 'bold')).pack(side='left', padx=10)
    tk.Button(button_frame, text='Create Surface Table from Vehicle Logs', 
              command=create_surface_from_vehicle, bg='lightblue', font=('TkDefaultFont', 10, 'bold')).pack(side='right', padx=10)


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

def show_surface_table(surface_data, x_values, y_values, z_values, percentages=None, total_points_inside=0, total_points_all=0, comparison_percentages=None, comparison_name="Comparison", z_values_for_comparison=None):
    """Show surface table in PyQt5 window"""
    global _active_viewers
    
    # Get or create QApplication instance on main thread
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    viewer = SurfaceTableViewer(surface_data, x_values, y_values, z_values, percentages, total_points_inside, total_points_all, comparison_percentages, comparison_name, z_values_for_comparison)
    
    # Keep reference to prevent garbage collection
    _active_viewers.append(viewer)
    viewer.show()
    
    # Don't call app.exec_() as it would block the main thread
    # Let the existing event loop handle the window





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