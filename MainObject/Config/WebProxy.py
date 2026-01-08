import json


class WebProxy:
    def __init__(self, **kwargs):
        self.lan_port: int = 0  # 本地端口
        self.lan_addr: str = ""  # 本地地址
        self.web_addr: str = ""  # 映射域名
        self.web_tips: str = ""  # 映射备注
        self.is_https: bool = False

    def __load__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __save__(self):
        return {
            "lan_port": self.lan_port,
            "lan_addr": self.lan_addr,
            "web_addr": self.web_addr,
            "web_tips": self.web_tips,
            "is_https": self.is_https
        }

    def __str__(self):
        return json.dumps(self.__save__())
