import tkinter as tk
from tkinter import ttk
from myfilesync.models.comparison import FileStatus, FileItem

class PreviewDialog:
    def __init__(self, parent, items, on_confirm):
        self.top = tk.Toplevel(parent)
        self.top.title('同步预览 (多目录对)')
        self.top.geometry('850x550')
        self.top.transient(parent)
        self.top.grab_set()

        self.on_confirm = on_confirm

        copy_count = 0
        delete_count = 0
        skip_count = 0

        for pair_idx, item in items:
            if item.status in (FileStatus.LEFT_ONLY, FileStatus.LEFT_NEWER, FileStatus.DIFFERENT, FileStatus.CONFLICT):
                copy_count += 1
            elif item.status == FileStatus.RIGHT_ONLY:
                delete_count += 1
            else:
                skip_count += 1

        lbl_frame = ttk.LabelFrame(self.top, text=' 预览统计 ')
        lbl_frame.pack(fill=tk.X, padx=10, pady=10)

        summary_text = '需复制/覆盖文件数: ' + str(copy_count) + '      需删除右侧多余文件数: ' + str(delete_count) + '      跳过/相同: ' + str(skip_count)
        ttk.Label(lbl_frame, text=summary_text).pack(padx=10, pady=10)

        mid_frame = ttk.Frame(self.top)
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ('pair_idx', 'action', 'rel_path', 'status')
        self.tree = ttk.Treeview(mid_frame, columns=columns, show='headings')
        self.tree.heading('pair_idx', text='目录对索引')
        self.tree.heading('action', text='同步动作')
        self.tree.heading('rel_path', text='文件相对路径')
        self.tree.heading('status', text='当前状态')

        self.tree.column('pair_idx', width=90, anchor=tk.CENTER)
        self.tree.column('action', width=110, anchor=tk.CENTER)
        self.tree.column('rel_path', width=400, anchor=tk.W)
        self.tree.column('status', width=150, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for pair_idx, item in items:
            if item.status in (FileStatus.LEFT_ONLY, FileStatus.LEFT_NEWER, FileStatus.DIFFERENT, FileStatus.CONFLICT):
                action = '[复制/覆盖]'
            elif item.status == FileStatus.RIGHT_ONLY:
                action = '[删除右侧]'
            else:
                action = '[跳过]'
            
            if action != '[跳过]':
                self.tree.insert('', tk.END, values=('第 ' + str(pair_idx) + ' 行', action, item.rel_path, item.status.value))

        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text='确认执行逐行同步', command=self._confirm).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text='取消', command=self.top.destroy).pack(side=tk.RIGHT, padx=5)

    def _confirm(self):
        self.top.destroy()
        if self.on_confirm:
            self.on_confirm()
