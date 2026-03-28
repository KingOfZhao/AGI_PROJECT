"""
AGI v13 路径引导模块
在任何入口脚本的最顶部 import _paths 即可自动加载 core/ 和 api/ 到 sys.path
"""
import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
for _subdir in ['core', 'api']:
    _p = os.path.join(_root, _subdir)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# 确保项目根目录也在 sys.path 中
if _root not in sys.path:
    sys.path.insert(0, _root)
