import tkinter as tk
from tkinter import ttk
import os

class LogDialog:
    def __init__(self, parent, log_file):
        self.top = tk.Toplevel(parent)
        self.top.title('同步日志')
        self.top.geometry('700, 500')
        self.top.transient(parent)

        txt_frame = ttk.Frame(self.top)
        txt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.text = tk.Text(txt_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscroll=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.text.insert(tk.END, content)
            except Exception as e:
                self.text.insert(tk.END, '读取日志失败: ' + str(e))
        else:
            self.text.insert(tk.END, '暂无日志记录。')

        self.text.config(state=tk.DISABLED)
