import os
import sys

tcl_dir = os.path.join(os.path.dirname(sys.executable), 'tcl', 'tcl8.6')
tk_dir = os.path.join(os.path.dirname(sys.executable), 'tcl', 'tk8.6')
if os.path.exists(tcl_dir):
    os.environ['TCL_LIBRARY'] = tcl_dir
if os.path.exists(tk_dir):
    os.environ['TK_LIBRARY'] = tk_dir

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import os
import sys
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 自动修复某些 Windows 环境下 Python 3.12 的 Tcl/Tk 环境变量缺失问题 
tcl_dir = os.path.join(os.path.dirname(sys.executable), 'tcl', 'tcl8.6')
tk_dir = os.path.join(os.path.dirname(sys.executable), 'tcl', 'tk8.6')
if os.path.exists(tcl_dir):
    os.environ['TCL_LIBRARY'] = tcl_dir
if os.path.exists(tk_dir):
    os.environ['TK_LIBRARY'] = tk_dir

import tkinter as tk
from tkinter import messagebox, filedialog

from myfilesync.ui.main_window import run_app

if __name__ == '__main__':
    run_app()