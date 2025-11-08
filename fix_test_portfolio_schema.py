#!/usr/bin/env python3
"""
Fix TestPortfolio schema - add missing position_quantity column
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'tradingbot.db')

def fix_test_portfolio_schema():
    """Add missing columns to test_portfolio table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if position_quantity column exists
        cursor.execute("PRAGMA table_info(test_portfolio)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'position_quantity' not in columns:
            print("Adding position_quantity column...")
            cursor.execute("""
                ALTER TABLE test_portfolio 
                ADD COLUMN position_quantity REAL DEFAULT 0.0
            """)
            print("✅ Added position_quantity column")
        else:
            print("✅ position_quantity column already exists")
        
        conn.commit()
        print("\n✅ Database schema updated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Fixing TestPortfolio schema...")
    fix_test_portfolio_schema()

