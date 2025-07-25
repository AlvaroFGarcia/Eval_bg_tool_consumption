# Enhanced Concentration Overlay Features

## Overview
The concentration overlay has been significantly enhanced with new visualization modes, advanced controls, and comprehensive metrics. This provides better insight into how time is spent across different operating conditions.

## New Features

### 1. Visualization Modes

#### Gradient Mode (Default)
- **Smooth interpolated surface**: Creates a lens-like effect that moves with X/Y table axes
- **Not restricted to cell boundaries**: Uses interpolation to create smooth gradients across the table
- **Blur effect**: Optional Gaussian blur for even smoother appearance
- **High-resolution rendering**: Adaptive grid resolution for optimal performance

#### Scatter Mode (New)
- **Point-based visualization**: Uses transparent points instead of gradient overlay
- **Density control**: Adjust the number of points per concentration level
- **Variable point sizes**: Configurable point size from 1-20 pixels
- **Consistent positioning**: Uses seeded random generation for stable point positions

### 2. Enhanced Controls

#### Basic Controls
- **Enable/Disable**: Toggle concentration overlay on/off
- **Mode Selection**: Choose between gradient and scatter modes
- **Transparency**: 0-100% transparency control
- **Intensity**: 0.1x to 3.0x intensity multiplier for enhanced visibility

#### Advanced Controls
- **Gamma Correction**: 0.1 to 3.0 gamma adjustment for non-linear scaling
- **Blur Toggle**: Enable/disable blur effect (gradient mode only)
- **Color Selection**: Customizable min and max colors

#### Scatter-Specific Controls
- **Point Size**: 1-20 pixel radius for scatter points
- **Density**: 0.1x to 5.0x density multiplier for point count
- **Auto-hiding**: Scatter controls only visible in scatter mode

### 3. Concentration Metrics

#### Time-Based Metrics
- **Maximum Concentration**: Shows peak concentration percentage and estimated time
- **Average Concentration**: Mean concentration across all valid data points
- **Total Time**: Sum of all concentration percentages with time estimate
- **Time Estimation**: Converts percentages to approximate hours based on typical test durations

#### Display Format
```
Max: 15.3% (~1.2h) | Avg: 4.7% | Total: 847.2% (~67.8h)
```

#### Metrics Features
- **Toggle Display**: Show/hide metrics with checkbox
- **Real-time Updates**: Updates automatically when settings change
- **Error Handling**: Graceful handling of invalid or missing data
- **Smart Units**: Automatically formats percentages and estimated time

### 4. Technical Enhancements

#### Performance Optimizations
- **Adaptive Resolution**: Grid resolution scales with viewport size
- **Efficient Rendering**: Uses simple rectangles for better performance
- **Smart Visibility**: Only renders visible portions of the overlay
- **Memory Management**: Optimized data structures and processing

#### Improved Interpolation
- **Cubic Interpolation**: Higher quality surface interpolation using scipy.griddata
- **Fallback Rendering**: Radial gradients when interpolation fails
- **Boundary Handling**: Proper handling of edge cases and missing data
- **Intensity Application**: Non-linear scaling with gamma correction

#### Better Integration
- **Comparison Mode Support**: Now works in all comparison modes
- **Persistent Settings**: All settings saved and restored automatically
- **Responsive UI**: Controls adapt based on selected mode
- **Table Synchronization**: Overlay updates with table scrolling and resizing

## Configuration Options

### Saved Settings
All concentration overlay settings are automatically saved to `fuel_config.json`:

```json
{
  "concentration_overlay": {
    "enabled": true,
    "mode": "gradient",
    "transparency": 0.5,
    "intensity": 1.0,
    "gamma": 1.0,
    "blur_enabled": true,
    "scatter_size": 5.0,
    "scatter_density": 1.0,
    "show_metrics": true,
    "min_color": "#ffffff00",
    "max_color": "#0064ffc8"
  }
}
```

### Default Values
- **Mode**: Gradient
- **Transparency**: 50%
- **Intensity**: 1.0x
- **Gamma**: 1.0 (linear)
- **Blur**: Enabled
- **Scatter Size**: 5 pixels
- **Scatter Density**: 1.0x
- **Metrics**: Enabled

## Usage Guidelines

### Best Practices

#### For Dense Data
- Use **gradient mode** with moderate blur for smooth visualization
- Adjust **intensity** (0.5-1.5x) for better contrast
- Enable **metrics** to understand data distribution

#### For Sparse Data
- Use **scatter mode** with increased density (1.5-3.0x)
- Larger **point sizes** (8-15px) for better visibility
- Lower **transparency** (20-40%) for clearer points

#### For Analysis
- Compare **metrics** between different datasets
- Use **gamma correction** to enhance low-concentration areas
- Toggle between **modes** to see different data perspectives

### Performance Tips
- **Higher intensity** reduces need for lower transparency
- **Blur disabled** improves performance on large tables
- **Lower scatter density** improves performance in scatter mode
- **Metrics disabled** reduces computational overhead

## Implementation Details

### Color Interpolation
The overlay uses linear RGB interpolation between min and max colors:
```
R = min_R + (max_R - min_R) * normalized_concentration
G = min_G + (max_G - min_G) * normalized_concentration  
B = min_B + (max_B - min_B) * normalized_concentration
Alpha = normalized_concentration * transparency * 255
```

### Intensity and Gamma Processing
```
normalized = clip(concentration / max_concentration, 0, 1)
normalized = normalized * intensity
normalized = power(clip(normalized, 0, 1), gamma)
```

### Scatter Point Generation
```
base_points = max(1, int(normalized_conc * 20 * density))
# Random positions within each cell using consistent seeding
```

## Compatibility

### Working Modes
- ✅ Normal surface table view
- ✅ Comparison mode (all variants)
- ✅ Percentage difference view
- ✅ Absolute difference view
- ✅ All zoom and scroll operations

### Requirements
- **scipy**: For interpolation (gradient mode)
- **numpy**: For data processing
- **PyQt5**: For UI and rendering
- **Python 3.6+**: Minimum version support

## Troubleshooting

### Common Issues

#### Overlay Not Visible
- Check **Enable Concentration Overlay** checkbox
- Increase **transparency** (lower values = more transparent)
- Increase **intensity** for better visibility
- Verify data contains non-zero concentration values

#### Poor Performance
- Disable **blur** for better performance
- Reduce **scatter density** in scatter mode
- Close other resource-intensive applications
- Consider reducing table size if very large

#### Metrics Not Updating
- Enable **Show Metrics** checkbox
- Verify concentration data is loaded
- Check for data validity (non-NaN values)
- Restart application if persistent

### Debug Information
The application provides error handling and fallback options:
- Invalid interpolation falls back to radial gradients
- Missing dependencies disable advanced features gracefully
- Error messages appear in metrics display when appropriate