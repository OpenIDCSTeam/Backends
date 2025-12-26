import json
import psutil

try:
    import GPUtil
except ModuleNotFoundError:
    GPUtil = None

import cpuinfo
import platform
from shutil import disk_usage
from loguru import logger
from MainObject.Public.HWStatus import HWStatus
from MainObject.Config.VMPowers import VMPowers


class HSStatus:
    def __init__(self):
        self.hw_status = HWStatus()

    # 转换为字典 ============================================================
    def __save__(self):
        return self.hw_status.__save__()

    # 转换为文本 ============================================================
    def __str__(self):
        return json.dumps(self.__save__())

    # 获取状态 ==============================================================
    def status(self) -> HWStatus:
        self.hw_status.ac_status = VMPowers.STARTED
        # 获取CPU信息 =======================================================
        try:
            self.hw_status.cpu_model = cpuinfo.get_cpu_info()['brand_raw']
            self.hw_status.cpu_total = psutil.cpu_count(logical=True)
            self.hw_status.cpu_usage = int(psutil.cpu_percent(interval=1))
        except Exception as e:
            self.hw_status.cpu_model = "Unknown"
        # 获取内存信息 ======================================================
        mem = psutil.virtual_memory()
        self.hw_status.mem_total = int(mem.total / (1024 * 1024))  # 转换为MB
        self.hw_status.mem_usage = int(mem.used / (1024 * 1024))  # 内存已用量（MB）
        # 获取系统磁盘信息 ==================================================
        disk_total, disk_used, disk_free = disk_usage('/')
        self.hw_status.hdd_total = int(disk_total / (1024 * 1024))
        self.hw_status.hdd_usage = int(disk_used / (1024 * 1024))
        # 获取其他磁盘信息 ==================================================
        for disk in psutil.disk_partitions():
            if disk.mountpoint != '/':
                total, used, free = disk_usage(disk.mountpoint)
                self.hw_status.ext_usage[disk.mountpoint] = [
                    int(total / (1024 * 1024)),  # 总空间MB
                    int(used / (1024 * 1024))  # 已用空间MB
                ]
        # 获取GPU信息 =======================================================
        if GPUtil is None:
            self.hw_status.gpu_total = 0
        else:
            gpus = GPUtil.getGPUs()
            self.hw_status.gpu_total = len(gpus)
            for gpu in gpus:
                self.hw_status.gpu_usage[gpu.id] = int(gpu.load * 100)  # 使用率
        # 获取网络带宽 ======================================================
        nic_list = psutil.net_io_counters(True)
        max_name = ""
        total_tx = total_rx = 0
        for nic_name in nic_list:
            # print("网卡 {} 信息: ".format(nic_name))
            nic_data = nic_list[nic_name]
            # print("网卡发送流量(MByte): ", nic_data.bytes_sent / (1024 * 1024))
            # print("网卡接收流量(MByte): ", nic_data.bytes_recv / (1024 * 1024))
            if nic_data.bytes_sent / (1024 * 1024) > total_tx:
                total_tx = nic_data.bytes_sent / (1024 * 1024)
                total_rx = nic_data.bytes_recv / (1024 * 1024)
                max_name = nic_name
        self.hw_status.flu_usage = int(total_tx + total_rx)
        self.hw_status.network_u = int(total_tx / 60 * 8)
        self.hw_status.network_d = int(total_rx / 60 * 8)
        # print("当前双向流量(MByte): ", self.hw_status.flu_usage)
        # print("当前上行带宽(MByte): ", self.hw_status.network_u)
        # print("当前下行带宽(MByte): ", self.hw_status.network_d)
        psutil.net_io_counters.cache_clear()
        # 物理网卡 ===========================================================
        nic_list = psutil.net_if_stats()
        if max_name in nic_list:
            self.hw_status.network_a = nic_list[max_name].speed
        # 获取CPU温度和功耗 =================================================
        if platform.system() == "Windows":
            self.hw_status.cpu_temp = 0
            self.hw_status.cpu_power = 0
        else:
            self.hw_status.cpu_temp = int(psutil.sensors_temperatures()['coretemp'][0].current)
            self.hw_status.cpu_power = int(psutil.sensors_battery().percent)
        return self.hw_status


if __name__ == "__main__":
    hs = HSStatus()
    logger.info(hs.status())
