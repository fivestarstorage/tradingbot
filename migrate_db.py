#!/usr/bin/env python3
"""
Create or update database tables
"""

from app.db import engine, Base
from app.models import *  # Import all models

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully!")

