class NCConfig:
    def __init__(self, **kwargs):
        self.mac_addr: str = ""
        self.nic_type: str = ""
        self.ip4_addr: str = ""
        self.ip6_addr: str = ""
        self.__load__(**kwargs)

    def __dict__(self):
        return {
            "mac_addr": self.mac_addr,
            "nic_type": self.nic_type,
            "ip4_addr": self.ip4_addr,
            "ip6_addr": self.ip6_addr,
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
        # 检查IP地址是否为空或无效
        if not self.ip4_addr or self.ip4_addr.strip() == "":
            return "00:00:00:00:00:00"

        ip4_parts = self.ip4_addr.split(".")

        # 验证IP地址格式，确保有4个部分且每部分都是数字
        if len(ip4_parts) != 4 or not all(part.strip().isdigit() for part in ip4_parts):
            return "00:00:00:00:00:00"

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
            # 如果转换失败，返回默认MAC地址
            return "00:00:00:00:00:00"
