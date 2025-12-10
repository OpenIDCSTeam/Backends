import json
import psutil
import GPUtil
from loguru import logger
from .HWStatus import HWStatus
from .VMPowers import VMPowers


class VMStatus:
    def __init__(self):
        self.vm_status = HWStatus()

    # 转换为字典 ============================================================
    def __dict__(self):
        return self.vm_status.__dict__()

    # 转换为文本 ============================================================
    def __str__(self):
        return json.dumps(self.__dict__())

    # 获取状态 ==============================================================
    def status(self) -> HWStatus:
        self.vm_status.ac_status = VMPowers.STARTED
        # 获取CPU信息 =======================================================
        self.vm_status.cpu_total = psutil.cpu_count(logical=True)
        self.vm_status.cpu_usage = int(psutil.cpu_percent(interval=1))
        # 获取内存信息 ======================================================
        mem = psutil.virtual_memory()
        self.vm_status.mem_total = int(mem.total / (1024 * 1024))  # 转换为MB
        self.vm_status.mem_usage = int(mem.used / (1024 * 1024))  # 内存已用量
        # 获取系统磁盘信息 ==================================================
        disk_usage = psutil.disk_usage('/')
        self.vm_status.hdd_total = int(disk_usage.total / (1024 * 1024))
        self.vm_status.hdd_usage = int(disk_usage.used / (1024 * 1024))
        # 获取其他磁盘信息 ==================================================
        for disk in psutil.disk_partitions():
            if disk.mountpoint != '/':
                usage = psutil.disk_usage(disk.mountpoint)
                self.vm_status.ext_usage[disk.mountpoint] = [
                    int(usage.total / (1024 * 1024)),  # 总空间MB
                    int(usage.used / (1024 * 1024))  # 已用空间MB
                ]
        # 获取GPU信息 =======================================================
        gpus = GPUtil.getGPUs()
        self.vm_status.gpu_total = len(gpus)
        for gpu in gpus:
            self.vm_status.gpu_usage[gpu.id] = int(gpu.load * 100)  # 使用率
        # 获取网络带宽 ======================================================
        nic_list = psutil.net_io_counters(True)
        max_name = ""
        total_tx = total_rx = 0
        for nic_name in nic_list:
            logger.debug("网卡 {} 信息: ".format(nic_name))
            nic_data = nic_list[nic_name]
            logger.debug("网卡发送流量(MByte): ", nic_data.bytes_sent / (1024 * 1024))
            logger.debug("网卡接收流量(MByte): ", nic_data.bytes_recv / (1024 * 1024))
            if nic_data.bytes_sent / (1024 * 1024) > total_tx:
                total_tx = nic_data.bytes_sent / (1024 * 1024)
                total_rx = nic_data.bytes_recv / (1024 * 1024)
                max_name = nic_name
        self.vm_status.flu_usage = int(total_tx + total_rx)
        self.vm_status.network_u = int(total_tx / 60 * 8)
        self.vm_status.network_d = int(total_rx / 60 * 8)
        logger.debug("当前双向流量(MByte): ", self.vm_status.flu_usage)
        logger.debug("当前上行带宽(MByte): ", self.vm_status.network_u)
        logger.debug("当前下行带宽(MByte): ", self.vm_status.network_d)
        psutil.net_io_counters.cache_clear()
        # 物理网卡 ===========================================================
        nic_list = psutil.net_if_stats()
        if max_name in nic_list:
            self.vm_status.network_a = nic_list[max_name].speed


if __name__ == "__main__":
    hs = VMStatus()
    # hs.server()
