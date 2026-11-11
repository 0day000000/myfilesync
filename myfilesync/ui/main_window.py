import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 保证能正确加载根包
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from myfilesync.models.task import TaskManager, TaskConfig, SyncPair
from myfilesync.models.comparison import FileStatus, FileItem
from myfilesync.core.filter import FileFilter
from myfilesync.core.scanner import FolderScanner
from myfilesync.core.syncer import SyncEngine
from myfilesync.utils.logger import SyncLogger
from myfilesync.utils.path_helper import check_path_validity

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title('Windows 文件夹比较与同步工具 (MyFileSync - 多对目录)')
        self.root.geometry('1100x800')

        self.logger = SyncLogger()
        self.task_manager = TaskManager()
        self.current_task = self.task_manager.tasks[0] if self.task_manager.tasks else TaskConfig()
        
        self.compared_items = []
        self.is_scanning = False
        self.cancel_flag = False

        self._create_widgets()
        self._load_task_to_ui()

    def _create_widgets(self):
        top_frame = ttk.LabelFrame(self.root, text=' 任务与文件夹目录对配置 ')
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        row_task = ttk.Frame(top_frame)
        row_task.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(row_task, text='当前任务:').pack(side=tk.LEFT, padx=5)
        self.task_combo_var = tk.StringVar()
        self.task_combo = ttk.Combobox(row_task, textvariable=self.task_combo_var, state='readonly', width=25)
        self.task_combo.pack(side=tk.LEFT, padx=5)
        self.task_combo.bind('<<ComboboxSelected>>', self._on_task_changed)

        ttk.Button(row_task, text='新建任务', command=self._new_task).pack(side=tk.LEFT, padx=2)
        ttk.Button(row_task, text='保存任务', command=self._save_task).pack(side=tk.LEFT, padx=2)
        ttk.Button(row_task, text='查看日志', command=self._show_logs).pack(side=tk.RIGHT, padx=5)

        pairs_container = ttk.LabelFrame(top_frame, text=' 文件夹对列表 (每行包含一个左侧目录和一个右侧目录) ')
        pairs_container.pack(fill=tk.X, padx=5, pady=5)

        canvas_frame = ttk.Frame(pairs_container)
        canvas_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(canvas_frame, height=160)
        self.pairs_inner_frame = ttk.Frame(self.canvas)
        
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.pairs_inner_frame, anchor='nw')

        self.pairs_inner_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        btn_row = ttk.Frame(pairs_container)
        btn_row.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_row, text='+ 添加目录对', command=self._add_pair_row).pack(side=tk.LEFT, padx=5)

        row_opt = ttk.Frame(top_frame)
        row_opt.pack(fill=tk.X, padx=5, pady=5)
        self.hash_var = tk.BooleanVar(value=self.current_task.compare_by_content)
        ttk.Checkbutton(row_opt, text='启用内容校验 (SHA-256)', variable=self.hash_var).pack(side=tk.LEFT, padx=5)

        mid_frame = ttk.Frame(self.root)
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ('pair_idx', 'status', 'rel_path', 'left_size', 'left_mtime', 'right_size', 'right_mtime')
        self.tree = ttk.Treeview(mid_frame, columns=columns, show='headings', selectmode='extended')
        self.tree.heading('pair_idx', text='目录对索引')
        self.tree.heading('status', text='文件状态')
        self.tree.heading('rel_path', text='相对路径')
        self.tree.heading('left_size', text='左侧大小')
        self.tree.heading('left_mtime', text='左侧修改时间')
        self.tree.heading('right_size', text='右侧大小')
        self.tree.heading('right_mtime', text='右侧修改时间')

        self.tree.column('pair_idx', width=80, anchor=tk.CENTER)
        self.tree.column('status', width=110, anchor=tk.CENTER)
        self.tree.column('rel_path', width=320, anchor=tk.W)
        self.tree.column('left_size', width=80, anchor=tk.E)
        self.tree.column('left_mtime', width=140, anchor=tk.CENTER)
        self.tree.column('right_size', width=80, anchor=tk.E)
        self.tree.column('right_mtime', width=140, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        self.status_label = ttk.Label(bottom_frame, text='就绪', relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=2)

        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.compare_btn = ttk.Button(btn_frame, text='比较所有目录对', command=self._start_compare)
        self.compare_btn.pack(side=tk.LEFT, padx=5)

        self.preview_btn = ttk.Button(btn_frame, text='同步预览', command=self._start_preview, state=tk.DISABLED)
        self.preview_btn.pack(side=tk.LEFT, padx=5)

        self.sync_btn = ttk.Button(btn_frame, text='开始逐行同步 (Mirror)', command=self._start_sync, state=tk.DISABLED)
        self.sync_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text='取消', command=self._cancel_task, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        self._refresh_task_combo()

    def _refresh_task_combo(self):
        names = [t.name for t in self.task_manager.tasks]
        self.task_combo['values'] = names
        self.task_combo_var.set(self.current_task.name)

    def _load_task_to_ui(self):
        self.hash_var.set(self.current_task.compare_by_content)
        for widget in self.pairs_inner_frame.winfo_children():
            widget.destroy()
        self.pair_rows = []
        for p in self.current_task.pairs:
            self._add_pair_row(p.left_dir, p.right_dir)

    def _add_pair_row(self, left_val='', right_val=''):
        row_frame = ttk.Frame(self.pairs_inner_frame)
        row_frame.pack(fill=tk.X, pady=3)

        ttk.Label(row_frame, text='左:', width=3).pack(side=tk.LEFT)
        l_entry = ttk.Entry(row_frame, width=42)
        l_entry.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        l_entry.insert(0, left_val)
        ttk.Button(row_frame, text='浏览...', width=6, command=lambda: self._browse_dir(l_entry)).pack(side=tk.LEFT, padx=2)

        ttk.Label(row_frame, text='右:', width=3).pack(side=tk.LEFT, padx=(10, 0))
        r_entry = ttk.Entry(row_frame, width=42)
        r_entry.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        r_entry.insert(0, right_val)
        ttk.Button(row_frame, text='浏览...', width=6, command=lambda: self._browse_dir(r_entry)).pack(side=tk.LEFT, padx=2)

        ttk.Button(row_frame, text='删除', width=6, command=lambda: self._remove_pair_row(row_frame)).pack(side=tk.LEFT, padx=5)

        self.pair_rows.append((row_frame, l_entry, r_entry))

    def _remove_pair_row(self, row_frame):
        if len(self.pair_rows) <= 1:
            messagebox.showwarning('提示', '至少保留一个目录对行！')
            return
        for item in self.pair_rows:
            if item[0] == row_frame:
                self.pair_rows.remove(item)
                break
        row_frame.destroy()

    def _save_current_task_from_ui(self):
        self.current_task.compare_by_content = self.hash_var.get()
        pairs = []
        for _, l_entry, r_entry in self.pair_rows:
            l_dir = l_entry.get().strip()
            r_dir = r_entry.get().strip()
            if l_dir or r_dir:
                pairs.append(SyncPair(left_dir=l_dir, right_dir=r_dir))
        if not pairs:
            pairs.append(SyncPair())
        self.current_task.pairs = pairs

    def _on_task_changed(self, event):
        name = self.task_combo_var.get()
        for t in self.task_manager.tasks:
            if t.name == name:
                self.current_task = t
                self._load_task_to_ui()
                break

    def _new_task(self):
        name = '任务_' + str(len(self.task_manager.tasks) + 1)
        new_t = TaskConfig(name=name, pairs=[SyncPair()])
        self.task_manager.tasks.append(new_t)
        self.current_task = new_t
        self._refresh_task_combo()
        self._load_task_to_ui()

    def _save_task(self):
        self._save_current_task_from_ui()
        self.task_manager.save()
        messagebox.showinfo('成功', '任务配置已保存！')

    def _browse_dir(self, entry_widget):
        d = filedialog.askdirectory()
        if d:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, os.path.normpath(d))

    def _start_compare(self):
        self._save_current_task_from_ui()
        
        for idx, pair in enumerate(self.current_task.pairs):
            if not pair.left_dir and not pair.right_dir:
                continue
            valid, msg = check_path_validity(pair.left_dir)
            if not valid:
                messagebox.showerror('错误', '第 ' + str(idx+1) + ' 行左侧文件夹无效: ' + msg)
                return
            valid, msg = check_path_validity(pair.right_dir)
            if not valid:
                messagebox.showerror('错误', '第 ' + str(idx+1) + ' 行右侧文件夹无效: ' + msg)
                return

        for row in self.tree.get_children():
            self.tree.delete(row)

        self.compared_items = []
        self.is_scanning = True
        self.cancel_flag = False

        self.compare_btn.config(state=tk.DISABLED)
        self.preview_btn.config(state=tk.DISABLED)
        self.sync_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)

        threading.Thread(target=self._run_compare_thread, daemon=True).start()

    def _run_compare_thread(self):
        try:
            all_results = []
            f_filter = FileFilter(exclude_patterns=self.current_task.exclude_patterns)

            for idx, pair in enumerate(self.current_task.pairs):
                if self.cancel_flag:
                    break
                if not pair.left_dir or not pair.right_dir:
                    continue

                msg = '正在比较第 ' + str(idx + 1) + ' 行目录对...'
                self.root.after(0, lambda m=msg: self.status_label.config(text=m))

                scanner = FolderScanner(
                    pair.left_dir,
                    pair.right_dir,
                    f_filter,
                    compare_by_content=self.current_task.compare_by_content
                )

                def cancel_check():
                    return self.cancel_flag

                items = scanner.compare(cancel_check=cancel_check)
                for item in items:
                    all_results.append((idx + 1, item))

            self.compared_items = all_results
            self.root.after(0, self._on_compare_finished)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror('错误', '比较过程发生异常: ' + str(e)))
            self.root.after(0, self._on_compare_finished)

    def _on_compare_finished(self):
        self.is_scanning = False
        self.cancel_btn.config(state=tk.DISABLED)
        self.compare_btn.config(state=tk.NORMAL)
        if self.compared_items:
            self.preview_btn.config(state=tk.NORMAL)
            self.sync_btn.config(state=tk.NORMAL)

        import datetime
        for pair_idx, item in self.compared_items:
            l_time_str = datetime.datetime.fromtimestamp(item.left_mtime).strftime('%Y-%m-%d %H:%M:%S') if item.left_mtime else ''
            r_time_str = datetime.datetime.fromtimestamp(item.right_mtime).strftime('%Y-%m-%d %H:%M:%S') if item.right_mtime else ''
            self.tree.insert('', tk.END, values=(
                '第 ' + str(pair_idx) + ' 行',
                item.status.value,
                item.rel_path,
                str(item.left_size) if item.left_path else '',
                l_time_str,
                str(item.right_size) if item.right_path else '',
                r_time_str
            ))

        self.status_label.config(text='比较完成. 共找到 ' + str(len(self.compared_items)) + ' 个文件差异项.')

    def _start_preview(self):
        if not self.compared_items:
            messagebox.showinfo('提示', '请先进行文件夹比较')
            return

        from myfilesync.ui.preview_dialog import PreviewDialog
        PreviewDialog(self.root, self.compared_items, on_confirm=self._execute_sync_confirmed)

    def _start_sync(self):
        if not self.compared_items:
            messagebox.showinfo('提示', '请先进行文件夹比较')
            return
        if messagebox.askyesno('确认', '确定要按行逐个执行镜像同步吗？建议先点击同步预览！'):
            self._execute_sync_confirmed()

    def _execute_sync_confirmed(self):
        self.compare_btn.config(state=tk.DISABLED)
        self.preview_btn.config(state=tk.DISABLED)
        self.sync_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.cancel_flag = False

        threading.Thread(target=self._run_sync_thread, daemon=True).start()

    def _run_sync_thread(self):
        try:
            pair_dict = {}
            for pair_idx, item in self.compared_items:
                if pair_idx not in pair_dict:
                    pair_dict[pair_idx] = []
                pair_dict[pair_idx].append(item)

            total_copied = 0
            total_deleted = 0
            total_failed = 0
            total_skipped = 0

            for pair_idx in sorted(pair_dict.keys()):
                if self.cancel_flag:
                    break
                pair = self.current_task.pairs[pair_idx - 1]
                if not pair.left_dir or not pair.right_dir:
                    continue

                engine = SyncEngine(pair.left_dir, pair.right_dir, self.logger, use_trash=self.current_task.use_trash)
                items_for_pair = pair_dict[pair_idx]

                def prog_cb(curr, total, name):
                    msg = '正在同步 [第 ' + str(pair_idx) + ' 行目录对] (' + str(curr) + '/' + str(total) + '): ' + name
                    self.root.after(0, lambda m=msg: self.status_label.config(text=m))

                def cancel_check():
                    return self.cancel_flag

                stats = engine.execute_mirror(items_for_pair, progress_callback=prog_cb, cancel_check=cancel_check)
                total_copied += stats['copied']
                total_deleted += stats['deleted']
                total_failed += stats['failed']
                total_skipped += stats['skipped']

            msg = '所有目录对镜像同步完成！\n成功复制: ' + str(total_copied) + '\n删除右侧多余: ' + str(total_deleted) + '\n失败: ' + str(total_failed) + '\n跳过: ' + str(total_skipped)
            self.root.after(0, lambda: messagebox.showinfo('同步报告', msg))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror('错误', '同步过程发生异常: ' + str(e)))
        finally:
            self.root.after(0, self._on_sync_finished)

    def _on_sync_finished(self):
        self.cancel_btn.config(state=tk.DISABLED)
        self.compare_btn.config(state=tk.NORMAL)
        self.preview_btn.config(state=tk.NORMAL)
        self.sync_btn.config(state=tk.NORMAL)
        self.status_label.config(text='同步任务结束')

    def _cancel_task(self):
        self.cancel_flag = True
        self.status_label.config(text='正在取消...')

    def _show_logs(self):
        from myfilesync.ui.log_dialog import LogDialog
        LogDialog(self.root, self.logger.log_file)

def run_app():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
