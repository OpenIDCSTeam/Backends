class NCConfig:
    def __init__(self, **kwargs):
        self.mac_addr: str = ""
        self.nic_type: str = ""
        self.ip4_addr: str = ""
        self.ip6_addr: str = ""
        self.nic_gate: str = ""  # 网关地址
        self.nic_mask: str = "255.255.255.0"  # 子网掩码，默认值
        self.dns_addr: list[str] = []
        self.__load__(**kwargs)

    def __dict__(self):
        return {
            "mac_addr": self.mac_addr,
            "nic_type": self.nic_type,
            "ip4_addr": self.ip4_addr,
            "ip6_addr": self.ip6_addr,
            "nic_gate": self.nic_gate,
            "nic_mask": self.nic_mask,
            "dns_addr": self.dns_addr,
        }

    # 加载数据 ===============================
    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        if self.mac_addr == "":
            self.mac_addr = self.send_mac()

    # 获取MAC地址 =============================
    def send_mac(self):
        import random
        
        # 检查IPv4地址是否有效
        if self.ip4_addr and self.ip4_addr.strip() != "":
            ip4_parts = self.ip4_addr.split(".")

            # 验证IP地址格式，确保有4个部分且每部分都是数字
            if len(ip4_parts) == 4 and all(part.strip().isdigit() for part in ip4_parts):
                try:
                    mac_parts = [format(int(part), '02x') for part in ip4_parts]  # 转换为两位十六进制
                    mac_parts = ":".join(mac_parts)
                    if self.ip4_addr.startswith("192"):
                        return "00:1C:" + mac_parts
                    elif self.ip4_addr.startswith("172"):
                        return "CC:D9:" + mac_parts
                    elif self.ip4_addr.startswith("10"):
                        return "10:F6:" + mac_parts
                    elif self.ip4_addr.startswith("100"):
                        return "00:1E:" + mac_parts
                    else:
                        return "00:00:" + mac_parts
                except (ValueError, TypeError):
                    pass  # 如果转换失败，继续尝试IPv6或生成随机MAC
        
        # 如果没有有效的IPv4，检查IPv6
        if self.ip6_addr and self.ip6_addr.strip() != "":
            try:
                # 移除IPv6地址中的冒号，获取后48位（12个十六进制字符）
                ipv6_clean = self.ip6_addr.replace(":", "").lower()
                if len(ipv6_clean) >= 12:
                    # 取后12个十六进制字符作为MAC地址的48位
                    mac_hex = ipv6_clean[-12:]
                    # 格式化为MAC地址格式 (每两个字符用冒号分隔)
                    mac_addr = ":".join([mac_hex[i:i+2] for i in range(0, 12, 2)])
                    return mac_addr
            except Exception:
                pass  # 如果IPv6处理失败，生成随机MAC

        # 如果IPv4和IPv6都没有，生成随机MAC地址
        # 生成4个随机字节（32位）
        random_bytes = [random.randint(0, 255) for _ in range(4)]
        random_mac = ":".join([format(b, '02x') for b in random_bytes])
        return "00:1C:" + random_mac
