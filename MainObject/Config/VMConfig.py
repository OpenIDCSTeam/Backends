import json
import random

from MainObject.Config.NCConfig import NCConfig
from MainObject.Config.PortData import PortData
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.WebProxy import WebProxy


class VMConfig:
    @staticmethod
    def generate_random_vnc_port():
        """生成随机VNC端口，范围5900-6999"""
        return str(random.randint(5900, 6999))

    def __init__(self, **kwargs):
        # 机器配置 ===========================
        self.vm_uuid = ""  # 设置虚拟机名-UUID
        self.os_name = ""  # 设置SYS操作系统名
        self.os_pass = ""  # 设置SYS系统的密码
        # 远程连接 ===========================
        self.vc_port = self.generate_random_vnc_port()  # 分配VNC远程的端口，默认随机生成
        self.vc_pass = ""  # 分配VNC远程的密码
        # 资源配置 ===========================
        self.cpu_num = 2  # 分配的处理器核心数，默认2
        self.cpu_per = 50  # 分配的处理器百分比
        self.gpu_num = 0  # 分配物理卡(0-没有)，默认0
        self.gpu_mem = 2048  # 分配显存值(0-没有)，默认2048MB
        self.mem_num = 2048  # 分配内存数(单位MB)，默认2048MB
        self.hdd_num = 20480  # 分配硬盘数(单位MB)，默认20480MB
        # 网络配置 ===========================
        self.speed_u = 100  # 上行带宽(单位Mbps)
        self.speed_d = 100  # 下行带宽(单位Mbps)
        self.flu_num = 102400  # 分配流量(单位Mbps)，默认102400
        self.nat_num = 100  # 分配端口(0-不分配)，默认100
        self.web_num = 100  # 分配代理(0-不分配)，默认100
        # 网卡配置 ===========================
        self.nic_all: dict[str, NCConfig] = {}
        self.hdd_all: dict[str, SDConfig] = {}
        self.nat_all: list[PortData] = []
        self.web_all: list[WebProxy] = []
        # 加载数据 ===========================
        self.__load__(**kwargs)

    # 加载数据 ===============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # 如果VNC端口为空，则重新生成随机端口
        if not self.vc_port:
            self.vc_port = self.generate_random_vnc_port()

        nic_list = self.nic_all
        hdd_list = self.hdd_all
        nat_list = self.nat_all
        web_list = self.web_all
        self.nic_all = {}
        self.hdd_all = {}
        self.nat_all = []
        self.web_all = []
        for nic in nic_list:
            nic_data = nic_list[nic]
            if type(nic_data) is dict:
                self.nic_all[nic] = NCConfig(**nic_data)
            else:
                self.nic_all[nic] = nic_data
        for hdd in hdd_list:
            hdd_data = hdd_list[hdd]
            if type(hdd_data) is dict:
                self.hdd_all[hdd] = SDConfig(**hdd_data)
            else:
                self.hdd_all[hdd] = hdd_data
        for nat in nat_list:
            if type(nat) is dict:
                nat_obj = PortData()
                nat_obj.__load__(**nat)
                self.nat_all.append(nat_obj)
            else:
                self.nat_all.append(nat)
        for web in web_list:
            if type(web) is dict:
                web_obj = WebProxy()
                web_obj.__load__(**web)
                self.web_all.append(web_obj)
            else:
                self.web_all.append(web)

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
            "os_pass": self.os_pass,
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
            "nic_all": {k: v.__dict__() if hasattr(v, '__dict__') and callable(getattr(v, '__dict__')) else v for k, v
                        in self.nic_all.items()},
            "hdd_all": {k: v.__dict__() if hasattr(v, '__dict__') and callable(getattr(v, '__dict__')) else v for k, v
                        in self.hdd_all.items()},
            "nat_all": [n.__save__() if hasattr(n, '__save__') and callable(getattr(n, '__save__')) else n for n in self.nat_all],
            "web_all": [w.__save__() if hasattr(w, '__save__') and callable(getattr(w, '__save__')) else w for w in self.web_all],
        }

    # 转换为字符串 ===========================
    def __str__(self):
        return json.dumps(self.__dict__())
