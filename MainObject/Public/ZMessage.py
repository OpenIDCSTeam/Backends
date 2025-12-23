import enum
import json


class ZActions(enum.Enum):
    HS_CREATE = "HS_CREATE"
    HS_DELETE = "HS_DELETE"
    HS_UPDATE = "HS_UPDATE"
    HS_SAVING = "HS_SAVING"
    HS_LOADER = "HS_LOADER"
    HS_STATUS = "HS_STATUS"
    VM_CREATE = "VM_CREATE"
    VM_DELETE = "VM_DELETE"
    VM_UPDATE = "VM_UPDATE"
    VM_POWERS = "VM_POWERS"


class ZMessage:
    def __init__(self, config=None, /, **kwargs):
        self.success: bool = True
        self.actions: str = ""
        self.message: str = ""
        self.results: dict = {}
        self.execute: Exception | None = None
        self.__load__(**kwargs)
        # 加载传入的参数 ====================
        if config is not None:
            self.__read__(config)
        self.__load__(**kwargs)

    # 加载数据 ==============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # 读取数据 ==============================
    def __read__(self, data: dict):
        for key, value in data.items():
            if key in self.__dict__:
                setattr(self, key, value)

    # 转换为字典 ============================
    def to_dict(self):
        return {
            "success": self.success,
            "actions": self.actions,
            "message": self.message,
            "results": self.results,
            "execute": str(self.execute) if self.execute else None
        }

    def __save__(self):
        return self.to_dict()

    # 转换为字符串 ==========================
    def __str__(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)
