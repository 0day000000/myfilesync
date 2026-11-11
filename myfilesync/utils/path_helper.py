import os
import stat

def check_path_validity(path_str):
    if not path_str:
        return False, '路径为空'
    if not os.path.exists(path_str):
        return False, '路径不存在'
    if not os.path.isdir(path_str):
        return False, '路径不是一个有效的文件夹'
    try:
        test_file = os.path.join(path_str, '.myfilesync_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
    except Exception as e:
        return False, f'路径无读写权限: {e}'
    return True, '正常'

def is_network_path(path_str):
    if not path_str:
        return False
    abs_path = os.path.abspath(path_str)
    if abs_path.startswith('\\\\'):
        return True
    try:
        import ctypes
        drive_letter = abs_path[:3]
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter)
        # DRIVE_REMOTE = 4
        return drive_type == 4
    except Exception:
        return False
