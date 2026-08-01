"""
Put the src/ directory on sys.path so modules that use flat imports
(e.g. rag_recommender's `from recommender import ...`) load under pytest.
"""

import os
import sys

_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
