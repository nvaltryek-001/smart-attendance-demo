"""Seed / re-seed the DEMO database. Usage: python scripts/seed_demo.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from app.seed import seed
if __name__ == "__main__":
    print("face profiles enrolled:", seed(create_app({"NO_SEED": True})))
