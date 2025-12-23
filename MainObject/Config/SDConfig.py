class SDConfig:
    def __init__(self, **kwargs):
        self.hdd_name: str = ""
        self.hdd_size: int = 0
        self.hdd_flag: int = 0  # 挂载状态
        self.__load__(**kwargs)

    def __save__(self):
        return {
            "hdd_name": self.hdd_name,
            "hdd_size": self.hdd_size,
            "hdd_flag": self.hdd_flag
        }

    # 加载数据 ===============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
