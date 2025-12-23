class IMConfig:
    def __init__(self, **kwargs):
        self.iso_name: str = ""
        self.iso_file: str = ""
        self.iso_hint: str = ""
        self.__load__(**kwargs)

    def __save__(self):
        return {
            "iso_name": self.iso_name,
            "iso_file": self.iso_file,
            "iso_hint": self.iso_hint,
        }

    # 加载数据 ===============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
