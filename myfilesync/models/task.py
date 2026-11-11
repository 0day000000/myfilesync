import json
import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class SyncPair:
    left_dir: str = ''
    right_dir: str = ''

    def to_dict(self):
        return {'left_dir': self.left_dir, 'right_dir': self.right_dir}

    @classmethod
    def from_dict(cls, d):
        return cls(left_dir=d.get('left_dir', ''), right_dir=d.get('right_dir', ''))

@dataclass
class TaskConfig:
    name: str = '默认任务'
    pairs: List[SyncPair] = field(default_factory=lambda: [SyncPair()])
    sync_mode: str = 'mirror'
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=lambda: ['*.tmp', '*.log', '__pycache__', '.git'])
    compare_by_content: bool = False
    use_trash: bool = True

    def to_dict(self):
        return {
            'name': self.name,
            'pairs': [p.to_dict() for p in self.pairs],
            'sync_mode': self.sync_mode,
            'include_patterns': self.include_patterns,
            'exclude_patterns': self.exclude_patterns,
            'compare_by_content': self.compare_by_content,
            'use_trash': self.use_trash
        }

    @classmethod
    def from_dict(cls, d):
        raw_pairs = d.get('pairs', [])
        pairs = [SyncPair.from_dict(p) for p in raw_pairs] if raw_pairs else [SyncPair(left_dir=d.get('left_dir', ''), right_dir=d.get('right_dir', ''))]
        if not pairs:
            pairs = [SyncPair()]
        return cls(
            name=d.get('name', '默认任务'),
            pairs=pairs,
            sync_mode=d.get('sync_mode', 'mirror'),
            include_patterns=d.get('include_patterns', []),
            exclude_patterns=d.get('exclude_patterns', ['*.tmp', '*.log', '__pycache__', '.git']),
            compare_by_content=d.get('compare_by_content', False),
            use_trash=d.get('use_trash', True)
        )

class TaskManager:
    def __init__(self, config_file=None):
        if not config_file:
            appdata = os.getenv('APPDATA') or os.path.expanduser('~')
            config_dir = os.path.join(appdata, 'MyFileSync')
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, 'tasks.json')
        self.config_file = config_file
        self.tasks: List[TaskConfig] = []
        self.load()

    def load(self):
        self.tasks = []
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        self.tasks.append(TaskConfig.from_dict(item))
            except Exception:
                pass
        if not self.tasks:
            self.tasks.append(TaskConfig(name='默认任务'))

    def save(self):
        try:
            data = [t.to_dict() for t in self.tasks]
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print('保存任务配置失败: ' + str(e))
