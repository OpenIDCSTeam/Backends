"""
Hyper-V虚拟机管理模块
支持Windows Hyper-V虚拟机的创建、管理、电源控制等功能
"""

import os
import shutil
import datetime
from copy import deepcopy
from loguru import logger

from HostServer.BasicServer import BasicServer
from VNCConsole.VNCSManager import VNCSManager
from HostServer.Win64HyperVAPI.HyperVAPI import HyperVAPI
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.IMConfig import IMConfig
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.VMBackup import VMBackup



class HostServer(BasicServer):
    """Hyper-V宿主机服务类"""

    # 宿主机服务 ###############################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)
        super().__load__(**kwargs)

        # 添加变量 =============================================================
        # 初始化Hyper-V API连接
        self.hyperv_api = HyperVAPI(
            host=self.hs_config.server_addr,
            user=self.hs_config.server_user,
            password=self.hs_config.server_pass,
            port=self.hs_config.server_port if hasattr(self.hs_config, 'server_port') else 5985,
            use_ssl=False
        )

        # VNC远程控制（Hyper-V使用增强会话模式，但保留接口兼容性）
        self.vm_remote: VNCSManager | None = None

    # 宿主机任务 ###############################################################
    def Crontabs(self) -> bool:
        """定时任务"""
        # 专用操作 =============================================================
        try:
            # 获取远程主机状态
            hw_status = self.HSStatus()
            # 保存主机状态到数据库
            if hw_status:
                from MainObject.Server.HSStatus import HSStatus
                hs_status = HSStatus()
                hs_status.hw_status = hw_status
                self.host_set(hs_status)
                logger.debug(f"[{self.hs_config.server_name}] 远程主机状态已保存")
        except Exception as e:
            logger.error(f"[{self.hs_config.server_name}] 获取远程主机状态失败: {str(e)}")
        # 通用操作 =============================================================
        return True

    # 宿主机状态 ###############################################################
    def HSStatus(self) -> HWStatus:
        """获取宿主机状态"""
        # 专用操作 =============================================================
        try:
            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                logger.error(f"无法连接到Hyper-V获取状态: {connect_result.message}")
                return super().HSStatus()

            # 获取远程主机状态
            host_status = self.hyperv_api.get_host_status()

            # 断开连接
            self.hyperv_api.disconnect()

            if host_status:
                hw_status = HWStatus()
                hw_status.cpu_usage = host_status.get("cpu_usage_percent", 0)
                hw_status.mem_usage = int(host_status.get("memory_used_mb", 0))
                hw_status.mem_total = int(host_status.get("memory_total_mb", 0))
                hw_status.hdd_usage = 0  # Hyper-V需要额外查询存储使用率
                hw_status.hdd_total = 0
                logger.debug(
                    f"[{self.hs_config.server_name}] 远程主机状态: "
                    f"CPU={hw_status.cpu_usage}%, "
                    f"MEM={hw_status.mem_usage}MB/{hw_status.mem_total}MB"
                )
                return hw_status
        except Exception as e:
            logger.error(f"获取Hyper-V主机状态失败: {str(e)}")

        # 通用操作 =============================================================
        return super().HSStatus()

    # 初始宿主机 ###############################################################
    def HSCreate(self) -> ZMessage:
        """初始化宿主机"""
        # 专用操作 =============================================================
        # Hyper-V不需要初始化操作，主机已经存在
        # 通用操作 =============================================================
        return super().HSCreate()

    # 还原宿主机 ###############################################################
    def HSDelete(self) -> ZMessage:
        """还原宿主机"""
        # 专用操作 =============================================================
        # Hyper-V不需要还原操作
        # 通用操作 =============================================================
        return super().HSDelete()

    # 读取宿主机 ###############################################################
    def HSLoader(self) -> ZMessage:
        """加载宿主机"""
        # 专用操作 =============================================================
        # 测试连接到Hyper-V
        result = self.hyperv_api.connect()
        if result.success:
            self.hyperv_api.disconnect()
            logger.info(f"成功连接到Hyper-V主机: {self.hs_config.server_addr}")
        else:
            logger.error(f"无法连接到Hyper-V主机: {result.message}")
            return result
        # 通用操作 =============================================================
        return super().HSLoader()

    # 卸载宿主机 ###############################################################
    def HSUnload(self) -> ZMessage:
        """卸载宿主机"""
        # 专用操作 =============================================================
        # 断开Hyper-V连接
        self.hyperv_api.disconnect()

        # 停止VNC服务
        if self.vm_remote:
            try:
                self.vm_remote.stop()
            except Exception as e:
                logger.warning(f"停止VNC服务失败: {str(e)}")

        # 通用操作 =============================================================
        return super().HSUnload()

    # 虚拟机列出 ###############################################################
    def VMStatus(self, vm_name: str = "", s_t: int = None,
                 e_t: int = None) -> dict[str, list[HWStatus]]:
        """获取虚拟机状态"""
        # 专用操作 =============================================================
        # Hyper-V的虚拟机状态通过API实时获取
        # 通用操作 =============================================================
        return super().VMStatus(vm_name, s_t, e_t)

    # 虚拟机扫描 ###############################################################
    def VMDetect(self) -> ZMessage:
        """扫描虚拟机"""
        # 专用操作 =============================================================
        try:
            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 使用主机配置的filter_name作为前缀过滤
            filter_prefix = self.hs_config.filter_name if self.hs_config else ""

            # 获取所有虚拟机列表
            vms_list = self.hyperv_api.list_vms(filter_prefix)

            scanned_count = len(vms_list)
            added_count = 0

            # 处理每个虚拟机
            for vm_info in vms_list:
                vm_name = vm_info.get("name", "")
                if not vm_name:
                    continue

                # 检查是否已存在
                if vm_name in self.vm_saving:
                    continue

                # 创建默认虚拟机配置
                default_vm_config = VMConfig()
                default_vm_config.vm_uuid = vm_name
                default_vm_config.cpu_num = vm_info.get("cpu", 1)
                default_vm_config.mem_num = vm_info.get("memory_mb", 1024)

                # 添加到服务器的虚拟机配置中
                self.vm_saving[vm_name] = default_vm_config
                added_count += 1

                # 记录日志
                log_msg = ZMessage(
                    success=True,
                    action="VScanner",
                    message=f"发现并添加虚拟机: {vm_name}",
                    results={
                        "vm_name": vm_name,
                        "cpu": vm_info.get("cpu", 0),
                        "memory_mb": vm_info.get("memory_mb", 0),
                        "state": vm_info.get("state", "unknown")
                    }
                )
                self.push_log(log_msg)

            # 断开连接
            self.hyperv_api.disconnect()

            # 保存到数据库
            if added_count > 0:
                success = self.data_set()
                if not success:
                    return ZMessage(
                        success=False, action="VScanner",
                        message="Failed to save scanned VMs to database")

            # 返回成功消息
            return ZMessage(
                success=True,
                action="VScanner",
                message=f"扫描完成。共扫描到{scanned_count}台虚拟机，新增{added_count}台虚拟机配置。",
                results={
                    "scanned": scanned_count,
                    "added": added_count,
                    "prefix_filter": filter_prefix
                }
            )

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(success=False, action="VScanner",
                            message=f"扫描虚拟机时出错: {str(e)}")

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        """创建虚拟机"""
        # 网络检查和IP分配
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.IPBinder(vm_conf, True)

        # 专用操作 =============================================================
        try:
            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 创建虚拟机
            create_result = self.hyperv_api.create_vm(vm_conf, self.hs_config)
            if not create_result.success:
                self.hyperv_api.disconnect()
                return create_result

            # 如果有系统镜像，安装系统
            if vm_conf.os_name:
                install_result = self.VMSetups(vm_conf)
                if not install_result.success:
                    # 安装失败，删除虚拟机
                    self.hyperv_api.delete_vm(vm_conf.vm_uuid)
                    self.hyperv_api.disconnect()
                    return install_result

            # 配置网络适配器
            if vm_conf.nic_all:
                for nic_name, nic_conf in vm_conf.nic_all.items():
                    if nic_conf.mac_addr:
                        self.hyperv_api.set_network_adapter(
                            vm_conf.vm_uuid,
                            "Default Switch",
                            nic_conf.mac_addr
                        )

            # 启动虚拟机
            self.hyperv_api.power_on(vm_conf.vm_uuid)

            # 断开连接
            self.hyperv_api.disconnect()

            logger.info(f"虚拟机 {vm_conf.vm_uuid} 创建成功")

        except Exception as e:
            self.hyperv_api.disconnect()
            # 创建失败时清理
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"虚拟机创建失败: {str(e)}")
            self.logs_set(hs_result)
            return hs_result

        # 通用操作 =============================================================
        return super().VMCreate(vm_conf)

    # 安装虚拟机 ###############################################################
    def VMSetups(self, vm_conf: VMConfig) -> ZMessage:
        """安装虚拟机系统"""
        # 专用操作 =============================================================
        try:
            # 获取镜像文件路径
            image_file = os.path.join(self.hs_config.images_path, vm_conf.os_name)
            if not os.path.exists(image_file):
                return ZMessage(
                    success=False, action="VInstall",
                    message=f"镜像文件不存在: {image_file}")

            # 判断是ISO还是磁盘镜像
            file_ext = os.path.splitext(vm_conf.os_name)[1].lower()

            if file_ext in ['.iso']:
                # ISO镜像，挂载到虚拟机
                iso_path = image_file

                # 挂载ISO
                attach_result = self.hyperv_api.attach_iso(vm_conf.vm_uuid, iso_path)
                if not attach_result.success:
                    return attach_result

                logger.info(f"ISO镜像 {vm_conf.os_name} 已挂载到虚拟机 {vm_conf.vm_uuid}")

            elif file_ext in ['.vhdx', '.vhd']:
                # 磁盘镜像，复制到虚拟机目录
                vm_path = os.path.join(self.hs_config.system_path, vm_conf.vm_uuid)
                vm_disk_path = os.path.join(vm_path, "Virtual Hard Disks", f"{vm_conf.vm_uuid}.vhdx")

                # 确保目录存在
                os.makedirs(os.path.dirname(vm_disk_path), exist_ok=True)

                # 复制磁盘镜像
                shutil.copy(image_file, vm_disk_path)
                logger.info(f"磁盘镜像已复制到: {vm_disk_path}")

            return ZMessage(success=True, action="VInstall",
                            message="系统安装完成")

        except Exception as e:
            logger.error(f"安装虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="VInstall",
                            message=f"安装失败: {str(e)}")

    # 配置虚拟机 ###############################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        """更新虚拟机配置"""
        # 网络检查
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.IPBinder(vm_conf, True)

        # 专用操作 =============================================================
        try:
            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 检查虚拟机是否存在
            if vm_conf.vm_uuid not in self.vm_saving:
                self.hyperv_api.disconnect()
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 不存在")

            # 更新虚拟机配置存储
            self.vm_saving[vm_conf.vm_uuid] = vm_conf

            # 关闭虚拟机（Hyper-V需要关机才能修改配置）
            self.hyperv_api.power_off(vm_conf.vm_uuid, force=True)

            # 重装系统
            if vm_conf.os_name != vm_last.os_name and vm_last.os_name != "":
                install_result = self.VMSetups(vm_conf)
                if not install_result.success:
                    self.hyperv_api.disconnect()
                    return install_result

            # 更新CPU和内存配置
            if vm_conf.cpu_num != vm_last.cpu_num or vm_conf.mem_num != vm_last.mem_num:
                update_result = self.hyperv_api.update_vm_config(vm_conf.vm_uuid, vm_conf)
                if not update_result.success:
                    self.hyperv_api.disconnect()
                    return update_result

            # 更新硬盘（如果需要扩容）
            if vm_conf.hdd_num > vm_last.hdd_num:
                # TODO: 实现磁盘扩容
                logger.warning("Hyper-V磁盘扩容功能待实现")

            # 更新网卡
            network_result = self.IPUpdate(vm_conf, vm_last)
            if not network_result.success:
                self.hyperv_api.disconnect()
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 网络配置更新失败: {network_result.message}")

            # 启动虚拟机
            start_result = self.hyperv_api.power_on(vm_conf.vm_uuid)
            if not start_result.success:
                self.hyperv_api.disconnect()
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 启动失败: {start_result.message}")

            # 断开连接
            self.hyperv_api.disconnect()

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机配置更新失败: {str(e)}")

        # 通用操作 =============================================================
        return super().VMUpdate(vm_conf, vm_last)

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str, rm_back=True) -> ZMessage:
        """删除虚拟机"""
        # 专用操作 =============================================================
        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False,
                    action="VMDelete",
                    message=f"虚拟机 {vm_name} 不存在")

            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 删除网络绑定
            self.IPBinder(vm_conf, False)

            # 删除虚拟机
            delete_result = self.hyperv_api.delete_vm(vm_name, remove_files=True)

            # 断开连接
            self.hyperv_api.disconnect()

            if not delete_result.success:
                return delete_result

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(
                success=False, action="VMDelete",
                message=f"删除虚拟机失败: {str(e)}")

        # 通用操作 =============================================================
        super().VMDelete(vm_name, rm_back)
        return ZMessage(success=True, action="VMDelete", message="虚拟机删除成功")

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        """虚拟机电源管理"""
        # 专用操作 =============================================================
        try:
            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 执行电源操作
            if power == VMPowers.S_START:
                hs_result = self.hyperv_api.power_on(vm_name)
            elif power == VMPowers.H_CLOSE:
                hs_result = self.hyperv_api.power_off(vm_name, force=True)
            elif power == VMPowers.A_PAUSE:
                hs_result = self.hyperv_api.suspend(vm_name)
            elif power == VMPowers.A_WAKED:
                hs_result = self.hyperv_api.resume(vm_name)
            elif power == VMPowers.H_RESET or power == VMPowers.S_RESET:
                hs_result = self.hyperv_api.reset(vm_name)
            else:
                hs_result = ZMessage(
                    success=False, action="VMPowers",
                    message=f"不支持的电源操作: {power}")

            # 断开连接
            self.hyperv_api.disconnect()

            self.logs_set(hs_result)

        except Exception as e:
            self.hyperv_api.disconnect()
            hs_result = ZMessage(
                success=False, action="VMPowers",
                message=f"电源操作失败: {str(e)}")
            self.logs_set(hs_result)

        # 通用操作 =============================================================
        super().VMPowers(vm_name, power)
        return hs_result

    # 设置虚拟机密码 ###########################################################
    def VMPasswd(self, vm_name: str, os_pass: str) -> ZMessage:
        """设置虚拟机密码"""
        # 专用操作 =============================================================
        # Hyper-V通过guest tools设置密码，这里使用父类的实现
        # 通用操作 =============================================================
        return super().VMPasswd(vm_name, os_pass)

    # 备份虚拟机 ###############################################################
    def VMBackup(self, vm_name: str, vm_tips: str) -> ZMessage:
        """备份虚拟机（创建快照）"""
        # 专用操作 =============================================================
        try:
            bak_time = datetime.datetime.now()
            bak_name = vm_name + "-" + bak_time.strftime("%Y%m%d%H%M%S")

            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 创建快照作为备份
            snapshot_result = self.hyperv_api.create_snapshot(
                vm_name,
                bak_name,
                vm_tips
            )

            # 断开连接
            self.hyperv_api.disconnect()

            if not snapshot_result.success:
                return snapshot_result

            # 记录备份信息
            if vm_name in self.vm_saving:
                self.vm_saving[vm_name].backups.append(
                    VMBackup(
                        backup_name=bak_name,
                        backup_time=bak_time,
                        backup_tips=vm_tips
                    )
                )
                self.data_set()

            return ZMessage(success=True, action="VMBackup",
                            message=f"虚拟机备份成功: {bak_name}")

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(success=False, action="VMBackup",
                            message=f"备份失败: {str(e)}")

    # 恢复虚拟机 ###############################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        """恢复虚拟机（恢复快照）"""
        # 专用操作 =============================================================
        try:
            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 恢复快照
            restore_result = self.hyperv_api.revert_snapshot(vm_name, vm_back)

            # 断开连接
            self.hyperv_api.disconnect()

            if not restore_result.success:
                return restore_result

            return ZMessage(success=True, action="Restores",
                            message=f"虚拟机恢复成功: {vm_back}")

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(success=False, action="Restores",
                            message=f"恢复失败: {str(e)}")

    # VM镜像挂载 ###############################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        """挂载/卸载虚拟硬盘"""
        # 专用操作 =============================================================
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="HDDMount", message="虚拟机不存在")

            old_conf = deepcopy(self.vm_saving[vm_name])

            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 关闭虚拟机
            self.hyperv_api.power_off(vm_name, force=True)

            if in_flag:  # 挂载磁盘
                # 添加磁盘
                add_result = self.hyperv_api.add_disk(
                    vm_name,
                    vm_imgs.hdd_size,
                    vm_imgs.hdd_name
                )
                if not add_result.success:
                    self.hyperv_api.disconnect()
                    return add_result

                vm_imgs.hdd_flag = 1
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name] = vm_imgs
            else:  # 卸载磁盘
                if vm_imgs.hdd_name not in self.vm_saving[vm_name].hdd_all:
                    self.hyperv_api.power_on(vm_name)
                    self.hyperv_api.disconnect()
                    return ZMessage(
                        success=False, action="HDDMount", message="磁盘不存在")

                # TODO: 实现磁盘卸载
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name].hdd_flag = 0

            # 启动虚拟机
            self.hyperv_api.power_on(vm_name)

            # 断开连接
            self.hyperv_api.disconnect()

            # 保存配置
            self.VMUpdate(self.vm_saving[vm_name], old_conf)
            self.data_set()

            action_text = "挂载" if in_flag else "卸载"
            return ZMessage(
                success=True,
                action="HDDMount",
                message=f"磁盘{action_text}成功")

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(
                success=False, action="HDDMount",
                message=f"磁盘操作失败: {str(e)}")

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        """挂载/卸载ISO镜像"""
        # 专用操作 =============================================================
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="ISOMount", message="虚拟机不存在")

            old_conf = deepcopy(self.vm_saving[vm_name])

            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            logger.info(f"准备{'挂载' if in_flag else '卸载'}ISO: {vm_imgs.iso_name}")

            # 关闭虚拟机
            self.hyperv_api.power_off(vm_name, force=True)

            if in_flag:  # 挂载ISO
                # ISO文件路径
                iso_path = os.path.join(self.hs_config.dvdrom_path, vm_imgs.iso_file)  # 使用dvdrom_path存储光盘镜像

                if not os.path.exists(iso_path):
                    self.hyperv_api.power_on(vm_name)
                    self.hyperv_api.disconnect()
                    return ZMessage(
                        success=False, action="ISOMount", message="ISO文件不存在")

                # 挂载ISO
                attach_result = self.hyperv_api.attach_iso(vm_name, iso_path)
                if not attach_result.success:
                    self.hyperv_api.power_on(vm_name)
                    self.hyperv_api.disconnect()
                    return attach_result

                # 检查挂载名称是否已存在
                if vm_imgs.iso_name in self.vm_saving[vm_name].iso_all:
                    self.hyperv_api.power_on(vm_name)
                    self.hyperv_api.disconnect()
                    return ZMessage(
                        success=False, action="ISOMount", message="挂载名称已存在")

                self.vm_saving[vm_name].iso_all[vm_imgs.iso_name] = vm_imgs
                logger.info(f"ISO挂载成功: {vm_imgs.iso_name} -> {vm_imgs.iso_file}")
            else:  # 卸载ISO
                if vm_imgs.iso_name not in self.vm_saving[vm_name].iso_all:
                    self.hyperv_api.power_on(vm_name)
                    self.hyperv_api.disconnect()
                    return ZMessage(
                        success=False, action="ISOMount", message="ISO镜像不存在")

                # 卸载ISO
                detach_result = self.hyperv_api.detach_iso(vm_name)
                if not detach_result.success:
                    logger.warning(f"ISO卸载警告: {detach_result.message}")

                del self.vm_saving[vm_name].iso_all[vm_imgs.iso_name]
                logger.info(f"ISO卸载成功: {vm_imgs.iso_name}")

            # 启动虚拟机
            self.hyperv_api.power_on(vm_name)

            # 断开连接
            self.hyperv_api.disconnect()

            # 保存配置
            self.VMUpdate(self.vm_saving[vm_name], old_conf)
            self.data_set()

            action_text = "挂载" if in_flag else "卸载"
            return ZMessage(
                success=True,
                action="ISOMount",
                message=f"ISO镜像{action_text}成功")

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(
                success=False, action="ISOMount",
                message=f"ISO操作失败: {str(e)}")

    # 加载备份 #################################################################
    def LDBackup(self, vm_back: str = "") -> ZMessage:
        """加载备份列表（从快照）"""
        # 专用操作 =============================================================
        try:
            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 清空现有备份记录
            for vm_name in self.vm_saving:
                self.vm_saving[vm_name].backups = []

            bal_nums = 0

            # 遍历所有虚拟机，获取快照信息
            # TODO: 实现从Hyper-V获取快照列表的功能
            # 目前Hyper-V API需要扩展以支持列出快照

            # 断开连接
            self.hyperv_api.disconnect()

            # 保存配置
            self.data_set()

            return ZMessage(
                success=True,
                action="LDBackup",
                message=f"{bal_nums}个备份快照已加载")

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(
                success=False, action="LDBackup",
                message=f"加载备份失败: {str(e)}")

    # 移除备份 #################################################################
    def RMBackup(self, vm_name: str, vm_back: str = "") -> ZMessage:
        """移除备份（删除快照）"""
        # 专用操作 =============================================================
        try:
            # 从备份名称中提取虚拟机名称
            parts = vm_back.split("-")
            if len(parts) < 2:
                return ZMessage(
                    success=False, action="RMBackup",
                    message="备份名称格式不正确")

            vm_name = parts[0]

            # 连接到Hyper-V
            connect_result = self.hyperv_api.connect()
            if not connect_result.success:
                return connect_result

            # 删除快照
            delete_result = self.hyperv_api.delete_snapshot(vm_name, vm_back)

            # 断开连接
            self.hyperv_api.disconnect()

            if not delete_result.success:
                return delete_result

            # 从配置中移除备份记录
            if vm_name in self.vm_saving:
                self.vm_saving[vm_name].backups = [
                    b for b in self.vm_saving[vm_name].backups
                    if b.backup_name != vm_back
                ]
                self.data_set()

            return ZMessage(
                success=True, action="RMBackup",
                message="备份快照已删除")

        except Exception as e:
            self.hyperv_api.disconnect()
            return ZMessage(
                success=False, action="RMBackup",
                message=f"删除备份失败: {str(e)}")

    # 移除磁盘 #################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str) -> ZMessage:
        """移除虚拟磁盘"""
        # 专用操作 =============================================================
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="RMMounts", message="虚拟机不存在")
            if vm_imgs not in self.vm_saving[vm_name].hdd_all:
                return ZMessage(
                    success=False, action="RMMounts", message="虚拟盘不存在")

            # 获取虚拟磁盘数据
            hd_data = self.vm_saving[vm_name].hdd_all[vm_imgs]

            # 卸载虚拟磁盘
            if hd_data.hdd_flag == 1:
                unmount_result = self.HDDMount(vm_name, hd_data, False)
                if not unmount_result.success:
                    return unmount_result

            # 从配置中移除
            self.vm_saving[vm_name].hdd_all.pop(vm_imgs)
            self.data_set()

            # TODO: 从Hyper-V中删除磁盘文件

            return ZMessage(
                success=True, action="RMMounts",
                message="磁盘删除成功")

        except Exception as e:
            return ZMessage(
                success=False, action="RMMounts",
                message=f"删除磁盘失败: {str(e)}")

    # 查找显卡 #################################################################
    def GPUShows(self) -> dict[str, str]:
        """查找可用显卡"""
        # 专用操作 =============================================================
        # Hyper-V的GPU直通需要特殊配置，这里返回空字典
        # TODO: 实现Hyper-V GPU查询
        # 通用操作 =============================================================
        return {}
