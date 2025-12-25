import os
import shutil
import datetime
from loguru import logger

from HostServer.BasicServer import BasicServer
from HostServer.vSphereESXiAPI.vSphereAPI import vSphereAPI
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.IMConfig import IMConfig
from MainObject.Config.SDConfig import SDConfig
from MainObject.Config.VMPowers import VMPowers
from MainObject.Public.HWStatus import HWStatus
from MainObject.Public.ZMessage import ZMessage
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.VMBackup import VMBackup


class HostServer(BasicServer):
    # 宿主机服务 ###############################################################
    def __init__(self, config: HSConfig, **kwargs):
        super().__init__(config, **kwargs)
        super().__load__(**kwargs)
        # 添加变量 =============================================================
        # 初始化vSphere API连接
        self.esxi_api = vSphereAPI(
            host=self.hs_config.server_addr,
            user=self.hs_config.server_user,
            password=self.hs_config.server_pass,
            port=self.hs_config.server_port if hasattr(self.hs_config, 'server_port') else 443,
            datastore_name=os.path.basename(self.hs_config.system_path) if self.hs_config.system_path else "datastore1"
        )

    # 宿主机任务 ###############################################################
    def Crontabs(self) -> bool:
        # 专用操作 =============================================================
        # ESXi不需要特殊的定时任务
        # 通用操作 =============================================================
        return super().Crontabs()

    # 宿主机状态 ###############################################################
    def HSStatus(self) -> HWStatus:
        # 专用操作 =============================================================
        try:
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                logger.error(f"无法连接到ESXi获取状态: {connect_result.message}")
                return super().HSStatus()
            
            # 获取主机状态
            host_status = self.esxi_api.get_host_status()
            
            # 断开连接
            self.esxi_api.disconnect()
            
            if host_status:
                hw_status = HWStatus()
                hw_status.cpu_usage = host_status.get("cpu_usage_percent", 0)
                hw_status.ram_usage = host_status.get("memory_usage_percent", 0)
                hw_status.hdd_usage = 0  # ESXi需要额外查询存储使用率
                return hw_status
        except Exception as e:
            logger.error(f"获取ESXi主机状态失败: {str(e)}")
        
        # 通用操作 =============================================================
        return super().HSStatus()

    # 初始宿主机 ###############################################################
    def HSCreate(self) -> ZMessage:
        # 专用操作 =============================================================
        # ESXi不需要初始化操作，主机已经存在
        # 通用操作 =============================================================
        return super().HSCreate()

    # 还原宿主机 ###############################################################
    def HSDelete(self) -> ZMessage:
        # 专用操作 =============================================================
        # ESXi不需要还原操作
        # 通用操作 =============================================================
        return super().HSDelete()

    # 读取宿主机 ###############################################################
    def HSLoader(self) -> ZMessage:
        # 专用操作 =============================================================
        # 测试连接到ESXi
        result = self.esxi_api.connect()
        if result.success:
            self.esxi_api.disconnect()
            logger.info(f"成功连接到ESXi主机: {self.hs_config.server_addr}")
        else:
            logger.error(f"无法连接到ESXi主机: {result.message}")
            return result
        
        # 通用操作 =============================================================
        return super().HSLoader()

    # 卸载宿主机 ###############################################################
    def HSUnload(self) -> ZMessage:
        # 专用操作 =============================================================
        # 断开ESXi连接
        self.esxi_api.disconnect()
        # 通用操作 =============================================================
        return super().HSUnload()

    # 虚拟机列出 ###############################################################
    def VMStatus(self, vm_name: str = "") -> dict[str, list[HWStatus]]:
        # 专用操作 =============================================================
        # ESXi的虚拟机状态通过API实时获取
        # 通用操作 =============================================================
        return super().VMStatus(vm_name)

    # 虚拟机扫描 ###############################################################
    def VScanner(self) -> ZMessage:
        # 专用操作 =============================================================
        try:
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 使用主机配置的filter_name作为前缀过滤
            filter_prefix = self.hs_config.filter_name if self.hs_config else ""
            
            # 获取所有虚拟机列表
            vms_list = self.esxi_api.list_vms(filter_prefix)
            
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
                default_vm_config.ram_num = vm_info.get("memory_mb", 1024)
                
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
                        "power_state": vm_info.get("power_state", "unknown")
                    }
                )
                self.LogStack(log_msg)
            
            # 断开连接
            self.esxi_api.disconnect()
            
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
            self.esxi_api.disconnect()
            return ZMessage(success=False, action="VScanner",
                          message=f"扫描虚拟机时出错: {str(e)}")
        
        # 通用操作 =============================================================
        # return ZMessage(success=False, action="VScanner", message="Not implemented")

    # 创建虚拟机 ###############################################################
    def VMCreate(self, vm_conf: VMConfig) -> ZMessage:
        # 网络检查和IP分配
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)
        
        # 专用操作 =============================================================
        try:
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 创建虚拟机
            create_result = self.esxi_api.create_vm(vm_conf, self.hs_config)
            if not create_result.success:
                self.esxi_api.disconnect()
                return create_result
            
            # 如果有系统镜像，安装系统
            if vm_conf.os_name:
                install_result = self.VInstall(vm_conf)
                if not install_result.success:
                    # 安装失败，删除虚拟机
                    self.esxi_api.delete_vm(vm_conf.vm_uuid)
                    self.esxi_api.disconnect()
                    return install_result
            
            # 启动虚拟机
            self.esxi_api.power_on(vm_conf.vm_uuid)
            
            # 断开连接
            self.esxi_api.disconnect()
            
            logger.info(f"虚拟机 {vm_conf.vm_uuid} 创建成功")
            
        except Exception as e:
            self.esxi_api.disconnect()
            # 创建失败时清理
            hs_result = ZMessage(
                success=False, action="VMCreate",
                message=f"虚拟机创建失败: {str(e)}")
            self.logs_set(hs_result)
            return hs_result
        
        # 通用操作 =============================================================
        return super().VMCreate(vm_conf)

    # 安装虚拟机 ###############################################################
    def VInstall(self, vm_conf: VMConfig) -> ZMessage:
        # 专用操作 =============================================================
        try:
            # 从images_path复制镜像到ESXi数据存储
            # 这里需要将本地镜像上传到ESXi
            
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
                datastore_path = f"[{self.esxi_api.datastore_name}] {vm_conf.vm_uuid}/{vm_conf.os_name}"
                
                # TODO: 这里需要实现文件上传到ESXi数据存储的功能
                # 目前假设镜像已经在ESXi的images目录中
                iso_path = f"[{self.esxi_api.datastore_name}] ISO/{vm_conf.os_name}"
                
                # 挂载ISO
                attach_result = self.esxi_api.attach_iso(vm_conf.vm_uuid, iso_path)
                if not attach_result.success:
                    return attach_result
                
                logger.info(f"ISO镜像 {vm_conf.os_name} 已挂载到虚拟机 {vm_conf.vm_uuid}")
                
            elif file_ext in ['.vmdk', '.vdi', '.qcow2']:
                # 磁盘镜像，需要转换并添加为虚拟机磁盘
                # TODO: 实现磁盘镜像的上传和添加
                logger.warning(f"磁盘镜像格式 {file_ext} 需要手动处理")
                
                # 添加一个新磁盘
                add_disk_result = self.esxi_api.add_disk(
                    vm_conf.vm_uuid, 
                    vm_conf.hdd_num, 
                    f"{vm_conf.vm_uuid}-disk1"
                )
                if not add_disk_result.success:
                    return add_disk_result
            
            return ZMessage(success=True, action="VInstall", 
                          message="系统安装完成")
            
        except Exception as e:
            logger.error(f"安装虚拟机失败: {str(e)}")
            return ZMessage(success=False, action="VInstall", 
                          message=f"安装失败: {str(e)}")
        
        # 通用操作 =============================================================
        # return super().VInstall(vm_conf)

    # 配置虚拟机 ###############################################################
    def VMUpdate(self, vm_conf: VMConfig, vm_last: VMConfig) -> ZMessage:
        # 网络检查
        vm_conf, net_result = self.NetCheck(vm_conf)
        if not net_result.success:
            return net_result
        self.NCCreate(vm_conf, True)
        
        # 专用操作 =============================================================
        try:
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 检查虚拟机是否存在
            if vm_conf.vm_uuid not in self.vm_saving:
                self.esxi_api.disconnect()
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 不存在")
            
            # 更新虚拟机配置存储
            self.vm_saving[vm_conf.vm_uuid] = vm_conf
            
            # 关闭虚拟机（ESXi需要关机才能修改配置）
            self.esxi_api.power_off(vm_conf.vm_uuid)
            
            # 重装系统
            if vm_conf.os_name != vm_last.os_name and vm_last.os_name != "":
                install_result = self.VInstall(vm_conf)
                if not install_result.success:
                    self.esxi_api.disconnect()
                    return install_result
            
            # 更新CPU和内存配置
            if vm_conf.cpu_num != vm_last.cpu_num or vm_conf.ram_num != vm_last.ram_num:
                update_result = self.esxi_api.update_vm_config(vm_conf.vm_uuid, vm_conf)
                if not update_result.success:
                    self.esxi_api.disconnect()
                    return update_result
            
            # 更新硬盘（如果需要扩容）
            if vm_conf.hdd_num > vm_last.hdd_num:
                # TODO: 实现磁盘扩容
                logger.warning("ESXi磁盘扩容功能待实现")
            
            # 更新网卡
            network_result = self.NCUpdate(vm_conf, vm_last)
            if not network_result.success:
                self.esxi_api.disconnect()
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 网络配置更新失败: {network_result.message}")
            
            # 启动虚拟机
            start_result = self.esxi_api.power_on(vm_conf.vm_uuid)
            if not start_result.success:
                self.esxi_api.disconnect()
                return ZMessage(
                    success=False, action="VMUpdate",
                    message=f"虚拟机 {vm_conf.vm_uuid} 启动失败: {start_result.message}")
            
            # 断开连接
            self.esxi_api.disconnect()
            
        except Exception as e:
            self.esxi_api.disconnect()
            return ZMessage(
                success=False, action="VMUpdate",
                message=f"虚拟机配置更新失败: {str(e)}")
        
        # 通用操作 =============================================================
        return super().VMUpdate(vm_conf, vm_last)

    # 删除虚拟机 ###############################################################
    def VMDelete(self, vm_name: str) -> ZMessage:
        # 专用操作 =============================================================
        try:
            vm_conf = self.VMSelect(vm_name)
            if vm_conf is None:
                return ZMessage(
                    success=False,
                    action="VMDelete",
                    message=f"虚拟机 {vm_name} 不存在")
            
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 删除网络绑定
            self.NCCreate(vm_conf, False)
            
            # 删除虚拟机
            delete_result = self.esxi_api.delete_vm(vm_name)
            
            # 断开连接
            self.esxi_api.disconnect()
            
            if not delete_result.success:
                return delete_result
            
        except Exception as e:
            self.esxi_api.disconnect()
            return ZMessage(
                success=False, action="VMDelete",
                message=f"删除虚拟机失败: {str(e)}")
        
        # 通用操作 =============================================================
        super().VMDelete(vm_name)
        return ZMessage(success=True, action="VMDelete", message="虚拟机删除成功")

    # 虚拟机电源 ###############################################################
    def VMPowers(self, vm_name: str, power: VMPowers) -> ZMessage:
        # 专用操作 =============================================================
        try:
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 执行电源操作
            if power == VMPowers.S_START:
                hs_result = self.esxi_api.power_on(vm_name)
            elif power == VMPowers.H_CLOSE:
                hs_result = self.esxi_api.power_off(vm_name)
            elif power == VMPowers.S_PAUSE:
                hs_result = self.esxi_api.suspend(vm_name)
            elif power == VMPowers.H_RESET or power == VMPowers.S_RESET:
                hs_result = self.esxi_api.reset(vm_name)
            else:
                hs_result = ZMessage(
                    success=False, action="VMPowers",
                    message=f"不支持的电源操作: {power}")
            
            # 断开连接
            self.esxi_api.disconnect()
            
            self.logs_set(hs_result)
            
        except Exception as e:
            self.esxi_api.disconnect()
            hs_result = ZMessage(
                success=False, action="VMPowers",
                message=f"电源操作失败: {str(e)}")
            self.logs_set(hs_result)
        
        # 通用操作 =============================================================
        super().VMPowers(vm_name, power)
        return hs_result

    # 设置虚拟机密码 ###########################################################
    def Password(self, vm_name: str, os_pass: str) -> ZMessage:
        # 专用操作 =============================================================
        # ESXi通过guest tools设置密码，这里使用父类的实现
        # 通用操作 =============================================================
        return super().Password(vm_name, os_pass)

    # 备份虚拟机 ###############################################################
    def VMBackup(self, vm_name: str, vm_tips: str) -> ZMessage:
        # 专用操作 =============================================================
        try:
            bak_time = datetime.datetime.now()
            bak_name = vm_name + "-" + bak_time.strftime("%Y%m%d%H%M%S")
            
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 创建快照作为备份
            snapshot_result = self.esxi_api.create_snapshot(
                vm_name, 
                bak_name, 
                vm_tips
            )
            
            # 断开连接
            self.esxi_api.disconnect()
            
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
            self.esxi_api.disconnect()
            return ZMessage(success=False, action="VMBackup", 
                          message=f"备份失败: {str(e)}")
        
        # 通用操作 =============================================================
        # return super().VMBackup(vm_name, vm_tips)

    # 恢复虚拟机 ###############################################################
    def Restores(self, vm_name: str, vm_back: str) -> ZMessage:
        # 专用操作 =============================================================
        try:
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 恢复快照
            restore_result = self.esxi_api.revert_snapshot(vm_name, vm_back)
            
            # 断开连接
            self.esxi_api.disconnect()
            
            if not restore_result.success:
                return restore_result
            
            return ZMessage(success=True, action="Restores", 
                          message=f"虚拟机恢复成功: {vm_back}")
            
        except Exception as e:
            self.esxi_api.disconnect()
            return ZMessage(success=False, action="Restores", 
                          message=f"恢复失败: {str(e)}")
        
        # 通用操作 =============================================================
        # return super().Restores(vm_name, vm_back)

    # VM镜像挂载 ###############################################################
    def HDDMount(self, vm_name: str, vm_imgs: SDConfig, in_flag=True) -> ZMessage:
        # 专用操作 =============================================================
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="HDDMount", message="虚拟机不存在")
            
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 关闭虚拟机
            self.esxi_api.power_off(vm_name)
            
            if in_flag:  # 挂载磁盘
                # 添加磁盘
                add_result = self.esxi_api.add_disk(
                    vm_name, 
                    vm_imgs.hdd_size, 
                    vm_imgs.hdd_name
                )
                if not add_result.success:
                    self.esxi_api.disconnect()
                    return add_result
                
                vm_imgs.hdd_flag = 1
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name] = vm_imgs
            else:  # 卸载磁盘
                if vm_imgs.hdd_name not in self.vm_saving[vm_name].hdd_all:
                    self.esxi_api.power_on(vm_name)
                    self.esxi_api.disconnect()
                    return ZMessage(
                        success=False, action="HDDMount", message="磁盘不存在")
                
                # TODO: 实现磁盘卸载
                self.vm_saving[vm_name].hdd_all[vm_imgs.hdd_name].hdd_flag = 0
            
            # 启动虚拟机
            self.esxi_api.power_on(vm_name)
            
            # 断开连接
            self.esxi_api.disconnect()
            
            # 保存配置
            self.data_set()
            
            action_text = "挂载" if in_flag else "卸载"
            return ZMessage(
                success=True,
                action="HDDMount",
                message=f"磁盘{action_text}成功")
            
        except Exception as e:
            self.esxi_api.disconnect()
            return ZMessage(
                success=False, action="HDDMount",
                message=f"磁盘操作失败: {str(e)}")
        
        # 通用操作 =============================================================
        # return super().HDDMount(vm_name, vm_imgs, in_flag)

    # ISO镜像挂载 ##############################################################
    def ISOMount(self, vm_name: str, vm_imgs: IMConfig, in_flag=True) -> ZMessage:
        # 专用操作 =============================================================
        try:
            if vm_name not in self.vm_saving:
                return ZMessage(
                    success=False, action="ISOMount", message="虚拟机不存在")
            
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            logger.info(f"准备{'挂载' if in_flag else '卸载'}ISO: {vm_imgs.iso_name}")
            
            # 关闭虚拟机
            self.esxi_api.power_off(vm_name)
            
            if in_flag:  # 挂载ISO
                # ISO文件路径（假设在ESXi的ISO目录中）
                iso_path = f"[{self.esxi_api.datastore_name}] ISO/{vm_imgs.iso_file}"
                
                # 挂载ISO
                attach_result = self.esxi_api.attach_iso(vm_name, iso_path)
                if not attach_result.success:
                    self.esxi_api.power_on(vm_name)
                    self.esxi_api.disconnect()
                    return attach_result
                
                # 检查挂载名称是否已存在
                if vm_imgs.iso_name in self.vm_saving[vm_name].iso_all:
                    self.esxi_api.power_on(vm_name)
                    self.esxi_api.disconnect()
                    return ZMessage(
                        success=False, action="ISOMount", message="挂载名称已存在")
                
                self.vm_saving[vm_name].iso_all[vm_imgs.iso_name] = vm_imgs
                logger.info(f"ISO挂载成功: {vm_imgs.iso_name} -> {vm_imgs.iso_file}")
            else:  # 卸载ISO
                if vm_imgs.iso_name not in self.vm_saving[vm_name].iso_all:
                    self.esxi_api.power_on(vm_name)
                    self.esxi_api.disconnect()
                    return ZMessage(
                        success=False, action="ISOMount", message="ISO镜像不存在")
                
                # TODO: 实现ISO卸载（设置为空）
                del self.vm_saving[vm_name].iso_all[vm_imgs.iso_name]
                logger.info(f"ISO卸载成功: {vm_imgs.iso_name}")
            
            # 启动虚拟机
            self.esxi_api.power_on(vm_name)
            
            # 断开连接
            self.esxi_api.disconnect()
            
            # 保存配置
            self.data_set()
            
            action_text = "挂载" if in_flag else "卸载"
            return ZMessage(
                success=True,
                action="ISOMount",
                message=f"ISO镜像{action_text}成功")
            
        except Exception as e:
            self.esxi_api.disconnect()
            return ZMessage(
                success=False, action="ISOMount",
                message=f"ISO操作失败: {str(e)}")
        
        # 通用操作 =============================================================
        # return super().ISOMount(vm_name, vm_imgs, in_flag)

    # 加载备份 #################################################################
    def LDBackup(self, vm_back: str = "") -> ZMessage:
        # 专用操作 =============================================================
        try:
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 清空现有备份记录
            for vm_name in self.vm_saving:
                self.vm_saving[vm_name].backups = []
            
            bal_nums = 0
            
            # 遍历所有虚拟机，获取快照信息
            for vm_name in self.vm_saving:
                vm = self.esxi_api.get_vm(vm_name)
                if not vm or not hasattr(vm, 'snapshot') or not vm.snapshot:
                    continue
                
                # 递归获取所有快照
                snapshots = self._get_all_snapshots(vm.snapshot.rootSnapshotList)
                
                for snapshot in snapshots:
                    bal_nums += 1
                    # 解析快照名称（格式：vm_name-YYYYMMDDHHmmss）
                    snap_name = snapshot.name
                    parts = snap_name.split("-")
                    if len(parts) >= 2:
                        try:
                            snap_time = datetime.datetime.strptime(parts[-1], "%Y%m%d%H%M%S")
                            self.vm_saving[vm_name].backups.append(
                                VMBackup(
                                    backup_name=snap_name,
                                    backup_time=snap_time,
                                    backup_tips=snapshot.description
                                )
                            )
                        except ValueError:
                            logger.warning(f"无法解析快照时间: {snap_name}")
            
            # 断开连接
            self.esxi_api.disconnect()
            
            # 保存配置
            self.data_set()
            
            return ZMessage(
                success=True,
                action="LDBackup",
                message=f"{bal_nums}个备份快照已加载")
            
        except Exception as e:
            self.esxi_api.disconnect()
            return ZMessage(
                success=False, action="LDBackup",
                message=f"加载备份失败: {str(e)}")
        
        # 通用操作 =============================================================
        # return super().LDBackup(vm_back)
    
    def _get_all_snapshots(self, snapshot_list):
        """递归获取所有快照"""
        snapshots = []
        for snapshot in snapshot_list:
            snapshots.append(snapshot)
            if hasattr(snapshot, 'childSnapshotList') and snapshot.childSnapshotList:
                snapshots.extend(self._get_all_snapshots(snapshot.childSnapshotList))
        return snapshots

    # 移除备份 #################################################################
    def RMBackup(self, vm_back: str) -> ZMessage:
        # 专用操作 =============================================================
        try:
            # 从备份名称中提取虚拟机名称
            parts = vm_back.split("-")
            if len(parts) < 2:
                return ZMessage(
                    success=False, action="RMBackup",
                    message="备份名称格式不正确")
            
            vm_name = parts[0]
            
            # 连接到ESXi
            connect_result = self.esxi_api.connect()
            if not connect_result.success:
                return connect_result
            
            # 删除快照
            delete_result = self.esxi_api.delete_snapshot(vm_name, vm_back)
            
            # 断开连接
            self.esxi_api.disconnect()
            
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
            self.esxi_api.disconnect()
            return ZMessage(
                success=False, action="RMBackup",
                message=f"删除备份失败: {str(e)}")
        
        # 通用操作 =============================================================
        # return super().RMBackup(vm_back)

    # 移除磁盘 #################################################################
    def RMMounts(self, vm_name: str, vm_imgs: str) -> ZMessage:
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
            
            # TODO: 从ESXi中删除磁盘文件
            
            return ZMessage(
                success=True, action="RMMounts",
                message="磁盘删除成功")
            
        except Exception as e:
            return ZMessage(
                success=False, action="RMMounts",
                message=f"删除磁盘失败: {str(e)}")
        
        # 通用操作 =============================================================
        # return super().RMMounts(vm_name, vm_imgs)

    # 查找显卡 #################################################################
    def GPUShows(self) -> dict[str, str]:
        # 专用操作 =============================================================
        # ESXi的GPU直通需要特殊配置，这里返回空字典
        # TODO: 实现ESXi GPU查询
        # 通用操作 =============================================================
        return {}