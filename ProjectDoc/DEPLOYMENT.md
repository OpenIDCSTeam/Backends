# OpenIDC-Client 完整部署指南

<div align="center">

专业的生产环境部署方案

[环境要求](#环境要求) • [安装部署](#安装部署) • [配置管理](#配置管理) • [安全加固](#安全加固) • [运维监控](#运维监控) • [故障排除](#故障排除)

</div>

---

## 📋 环境要求

### 系统要求

| 组件 | 最低要求 | 推荐配置 | 说明 |
|------|----------|----------|------|
| **操作系统** | Windows 10<br>Ubuntu 18.04<br>CentOS 7<br>macOS 10.14 | Windows Server 2019<br>Ubuntu 20.04 LTS<br>CentOS 8<br>macOS 12 | 支持主流操作系统 |
| **Python** | 3.8.0 | 3.9.x 或 3.10.x | 需要pip包管理器 |
| **内存** | 4GB RAM | 8GB+ RAM | 根据管理的虚拟机数量调整 |
| **存储** | 2GB 可用空间 | 10GB+ 可用空间 | 包含日志和数据存储 |
| **CPU** | 双核处理器 | 四核+ 处理器 | 支持硬件虚拟化 |
| **网络** | 100Mbps | 1Gbps+ | 管理网络通信需求 |

### 虚拟化平台支持

| 平台 | 状态 | 系统要求 | 网络要求 |
|------|------|----------|----------|
| **VMware Workstation** | ✅ 生产就绪 | Windows 10/11<br>VMware Workstation 15+ | 主机可达，管理员权限 |
| **VMware vSphere ESXi** | 🚧 计划中 | ESXi 6.7+<br>vCenter Server | 443端口开放，API访问 |
| **LXC/LXD** | ℹ️ 开发中 | Ubuntu 18.04+<br>LXD 4.0+ | Unix socket或HTTPS访问 |
| **Docker/Podman** | ℹ️ 开发中 | Docker 20.10+ | Unix socket或TCP访问 |

### 网络端口要求

| 端口 | 协议 | 用途 | 外部访问 |
|------|------|------|----------|
| **1880** | HTTP | Web管理界面 | ✅ 可配置 |
| **6080** | HTTP | VNC代理服务 | ✅ 可配置 |
| **7681** | HTTP | WebSocket终端 | ✅ 可配置 |
| **443** | HTTPS | 安全Web访问 | ✅ 推荐生产环境 |
| **22** | TCP | SSH管理 | ❌ 仅内网 |

---

## 🚀 安装部署

### 方式一：快速部署（推荐新手）

#### Windows 环境

```batch
:: 1. 下载项目
curl -L -o OpenIDC-Client.zip https://github.com/OpenIDCSTeam/OpenIDCS-Client/archive/main.zip
powershell Expand-Archive OpenIDC-Client.zip -DestinationPath .
cd OpenIDC-Client-main

:: 2. 安装Python依赖（需要Python 3.8+）
pip install -r HostConfig/requirements.txt

:: 3. 启动服务
python HostServer.py

:: 4. 访问管理界面
:: 打开浏览器访问 http://localhost:1880
```

#### Linux 环境（Ubuntu/Debian）

```bash
#!/bin/bash
# 1. 安装系统依赖
sudo apt update
sudo apt install -y python3 python3-pip python3-venv curl wget

# 2. 下载项目
echo "下载项目..."
curl -L -o OpenIDC-Client.tar.gz https://github.com/OpenIDCSTeam/OpenIDCS-Client/archive/main.tar.gz
tar -xzf OpenIDC-Client.tar.gz
cd OpenIDC-Client-main

# 3. 创建虚拟环境（推荐）
echo "创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 4. 安装Python依赖
echo "安装依赖包..."
pip install --upgrade pip
pip install -r HostConfig/requirements.txt

# 5. 创建数据和日志目录
mkdir -p DataSaving logs

# 6. 启动服务
echo "启动服务..."
python HostServer.py --production

# 7. 验证服务
echo "服务已启动，访问 http://$(hostname -I | awk '{print $1}'):1880"
```

#### Linux 环境（CentOS/RHEL）

```bash
#!/bin/bash
# 1. 安装系统依赖
sudo yum update -y
sudo yum install -y python3 python3-pip curl wget gcc python3-devel

# 2. 下载项目
echo "下载项目..."
curl -L -o OpenIDC-Client.tar.gz https://github.com/OpenIDCSTeam/OpenIDCS-Client/archive/main.tar.gz
tar -xzf OpenIDC-Client.tar.gz
cd OpenIDC-Client-main

# 3. 创建虚拟环境
sudo dnf install -y python3-venv || sudo yum install -y python3-virtualenv
python3 -m venv venv
source venv/bin/activate

# 4. 安装Python依赖
echo "安装依赖包..."
pip install --upgrade pip
pip install -r HostConfig/requirements.txt

# 5. 创建数据和日志目录
mkdir -p DataSaving logs

# 6. 启动服务
echo "启动服务..."
python HostServer.py --production
```

### 方式二：Docker 部署（推荐生产环境）

#### Docker Compose 部署

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  openidc-client:
    build: .
    container_name: openidc-client
    ports:
      - "1880:1880"
      - "6080:6080"
      - "7681:7681"
    volumes:
      - ./DataSaving:/app/DataSaving
      - ./HostConfig:/app/HostConfig
      - ./logs:/app/logs
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - FLASK_ENV=production
      - HOST_SERVER_PORT=1880
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:1880/api/system/stats"]
      interval: 30s
      timeout: 10s
      retries: 3
```

创建 `Dockerfile`：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r HostConfig/requirements.txt

# 创建必要目录
RUN mkdir -p DataSaving logs

# 暴露端口
EXPOSE 1880 6080 7681

# 启动命令
CMD ["python", "HostServer.py", "--production"]
```

启动服务：

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式三：生产环境部署

#### 系统服务配置（Linux）

创建 systemd 服务文件 `/etc/systemd/system/openidc-client.service`：

```ini
[Unit]
Description=OpenIDC-Client Virtualization Management Platform
Documentation=https://github.com/OpenIDCSTeam/OpenIDCS-Client
After=network.target

[Service]
Type=simple
User=openidc
Group=openidc
WorkingDirectory=/opt/OpenIDC-Client
Environment=PATH=/opt/OpenIDC-Client/venv/bin
Environment=FLASK_ENV=production
ExecStart=/opt/OpenIDC-Client/venv/bin/python HostServer.py --production
ExecReload=/bin/kill -USR1 $MAINPID
Restart=always
RestartSec=3

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/OpenIDC-Client/DataSaving /opt/OpenIDC-Client/logs

# 资源限制
MemoryLimit=1G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

部署步骤：

```bash
# 1. 创建专用用户
sudo useradd -r -s /bin/false openidc

# 2. 安装项目
sudo mkdir -p /opt/OpenIDC-Client
sudo chown openidc:openidc /opt/OpenIDC-Client
cd /opt
sudo -u openidc git clone https://github.com/OpenIDCSTeam/OpenIDCS-Client.git OpenIDC-Client
cd OpenIDC-Client

# 3. 设置Python环境
sudo -u openidc python3 -m venv venv
sudo -u openidc venv/bin/pip install --upgrade pip
sudo -u openidc venv/bin/pip install -r HostConfig/requirements.txt

# 4. 创建必要目录
sudo -u openidc mkdir -p DataSaving logs

# 5. 配置系统服务
sudo cp openidc-client.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable openidc-client

# 6. 启动服务
sudo systemctl start openidc-client
sudo systemctl status openidc-client
```

---

## ⚙️ 配置管理

### 基础配置

#### 环境变量配置

创建 `.env` 文件：

```bash
# 应用配置
FLASK_ENV=production
HOST_SERVER_PORT=1880
SECRET_KEY=your-secret-key-here-change-in-production

# 数据库配置
DATABASE_PATH=DataSaving/database.db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=DataSaving/log-main.log
LOG_ROTATION=10 MB
LOG_RETENTION=7 days

# 安全配置
TOKEN_EXPIRE_HOURS=24
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=30

# 虚拟化平台配置
VMWARE_WORKSTATION_ENABLED=true
VSPHERE_ENABLED=false
LXC_ENABLED=false
DOCKER_ENABLED=false
```

#### 主机配置

首次启动后会自动生成配置文件，位于 `DataSaving/` 目录：

```json
{
  "hosts": {
    "workstation-01": {
      "server_name": "workstation-01",
      "server_type": "VmwareWork",
      "server_addr": "192.168.1.100",
      "server_user": "administrator",
      "server_pass": "encrypted_password",
      "status": "online",
      "vm_path": "C:\\Virtual Machines\\",
      "max_vms": 50,
      "enabled": true
    }
  },
  "settings": {
    "auto_start": true,
    "backup_interval": 3600,
    "cleanup_temp": true,
    "log_level": "INFO"
  }
}
```

### 网络配置

#### 防火墙设置

**Linux (ufw)**:
```bash
# 允许Web访问
sudo ufw allow 1880/tcp
# 允许VNC代理
sudo ufw allow 6080/tcp
# 允许WebSocket
sudo ufw allow 7681/tcp
# 允许SSH管理
sudo ufw allow from 192.168.1.0/24 to any port 22
```

**Linux (firewalld)**:
```bash
# 添加服务
sudo firewall-cmd --permanent --add-port=1880/tcp
sudo firewall-cmd --permanent --add-port=6080/tcp
sudo firewall-cmd --permanent --add-port=7681/tcp
# 重载配置
sudo firewall-cmd --reload
```

**Windows**:
```powershell
# 使用PowerShell配置防火墙
New-NetFirewallRule -DisplayName "OpenIDC-Client Web" -Direction Inbound -Protocol TCP -LocalPort 1880 -Action Allow
New-NetFirewallRule -DisplayName "OpenIDC-Client VNC" -Direction Inbound -Protocol TCP -LocalPort 6080 -Action Allow
New-NetFirewallRule -DisplayName "OpenIDC-Client WebSocket" -Direction Inbound -Protocol TCP -LocalPort 7681 -Action Allow
```

### SSL/TLS 配置

#### 使用Nginx反向代理（推荐）

安装Nginx并配置SSL：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL证书
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

    # 代理设置
    location / {
        proxy_pass http://127.0.0.1:1880;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # WebSocket代理
    location /websockify {
        proxy_pass http://127.0.0.1:6080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# HTTP重定向到HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 🔒 安全加固

### 访问控制

#### 1. IP白名单配置

在 `DataSaving/security.json` 中配置：

```json
{
  "ip_whitelist": [
    "192.168.1.0/24",
    "10.0.0.0/8",
    "203.0.113.0/24"
  ],
  "admin_ips": [
    "192.168.1.100",
    "192.168.1.101"
  ],
  "enable_rate_limit": true,
  "rate_limit_per_minute": 60
}
```

#### 2. Token安全配置

```bash
# 定期更换Token（建议每月）
curl -X POST http://localhost:1880/api/token/reset \
  -H "Authorization: Bearer YOUR_CURRENT_TOKEN"

# 设置强Token（32位以上随机字符串）
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

#### 3. 用户权限管理

```sql
-- 创建不同权限的用户
-- 管理员用户（全权限）
INSERT INTO users (username, password, email, is_admin, can_create_vm, can_modify_vm, can_delete_vm) 
VALUES ('admin', 'hashed_password', 'admin@company.com', 1, 1, 1, 1);

-- 普通用户（受限权限）
INSERT INTO users (username, password, email, is_admin, can_create_vm, can_modify_vm, can_delete_vm, quota_cpu, quota_ram, quota_ssd) 
VALUES ('user1', 'hashed_password', 'user1@company.com', 0, 1, 1, 0, 2, 4096, 50);
```

### 网络安全

#### 1. VPN访问

建议通过VPN访问管理界面：

```bash
# OpenVPN配置示例
# 只允许VPN网段访问管理端口
iptables -A INPUT -p tcp --dport 1880 -s 10.8.0.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 1880 -j DROP
```

#### 2. 审计日志

启用详细审计日志：

```python
# 在配置中启用
export LOG_LEVEL=DEBUG
export AUDIT_LOGGING=true
export LOG_SENSITIVE_DATA=false  # 不记录敏感信息
```

### 系统安全

#### 1. 定期更新

```bash
# 更新系统包
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y

# 更新Python依赖
pip list --outdated
pip install --upgrade -r HostConfig/requirements.txt
```

#### 2. 备份策略

```bash
#!/bin/bash
# 每日备份脚本
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/openidc-client"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据和配置
cp -r DataSaving $BACKUP_DIR/data_$DATE
cp -r HostConfig $BACKUP_DIR/config_$DATE
tar -czf $BACKUP_DIR/full_backup_$DATE.tar.gz DataSaving HostConfig

# 保留最近30天的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "data_*" -mtime +30 -exec rm -rf {} \;
find $BACKUP_DIR -name "config_*" -mtime +30 -exec rm -rf {} \;
```

---

## 📊 运维监控

### 健康检查

#### 1. 应用健康检查

```bash
#!/bin/bash
# 健康检查脚本
ENDPOINTS=(
    "http://localhost:1880/api/system/stats"
    "http://localhost:1880/api/server/detail"
    "http://localhost:1880/api/users/current"
)

for endpoint in "${ENDPOINTS[@]}"; do
    response=$(curl -s -o /dev/null -w "%{http_code}" $endpoint)
    if [ $response -eq 200 ]; then
        echo "✅ $endpoint - OK"
    else
        echo "❌ $endpoint - FAILED (HTTP $response)"
        # 发送告警
        # send_alert "OpenIDC-Client健康检查失败: $endpoint"
    fi
done
```

#### 2. 性能监控

使用Prometheus + Grafana监控：

```yaml
# prometheus.yml 配置片段
scrape_configs:
  - job_name: 'openidc-client'
    static_configs:
      - targets: ['localhost:1880']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### 日志管理

#### 1. 日志轮转配置

```python
# loguru配置示例
from loguru import logger

logger.add(
    "DataSaving/log-app.log",
    rotation="10 MB",      # 文件达到10MB时轮转
    retention="30 days",   # 保留30天
    compression="zip",    # 压缩旧日志
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
)
```

#### 2. 日志分析

```bash
# 分析错误日志
grep -i error DataSaving/log-main.log | tail -20

# 统计访问量
awk '/GET\|POST/ {print $4}' DataSaving/log-access.log | sort | uniq -c

# 监控异常登录
grep "Failed login" DataSaving/log-security.log | awk '{print $1}' | sort | uniq -c | sort -nr
```

---

## 🔧 故障排除

### 常见问题

#### 1. 服务无法启动

**症状**: 启动时报错或端口占用

**排查步骤**:
```bash
# 检查端口占用
netstat -tlnp | grep :1880
lsof -i :1880

# 检查Python依赖
pip check

# 检查配置文件
python -c "import json; json.load(open('DataSaving/config.json'))"

# 查看详细错误日志
tail -f DataSaving/log-main.log
```

**解决方案**:
```bash
# 释放端口
kill -9 $(lsof -ti:1880)

# 重新安装依赖
pip install --force-reinstall -r HostConfig/requirements.txt

# 重置配置文件
rm -rf DataSaving/*.json
python HostServer.py  # 重新生成配置
```

#### 2. 虚拟机无法连接

**症状**: 添加主机成功但无法管理虚拟机

**排查步骤**:
```bash
# 检查网络连接
ping <vmware_host_ip>
telnet <vmware_host_ip> 443

# 验证凭据
curl -k -u "username:password" https://<vmware_host_ip>/sdk

# 检查防火墙
iptables -L | grep <vmware_host_ip>

# 查看详细错误
journalctl -u openidc-client -f
```

**解决方案**:
```bash
# 检查VMware Workstation服务
# Windows: 服务管理中确认VMware相关服务运行
# Linux: systemctl status vmware

# 验证SDK访问权限
# 确保用户具有管理员权限

# 配置防火墙规则
# 允许出站连接到VMware主机的443端口
```

#### 3. Web界面无法访问

**症状**: 浏览器无法连接或显示错误

**排查步骤**:
```bash
# 检查服务状态
systemctl status openidc-client
ps aux | grep HostServer.py

# 检查端口监听
netstat -tlnp | grep 1880

# 测试本地访问
curl http://localhost:1880/api/system/stats

# 检查防火墙
iptables -L -n | grep 1880
```

**解决方案**:
```bash
# 重启服务
systemctl restart openidc-client

# 检查SELinux状态（CentOS/RHEL）
setenforce 0  # 临时禁用
sestatus      # 查看状态

# 配置防火墙
sudo ufw allow 1880/tcp
```

#### 4. 权限相关问题

**症状**: 用户无法执行某些操作

**排查步骤**:
```sql
-- 检查用户权限
SELECT username, is_admin, can_create_vm, can_modify_vm, can_delete_vm 
FROM users WHERE username='problem_user';

-- 检查资源配额
SELECT username, quota_cpu, quota_ram, quota_ssd, 
       used_cpu, used_ram, used_ssd 
FROM users WHERE username='problem_user';
```

**解决方案**:
```sql
-- 更新用户权限
UPDATE users SET 
    can_create_vm=1, 
    can_modify_vm=1, 
    quota_cpu=4, 
    quota_ram=8192 
WHERE username='problem_user';
```

### 性能优化

#### 1. 数据库优化

```python
# 定期清理和优化数据库
import sqlite3
conn = sqlite3.connect('DataSaving/database.db')
conn.execute('VACUUM')
conn.execute('ANALYZE')
conn.close()
```

#### 2. 内存优化

```bash
# 调整Python内存设置
export PYTHONMALLOC=malloc
export PYTHONOPTIMIZE=2

# 增加系统文件描述符限制
ulimit -n 65536
```

---

## 📈 维护指南

### 日常维护

#### 每日任务
- [ ] 检查服务运行状态
- [ ] 查看错误日志
- [ ] 监控系统资源使用
- [ ] 验证备份完整性

#### 每周任务
- [ ] 更新系统安全补丁
- [ ] 清理临时文件
- [ ] 检查磁盘空间
- [ ] 审查用户活动日志

#### 每月任务
- [ ] 更新Python依赖包
- [ ] 轮换访问Token
- [ ] 数据库优化和清理
- [ ] 安全配置审查

### 升级指南

#### 版本升级
```bash
# 1. 备份当前版本
cp -r /opt/OpenIDC-Client /opt/OpenIDC-Client.backup.$(date +%Y%m%d)

# 2. 拉取新版本
git pull origin main

# 3. 更新依赖
pip install -r HostConfig/requirements.txt --upgrade

# 4. 数据库迁移（如有）
python migrate_db.py

# 5. 重启服务
systemctl restart openidc-client

# 6. 验证功能
curl http://localhost:1880/api/system/stats
```

---

## 📞 技术支持

### 获取帮助

- **文档**: https://github.com/OpenIDCSTeam/OpenIDCS-Client/wiki
- **问题反馈**: https://github.com/OpenIDCSTeam/OpenIDCS-Client/issues
- **讨论区**: https://gitter.im/OpenIDCSTeam/community
- **邮件支持**: openidcs-support@team.org

### 紧急联系

- **安全漏洞**: security@openidcs.org
- **商业支持**: business@openidcs.org

---

<div align="center">

**📖 更多详细配置请参考各平台专项文档**

• [VMware Workstation 配置](ProjectDoc/SETUPS_ESX.md)  
• [LXC/LXD 环境搭建](ProjectDoc/SETUPS_LXD.md)  
• [Oracle Cloud 集成](ProjectDoc/SETUPS_OCI.md)  
• [构建部署说明](ProjectDoc/BUILDS_DOC.md)

</div>