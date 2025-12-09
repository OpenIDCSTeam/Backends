import json
from MainObject.Config.VMPowers import VMPowers as VPower


class HWStatus:
    def __init__(self, config=None, /, **kwargs):
        # 基础数据 ============================
        self.ac_status: VPower = VPower.UNKNOWN
        self.cpu_model: str = ""  # 当前CPU名称
        self.cpu_total: int = 0  # 当前核心总计
        self.cpu_usage: int = 0  # 当前核心已用
        self.mem_total: int = 0  # 当前内存总计
        self.mem_usage: int = 0  # 当前内存已用
        self.hdd_total: int = 0  # 当前磁盘总计
        self.hdd_usage: int = 0  # 当前磁盘已用
        self.ext_usage: dict = {}  # 数据盘已用
        # 网络信息 ============================
        self.flu_total: int = 0  # 当前流量总计
        self.flu_usage: int = 0  # 当前流量已用
        self.nat_total: int = 0  # 当前端口总计
        self.nat_usage: int = 0  # 当前端口已用
        self.web_total: int = 0  # 当前代理总计
        self.web_usage: int = 0  # 当前代理已用
        # 其他信息 ============================
        self.gpu_usage: dict = {}  # GPU 使用率
        self.gpu_total: int = 0  # 当前显卡数量
        self.network_u: int = 0  # 当前上行带宽
        self.network_d: int = 0  # 当前下行带宽
        self.network_a: int = 0  # 当前网卡带宽
        self.cpu_heats: int = 0  # 当前核心温度
        self.cpu_power: int = 0  # 当前核心功耗
        # 加载传入的参数 ======================
        if config is not None:
            self.__read__(config)
        self.__load__(**kwargs)

    # 加载数据 ================================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == "ac_status" and isinstance(value, str):
                    # 特殊处理ac_status字段，将字符串转换为枚举
                    try:
                        self.ac_status = VPower[value]
                    except KeyError:
                        self.ac_status = VPower.UNKNOWN
                else:
                    setattr(self, key, value)

    # 读取数据 ================================
    def __read__(self, data: dict):
        for key, value in data.items():
            if key in self.__dict__:
                setattr(self, key, value)

    # 转换为字典 ==============================
    def __dict__(self):
        return {
            "ac_status": VPower.to_json(
                self.ac_status),
            "cpu_model": self.cpu_model,
            "cpu_total": self.cpu_total,
            "cpu_usage": self.cpu_usage,
            "mem_total": self.mem_total,
            "mem_usage": self.mem_usage,
            "hdd_total": self.hdd_total,
            "hdd_usage": self.hdd_usage,
            "ext_usage": self.ext_usage,
            "flu_total": self.flu_total,
            "flu_usage": self.flu_usage,
            "nat_total": self.nat_total,
            "nat_usage": self.nat_usage,
            "web_total": self.web_total,
            "web_usage": self.web_usage,
            "gpu_usage": self.gpu_usage,
            "gpu_total": self.gpu_total,
            "network_u": self.network_u,
            "network_d": self.network_d,
            "network_a": self.network_a,
            "cpu_heats": self.cpu_heats,
            "cpu_power": self.cpu_power,
        }

    # 转换为文本 ==============================
    def __str__(self):
        return json.dumps(self.__dict__())
