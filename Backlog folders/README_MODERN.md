# 🚗 Vehicle Log Channel Appender - Modern Edition

A contemporary, professional Python application for analyzing and processing vehicle log files with custom channel interpolation. Built with **CustomTkinter** for a modern, Windows-compatible interface.

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.2+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 🎨 Modern User Interface
- **Dark/Light Theme Support** - Switch between modern dark and light themes
- **Professional Design** - Contemporary card-based layout with proper spacing
- **Windows Optimized** - Perfect compatibility with Windows PCs and proper scaling
- **Responsive Layout** - Adapts to different window sizes and screen resolutions
- **Modern Icons & Typography** - Emoji icons and clean, readable fonts

### 🔧 Core Functionality
- **MDF File Analysis** - Comprehensive analysis of vehicle log files (.mf4, .mdf)
- **Channel Sampling Analysis** - Detailed sampling rate analysis with recommendations
- **Custom Channel Creation** - Build interpolated channels from surface table data
- **Raster Processing** - Process channels at any target frequency with interpolation
- **Enhanced Raster Selection** - Smart dialog with recommendations based on file analysis

### 💼 Professional Features
- **Progress Indicators** - Modern progress dialogs with real-time status updates
- **Settings Management** - Save and load application settings and channel configurations
- **Configuration Export** - Export channel configurations for reuse
- **Comprehensive Logging** - Detailed status log with timestamps and emoji indicators
- **Threaded Processing** - Non-blocking file analysis and processing

## 🚀 Installation

### Prerequisites
- **Python 3.7 or higher**
- **pip** (Python package installer)

### Quick Install
```bash
# Clone or download the application files
# Install dependencies
pip install -r requirements_modern.txt

# Run the application
python vehicle_log_channel_appender_modern.py
```

### Manual Installation
```bash
# Install core dependencies
pip install customtkinter>=5.2.0
pip install asammdf>=7.0.0
pip install numpy>=1.21.0
pip install pandas>=1.3.0
pip install scipy>=1.7.0

# Run the application
python vehicle_log_channel_appender_modern.py
```

## 🖥️ Usage

### 1. **Start the Application**
Run the Python script to launch the modern interface:
```bash
python vehicle_log_channel_appender_modern.py
```

### 2. **Select Vehicle File**
- Click **"Select MDF File"** in the sidebar
- Choose your vehicle log file (.mf4 or .mdf format)
- The application will automatically analyze the file

### 3. **Review Analysis**
- Switch to the **"🔧 Processing"** tab
- Review the detailed file analysis showing:
  - Channel count and sampling rates
  - Recommended raster values
  - Channel distribution by frequency

### 4. **Configure Custom Channels**
- Switch to the **"📊 Custom Channels"** tab
- Add custom channels using the form:
  - **Channel Name**: Output channel name
  - **X Variable**: Independent variable from source file
  - **Y Variable**: Dependent variable from source file
- Use the search feature to find channels quickly

### 5. **Set Processing Parameters**
- Return to the **"🔧 Processing"** tab
- Enter target raster frequency or use **"Enhanced Raster Selection"**
- The enhanced dialog provides smart recommendations

### 6. **Process Channels**
- Click **"🚀 Process Channels"** to begin processing
- Monitor progress with the modern progress dialog
- Save the processed file when complete

### 7. **Monitor Status**
- Check the **"📋 Status Log"** tab for detailed operation logs
- All actions are logged with timestamps and status indicators

## 🎯 Key Improvements Over Original

### Visual & UX Enhancements
✅ **Modern Framework**: CustomTkinter instead of basic Tkinter  
✅ **Professional Appearance**: Dark/light themes with contemporary styling  
✅ **Better Organization**: Sidebar navigation with clear sections  
✅ **Enhanced Buttons**: Larger, more accessible controls with hover effects  
✅ **Progress Feedback**: Real-time progress bars and status updates  
✅ **Responsive Design**: Proper scaling for different screen sizes  

### Functional Improvements
✅ **Threaded Operations**: Non-blocking file analysis and processing  
✅ **Smart Recommendations**: Enhanced raster selection with analysis-based suggestions  
✅ **Configuration Management**: Save/load settings and channel configurations  
✅ **Better Error Handling**: User-friendly error messages and validation  
✅ **Comprehensive Logging**: Detailed operation logs with emoji indicators  

### Windows Compatibility
✅ **Proper Window Sizing**: Automatically centers and sizes for Windows PCs  
✅ **Modern Dialogs**: Native-looking progress and selection dialogs  
✅ **Font Optimization**: Windows-compatible fonts with proper scaling  
✅ **DPI Awareness**: Proper scaling on high-DPI displays  

## 🔧 Technical Details

### Architecture
- **Framework**: CustomTkinter 5.2+ for modern UI components
- **Threading**: Background processing to prevent UI freezing
- **File Handling**: asammdf library for MDF file operations
- **Data Processing**: NumPy and SciPy for numerical operations

### File Support
- **Input**: MDF4 (.mf4) and MDF3 (.mdf) files
- **Output**: Processed MDF4 files with custom channels
- **Settings**: JSON format for configuration persistence

### System Requirements
- **OS**: Windows 10/11, macOS 10.14+, Linux
- **Memory**: 4GB RAM minimum (8GB recommended for large files)
- **Storage**: 100MB for application + space for processed files
- **Display**: 1000x600 minimum resolution (1200x800 recommended)

## 📝 Configuration Files

### Settings Format
```json
{
  "theme": "Dark",
  "custom_channels": [
    {
      "name": "Engine_Load_Map",
      "x_variable": "Engine_RPM",
      "y_variable": "Throttle_Position",
      "created": "2024-01-15 10:30:00"
    }
  ],
  "last_raster": "10.0",
  "saved_at": "2024-01-15T10:30:00"
}
```

### Channel Configuration Export
```json
{
  "channels": [...],
  "exported_at": "2024-01-15T10:30:00",
  "total_channels": 5
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on Windows
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Common Issues

**CustomTkinter not found**
```bash
pip install customtkinter --upgrade
```

**MDF file errors**
```bash
pip install asammdf --upgrade
```

**Font rendering issues on Windows**
- Ensure Windows is updated
- Check display scaling settings
- Try both dark and light themes

**Performance issues with large files**
- Close other applications
- Use recommended raster values
- Process channels in smaller batches

### Support
- Check the **Status Log** tab for detailed error information
- Ensure all dependencies are properly installed
- Verify MDF file integrity with other tools first

---

**Made with ❤️ for the automotive analysis community**