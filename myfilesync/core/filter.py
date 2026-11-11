import pathlib
import os
import fnmatch

class FileFilter:
    def __init__(self, include_patterns=None, exclude_patterns=None):
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or ['*.tmp', '*.log', '__pycache__', '.git', '.myfilesync_test']

    def should_ignore(self, rel_path, is_dir=False):
        parts = pathlib.PurePath(rel_path).parts
        name = os.path.basename(rel_path)

        for part in parts:
            for pat in self.exclude_patterns:
                if fnmatch.fnmatch(part, pat) or fnmatch.fnmatch(name, pat):
                    return True
        
        if self.include_patterns:
            matched = False
            for pat in self.include_patterns:
                if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_path, pat):
                    matched = True
                    break
            if not matched:
                return True

        return False
