from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class FileStatus(Enum):
    LEFT_ONLY = '仅左侧存在'
    RIGHT_ONLY = '仅右侧存在'
    IDENTICAL = '两边文件相同'
    DIFFERENT = '两边文件不同'
    LEFT_NEWER = '左侧文件较新'
    RIGHT_NEWER = '右侧文件较新'
    CONFLICT = '文件类型不同或冲突'

@dataclass
class FileItem:
    rel_path: str
    left_path: Optional[str]
    right_path: Optional[str]
    is_dir: bool
    left_size: int = 0
    right_size: int = 0
    left_mtime: float = 0.0
    right_mtime: float = 0.0
    status: FileStatus = FileStatus.IDENTICAL
    hash_checked: bool = False
    left_hash: str = ''
    right_hash: str = ''
