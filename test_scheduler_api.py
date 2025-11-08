#!/usr/bin/env python3
"""
Quick test script to verify the scheduler status API is working
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_scheduler_status():
    """Test the scheduler status endpoint"""
    print("\n" + "="*60)
    print("Testing Scheduler Status API")
    print("="*60 + "\n")
    
    try:
        url = f"{API_BASE}/api/scheduler/status"
        print(f"📡 Calling: {url}")
        
        response = requests.get(url, timeout=5)
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ API Response:")
            print(json.dumps(data, indent=2))
            
            # Parse and display in human-readable format
            print(f"\n📋 Summary:")
            print(f"   Status: {data.get('status')}")
            print(f"   Interval: Every {data.get('interval_minutes')} minutes")
            
            if data.get('last_run'):
                last_run = datetime.fromisoformat(data['last_run'].replace('Z', '+00:00'))
                print(f"   Last Run: {last_run.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            else:
                print(f"   Last Run: Not yet (waiting for first run)")
            
            if data.get('next_run'):
                next_run = datetime.fromisoformat(data['next_run'].replace('Z', '+00:00'))
                print(f"   Next Run: {next_run.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            seconds = data.get('seconds_until_next')
            if seconds is not None:
                minutes = seconds // 60
                secs = seconds % 60
                print(f"   Countdown: {minutes:02d}:{secs:02d}")
            
            print("\n✅ Scheduler API is working correctly!")
            return True
            
        else:
            print(f"\n❌ API returned error status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error!")
        print("   Is the backend server running on http://localhost:8000?")
        print("   Start it with: cd /Users/rileymartin/tradingbot && python -m uvicorn app.server:app --reload")
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_scheduler_status()

