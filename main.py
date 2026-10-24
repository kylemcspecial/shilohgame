"""Fierce Monster Hunter - entry point."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from src.engine.game import main

if __name__ == "__main__":
    main()
