# Vehicle Log Channel Appender

This program allows you to add calculated channels to vehicle log files (CSV, .dat, MDF, MF4) based on interpolation from a CSV surface table lookup.

## Features

- **Single File Processing**: Select and process one vehicle log file at a time
- **Multiple Format Support**: Works with CSV, .dat, MDF, and MF4 files
- **Surface Table Interpolation**: Uses CSV surface tables to calculate Z values based on ETASP and RPM
- **Channel Appending**: Adds the calculated channel back to the original file format
- **User-Friendly Interface**: Step-by-step GUI workflow

## How It Works

1. **CSV Surface Table**: Loads a 3-column CSV file (RPM, ETASP, Z) as a lookup table
2. **Vehicle Log**: Loads a single vehicle log file and extracts available channels
3. **Parameter Selection**: Choose RPM and ETASP channels from the vehicle log
4. **Interpolation**: Calculates Z values by interpolating between CSV surface table points
5. **Channel Addition**: Appends the calculated channel to the original file and saves a new copy

## Installation

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the program:
   ```bash
   python vehicle_log_channel_appender.py
   ```

## Usage

### Step 1: Select CSV Surface Table
- Click "Select CSV Surface Table"
- Choose a CSV file with 3 columns: RPM, ETASP, Z (in that order)
- The program will display the data ranges loaded

### Step 2: Select Vehicle Log File
- Click "Select Vehicle Log File"
- Choose a single vehicle log file (.csv, .dat, .mdf, or .mf4)
- Available channels will be loaded automatically

### Step 3: Select Parameters
- **RPM Channel**: Choose the RPM channel from the dropdown
- **ETASP Channel**: Choose the ETASP channel from the dropdown
- **New Channel Name**: Enter a name for the calculated channel (default: "Calculated_Z")

### Step 4: Process and Export
- Click "Calculate and Append Channel"
- The program will:
  - Synchronize RPM and ETASP data to a common time base
  - Interpolate Z values using the CSV surface table
  - Add the new channel to the file
  - Save a new file with "_with_{ChannelName}" suffix

## Input File Formats

### CSV Surface Table Format
```csv
RPM,ETASP,Z_Value
1000,0.1,15.5
1200,0.15,18.2
1500,0.2,22.1
...
```

### Vehicle Log Files
- **CSV**: Standard comma-separated values with column headers
- **MDF/MF4**: ASAM MDF measurement data files
- **DAT**: Data acquisition files

## Interpolation Method

The program uses scipy's `griddata` function with:
1. **Linear interpolation** for points within the surface table bounds
2. **Nearest neighbor** interpolation for points outside bounds or to fill NaN values

## Output

- Creates a new file in the same directory as the input
- Maintains original format (CSV→CSV, MDF→MDF, etc.)
- Adds suffix: `originalname_with_ChannelName.ext`
- If file exists, adds number suffix: `originalname_with_ChannelName_1.ext`

## Error Handling

- Validates all inputs before processing
- Handles missing data points gracefully
- Provides detailed status logging
- Shows informative error messages

## Limitations

- CSV surface tables must have exactly 3 columns in RPM, ETASP, Z order
- Vehicle log files must contain both RPM and ETASP channels
- Processing time depends on file size and number of data points

## Troubleshooting

1. **"No channels found"**: Ensure vehicle log file is valid format
2. **"Interpolation failed"**: Check that CSV surface table covers the RPM/ETASP ranges in vehicle log
3. **"File save error"**: Ensure write permissions in output directory

## Dependencies

- numpy: Numerical operations
- pandas: Data handling
- asammdf: MDF/MF4 file support
- scipy: Interpolation functions
- tkinter: GUI interface (usually included with Python)

## Example Workflow

1. Prepare CSV surface table with known RPM/ETASP/Z relationships
2. Load vehicle log file containing actual RPM and ETASP measurements
3. Select appropriate channels for RPM and ETASP
4. Run calculation to generate Z values for each time point
5. Get new file with original data plus calculated Z channel

This allows you to apply calibrated surface maps to real vehicle data without filters, generating accurate Z parameter values based on actual operating conditions.