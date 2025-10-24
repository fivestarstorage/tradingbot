#!/bin/bash
#
# Trading Bot Startup Script
# ==========================
#
# This script starts the web dashboard so you can manage your trading bots.
#
# Usage:
#   ./start.sh
#
# Then open your browser to: http://localhost:5001
#

echo "=================================================="
echo "🤖 Starting Trading Bot Dashboard"
echo "=================================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "   Please install Python 3 first"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Creating from template..."
    if [ -f env_template.txt ]; then
        cp env_template.txt .env
        echo "✅ Created .env file"
        echo "⚠️  IMPORTANT: Edit .env and add your Binance API keys!"
        echo ""
        read -p "Press Enter to continue (make sure to edit .env first)..."
    else
        echo "❌ Error: env_template.txt not found"
        exit 1
    fi
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed. Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install dependencies"
        echo "   Try manually: pip3 install -r requirements.txt"
        exit 1
    fi
fi

echo "✅ Dependencies OK"
echo ""

# Start the dashboard
echo "🚀 Starting dashboard on http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop the dashboard"
echo ""
echo "=================================================="
echo ""

# Run the dashboard
python3 simple_dash.py

