import json

import psutil
import GPUtil
import cpuinfo
import platform
from MainObject.Public.HWStatus import HWStatus
from MainObject.Config.VMPowers import VMPowers


class HSStatus:
    def __init__(self):
        self.hw_status = HWStatus()

    # 转换为字典 ============================================================
    def __dict__(self):
        return self.hw_status.__dict__()

    # 转换为文本 ============================================================
    def __str__(self):
        return json.dumps(self.__dict__())

    # 获取状态 ==============================================================
    def status(self) -> HWStatus:
        self.hw_status.ac_status = VMPowers.STARTED
        # 获取CPU信息 =======================================================
        self.hw_status.cpu_model = cpuinfo.get_cpu_info()['brand_raw']
        self.hw_status.cpu_total = psutil.cpu_count(logical=True)
        self.hw_status.cpu_usage = int(psutil.cpu_percent(interval=1))
        # 获取内存信息 ======================================================
        mem = psutil.virtual_memory()
        self.hw_status.mem_total = int(mem.total / (1024 * 1024))  # 转换为MB
        self.hw_status.mem_usage = int(mem.used / (1024 * 1024))  # 内存已用量（MB）
        # 获取系统磁盘信息 ==================================================
        disk_usage = psutil.disk_usage('/')
        self.hw_status.hdd_total = int(disk_usage.total / (1024 * 1024))
        self.hw_status.hdd_usage = int(disk_usage.used / (1024 * 1024))
        # 获取其他磁盘信息 ==================================================
        for disk in psutil.disk_partitions():
            if disk.mountpoint != '/':
                usage = psutil.disk_usage(disk.mountpoint)
                self.hw_status.ext_usage[disk.mountpoint] = [
                    int(usage.total / (1024 * 1024)),  # 总空间MB
                    int(usage.used / (1024 * 1024))  # 已用空间MB
                ]
        # 获取GPU信息 =======================================================
        gpus = GPUtil.getGPUs()
        self.hw_status.gpu_total = len(gpus)
        for gpu in gpus:
            self.hw_status.gpu_usage[gpu.id] = int(gpu.load * 100)  # 使用率
        # 获取网络带宽 ======================================================
        net_io = psutil.net_io_counters()
        self.hw_status.network_u = int(net_io.bytes_sent / (1024 * 1024))
        self.hw_status.network_d = int(net_io.bytes_recv / (1024 * 1024))
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
    print(hs.status())
