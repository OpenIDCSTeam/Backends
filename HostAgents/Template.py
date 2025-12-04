import abc
from HostObject.HSConfig import HSConfig
from HostObject.HSTasker import HSTasker
from HostObject.VMPowers import VMPowers
from HostObject.HWStatus import HWStatus
from HostObject.ZMessage import ZMessage
from HostObject.VMConfig import VMConfig


class BaseServer(abc.ABC):
    def __init__(self, config: HSConfig, **kwargs):
        # 宿主机配置 =========================================
        self.hs_config: HSConfig | None = config  # 物理机配置
        self.hs_status: list[HWStatus] = []  # Hosts主机使用率
        self.hs_saving: dict[str, ...] = {}  # Hosts存储的配置
        # 虚拟机配置 =========================================
        self.vm_saving: dict[str, VMConfig] = {}  # 存储的配置
        self.vm_status: dict[str, list[HWStatus]] = {}  # 状态
        self.vm_tasker: list[HSTasker] = []  # SUB搜集任务列表
        # 日志记录 ===========================================
        self.save_logs: list[ZMessage] = []  # SUB搜集日志记录
        # 加载数据 ===========================================
        self.__load__(**kwargs)

    # 转换为字典 =============================================
    @staticmethod
    def __to_dict__(obj):
        """辅助方法：将对象转换为可序列化的字典"""
        if obj is None:
            return None
        # 处理列表类型，递归转换每个元素
        if isinstance(obj, list):
            return [BaseServer.__to_dict__(item) for item in obj]
        if hasattr(obj, '__dict__') and callable(getattr(obj, '__dict__')):
            return obj.__dict__()
        return obj

    def __dict__(self):
        return {
            "hs_config": self.__to_dict__(self.hs_config),
            "hs_saving": {
                string: self.__to_dict__(saving)
                for string, saving in self.hs_saving.items()
            },
            "hs_status": [
                self.__to_dict__(status)
                for status in self.hs_status
            ],
            "vm_saving": {
                string: self.__to_dict__(saving)
                for string, saving in self.vm_saving.items()
            },
            "vm_status": {
                string: self.__to_dict__(record)
                for string, record in self.vm_status.items()
            },
            "vm_tasker": [
                self.__to_dict__(tasker)
                for tasker in self.vm_tasker
            ],
            "save_logs": [
                self.__to_dict__(logger)
                for logger in self.save_logs
            ]
        }

    # 加载数据 ===============================================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # 读取数据 ===============================================
    def __read__(self, data: dict):
        self.hs_config = HSConfig(data["hs_config"])
        self.hs_saving = {
            k: VMConfig(**v) for k, v in data["hs_saving"].items()
        }
        self.hs_status = data["hs_status"]
        self.vm_saving = data["vm_saving"]
        self.vm_status = data["vm_status"]
        self.vm_tasker = data["vm_tasker"]
        self.save_logs = data["save_logs"]

    # 执行此任务 =============================================
    def Crontabs(self) -> ZMessage:
        pass

    # 宿主机状态 =============================================
    def HSStatus(self) -> HWStatus:
        pass

    # 初始宿主机 =============================================
    def HSCreate(self) -> ZMessage:
        pass

    # 还原宿主机 =============================================
    def HSDelete(self) -> ZMessage:
        pass

    # 读取宿主机 =============================================
    def HSLoader(self) -> ZMessage:
        pass

    # 卸载宿主机 =============================================
    def HSUnload(self) -> ZMessage:
        pass

    # 宿主机操作 =============================================
    def HSAction(self) -> ZMessage:
        pass

    # 创建虚拟机 =============================================
    def VMCreate(self, config: VMConfig) -> ZMessage:
        pass

    # 配置虚拟机 ==========================================
    def VMUpdate(self, config: VMConfig) -> ZMessage:
        pass

    # 虚拟机列出 ==========================================
    def VMStatus(self, select: str = "") -> dict[HWStatus]:
        pass

    # 删除虚拟机 ==========================================
    def VMDelete(self, select: str) -> ZMessage:
        pass

    # 虚拟机电源 ==========================================
    def VMPowers(self, select: str, p: VMPowers) -> ZMessage:
        pass

    # 虚拟机电源 ==========================================
    def VConsole(self, select: str) -> str:
        pass
