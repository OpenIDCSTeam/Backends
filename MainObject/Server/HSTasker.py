import abc

from MainObject.Public.ZMessage import ZMessage


class HSTasker(abc.ABC):
    def __init__(self, config=None, /, **kwargs):
        self.process = {}  # 任务所需信息
        self.success: bool = False
        self.results: int = 0
        self.message: ZMessage | None = None
        # 加载传入的参数 =======================
        if config is not None:
            self.__read__(config)
        self.__load__(**kwargs)

    def __save__(self):
        return {
            "process": self.process,
            "success": self.success,
            "results": self.results,
            "message": self.message.__save__() if self.message else None,
        }

    # 加载数据 ==============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # 读取数据 =============================
    def __read__(self, data: dict):
        for key, value in data.items():
            if key in self.__dict__:
                setattr(self, key, value)

    # 检查任务状态 =========================
    def check_task(self):
        pass

    # 开始执行任务 =========================
    def start_task(self):
        pass

    # 停止执行任务 =========================
    def force_stop(self):
        pass
