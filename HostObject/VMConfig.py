import json

from HostObject.ZMConfig import NCConfig, SDConfig


class VMConfig:
    def __init__(self, **kwargs):
        # 机器配置 ===========================
        self.vm_uuid = ""  # 设置虚拟机名-UUID
        self.os_name = ""  # 设置SYS操作系统名
        # 资源配置 ===========================
        self.cpu_num = 0  # 分配的处理器核心数
        self.cpu_per = 0  # 分配的处理器百分比
        self.gpu_num = 0  # 分配物理卡(0-没有)
        self.gpu_mem = 0  # 分配显存值(0-没有)
        self.mem_num = 0  # 分配内存数(单位MB)
        self.hdd_num = 0  # 分配硬盘数(单位MB)
        # 网络配置 ===========================
        self.speed_u = 0  # 上行带宽(单位Mbps)
        self.speed_d = 0  # 下行带宽(单位Mbps)
        self.flu_num = 0  # 分配流量(单位Mbps)
        self.nat_num = 0  # 分配端口(0-不分配)
        self.web_num = 0  # 分配代理(0-不分配)
        # 远程连接 ===========================
        self.vc_port = ""  # 分配VNC远程的端口
        self.vc_pass = ""  # 分配VNC远程的密码
        # 网卡配置 ===========================
        self.nic_all: dict[str, NCConfig] = {}
        self.hdd_all: dict[str, SDConfig] = {}
        # 加载数据 ===========================
        self.__load__(**kwargs)

    # 加载数据 ===============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # 读取数据 ===============================
    def __read__(self, data: dict):
        for key, value in data.items():
            if key in self.__dict__:
                setattr(self, key, value)

    # 转换为字典 =============================
    def __dict__(self):
        return {
            "vm_uuid": self.vm_uuid,
            "os_name": self.os_name,
            # 资源配置 =============
            "cpu_num": self.cpu_num,
            "cpu_per": self.cpu_per,
            "gpu_num": self.gpu_num,
            "gpu_mem": self.gpu_mem,
            "mem_num": self.mem_num,
            "hdd_num": self.hdd_num,
            # 网络配置 =============
            "speed_u": self.speed_u,
            "speed_d": self.speed_d,
            "flu_num": self.flu_num,
            "nat_num": self.nat_num,
            "web_num": self.web_num,
            # 远程连接 =============
            "vc_port": self.vc_port,
            "vc_pass": self.vc_pass,
            # 网卡配置 =============
            "nic_all": {k: v.__dict__() for k, v in self.nic_all.items()},
            "hdd_all": {k: v.__dict__() for k, v in self.hdd_all.items()},
        }

    # 转换为字符串 ===========================
    def __str__(self):
        return json.dumps(self.__dict__())
