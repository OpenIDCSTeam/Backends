import json
import secrets
import traceback

from HostAgents.Template import BaseServer
from HostAgents.Vmware64 import HostServer
from HostObject.HSConfig import HSConfig
from HostObject.HSEngine import HEConfig
from HostObject.VMConfig import VMConfig
from HostObject.VMPowers import VMPowers
from HostObject.ZMConfig import NCConfig
from HostObject.ZMessage import ZMessage


class HostManage:
    # 初始化 #####################################################################
    def __init__(self):
        self.engine: dict[str, BaseServer] = {}
        self.logger: list[ZMessage] = []
        self.bearer: str = ""
        self.saving: str = "./DataSaving"

    # 字典化 #####################################################################
    def __dict__(self):
        return {
            "engine": {
                string: server.__dict__() for string, server in self.engine.items()
            },
            "logger": [
                logger.__dict__() for logger in self.logger
            ],
            "bearer": self.bearer
        }

    # 设置/重置访问Token ##########################################################
    def set_pass(self, bearer: str = "") -> str:
        """
        设置或重置访问Token
        :param bearer: 指定的Token，为空则自动生成16位随机Token
        :return: 设置后的Token
        """
        if bearer:
            self.bearer = bearer
        else:
            # 生成16位随机Token（包含字母和数字）
            self.bearer = secrets.token_hex(8)
        self.all_save()
        return self.bearer

    # 验证Token ##################################################################
    def verify_token(self, token: str) -> bool:
        """
        验证访问Token是否正确
        :param token: 待验证的Token
        :return: 验证结果
        """
        return token and token == self.bearer

    # 获取主机 ###################################################################
    def get_host(self, hs_name: str) -> BaseServer | None:
        if hs_name not in self.engine:
            return None
        return self.engine[hs_name]

    # 添加主机 ###################################################################
    def add_host(self, hs_name: str, hs_type: str, hs_conf: HSConfig) -> ZMessage:
        if hs_name in self.engine:
            return ZMessage(success=False, message="Host already add")
        if hs_type not in HEConfig:
            return ZMessage(success=False, message="Host unsupported")
        self.engine[hs_name] = HEConfig[hs_type]["Imported"](hs_conf)
        self.engine[hs_name].HSCreate()
        self.engine[hs_name].HSLoader()
        return ZMessage(success=True, message="Host added successful")

    # 删除主机 ###################################################################
    def del_host(self, server):
        if server in self.engine:
            del self.engine[server]
            return True
        return False

    # 修改主机 ###################################################################
    def set_host(self, hs_name: str, hs_conf: HSConfig) -> ZMessage:
        if hs_name not in self.engine:
            return ZMessage(success=False, message="Host not found")
        self.engine[hs_name] = HEConfig[hs_conf.server_type]["Imported"](hs_conf)
        self.engine[hs_name].HSUnload()
        self.engine[hs_name].HSLoader()
        return ZMessage(success=True, message="Host updated successful")

    # 修改主机 ###################################################################
    def pwr_host(self, hs_name: str, hs_flag: bool) -> ZMessage:
        if hs_name not in self.engine:
            return ZMessage(success=False, message="Host not found")
        if hs_flag:
            self.engine[hs_name].HSLoader()
        else:
            self.engine[hs_name].HSUnload()
        return ZMessage(success=True, message="Host enable=" + str(hs_flag))

    # 加载信息 ###################################################################
    def all_load(self):
        with open(self.saving + "/HostServer.json", "r") as read_file:
            save_full = json.load(read_file)
            save_data = save_full["engine"]
            self.bearer = save_full["bearer"]
            self.logger = [
                ZMessage(**logger) for logger in save_full["logger"]
            ]
            for hs_name in save_data:
                hs_data = save_data[hs_name]
                hs_conf = HSConfig(**hs_data["hs_config"])
                hs_type = HEConfig[hs_conf.server_type]["Imported"]
                self.engine[hs_name] = hs_type(
                    hs_conf,
                    hs_status=save_data[hs_name]["hs_status"],
                    hs_saving=save_data[hs_name]["hs_saving"],
                    vm_saving=save_data[hs_name]["vm_saving"],
                    vm_status=save_data[hs_name]["vm_status"],
                    vm_tasker=save_data[hs_name]["vm_tasker"],
                    save_logs=save_data[hs_name]["save_logs"],
                )
                self.engine[hs_name].HSLoader()

    # 保存信息 ###################################################################
    def all_save(self) -> bool:
        try:
            result = self.__dict__()
        except Exception as e:
            print(e)
            traceback.print_exc()
            return False
        with open(self.saving + "/HostServer.json", "w") as save_file:
            json.dump(result, save_file)
        return True

    # 退出程序 ###################################################################
    def all_exit(self):
        for server in self.engine:
            self.engine[server].HSUnload()

    # 定时任务 ###################################################################
    def exe_cron(self):
        for server in self.engine:
            print(f'[Cron] 执行{server}的定时任务')
            self.engine[server].Crontabs()
        print('[Cron] 执行定时任务完成')


if __name__ == "__main__":
    # 创建一个接口对象 ======================================================
    hs_manage = HostManage()
    # 添加一个主机 ==========================================================
    # hs_manage.add_host(
    #     "host1", "VMWareSetup",
    #     HSConfig(
    #         server_type="Win64VMW",
    #         server_addr="localhost:8697",
    #         server_user="root",
    #         server_pass="VmD55!MkW@%Q",
    #         filter_name="",
    #         images_path=r"G:\OIDCS\Win64VMW\images",
    #         system_path=r"G:\OIDCS\Win64VMW\system",
    #         backup_path=r"G:\OIDCS\Win64VMW\backup",
    #         extern_path=r"G:\OIDCS\Win64VMW\extern",
    #         launch_path=r"C:\Program Files (x86)\VMware\VMware Workstation",
    #         network_nat="nat",
    #         network_pub="",
    #         extend_data={
    #
    #         }
    #     ))
    # 加载所有主机 ==========================================================
    hs_manage.all_load()
    # 获取一个主机 ==========================================================
    hs_server = hs_manage.get_host("host1")
    # 创建虚拟机配置 ========================================================
    vm_config = VMConfig(
        vm_uuid="ecs_testvm",
        os_name="windows10x64",
        cpu_num=4,
        mem_num=4096,
        hdd_num=10240,
        gpu_num=0,
        net_num=100,
        flu_num=100,
        nat_num=100,
        web_num=100,
        gpu_mem=8192,
        speed_u=100,
        speed_d=100,
        nic_all={
            "ethernet0": NCConfig(
                ip4_addr="192.168.4.101",
                nic_type="nat",
            )
        }
    )
    # 创建虚拟机 ============================================================
    # hs_result = hs_server.VMCreate(vm_config)
    # print(hs_result)
    # 启动虚拟机 ============================================================
    # hs_result = hs_server.VMPowers(vm_config.vm_uuid, VMPowers.S_START)
    # print(hs_result)
    # 获取主机状态 ==========================================================
    hs_status = hs_server.HSStatus()
    print(hs_status)
    # 获取虚拟机状态 ========================================================
    vm_status = hs_server.VMStatus(vm_config.vm_uuid)
    for name, nc_status in vm_status.items():
        print(name, nc_status)
    # 保存所有主机 ==========================================================
    hs_manage.all_save()
    # 退出程序 ==============================================================
    hs_manage.all_exit()
    # 调试 ==================================================================
    # print(hs_server.__dict__())
