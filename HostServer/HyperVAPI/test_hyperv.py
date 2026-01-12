"""
Hyper-V模块测试脚本
用于验证Hyper-V虚拟机管理功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Config.VMPowers import VMPowers
from HostServer.Win64HyperV import HostServer


def test_connection():
    """测试连接到Hyper-V主机"""
    print("=" * 60)
    print("测试1: 连接到Hyper-V主机")
    print("=" * 60)
    
    # 创建主机配置（本地测试）
    config = HSConfig(
        server_name="HyperV-Test",
        server_addr="localhost",  # 本地测试
        server_user="",
        server_pass="",
        server_port=5985,
        system_path="C:\\Hyper-V\\VMs",
        images_path="C:\\Hyper-V\\Images",
        backup_path="C:\\Hyper-V\\Backups",
        remote_port=6080
    )
    
    # 创建主机服务
    host_server = HostServer(config)
    
    # 测试连接
    result = host_server.HSLoader()
    if result.success:
        print("✅ 连接成功")
        return host_server
    else:
        print(f"❌ 连接失败: {result.message}")
        return None


def test_vm_scan(host_server):
    """测试虚拟机扫描"""
    print("\n" + "=" * 60)
    print("测试2: 扫描虚拟机")
    print("=" * 60)
    
    result = host_server.VMDetect()
    if result.success:
        print(f"✅ 扫描成功: {result.message}")
        print(f"   扫描结果: {result.results}")
    else:
        print(f"❌ 扫描失败: {result.message}")


def test_host_status(host_server):
    """测试获取主机状态"""
    print("\n" + "=" * 60)
    print("测试3: 获取主机状态")
    print("=" * 60)
    
    status = host_server.HSStatus()
    print(f"✅ CPU使用率: {status.cpu_usage}%")
    print(f"✅ 内存使用率: {status.ram_usage}%")
    print(f"✅ 磁盘使用率: {status.hdd_usage}%")


def test_vm_list(host_server):
    """测试列出虚拟机"""
    print("\n" + "=" * 60)
    print("测试4: 列出虚拟机")
    print("=" * 60)
    
    if host_server.vm_saving:
        print(f"✅ 找到 {len(host_server.vm_saving)} 台虚拟机:")
        for vm_name, vm_config in host_server.vm_saving.items():
            print(f"   - {vm_name}")
            print(f"     CPU: {vm_config.cpu_num} 核")
            print(f"     内存: {vm_config.ram_num} MB")
    else:
        print("⚠️  未找到虚拟机")


def test_api_methods(host_server):
    """测试API方法是否存在"""
    print("\n" + "=" * 60)
    print("测试5: 验证API方法")
    print("=" * 60)
    
    required_methods = [
        'HSCreate', 'HSDelete', 'HSLoader', 'HSUnload',
        'VMCreate', 'VMDelete', 'VMUpdate', 'VMDetect',
        'VMPowers', 'VMPasswd', 'VMBackup', 'Restores',
        'HDDMount', 'ISOMount', 'LDBackup', 'RMBackup',
        'RMMounts', 'GPUShows', 'VMSetups'
    ]
    
    missing_methods = []
    for method in required_methods:
        if not hasattr(host_server, method):
            missing_methods.append(method)
    
    if not missing_methods:
        print(f"✅ 所有必需方法都已实现 ({len(required_methods)} 个)")
    else:
        print(f"❌ 缺少以下方法: {', '.join(missing_methods)}")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Hyper-V 虚拟机管理模块测试")
    print("=" * 60)
    
    try:
        # 测试1: 连接
        host_server = test_connection()
        if not host_server:
            print("\n⚠️  无法连接到Hyper-V主机，跳过后续测试")
            print("   请确保:")
            print("   1. 已启用Hyper-V功能")
            print("   2. 以管理员身份运行此脚本")
            print("   3. WinRM服务正在运行")
            return
        
        # 测试2: 扫描虚拟机
        test_vm_scan(host_server)
        
        # 测试3: 获取主机状态
        test_host_status(host_server)
        
        # 测试4: 列出虚拟机
        test_vm_list(host_server)
        
        # 测试5: 验证API方法
        test_api_methods(host_server)
        
        # 清理
        print("\n" + "=" * 60)
        print("清理资源")
        print("=" * 60)
        result = host_server.HSUnload()
        if result.success:
            print("✅ 资源清理成功")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
