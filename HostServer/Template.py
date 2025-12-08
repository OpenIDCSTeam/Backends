import abc
from MainObject.Config.HSConfig import HSConfig
from MainObject.Server.HSTasker import HSTasker
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from HostModule.NetsManage import NetsManage


class BaseServer(abc.ABC):
    def __init__(self, config: HSConfig, **kwargs):
        # 宿主机配置 =========================================
        self.hs_config: HSConfig | None = config  # 物理机配置
        self.hs_status: list[HWStatus] = []  # Hosts主机使用率
        self.hs_logger: list[ZMessage] = []  # SUB搜集日志记录
        # 虚拟机配置 =========================================
        self.vm_saving: dict[str, VMConfig] = {}  # 存储的配置
        self.vm_status: dict[str, list[HWStatus]] = {}  # 状态
        self.vm_tasker: list[HSTasker] = []  # SUB搜集任务列表
        # 数据库引用 =========================================
        self.db = kwargs.get('db', None)  # 数据库操作实例
        self.hs_name = kwargs.get('hs_name', '')  # 主机名称
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
        if hasattr(obj, '__dict__'):
            if callable(getattr(obj, '__dict__')):
                return obj.__dict__()
        return obj

    # 转换为字典 =============================================
    def __dict__(self):
        return {
            "hs_config": self.__to_dict__(self.hs_config),
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
                for logger in self.hs_logger
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
        self.hs_status = data["hs_status"]
        self.vm_saving = data["vm_saving"]
        self.vm_status = data["vm_status"]
        self.vm_tasker = data["vm_tasker"]
        self.hs_logger = data["save_logs"]

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

    # 静态IP #########################################################
    def NCStatic(self, ip, mac, uuid, flag=True) -> ZMessage:
        nc_server = NetsManage(
            self.hs_config.i_kuai_addr,
            self.hs_config.i_kuai_user,
            self.hs_config.i_kuai_pass)
        if flag:
            nc_server.add_dhcp(ip, mac, comment=uuid)
        else:
            nc_server.del_dhcp(ip)
        return ZMessage(success=True, action="NCStatic")

    # 端口映射 #######################################################
    def PortsMap(self, ip, in_pt, ex_pt=None,
                 flag=True) -> ZMessage:
        nc_server = NetsManage(
            self.hs_config.i_kuai_addr,
            self.hs_config.i_kuai_user,
            self.hs_config.i_kuai_pass)
        if flag:
            nc_server.add_port(ex_pt, ip, in_pt)
        else:
            nc_server.del_port(ex_pt, ip)
        return ZMessage(success=True, action="PortsMap")

    # 创建虚拟机 #####################################################
    def VMCreate(self, config: VMConfig) -> ZMessage:
        pass

    # 配置虚拟机 #####################################################
    def VMUpdate(self, config: VMConfig) -> ZMessage:
        pass

    # 虚拟机列出 #####################################################
    def VMStatus(self, select: str = "") -> dict[str, list[HWStatus]]:
        pass

    # 删除虚拟机 #####################################################
    def VMDelete(self, select: str) -> ZMessage:
        pass

    # 虚拟机电源 #####################################################
    def VMPowers(self, select: str, p: VMPowers) -> ZMessage:
        pass

    # 虚拟机控制 #####################################################
    def VConsole(self, select: str) -> str:
        pass

    # 安装虚拟机 #####################################################
    def VInstall(self, select: str) -> ZMessage:
        pass

    # 保存数据到数据库 ###############################################
    def data_set(self) -> bool:
        """保存当前数据到数据库"""
        if self.db and self.hs_name:
            return self.db.save_host_full_data(self.hs_name, self.__dict__())
        return False

    # 从数据库重新加载数据 ###########################################
    def data_get(self) -> bool:
        """从数据库重新加载虚拟机数据"""
        if self.db and self.hs_name:
            try:
                # 从数据库获取主机状态
                hs_status_data = self.db.get_hs_status(self.hs_name)
                if hs_status_data:
                    self.hs_status = hs_status_data

                # 从数据库获取虚拟机配置
                vm_saving_data = self.db.get_vm_saving(self.hs_name)
                if vm_saving_data:
                    self.vm_saving = {}
                    for vm_uuid, vm_config in vm_saving_data.items():
                        if isinstance(vm_config, dict):
                            self.vm_saving[vm_uuid] = VMConfig(**vm_config)
                        else:
                            self.vm_saving[vm_uuid] = vm_config

                # 从数据库获取虚拟机状态
                vm_status_data = self.db.get_vm_status(self.hs_name)
                if vm_status_data:
                    self.vm_status = vm_status_data

                # 从数据库获取虚拟机任务
                vm_tasker_data = self.db.get_vm_tasker(self.hs_name)
                if vm_tasker_data:
                    self.vm_tasker = vm_tasker_data

                # 从数据库获取日志记录
                logger_data = self.db.get_logger(self.hs_name)
                if logger_data:
                    self.hs_logger = []
                    for log_data in logger_data:
                        if isinstance(log_data, dict):
                            self.hs_logger.append(ZMessage(**log_data))
                        else:
                            self.hs_logger.append(log_data)

                return True
            except Exception as e:
                print(f"从数据库加载数据失败: {e}")
                return False
        return False

    # 添加日志记录 ###################################################
    def add_log(self, log: ZMessage):
        """添加日志记录并保存到数据库"""
        self.hs_logger.append(log)
        if self.db and self.hs_name:
            self.db.save_logger(self.hs_name, self.hs_logger)
