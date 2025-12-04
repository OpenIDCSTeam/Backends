from VNCConsole.VNCSetup import NoVNCService


class VNCStart:
    def __init__(self):
        self.vnc: dict[str, dict[str, NoVNCService]] = {}

    def start(self, in_host, in_name, in_port, in_pass):
        pass

    def close(self, in_host, in_name):
        pass
