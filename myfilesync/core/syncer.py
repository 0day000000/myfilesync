import os
import shutil
import tempfile
from typing import List, Callable, Optional
from myfilesync.models.comparison import FileItem, FileStatus
from myfilesync.utils.logger import SyncLogger

class SyncEngine:
    def __init__(self, left_dir: str, right_dir: str, logger: SyncLogger, use_trash: bool = True):
        self.left_dir = os.path.abspath(left_dir)
        self.right_dir = os.path.abspath(right_dir)
        self.logger = logger
        self.use_trash = use_trash

    def execute_mirror(self, items: List[FileItem], progress_callback: Optional[Callable[[int, int, str], None]] = None, cancel_check: Callable[[], bool] = lambda: False) -> dict:
        stats = {'copied': 0, 'deleted': 0, 'failed': 0, 'skipped': 0}
        total = len(items)

        self.logger.info('开始镜像同步: 左侧 [' + self.left_dir + '] -> 右侧 [' + self.right_dir + ']')

        for idx, item in enumerate(items):
            if cancel_check():
                self.logger.warning('用户取消了同步任务')
                break

            if progress_callback:
                progress_callback(idx + 1, total, item.rel_path)

            try:
                target_path = os.path.join(self.right_dir, item.rel_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                if item.status in (FileStatus.LEFT_ONLY, FileStatus.LEFT_NEWER, FileStatus.DIFFERENT, FileStatus.CONFLICT):
                    if item.left_path and os.path.exists(item.left_path):
                        tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(target_path), prefix='.myfilesync_')
                        os.close(tmp_fd)
                        try:
                            shutil.copy2(item.left_path, tmp_path)
                            if os.path.exists(target_path):
                                os.remove(target_path)
                            os.replace(tmp_path, target_path)
                            stats['copied'] += 1
                            self.logger.info('复制文件成功: ' + item.rel_path)
                        except Exception as ex:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
                            raise ex
                    else:
                        stats['skipped'] += 1
                elif item.status == FileStatus.RIGHT_ONLY:
                    if os.path.exists(target_path):
                        if os.path.isfile(target_path) or os.path.islink(target_path):
                            os.remove(target_path)
                        elif os.path.isdir(target_path):
                            shutil.rmtree(target_path, ignore_errors=True)
                        stats['deleted'] += 1
                        self.logger.info('删除右侧多余文件: ' + item.rel_path)
                    else:
                        stats['skipped'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                stats['failed'] += 1
                self.logger.error('同步文件失败 [' + item.rel_path + ']: ' + str(e))

        self.logger.info('镜像同步完成. 统计: 成功复制=' + str(stats['copied']) + ', 删除=' + str(stats['deleted']) + ', 失败=' + str(stats['failed']) + ', 跳过=' + str(stats['skipped']))
        return stats
