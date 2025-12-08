from HostServer import VmwareWork

HEConfig = {
    "VMWareSetup": {
        "Imported": VmwareWork.HostServer,
        "Descript": "VMWare Workstation",
        "isEnable": True,
        "isRemote": False,
        "Platform": ["Windows"],
        "CPU_Arch": ["x86_64"],
        "Optional": {},
        "SystemOS": {
            "Windows 10 x64": "windows9-64",

        },
        "Messages": ""
    },
    "HyperVSetup": {
        "Imported": None,
        "Descript": "Win HyperV Platform",
        "isEnable": False,
        "Platform": ["Windows"],
        "CPU_Arch": ["x86_64"],
        "Messages": "1、无法单独限制上下行带宽，取最低值"
    },
    "PromoxSetup": {
        "Descript": "PVE Runtime Platform",
        "isEnable": False,
        "Platform": ["Linux", "Windows"],
        "CPU_Arch": ["x86_64", "aarch64"],
    },
    "VirtualBoxs": {
        "Descript": "PVE Runtime Platform",
        "isEnable": False,
        "Platform": ["Linux", "Windows"],
        "CPU_Arch": ["x86_64", "aarch64"],
    },
    "vSphereESXi": {
        "Descript": "vSphere ESXi Runtime",
        "isEnable": False,
        "Platform": ["Linux", "Windows"],
        "CPU_Arch": ["x86_64"],
    },
    "MemuAndroid": {
        "Descript": "XYAndroid Simulator",
        "isEnable": False,
        "Platform": ["Windows"],
        "CPU_Arch": ["x86_64"],
        "Optional": {
            "graphics_render_mode": "图形渲染模式(1:DirectX, 0:OpenGL)",
            "enable_su": "是否以超级用户权限启动",
            "enable_audio": "是否启用音频",
            "fps": "帧率"
        }
    },
    "LxContainer": {
        "Descript": "Linux Container App",
        "isEnable": False,
        "Platform": ["Linux"],
        "CPU_Arch": ["x86_64", "aarch64"],
    },
    "DockerSetup": {
        "Descript": "Docker Runtime Host",
        "isEnable": False,
        "Platform": ["Linux", "Windows", "MacOS"],
        "CPU_Arch": ["x86_64", "aarch64"],
    },
    "PodmanSetup": {
        "Descript": "Podman Runtime, Host",
        "isEnable": False,
        "Platform": ["Linux", "Windows", "MacOS"],
        "CPU_Arch": ["x86_64", "aarch64"],
    },
    "MacOSFusion": {
        "Descript": "VMware Fusion Pro Mac",
        "isEnable": False,
        "Platform": ["MacOS"],
        "CPU_Arch": ["x86_64", "aarch64"],
    }
}
