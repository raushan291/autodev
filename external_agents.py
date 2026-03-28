import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

FMA_ROOT = os.path.join(ROOT, "file-management-agent")

sys.path.append(FMA_ROOT)
sys.path.append(os.path.join(FMA_ROOT, "v3"))

from  tool_registry import TOOLS
