import datetime


class VMBackup:
    def __init__(self, **kwargs):
        self.backup_time = 0
        self.backup_name = ""
        self.backup_hint = ""
        self.old_os_name = ""
        self.__load__(**kwargs)

    def __save__(self):
        # 如果backup_time是datetime对象，转换为Unix时间戳（秒）
        backup_time_value = self.backup_time
        if isinstance(self.backup_time, datetime.datetime):
            backup_time_value = int(self.backup_time.timestamp())
        
        return {
            "backup_time": backup_time_value,
            "backup_name": self.backup_name,
            "backup_hint": self.backup_hint,
            "old_os_name": self.old_os_name,
        }

    # 加载数据 ===============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                # 如果是backup_time字段，根据类型转换为datetime对象
                if key == "backup_time":
                    if isinstance(value, str):
                        # 兼容旧的字符串格式
                        try:
                            setattr(self, key, datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S"))
                        except ValueError:
                            setattr(self, key, value)
                    elif isinstance(value, (int, float)):
                        # Unix时间戳转换为datetime对象
                        try:
                            setattr(self, key, datetime.datetime.fromtimestamp(value))
                        except (ValueError, OSError):
                            setattr(self, key, value)
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)
