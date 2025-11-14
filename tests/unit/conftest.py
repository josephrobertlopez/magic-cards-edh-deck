"""Pytest configuration and shared fixtures."""
import sys
from pathlib import Path

# Add project root to Python path for imports
# tests/unit/conftest.py -> go up 2 levels to project root
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
