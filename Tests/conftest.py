
import sys
from unittest.mock import MagicMock

# Mock PsychoPy and Pyglet modules BEFORE they are imported by any test
# This prevents OpenGL context creation which fails in headless environments (CI)

# Create mocks
mock_psychopy = MagicMock()
mock_visual = MagicMock()
mock_core = MagicMock()
mock_event = MagicMock()
mock_gui = MagicMock()

# Configure specific behaviors/attributes that might be accessed at import time
mock_visual.Window = MagicMock
mock_visual.TextStim = MagicMock
mock_visual.ImageStim = MagicMock
mock_visual.Rect = MagicMock

# Attach mocks to the psychopy mock
mock_psychopy.visual = mock_visual
mock_psychopy.core = mock_core
mock_psychopy.event = mock_event
mock_psychopy.gui = mock_gui

# Patch sys.modules
# We need to patch individual submodules because that's how they are often imported
sys.modules['psychopy'] = mock_psychopy
sys.modules['psychopy.visual'] = mock_visual
sys.modules['psychopy.core'] = mock_core
sys.modules['psychopy.event'] = mock_event
sys.modules['psychopy.gui'] = mock_gui

# Also mock pyglet just in case
mock_pyglet = MagicMock()
sys.modules['pyglet'] = mock_pyglet
sys.modules['pyglet.gl'] = MagicMock()
sys.modules['pyglet.window'] = MagicMock()
