import json


class HSConfig:
    def __init__(self, config=None, /, **kwargs):
        self.server_name: str = ""  # 服务器名称
        self.server_type: str = ""  # 服务器类型（Workstation/vSphereESXi/LXD等）
        self.server_addr: str = ""  # 服务器地址（ESXi主机IP地址）
        self.server_user: str = ""  # 服务器用户（ESXi用户名，通常是root）
        self.server_pass: str = ""  # 服务器密码（ESXi密码）
        self.server_port: int = 443  # 服务器端口（ESXi API端口，默认443）
        self.filter_name: str = ""  # 过滤器名称
        self.images_path: str = ""  # 镜像存储池（ESXi: 数据存储中的ISO目录，如datastore1/ISO）
        self.system_path: str = ""  # 系统存储池（ESXi: 数据存储名称，如datastore1）
        self.backup_path: str = ""  # 备份存储池（ESXi: 使用快照，此路径用于导出备份）
        self.extern_path: str = ""  # 数据存储池
        self.launch_path: str = ""  # 二进制路径（ESXi不需要）
        self.network_nat: str = ""  # NAT网络NIC（ESXi: 虚拟交换机或端口组名称）
        self.network_pub: str = ""  # PUB网络NIC（ESXi: 虚拟交换机或端口组名称）
        self.i_kuai_addr: str = ""  # 爱快OS地址
        self.i_kuai_user: str = ""  # 爱快OS用户
        self.i_kuai_pass: str = ""  # 爱快OS密码
        self.ports_start: int = 0  # TCP端口起始
        self.ports_close: int = 0  # TCP端口结束
        self.remote_port: int = 0  # VNC服务端口
        self.limits_nums: int = 0  # VMS虚拟数量
        self.public_addr: list = []  # 公共IPV46
        self.server_dnss: list = []  # DNS服务器
        self.extend_data: dict = {}  # API可选项
        self.system_maps: dict[str, list] = {}
        self.images_maps: dict[str, str] = {}  # ISO镜像映射: 显示名称->文件名(xxx.iso)
        self.ipaddr_maps: dict[str, dict] = {}
        # self.ipaddr_maps：{
        #     "Set1": {
        #         "vers": "ipv4",
        #         "type": "nat",
        #         "gate": "192.168.1.1",
        #         "mask": "255.255.255.0",
        #         "from": "192.168.1.100",
        #         "nums": 100,
        #     }
        # }
        self.ipaddr_dnss: list = ["119.29.29.29", "223.5.5.5"]
        # 加载传入的参数 =======================
        if config is not None:
            self.__read__(config)
        self.__load__(**kwargs)

    # 加载数据 =================================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # 读取数据 =================================
    def __read__(self, data: dict):
        for key, value in data.items():
            if key in self.__save__:
                setattr(self, key, value)

    # 转换为字典 ===============================
    def __save__(self):
        return {
            "server_name": self.server_name,
            "server_type": self.server_type,
            "server_addr": self.server_addr,
            "server_user": self.server_user,
            "server_pass": self.server_pass,
            "server_port": self.server_port,
            "filter_name": self.filter_name,
            "images_path": self.images_path,
            "system_path": self.system_path,
            "backup_path": self.backup_path,
            "extern_path": self.extern_path,
            "launch_path": self.launch_path,
            "network_nat": self.network_nat,
            "network_pub": self.network_pub,
            "i_kuai_addr": self.i_kuai_addr,
            "i_kuai_user": self.i_kuai_user,
            "i_kuai_pass": self.i_kuai_pass,
            "ports_start": self.ports_start,
            "ports_close": self.ports_close,
            "remote_port": self.remote_port,
            "limits_nums": self.limits_nums,
            "system_maps": self.system_maps,
            "images_maps": self.images_maps,
            "ipaddr_maps": self.ipaddr_maps,
            "ipaddr_dnss": self.ipaddr_dnss,
            "public_addr": self.public_addr,
            "extend_data": self.extend_data,
            "server_dnss": self.server_dnss,
        }

    # 转换为字符串 ===========================
    def __str__(self):
        return json.dumps(self.__save__())
