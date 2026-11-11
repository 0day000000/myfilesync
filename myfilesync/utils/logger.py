import os
import logging
from datetime import datetime

class SyncLogger:
    def __init__(self, log_dir=None):
        if not log_dir:
            appdata = os.getenv('APPDATA') or os.path.expanduser('~')
            log_dir = os.path.join(appdata, 'MyFileSync', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, 'sync.log')
        
        self.logger = logging.getLogger('MyFileSync')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            fh = logging.FileHandler(self.log_file, encoding='utf-8')
            fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            self.logger.addHandler(fh)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

    def warning(self, msg):
        self.logger.warning(msg)
