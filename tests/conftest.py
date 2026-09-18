import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Désactive le middleware auth pour les tests
import os

os.environ['EZZIO_DISABLE_AUTH'] = '1'
