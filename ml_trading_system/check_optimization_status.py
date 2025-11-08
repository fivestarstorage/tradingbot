"""
Check Optimization Status

Monitors the running optimization and shows current progress
"""

import json
import os
from pathlib import Path
from datetime import datetime


def check_status():
    """Check optimization status"""
    print("\n" + "="*80)
    print("📊 ML STRATEGY OPTIMIZATION STATUS")
    print("="*80)
    
    # Check if process is running
    pid_file = Path("optimization_run.pid")
    if pid_file.exists():
        pid = pid_file.read_text().strip()
        
        # Check if process still running
        try:
            os.kill(int(pid), 0)  # Signal 0 checks if process exists
            print(f"\n✅ Optimization is RUNNING (PID: {pid})")
        except OSError:
            print(f"\n⏹️  Optimization has FINISHED or STOPPED (PID: {pid})")
    else:
        print(f"\n❌ No optimization running (no PID file found)")
    
    # Check log file
    log_file = Path("optimization_run.log")
    if log_file.exists():
        print(f"\n📋 Log file: {log_file}")
        print(f"   Size: {log_file.stat().st_size / 1024:.1f} KB")
        print(f"   Modified: {datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show last 20 lines
        print(f"\n📝 Last 20 lines of log:")
        print("-" * 80)
        with open(log_file, 'r') as f:
            lines = f.readlines()
            for line in lines[-20:]:
                print(line.rstrip())
    
    # Check results
    results_dir = Path("optimization_results")
    if results_dir.exists():
        result_files = sorted(results_dir.glob("strategy_optimization_*.json"), reverse=True)
        
        if result_files:
            latest = result_files[0]
            print(f"\n📊 Latest Results: {latest.name}")
            print(f"   Modified: {datetime.fromtimestamp(latest.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Load and show summary
            with open(latest, 'r') as f:
                results = json.load(f)
            
            if results:
                print(f"\n✅ Completed {len(results)} strategies so far")
                
                # Quick stats
                profitable = sum(1 for r in results if r['metrics']['total_return'] > 0)
                avg_roi = sum(r['metrics']['total_return'] for r in results) / len(results) * 100
                best_roi = max(r['metrics']['total_return'] for r in results) * 100
                best_sharpe = max(r['metrics']['sharpe_ratio'] for r in results)
                
                print(f"   Profitable: {profitable}/{len(results)} ({profitable/len(results)*100:.1f}%)")
                print(f"   Avg ROI: {avg_roi:.2f}%")
                print(f"   Best ROI: {best_roi:.2f}%")
                print(f"   Best Sharpe: {best_sharpe:.2f}")
                
                # Top 3 so far
                sorted_results = sorted(results, key=lambda x: x['metrics']['total_return'], reverse=True)
                print(f"\n🏆 Top 3 Strategies So Far:")
                for i, r in enumerate(sorted_results[:3], 1):
                    m = r['metrics']
                    print(f"   {i}. Strategy #{r['id']} - "
                          f"ROI: {m['total_return']*100:+.2f}%, "
                          f"Win: {m['win_rate']*100:.1f}%, "
                          f"Sharpe: {m['sharpe_ratio']:.2f}")
                    print(f"      {r['model'].upper()} | "
                          f"{r['label_horizon']}min/{r['label_threshold']*100:.1f}% | "
                          f"prob={r['probability_threshold']}")
            else:
                print(f"\n⏳ No results yet (file is empty)")
        else:
            print(f"\n⏳ No result files found yet")
    
    print("\n" + "="*80)
    print("\n💡 Commands:")
    print("   Monitor live:  tail -f optimization_run.log")
    print("   Stop:          kill $(cat optimization_run.pid)")
    print("   Check again:   python3 check_optimization_status.py")
    print("")


if __name__ == '__main__':
    check_status()

