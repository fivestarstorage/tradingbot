#!/usr/bin/env python3
"""
Migration script to add price_change_1h and price_change_7d columns to community_tips table
"""

import sqlite3
import sys
from app.db import engine, Base
import app.models

def migrate_database():
    """Add new price columns to community_tips table"""
    
    db_path = 'tradingbot.db'
    
    try:
        print("🔄 Connecting to database...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='community_tips';")
        if not cursor.fetchone():
            print("⚠️  Table 'community_tips' doesn't exist yet. Creating all tables...")
            conn.close()
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            print("✅ All tables created!")
            return True
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(community_tips);")
        columns = [row[1] for row in cursor.fetchall()]
        
        needs_migration = False
        
        # Add price_change_1h if it doesn't exist
        if 'price_change_1h' not in columns:
            print("➕ Adding column 'price_change_1h'...")
            cursor.execute("ALTER TABLE community_tips ADD COLUMN price_change_1h FLOAT;")
            needs_migration = True
            print("   ✅ Added price_change_1h")
        else:
            print("   ℹ️  Column 'price_change_1h' already exists")
        
        # Add price_change_7d if it doesn't exist
        if 'price_change_7d' not in columns:
            print("➕ Adding column 'price_change_7d'...")
            cursor.execute("ALTER TABLE community_tips ADD COLUMN price_change_7d FLOAT;")
            needs_migration = True
            print("   ✅ Added price_change_7d")
        else:
            print("   ℹ️  Column 'price_change_7d' already exists")
        
        if needs_migration:
            conn.commit()
            print("\n✅ Database migration completed successfully!")
        else:
            print("\n✅ Database is already up to date!")
        
        # Show current schema
        print("\n📋 Current community_tips schema:")
        cursor.execute("PRAGMA table_info(community_tips);")
        for row in cursor.fetchall():
            col_id, name, col_type, not_null, default, pk = row
            print(f"   {name:25s} {col_type:15s} {'NOT NULL' if not_null else 'NULL':10s}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("DATABASE MIGRATION: Add Price Columns")
    print("="*80 + "\n")
    
    success = migrate_database()
    
    if success:
        print("\n" + "="*80)
        print("✅ Migration complete! You can now restart the server.")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ Migration failed! Check the errors above.")
        print("="*80 + "\n")
        sys.exit(1)

