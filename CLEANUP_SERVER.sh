#!/bin/bash
# Script to clean up disk space on the server

echo "========================================="
echo "SERVER DISK CLEANUP"
echo "========================================="

echo ""
echo "[1] Current disk usage:"
df -h

echo ""
echo ""
echo "[2] Finding large files/directories..."
du -sh /var/log/* 2>/dev/null | sort -h | tail -10
du -sh /tmp/* 2>/dev/null | sort -h | tail -10
du -sh ~/.cache/* 2>/dev/null | sort -h | tail -10

echo ""
echo ""
echo "[3] Cleaning up common bloat..."

# Clean apt cache
echo "Cleaning apt cache..."
sudo apt-get clean
sudo apt-get autoclean

# Remove old logs
echo "Removing old logs..."
sudo journalctl --vacuum-time=7d

# Clean pip cache
echo "Cleaning pip cache..."
pip3 cache purge 2>/dev/null || true

# Clean npm cache
echo "Cleaning npm cache..."
npm cache clean --force 2>/dev/null || true

# Remove Chrome driver downloads (Selenium cache)
echo "Cleaning Selenium cache..."
rm -rf ~/.cache/selenium 2>/dev/null || true

# Clean tmp files older than 7 days
echo "Cleaning old tmp files..."
sudo find /tmp -type f -atime +7 -delete 2>/dev/null || true

echo ""
echo ""
echo "[4] Final disk usage:"
df -h

echo ""
echo "========================================="
echo "DONE"
echo "========================================="

