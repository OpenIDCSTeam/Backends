import requests
import json
import hashlib
from typing import Optional, Dict, Any
from loguru import logger


class NetsManage:
    """爱快路由器管理类"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.sess_key = None
        self.session = requests.Session()

    # 登录WEB调用方法 ########################################################################
    def login(self) -> bool:
        """
        登录爱快路由器，设置cookie
        
        Returns:
            bool: 登录是否成功
        """
        try:
            # 构造登录数据
            passwd_md5 = hashlib.md5(self.password.encode()).hexdigest()
            # 根据要求，pass字段为salt_11+密码
            pass_str = "salt_11" + self.password

            login_data = {
                "username": self.username,
                "passwd": passwd_md5,
                "pass": pass_str,
                "remember_password": ""
            }

            # 发送登录请求
            response = self.session.post(
                f"{self.base_url}/Action/login",
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                # 解析响应JSON
                try:
                    response_data = response.json()

                    # 检查登录结果
                    if response_data.get("Result") == 10000:
                        # 提取session_key
                        cookies = response.headers.get('Set-Cookie', '')

                        if 'sess_key=' in cookies:
                            import re
                            match = re.search(r'sess_key=([^;]+)', cookies)
                            if match:
                                self.sess_key = match.group(1)

                                # 设置正确的cookie格式
                                cookie_header = f"sess_key={self.sess_key}; username={self.username}; login=1"
                                self.session.headers.update({'Cookie': cookie_header})

                                # 同时设置到cookies对象中
                                self.session.cookies.set('sess_key', self.sess_key)
                                self.session.cookies.set('username', self.username)
                                self.session.cookies.set('login', '1')

                                return True
                    else:
                        error_msg = response_data.get("ErrMsg", "未知错误")
                        logger.error(f"登录失败: {error_msg}")

                except json.JSONDecodeError:
                    logger.error("响应不是有效的JSON格式")
            else:
                logger.error(f"登录失败，状态码: {response.status_code}")

            return False

        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False

    # 内部API调用方法 ########################################################################
    def posts(self, func_name: str, action: str, param: Dict[str, Any]) -> Optional[Dict]:
        """
        内部API调用方法
        
        Args:
            func_name: 功能名称
            action: 操作类型
            param: 参数字典
            
        Returns:
            Optional[Dict]: API响应结果
        """
        if not self.sess_key:
            logger.warning("请先登录")
            return None

        try:
            api_data = {
                "func_name": func_name,
                "action": action,
                "param": param
            }

            response = self.session.post(
                f"{self.base_url}/Action/call",
                json=api_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API调用失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return None

    # 获取静态IP4列表 ########################################################################
    def get_dhcp(self, limit: str = "0,20", order_by: str = "", order: str = "") -> Optional[Dict]:
        """
        获取静态IP列表
        
        Args:
            limit: 分页限制，格式为"offset,count"
            order_by: 排序字段
            order: 排序方式
            
        Returns:
            Optional[Dict]: 静态IP列表数据
        """
        param = {
            "TYPE": "static_total,static_data",
            "limit": limit,
            "ORDER_BY": order_by,
            "ORDER": order
        }
        
        result = self.posts("dhcp_static", "show", param)
        if result and result.get("ErrMsg") == "Success":
            logger.info(f"✅ 获取静态IP列表成功，共{result['Data'].get('static_total', 0)}条")
            return result
        else:
            logger.error("❌ 获取静态IP列表失败")
            return None

    # 静态IP4设置方法 ########################################################################
    def add_dhcp(self, ip_addr: str, mac: str, hostname: str = "",
                 gateway: str = "auto", interface: str = "auto",
                 dns1: str = "119.29.29.29", dns2: str = "223.5.5.5",
                 comment: str = "") -> bool:
        """
        添加静态IP设置
        
        Args:
            ip_addr: IP地址
            mac: MAC地址
            hostname: 主机名
            gateway: 网关
            interface: 接口
            dns1: 主DNS
            dns2: 备用DNS
            comment: 备注
            
        Returns:
            bool: 操作是否成功
        """
        param = {
            "newRow": True,
            "hostname": hostname,
            "ip_addr": ip_addr,
            "mac": mac,
            "gateway": gateway,
            "interface": interface,
            "dns1": dns1,
            "dns2": dns2,
            "comment": comment,
            "enabled": "yes"
        }
        
        logger.info(f"🔍 准备添加DHCP - 提交参数: {json.dumps(param, ensure_ascii=False)}")

        result = self.posts("dhcp_static", "add", param)
        success = result is not None and result.get("success", False)
        if result['ErrMsg'] == "Success":
            success = True
        if success:
            logger.info(f"✅ 静态IP添加成功: {ip_addr} -> {mac}")
        else:
            logger.error(f"❌ 静态IP添加失败: {ip_addr} -> {mac}")
            logger.error(result)

        return success

    # 静态IP4删除方法 ########################################################################
    def del_dhcp(self, ip_addr: str = None, mac: str = None,
                 entry_id: int = None) -> bool:
        """
        删除静态IP设置
        
        Args:
            ip_addr: IP地址（可选）
            mac: MAC地址（可选）
            entry_id: 条目ID（可选）
            
        Returns:
            bool: 操作是否成功
        """
        # 如果没有提供entry_id，则通过get_dhcp查找
        if not entry_id:
            if not ip_addr and not mac:
                logger.warning("必须提供entry_id、ip_addr或mac中的一个")
                return False
            
            # 获取DHCP列表
            dhcp_list = self.get_dhcp(limit="0,100")
            if not dhcp_list or 'Data' not in dhcp_list:
                logger.error("无法获取DHCP列表")
                return False
            
            # 查找匹配的条目
            for item in dhcp_list['Data'].get('static_data', []):
                if (ip_addr and item.get('ip_addr') == ip_addr) or \
                   (mac and item.get('mac') == mac):
                    entry_id = item.get('id')
                    logger.info(f"找到匹配的DHCP条目: ID={entry_id}, IP={item.get('ip_addr')}, MAC={item.get('mac')}")
                    break
            
            if not entry_id:
                identifier = ip_addr or mac
                logger.error(f"未找到匹配的DHCP条目: {identifier}")
                return False
        
        param = {"id": entry_id}
        logger.info(f"🔍 准备删除DHCP - 提交参数: {json.dumps(param, ensure_ascii=False)}")

        result = self.posts("dhcp_static", "del", param)
        success = result is not None and result.get("success", False)
        logger.debug(result)
        if result and result.get('ErrMsg') == "Success":
            success = True
        if success:
            identifier = entry_id or ip_addr or mac
            logger.info(f"✅ 静态IP删除成功: {identifier}")
        else:
            identifier = entry_id or ip_addr or mac
            logger.error(f"❌ 静态IP删除失败: {identifier}")

        return success

    # TCP/UDP转发设置 ########################################################################
    def add_port(self, wan_port: str, lan_addr: str, lan_port: str,
                 interface: str = "wan1", protocol: str = "tcp+udp",
                 src_addr: str = "", comment: str = "") -> bool:
        """
        添加端口转发设置
        
        Args:
            wan_port: 外部端口
            lan_addr: 内部IP地址
            lan_port: 内部端口
            interface: 接口
            protocol: 协议类型
            src_addr: 源地址
            comment: 备注
            
        Returns:
            bool: 操作是否成功
        """
        param = {
            "enabled": "yes",
            "comment": comment,
            "interface": interface,
            "lan_addr": lan_addr,
            "protocol": protocol,
            "wan_port": wan_port,
            "lan_port": lan_port,
            "src_addr": src_addr
        }

        result = self.posts("dnat", "add", param)
        success = result is not None and result.get("success", False)
        if result['ErrMsg'] == "Success":
            success = True
        if success:
            logger.info(f"✅ 端口转发添加成功: 外部端口{wan_port} -> {lan_addr}:{lan_port}")
        else:
            logger.error(f"❌ 端口转发添加失败: 外部端口{wan_port} -> {lan_addr}:{lan_port}")
        return success

    # TCP/UDP转发删除 ########################################################################
    def del_port(self, wan_port: str = None, lan_addr: str = None,
                 entry_id: int = None) -> bool:
        """
        删除端口转发设置
        
        Args:
            wan_port: 外部端口（可选）
            lan_addr: 内部IP地址（可选）
            entry_id: 条目ID（可选）
            
        Returns:
            bool: 操作是否成功
        """
        if entry_id:
            param = {"id": entry_id}
        elif wan_port and lan_addr:
            param = {"wan_port": wan_port, "lan_addr": lan_addr}
        else:
            logger.warning("必须提供entry_id或wan_port+lan_addr")
            return False

        result = self.posts("dnat", "del", param)
        success = result is not None and result.get("success", False)
        if result['ErrMsg'] == "Success":
            success = True
        if success:
            identifier = entry_id or f"{wan_port}->{lan_addr}"
            logger.info(f"✅ 端口转发删除成功: {identifier}")
        else:
            identifier = entry_id or f"{wan_port}->{lan_addr}"
            logger.error(f"❌ 端口转发删除失败: {identifier}")
        return success

    # 获取ARP列表 ############################################################################
    def get_arp(self, limit: str = "0,20", order_by: str = "ip_addr_int", 
                order_type: str = "IP", order: str = "asc") -> Optional[Dict]:
        """
        获取ARP列表
        
        Args:
            limit: 分页限制，格式为"offset,count"
            order_by: 排序字段
            order_type: 排序类型
            order: 排序方式
            
        Returns:
            Optional[Dict]: ARP列表数据
        """
        param = {
            "TYPE": "total,data",
            "ORDER_BY": order_by,
            "orderType": order_type,
            "ORDER": order,
            "limit": limit
        }
        
        result = self.posts("arp", "show", param)
        if result and result.get("ErrMsg") == "Success":
            logger.info(f"✅ 获取ARP列表成功，共{result['Data'].get('total', 0)}条")
            return result
        else:
            logger.error("❌ 获取ARP列表失败")
            return None

    # ARP绑定方法 ############################################################################
    def add_arp(self, ip_addr: str, mac: str, interface: str = "lan1",
                comment: str = "") -> bool:
        """
        添加ARP绑定
        
        Args:
            ip_addr: IP地址
            mac: MAC地址
            interface: 接口
            comment: 备注
            
        Returns:
            bool: 操作是否成功
        """
        param = {
            "bind_type": 0,
            "interface": interface,
            "ip_addr": ip_addr,
            "mac": mac,
            "comment": comment,
            "old_ip_addr": ""
        }

        result = self.posts("arp", "add", param)
        success = result is not None and result.get("success", False)
        if result['ErrMsg'] == "Success" or result['Result'] == 3000:
            success = True
        if success:
            logger.info(f"✅ ARP绑定添加成功: {ip_addr} -> {mac}")
        else:
            logger.error(f"❌ ARP绑定添加失败: {ip_addr} -> {mac}")
        return success

    def del_arp(self, ip_addr: str = None, mac: str = None,
                entry_id: int = None) -> bool:
        """
        删除ARP绑定
        
        Args:
            ip_addr: IP地址（可选）
            mac: MAC地址（可选）
            entry_id: 条目ID（可选）
            
        Returns:
            bool: 操作是否成功
        """
        # 如果没有提供entry_id或ip_addr，则通过get_arp查找
        target_ip = ip_addr
        target_id = entry_id
        
        if not target_id or not target_ip:
            if not ip_addr and not mac and not entry_id:
                logger.warning("必须提供entry_id、ip_addr或mac中的一个")
                return False
            
            # 获取ARP列表
            arp_list = self.get_arp(limit="0,100")
            if not arp_list or 'Data' not in arp_list:
                logger.error("无法获取ARP列表")
                return False
            
            # 查找匹配的条目
            for item in arp_list['Data'].get('data', []):
                if (entry_id and item.get('id') == entry_id) or \
                   (ip_addr and item.get('ip_addr') == ip_addr) or \
                   (mac and item.get('mac') == mac):
                    target_id = item.get('id')
                    target_ip = item.get('ip_addr')
                    logger.info(f"找到匹配的ARP条目: ID={target_id}, IP={target_ip}, MAC={item.get('mac')}")
                    break
            
            if not target_id or not target_ip:
                identifier = entry_id or ip_addr or mac
                logger.error(f"未找到匹配的ARP条目: {identifier}")
                return False
        
        param = {
            "id": target_id,
            "ip_addr": target_ip
        }
        logger.info(f"🔍 准备删除ARP - 提交参数: {json.dumps(param, ensure_ascii=False)}")

        result = self.posts("arp", "del", param)
        success = result is not None and result.get("success", False)
        if result and result.get('ErrMsg') == "Success":
            success = True
        if success:
            logger.info(f"✅ ARP绑定删除成功: ID={target_id}, IP={target_ip}")
        else:
            logger.error(f"❌ ARP绑定删除失败: ID={target_id}, IP={target_ip}")
            logger.error(result)
        return success


# 使用示例
if __name__ == "__main__":
    # 创建管理对象
    nets = NetsManage("http://192.168.4.251", "admin", "IM807581")
    # 登录
    if nets.login():
        logger.info("登录成功")
        # 添加静态IP
        if nets.add_dhcp("10.1.9.101", "00:22:33:44:55:66", comment="测试设备"):
            logger.info("静态IP添加成功")
        # 添加端口转发
        if nets.add_port("1081", "10.1.9.101", "1081", comment="测试转发"):
            logger.info("端口转发添加成功")
    else:
        logger.error("登录失败")
