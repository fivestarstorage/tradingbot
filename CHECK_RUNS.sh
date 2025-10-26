#!/bin/bash
# Quick script to check if runs are working on the server

echo "========================================="
echo "CHECKING NEWS RUNS"
echo "========================================="

echo ""
echo "[1] Checking if backend is running..."
curl -s http://localhost:8001/api/runs/debug | python3 -m json.tool

echo ""
echo ""
echo "[2] Forcing a news refresh..."
curl -X POST http://localhost:8001/api/runs/refresh

echo ""
echo ""
echo "[3] Waiting 5 seconds..."
sleep 5

echo ""
echo "[4] Checking runs again..."
curl -s http://localhost:8001/api/runs/debug | python3 -m json.tool

echo ""
echo ""
echo "[5] Fetching last 5 runs..."
curl -s http://localhost:8001/api/runs | python3 -m json.tool | head -100

echo ""
echo ""
echo "========================================="
echo "DONE - Check the output above"
echo "========================================="

