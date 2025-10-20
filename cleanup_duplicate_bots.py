#!/usr/bin/env python3
"""
Cleanup Duplicate Bots
Removes duplicate bots that manage the same coin/symbol
"""
import json
import os

BOTS_FILE = 'bots.json'

def load_bots():
    """Load bots from file"""
    if not os.path.exists(BOTS_FILE):
        print(f"❌ {BOTS_FILE} not found!")
        return []
    
    with open(BOTS_FILE, 'r') as f:
        return json.load(f)

def save_bots(bots):
    """Save bots to file"""
    with open(BOTS_FILE, 'w') as f:
        json.dump(bots, f, indent=2)

def cleanup_duplicates():
    """Remove duplicate bots for the same symbol"""
    print("\n🔍 Checking for duplicate bots...\n")
    
    bots = load_bots()
    
    if not bots:
        print("No bots found.")
        return
    
    # Group bots by symbol
    symbol_groups = {}
    for bot in bots:
        symbol = bot['symbol']
        if symbol not in symbol_groups:
            symbol_groups[symbol] = []
        symbol_groups[symbol].append(bot)
    
    # Find duplicates
    duplicates_found = False
    bots_to_keep = []
    
    for symbol, bot_list in symbol_groups.items():
        if len(bot_list) > 1:
            duplicates_found = True
            print(f"⚠️  {symbol} has {len(bot_list)} bots:")
            for i, bot in enumerate(bot_list, 1):
                print(f"   {i}. Bot #{bot['id']}: {bot['name']} - {bot['status'].upper()}")
            
            # Keep the FIRST bot (oldest), delete the rest
            keep = bot_list[0]
            delete = bot_list[1:]
            
            print(f"   ✅ Keeping: Bot #{keep['id']} (oldest)")
            print(f"   🗑️  Deleting: {len(delete)} duplicate(s)")
            print()
            
            bots_to_keep.append(keep)
        else:
            # No duplicates, keep it
            bots_to_keep.append(bot_list[0])
    
    if not duplicates_found:
        print("✅ No duplicates found! All bots are unique.")
        return
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"   Original bots: {len(bots)}")
    print(f"   After cleanup: {len(bots_to_keep)}")
    print(f"   Bots removed: {len(bots) - len(bots_to_keep)}")
    
    # Confirm
    print("\n⚠️  This will permanently delete duplicate bots!")
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response == 'yes':
        save_bots(bots_to_keep)
        print(f"\n✅ Cleanup complete! Removed {len(bots) - len(bots_to_keep)} duplicate bot(s).")
        print(f"   Refresh your dashboard to see the changes.\n")
    else:
        print("\n❌ Cleanup canceled. No changes made.\n")

if __name__ == '__main__':
    cleanup_duplicates()

