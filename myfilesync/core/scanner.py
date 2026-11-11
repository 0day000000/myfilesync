import pathlib
import os
import hashlib
from typing import Dict, List, Callable, Optional
from myfilesync.models.comparison import FileItem, FileStatus
from myfilesync.core.filter import FileFilter
from myfilesync.utils.path_helper import is_network_path

def compute_file_sha256(filepath: str, block_size=65536) -> str:
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while True:
                buf = f.read(block_size)
                if not buf:
                    break
                hasher.update(buf)
        return hasher.hexdigest()
    except Exception:
        return ''

class FolderScanner:
    def __init__(self, left_dir: str, right_dir: str, file_filter: FileFilter, compare_by_content: bool = False):
        self.left_dir = os.path.abspath(left_dir)
        self.right_dir = os.path.abspath(right_dir)
        self.file_filter = file_filter
        self.compare_by_content = compare_by_content

    def _scan_single_dir(self, root_dir: str, cancel_check: Callable[[], bool] = lambda: False) -> Dict[str, dict]:
        result = {}
        if not os.path.exists(root_dir):
            return result
        
        # 安全检查：网络共享断连保护
        if is_network_path(root_dir):
            try:
                os.listdir(root_dir)
            except Exception:
                raise RuntimeError(f'网络共享目录无法访问或已断开: {root_dir}')

        base_len = len(root_dir)
        for parent, dirs, files in os.walk(root_dir, topdown=True, followlinks=False):
            if cancel_check():
                break
            
            # 过滤目录
            dirs[:] = [d for d in dirs if not self.file_filter.should_ignore(os.path.relpath(os.path.join(parent, d), root_dir), is_dir=True)]

            for name in files:
                if cancel_check():
                    break
                full_path = os.path.join(parent, name)
                if os.path.islink(full_path):
                    continue
                rel_path = os.path.relpath(full_path, root_dir)
                if self.file_filter.should_ignore(rel_path, is_dir=False):
                    continue
                
                try:
                    stat = os.stat(full_path)
                    result[rel_path] = {
                        'path': full_path,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                        'is_dir': False
                    }
                except Exception:
                    pass
        return result

    def compare(self, progress_callback: Optional[Callable[[str], None]] = None, cancel_check: Callable[[], bool] = lambda: False) -> List[FileItem]:
        if progress_callback:
            progress_callback('正在扫描左侧文件夹...')
        left_files = self._scan_single_dir(self.left_dir, cancel_check)
        
        if cancel_check():
            return []

        if progress_callback:
            progress_callback('正在扫描右侧文件夹...')
        right_files = self._scan_single_dir(self.right_dir, cancel_check)

        if cancel_check():
            return []

        if progress_callback:
            progress_callback('正在对比差异...')

        all_keys = set(left_files.keys()).union(set(right_files.keys()))
        items: List[FileItem] = []

        for rel_path in sorted(all_keys):
            if cancel_check():
                break

            l_info = left_files.get(rel_path)
            r_info = right_files.get(rel_path)

            l_path = l_info['path'] if l_info else None
            r_path = r_info['path'] if r_info else None
            l_size = l_info['size'] if l_info else 0
            r_size = r_info['size'] if r_info else 0
            l_mtime = l_info['mtime'] if l_info else 0.0
            r_mtime = r_info['mtime'] if r_info else 0.0

            if l_info and not r_info:
                status = FileStatus.LEFT_ONLY
            elif not l_info and r_info:
                status = FileStatus.RIGHT_ONLY
            else:
                # 两边都有
                if l_size == r_size and abs(l_mtime - r_mtime) < 2.0:
                    status = FileStatus.IDENTICAL
                else:
                    if l_mtime > r_mtime + 2.0:
                        status = FileStatus.LEFT_NEWER
                    elif r_mtime > l_mtime + 2.0:
                        status = FileStatus.RIGHT_NEWER
                    else:
                        status = FileStatus.DIFFERENT

                # 可选内容校验
                if status != FileStatus.IDENTICAL and self.compare_by_content and l_path and r_path:
                    l_hash = compute_file_sha256(l_path)
                    r_hash = compute_file_sha256(r_path)
                    if l_hash and r_hash and l_hash == r_hash:
                        status = FileStatus.IDENTICAL

            item = FileItem(
                rel_path=rel_path,
                left_path=l_path,
                right_path=r_path,
                is_dir=False,
                left_size=l_size,
                right_size=r_size,
                left_mtime=l_mtime,
                right_mtime=r_mtime,
                status=status
            )
            items.append(item)

        return items
