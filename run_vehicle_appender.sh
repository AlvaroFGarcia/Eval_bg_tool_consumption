#!/bin/bash

# Vehicle Log Channel Appender Startup Script

echo "Starting Vehicle Log Channel Appender..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating it..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing required packages..."
    pip install asammdf scipy numpy pandas
else
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if required packages are installed
python3 -c "import vehicle_log_channel_appender" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing missing packages..."
    pip install asammdf scipy numpy pandas
fi

echo "Launching Vehicle Log Channel Appender GUI..."
python3 vehicle_log_channel_appender.py

echo "Application closed."