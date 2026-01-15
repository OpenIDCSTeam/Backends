class SDConfig:
    def __init__(self, **kwargs):
        self.hdd_name: str = ""
        self.hdd_size: int = 0
        self.hdd_flag: int = 0  # 挂载状态
        self.uid_scsi: str = ""  # scsi设备号，如 "scsi1"
        self.hdd_file: str = ""  # 磁盘文件名，如 "vm-100-disk-1.qcow2"
        self.__load__(**kwargs)

    def __save__(self):
        return {
            "hdd_name": self.hdd_name,
            "hdd_size": self.hdd_size,
            "hdd_flag": self.hdd_flag,
            "uid_scsi": self.uid_scsi,
            "hdd_file": self.hdd_file
        }

    # 加载数据 ===============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
