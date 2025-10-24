#!/bin/bash

echo "🛑 Stopping Web Dashboard..."

if screen -list | grep -q "dashboard"; then
    screen -X -S dashboard quit
    echo "✅ Dashboard stopped!"
else
    echo "❌ Dashboard not running"
fi
