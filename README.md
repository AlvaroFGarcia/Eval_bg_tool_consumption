# Fuel Consumption Evaluation Tool

A Python application for analyzing fuel consumption data from vehicle logs and comparing against surface tables.

## Features

- Load and analyze MDF/MF4/DAT vehicle log files
- Compare vehicle data against CSV surface tables
- Interactive surface table visualization with PyQt5
- Data filtering and interpolation capabilities
- Export functionality for analysis results

## Requirements

- Python 3.x
- Required packages: numpy, pandas, asammdf, tkinter, PyQt5, scipy

## Usage

Run the main application:
```bash
python Fuel_Consumption_Eval_Tool.py
```

Follow the GUI workflow:
1. Select Surface Table CSV file (defines RPM/ETASP ranges)
2. Select vehicle log files (MDF/MF4/DAT)
3. Choose analysis or surface creation mode
4. Configure parameters and filters as needed