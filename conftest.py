import sys
import os

# Make all top-level packages (core, api, worker, mcp) importable from tests
sys.path.insert(0, os.path.dirname(__file__))
