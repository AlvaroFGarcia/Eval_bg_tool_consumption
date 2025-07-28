# Performance and File Management Improvements

## Summary of Changes

I've implemented significant performance improvements to the Surface Table Viewer and added a file address saving feature as requested.

## Performance Improvements

### 1. **Concentration Overlay Optimization**
- **Throttled Updates**: Added update throttling with a QTimer to limit updates to ~60 FPS maximum
- **Simplified Rendering**: Replaced complex cubic interpolation and Gaussian filtering with simple rectangle-based rendering
- **Visibility Culling**: Only render cells that are actually visible on screen
- **Antialiasing Disabled**: Turned off antialiasing by default for better performance
- **Default Settings Optimized**: Reduced default transparency (30% vs 50%) and disabled blur by default

### 2. **Update Frequency Reduction**
- **Smart Update Throttling**: Multiple rapid overlay updates are now batched and throttled
- **Cache Invalidation**: Added caching mechanism (prepared for future complex calculations)
- **Selective Updates**: Updates are only triggered when absolutely necessary

### 3. **Performance Mode Toggle**
- **Added Performance Mode Checkbox**: Users can toggle between performance and quality modes
- **Performance Mode**: 
  - 20% transparency
  - Blur disabled
  - Reduced intensity (70%)
- **Quality Mode**: 
  - 50% transparency
  - Blur enabled
  - Full intensity (100%)

### 4. **Rendering Optimizations**
- **Simplified Gradient Mode**: Removed expensive interpolation calculations
- **Direct Cell Rendering**: Each cell is rendered directly without complex transformations
- **Reduced Memory Allocations**: Fewer temporary objects created during rendering

## File Address Saving Feature

### 1. **Configuration Storage**
- **JSON Configuration**: Extended `fuel_config.json` to store last used file paths
- **Auto-persistence**: File paths are automatically saved when selected
- **Validation**: Only existing files are auto-loaded on startup

### 2. **Auto-loading on Startup**
- **Last CSV File**: Automatically detects and loads the last selected surface table CSV
- **Last MDF Files**: Automatically loads the last selected vehicle log files
- **Smart Validation**: Checks if files still exist before attempting to load

### 3. **Enhanced User Interface**
- **Status Indicators**: Shows when previous files are detected
- **Auto-proceed Button**: "🚀 Use Last Configuration" button for quick restart
- **File Status Display**: Shows loaded file names in the interface
- **Confirmation Dialog**: Asks user before auto-proceeding with last configuration

### 4. **Configuration Functions Added**
```python
def save_last_file_path(key, file_path)    # Saves file path to config
def load_last_file_path(key)               # Loads file path from config
def auto_load_last_files()                 # Auto-loads both CSV and MDF files
```

## Technical Implementation Details

### Performance Improvements Location:
- **ConcentrationOverlay class**: Lines 47-330 (added throttling and simplified rendering)
- **SurfaceTableViewer**: Added performance mode toggle and optimized defaults
- **Update Methods**: Replaced direct `update()` calls with `throttled_update()`

### File Saving Implementation Location:
- **Helper Functions**: Lines 294-340 (save/load file path functions)
- **Main Function**: Lines 2164-2185 (auto-loading logic)
- **UI Updates**: Lines 2267-2290 (auto-proceed button and status indicators)

## User Experience Improvements

### Before Changes:
- Surface table viewer was laggy during interactions
- No memory of previously used files
- Had to re-select files every time the program was restarted

### After Changes:
- **Fluid Interaction**: Responsive table interactions with throttled updates
- **Quick Restart**: Program remembers last configuration and can auto-proceed
- **Performance Control**: Users can choose between speed and visual quality
- **Better Feedback**: Clear status indicators and confirmation dialogs

## Configuration File Structure

The `fuel_config.json` now includes:
```json
{
  "last_files": {
    "last_csv_file": "/path/to/surface_table.csv",
    "last_mdf_files": ["/path/to/file1.mdf", "/path/to/file2.mdf"]
  },
  // ... existing configuration options
}
```

## Usage Instructions

1. **First Time**: Select files normally using the file selection buttons
2. **Subsequent Uses**: 
   - Program will auto-detect and display previously used files
   - Click "🚀 Use Last Configuration" for quick restart
   - Or select new files as needed
3. **Performance**: Toggle "Performance Mode" in the concentration overlay for better responsiveness

These improvements should significantly enhance the Python fluidity in the Surface table viewer while providing the requested file persistence feature.