# OpenIDC-Client API 文档 v2.0

<div align="center">

<strong>完整的 REST API 参考文档 - 支持多虚拟化平台统一管理</strong>

<a href="#基础信息">📋 基础信息</a> • <a href="#认证授权">🔐 认证授权</a> • <a href="#系统管理">⚙️ 系统管理</a> • <a href="#主机管理">🖥️ 主机管理</a> • <a href="#虚拟机管理">📦 虚拟机管理</a> • <a href="#网络管理">🌐 网络管理</a> • <a href="#存储管理">💾 存储管理</a> • <a href="#用户管理">👥 用户管理</a> • <a href="#错误码">❌ 错误码</a>

</div>

---

## 📋 基础信息

### 服务器信息

- **默认地址**: `http://localhost:1880`
- **API前缀**: `/api`
- **默认端口**: `1880` (Web), `6080` (VNC), `7681` (WebSocket)
- **传输协议**: HTTP/HTTPS, WebSocket
- **数据格式**: JSON
- **字符编码**: UTF-8

### 认证方式

#### Token 认证（推荐用于API调用）
```http
Authorization: Bearer <your-token>
```

#### Session 认证（用于Web界面）
通过登录页面获取Session Cookie

#### 获取初始Token
首次启动服务时会自动生成Token，可在控制台输出或数据库中查看：
```bash
python HostServer.py
# 控制台会显示: 访问Token: abc123def456...
```

### 响应格式

所有API响应均采用统一的JSON格式：

```json
{
  "code": 200,
  "msg": "success",
  "data": {},
  "timestamp": "2025-01-26T10:30:00Z"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码，200表示成功 |
| `msg` | string | 响应消息 |
| `data` | object | 响应数据，成功时返回 |
| `timestamp` | string | 响应时间戳（ISO 8601格式） |

### 通用状态码

| 状态码 | 说明 | 处理建议 |
|--------|------|----------|
| 200 | 成功 | 正常处理响应数据 |
| 400 | 请求参数错误 | 检查请求参数格式和内容 |
| 401 | 未授权 | 检查Token或登录状态 |
| 403 | 权限不足 | 检查用户权限和资源访问权限 |
| 404 | 资源不存在 | 检查资源ID或路径是否正确 |
| 409 | 资源冲突 | 资源已存在或状态冲突 |
| 422 | 参数验证失败 | 检查参数约束条件 |
| 429 | 请求频率超限 | 降低请求频率 |
| 500 | 服务器内部错误 | 联系管理员或查看日志 |
| 502 | 网关错误 | 检查后端服务状态 |
| 503 | 服务不可用 | 服务维护中或过载 |

---

## 🔐 认证授权

### 用户登录

```http
POST /login
Content-Type: application/json
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `login_type` | string | 否 | 登录类型：`token`（默认）或 `user` |
| `token` | string | 条件 | login_type为`token`时必填 |
| `username` | string | 条件 | login_type为`user`时必填 |
| `password` | string | 条件 | login_type为`user`时必填 |

**请求示例**:
```json
{
  "login_type": "token",
  "token": "abc123def456ghi789"
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "redirect": "/admin",
    "token": "abc123def456ghi789",
    "user_info": {
      "id": 1,
      "username": "admin",
      "is_admin": true,
      "is_active": true
    }
  },
  "timestamp": "2025-01-26T10:30:00Z"
}
```

### 用户登出

```http
GET /logout
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "退出成功",
  "data": null
}
```

### 获取当前用户信息

```http
GET /api/users/current
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "is_admin": true,
    "is_active": true,
    "email_verified": true,
    "created_at": "2025-01-01T00:00:00Z",
    "last_login": "2025-01-26T09:00:00Z",
    "assigned_hosts": ["workstation-01", "esxi-cluster-01"],
    
    "quota_cpu": 9999,
    "quota_ram": 999999,
    "quota_ssd": 999999,
    "quota_gpu": 9999,
    "quota_nat_ports": 9999,
    "quota_web_proxy": 9999,
    "quota_bandwidth_up": 9999,
    "quota_bandwidth_down": 9999,
    "quota_traffic": 999999,
    "quota_nat_ips": 100,
    "quota_pub_ips": 50,
    
    "used_cpu": 8,
    "used_ram": 16384,
    "used_ssd": 500,
    "used_gpu": 2,
    "used_nat_ports": 5,
    "used_web_proxy": 2,
    "used_upload_bw": 10,
    "used_download_bw": 50,
    "used_traffic": 1024,
    "used_nat_ips": 3,
    "used_pub_ips": 1,
    
    "can_create_vm": true,
    "can_modify_vm": true,
    "can_delete_vm": true
  }
}
```

---

## ⚙️ 系统管理

### 获取系统统计信息

```http
GET /api/system/stats
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "hosts_count": 5,
    "vms_count": 42,
    "users_count": 10,
    "running_vms": 28,
    "stopped_vms": 14,
    "total_cpu_cores": 40,
    "total_memory_gb": 128,
    "total_storage_gb": 2048,
    "cpu_usage_percent": 45.2,
    "memory_usage_percent": 67.8,
    "storage_usage_percent": 52.3,
    "network_rx_mbps": 125.6,
    "network_tx_mbps": 89.3
  }
}
```

### 获取系统日志

```http
GET /api/system/logger/detail?limit=100&level=INFO
Authorization: Bearer <token>
```

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `limit` | integer | 返回条数，默认100，最大1000 |
| `level` | string | 日志级别：DEBUG/INFO/WARNING/ERROR |
| `start_time` | string | 开始时间（ISO 8601格式） |
| `end_time` | string | 结束时间（ISO 8601格式） |

### 获取支持的引擎类型

```http
GET /api/system/engine
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "type": "VmwareWork",
      "name": "VMware Workstation",
      "description": "VMware Workstation for Windows",
      "status": "supported",
      "platforms": ["Windows"],
      "features": ["full_management", "snapshot", "clone"]
    },
    {
      "type": "vSphereESXi",
      "name": "VMware vSphere ESXi",
      "description": "Enterprise virtualization platform",
      "status": "planned",
      "platforms": ["Windows", "Linux"],
      "features": ["cluster_management", "ha", "drs"]
    },
    {
      "type": "Containers",
      "name": "LXC Containers",
      "description": "Lightweight container virtualization",
      "status": "developing",
      "platforms": ["Linux"],
      "features": ["resource_limits", "snapshots"]
    }
  ]
}
```

### Token 管理

#### 获取当前Token
```http
GET /api/token/current
Authorization: Bearer <token>
```

#### 设置新Token
```http
POST /api/token/set
Authorization: Bearer <token>
Content-Type: application/json

{
  "token": "new-token-string-here"
}
```

#### 重置Token（自动生成）
```http
POST /api/token/reset
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "Token重置成功",
  "data": {
    "token": "new-generated-token-xyz789abc123",
    "expires_at": "2025-02-26T10:30:00Z"
  }
}
```

### 系统设置管理

#### 获取系统设置
```http
GET /api/system/settings
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "registration_enabled": "1",
    "email_verification_enabled": "1",
    "default_quota_cpu": "2",
    "default_quota_ram": "4",
    "default_quota_ssd": "20",
    "max_vms_per_user": "10",
    "session_timeout": "3600",
    "log_level": "INFO",
    "backup_enabled": "1",
    "auto_cleanup_days": "30",
    "resend_apikey": "re_xxxxxxxxxxxxx",
    "resend_email": "noreply@openidcs.org"
  }
}
```

#### 更新系统设置
```http
POST /api/system/settings
Authorization: Bearer <token>
Content-Type: application/json

{
  "registration_enabled": "0",
  "email_verification_enabled": "1",
  "default_quota_cpu": "4",
  "max_vms_per_user": "20",
  "session_timeout": "7200"
}
```

---

## 🖥️ 主机管理

### 获取主机列表

```http
GET /api/server/detail
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "workstation-01": {
      "server_name": "workstation-01",
      "server_type": "VmwareWork",
      "server_addr": "192.168.1.100",
      "server_user": "administrator",
      "status": "online",
      "vms_count": 12,
      "running_vms": 8,
      "stopped_vms": 4,
      "cpu_usage": 45.2,
      "memory_usage": 67.8,
      "disk_usage": 52.3,
      "last_check": "2025-01-26T10:25:00Z",
      "version": "VMware Workstation 17 Pro",
      "uptime_seconds": 86400
    },
    "esxi-cluster-01": {
      "server_name": "esxi-cluster-01",
      "server_type": "vSphereESXi",
      "server_addr": "192.168.1.200",
      "server_user": "root",
      "status": "offline",
      "vms_count": 0,
      "error_message": "Connection timeout",
      "last_check": "2025-01-26T10:20:00Z"
    }
  }
}
```

### 获取单个主机详情

```http
GET /api/server/detail/{hs_name}
Authorization: Bearer <token>
```

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `hs_name` | string | 主机名称 |

### 添加主机

```http
POST /api/server/create
Authorization: Bearer <token>
Content-Type: application/json
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `server_name` | string | 是 | 主机名称，唯一标识 |
| `server_type` | string | 是 | 主机类型：`VmwareWork`、`vSphereESXi`、`Containers`等 |
| `server_addr` | string | 是 | 主机IP地址或域名 |
| `server_user` | string | 是 | 登录用户名 |
| `server_pass` | string | 是 | 登录密码（会自动加密存储） |
| `server_port` | integer | 否 | 端口号，默认根据类型决定 |
| `vm_path` | string | 否 | 虚拟机存储路径 |
| `max_vms` | integer | 否 | 最大虚拟机数量限制 |
| `enabled` | boolean | 否 | 是否启用，默认true |

**请求示例**:
```json
{
  "server_name": "workstation-01",
  "server_type": "VmwareWork",
  "server_addr": "192.168.1.100",
  "server_user": "administrator",
  "server_pass": "my-password",
  "vm_path": "C:\\Virtual Machines\\",
  "max_vms": 50,
  "enabled": true
}
```

### 更新主机配置

```http
PUT /api/server/update/{hs_name}
Authorization: Bearer <token>
Content-Type: application/json
```

### 删除主机

```http
DELETE /api/server/delete/{hs_name}
Authorization: Bearer <token>
```

### 主机电源管理

```http
POST /api/server/powers/{hs_name}
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "start"
}
```

**电源操作类型**:

| 操作 | 说明 | 支持的平台 |
|------|------|------------|
| `start` | 启动主机 | 物理主机 |
| `stop` | 关闭主机 | 物理主机 |
| `restart` | 重启主机 | 物理主机 |
| `enable` | 启用监控 | 所有平台 |
| `disable` | 禁用监控 | 所有平台 |

### 获取主机状态

```http
GET /api/server/status/{hs_name}
Authorization: Bearer <token>
```

---

## 📦 虚拟机管理

### 获取虚拟机列表

```http
GET /api/client/detail/{hs_name}
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "vm_uuid": "420d5c8f-8e1a-4b5c-9f2e-1a2b3c4d5e6f",
      "vm_name": "Ubuntu-Server-01",
      "display_name": "Ubuntu Server Production",
      "os_name": "ubuntu-22.04",
      "os_version": "22.04.3 LTS",
  "cpu_num": 2,
  "mem_num": 8192,
  "hdd_num": 100,
      "gpu_num": 1,
      "status": "running",
      "power_state": "powered_on",
      "ip_address": "192.168.1.101",
      "mac_address": "00:50:56:XX:XX:XX",
      "created_time": "2025-01-15T08:00:00Z",
      "modified_time": "2025-01-26T09:30:00Z",
      "last_boot": "2025-01-26T07:00:00Z",
      "tools_status": "guestToolsRunning",
      "snapshot_count": 3,
      "is_template": false,
      "owner": "admin",
      "tags": ["production", "web-server"]
    }
  ]
}
```

### 获取虚拟机详情

```http
GET /api/client/detail/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

### 创建虚拟机

```http
POST /api/client/create/{hs_name}
Authorization: Bearer <token>
Content-Type: application/json
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `vm_uuid` | string | 是 | 虚拟机UUID，符合RFC 4122标准 |
| `vm_name` | string | 是 | 虚拟机名称 |
| `display_name` | string | 否 | 显示名称 |
| `os_name` | string | 是 | 操作系统名称 |
| `os_version` | string | 否 | 操作系统版本 |
| `cpu_num` | integer | 是 | CPU核心数，1-64 |
| `mem_num` | integer | 是 | 内存大小(MB)，512-1048576 |
| `hdd_num` | integer | 是 | 磁盘大小(GB)，1-10240 |
| `gpu_num` | integer | 否 | GPU数量，0-8，默认0 |
| `vm_path` | string | 否 | 虚拟机存储路径 |
| `iso_path` | string | 否 | 安装ISO文件路径 |
| `network_type` | string | 否 | 网络类型：`bridged`、`nat`、`hostonly` |
| `description` | string | 否 | 虚拟机描述 |
| `template_uuid` | string | 否 | 基于模板创建时的模板UUID |

**请求示例**:
```json
{
  "vm_uuid": "420d5c8f-8e1a-4b5c-9f2e-1a2b3c4d5e6f",
  "vm_name": "ubuntu-web-01",
  "display_name": "Ubuntu Web Server",
  "os_name": "ubuntu-22.04",
  "cpu_num": 2,
  "mem_num": 4096,
  "hdd_num": 50,
  "network_type": "bridged",
  "description": "Production web server",
  "tags": ["production", "web"]
}
```

### 更新虚拟机配置

```http
PUT /api/client/update/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json
```

**可更新字段**:
- `vm_name`, `display_name`, `description`
- `cpu_num`, `mem_num`, `hdd_num`, `gpu_num`
- `network_type`, `vm_path`

### 删除虚拟机

```http
DELETE /api/client/delete/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

**查询参数**:
- `force`: boolean，是否强制删除，默认false

### 虚拟机电源控制

```http
POST /api/client/powers/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "S_START"
}
```

**电源操作类型**:

| 操作 | 说明 | VMware对应值 |
|------|------|-------------|
| `S_START` | 启动虚拟机 | poweredOn |
| `H_CLOSE` | 关闭虚拟机 | poweredOff |
| `S_RESET` | 重启虚拟机 | reset |
| `S_PAUSE` | 挂起虚拟机 | suspended |
| `S_RESUME` | 恢复虚拟机 | resume |

### 获取虚拟机状态

```http
GET /api/client/status/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "vm_uuid": "420d5c8f-8e1a-4b5c-9f2e-1a2b3c4d5e6f",
    "status": "running",
    "power_state": "powered_on",
    "cpu_usage": 15.2,
    "memory_usage": 2048,
    "memory_total": 4096,
    "disk_read_rate": 1024,
    "disk_write_rate": 512,
    "network_rx_rate": 125.6,
    "network_tx_rate": 89.3,
    "uptime_seconds": 3600,
    "tools_version": "12.1.0",
    "guest_os": "Ubuntu 22.04 LTS",
    "ip_addresses": ["192.168.1.101"],
    "state_changed": "2025-01-26T10:25:00Z"
  }
}
```

### 获取控制台访问地址

```http
GET /api/client/remote/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "console_url": "http://192.168.1.100:6080/vnc_auto.html?token=vnc-token-xyz789",
    "terminal_url": "http://192.168.1.100:7681/?arg=ssh-connection&token=ssh-token-abc123",
    "websocket_console": "ws://192.168.1.100:6080/websockify",
    "access_methods": [
      {
        "type": "vnc",
        "url": "http://192.168.1.100:6080/vnc_auto.html?token=vnc-token-xyz789",
        "description": "图形化控制台"
      },
      {
        "type": "ssh",
        "url": "http://192.168.1.100:7681/?arg=ssh-connection&token=ssh-token-abc123",
        "description": "命令行终端"
      }
    ],
    "expires_at": "2025-01-26T18:30:00Z"
  }
}
```

### 扫描主机虚拟机

```http
POST /api/client/scaner/{hs_name}
Authorization: Bearer <token>
```

---

## 🌐 网络管理

### IP地址管理

#### 获取虚拟机IP地址列表
```http
GET /api/client/ipaddr/detail/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "nic_name": "Network adapter 1",
      "nic_type": "bridged",
      "mac_address": "00:50:56:XX:XX:01",
      "ip_address": "192.168.1.101",
      "subnet_mask": "255.255.255.0",
      "gateway": "192.168.1.1",
      "dns_servers": ["8.8.8.8", "8.8.4.4"],
      "dhcp_enabled": false
    }
  ]
}
```

#### 添加IP地址配置
```http
POST /api/client/ipaddr/create/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "nic_name": "Network adapter 1",
  "nic_type": "bridged",
  "ip_address": "192.168.1.102",
  "subnet_mask": "255.255.255.0",
  "gateway": "192.168.1.1",
  "dns_servers": ["8.8.8.8"],
  "dhcp_enabled": false
}
```

#### 删除IP地址配置
```http
DELETE /api/client/ipaddr/delete/{hs_name}/{vm_uuid}/{nic_name}
Authorization: Bearer <token>
```

### NAT端口转发

#### 获取NAT规则
```http
GET /api/client/natget/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "rule_index": 0,
      "host_port": 8080,
      "vm_port": 80,
      "protocol": "tcp",
      "description": "HTTP web access",
      "enabled": true,
      "created_time": "2025-01-20T10:00:00Z"
    },
    {
      "rule_index": 1,
      "host_port": 8443,
      "vm_port": 443,
      "protocol": "tcp",
      "description": "HTTPS web access",
      "enabled": true,
      "created_time": "2025-01-20T10:05:00Z"
    }
  ]
}
```

#### 添加NAT规则
```http
POST /api/client/natadd/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "host_port": 3306,
  "vm_port": 3306,
  "protocol": "tcp",
  "description": "MySQL database access"
}
```

#### 删除NAT规则
```http
DELETE /api/client/natdel/{hs_name}/{vm_uuid}/{rule_index}
Authorization: Bearer <token>
```

### 反向代理配置

#### 获取代理配置列表
```http
GET /api/client/proxys/detail/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "proxy_index": 0,
      "domain": "web1.example.com",
      "target_port": 80,
      "ssl_enabled": true,
      "ssl_cert_path": "/certs/example.com.crt",
      "ssl_key_path": "/certs/example.com.key",
      "description": "Main website",
      "enabled": true
    }
  ]
}
```

#### 添加反向代理配置
```http
POST /api/client/proxys/create/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "domain": "api.example.com",
  "target_port": 8080,
  "ssl_enabled": true,
  "description": "API service"
}
```

#### 删除反向代理配置
```http
DELETE /api/client/proxys/delete/{hs_name}/{vm_uuid}/{proxy_index}
Authorization: Bearer <token>
```

### 管理员反向代理管理

#### 获取所有反向代理配置
```http
GET /api/admin/proxys/list
Authorization: Bearer <token>
```

#### 获取指定主机的所有反向代理
```http
GET /api/admin/proxys/list/{hs_name}
Authorization: Bearer <token>
```

---

## 💾 存储管理

### 数据盘管理

#### 挂载数据盘
```http
POST /api/client/hdd/mount/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "hdd_name": "data-disk-01",
  "hdd_size": 100,
  "disk_type": "scsi",
  "persistent": true,
  "description": "Application data storage"
}
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `hdd_name` | string | 是 | 磁盘名称 |
| `hdd_size` | integer | 是 | 磁盘大小(GB) |
| `disk_type` | string | 否 | 磁盘类型：`ide`、`scsi`、`sata`，默认`scsi` |
| `persistent` | boolean | 否 | 是否持久化，默认true |
| `description` | string | 否 | 磁盘描述 |

#### 卸载数据盘
```http
POST /api/client/hdd/unmount/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "hdd_name": "data-disk-01"
}
```

#### 删除数据盘
```http
DELETE /api/client/hdd/delete/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "hdd_name": "data-disk-01",
  "force": false
}
```

#### 移交数据盘所有权
```http
POST /api/client/hdd/transfer/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "hdd_name": "data-disk-01",
  "new_owner": "user2"
}
```

### ISO管理

#### 挂载ISO镜像
```http
POST /api/client/iso/mount/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "iso_name": "ubuntu-22.04.iso",
  "description": "Ubuntu installation media"
}
```

#### 卸载ISO镜像
```http
DELETE /api/client/iso/unmount/{hs_name}/{vm_uuid}/{iso_name}
Authorization: Bearer <token>
```

---

## 🗄️ 备份管理

### 虚拟机备份

#### 创建备份
```http
POST /api/client/backup/create/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "backup_name": "pre-upgrade-backup",
  "description": "Backup before system upgrade",
  "include_memory": false,
  "compress": true
}
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `backup_name` | string | 否 | 备份名称，默认自动生成 |
| `description` | string | 否 | 备份描述 |
| `include_memory` | boolean | 否 | 是否包含内存状态，默认false |
| `compress` | boolean | 否 | 是否压缩，默认true |

#### 获取备份列表
```http
GET /api/client/backup/list/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "backup_name": "backup-20250126-103000",
      "description": "Pre-upgrade backup",
      "size_mb": 2048,
      "created_time": "2025-01-26T10:30:00Z",
      "created_by": "admin",
      "vm_state": "poweredOn",
      "include_memory": false,
      "compressed": true
    }
  ]
}
```

#### 恢复备份
```http
POST /api/client/backup/restore/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "backup_name": "backup-20250126-103000",
  "power_on_after_restore": true
}
```

#### 删除备份
```http
DELETE /api/client/backup/delete/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "backup_name": "backup-20250126-103000"
}
```

#### 扫描主机备份文件
```http
POST /api/server/backup/scan/{hs_name}
Authorization: Bearer <token>
```

---

## 👥 用户管理

### 用户CRUD操作

#### 获取用户列表
```http
GET /api/users?page=1&page_size=20&role=admin
Authorization: Bearer <token>
```

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | integer | 页码，默认1 |
| `page_size` | integer | 每页数量，默认20，最大100 |
| `role` | string | 筛选角色：`admin`、`user` |
| `status` | string | 筛选状态：`active`、`inactive` |
| `search` | string | 搜索关键词（用户名、邮箱） |

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "users": [
      {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_admin": true,
        "is_active": true,
        "email_verified": true,
        "created_at": "2025-01-01T00:00:00Z",
        "last_login": "2025-01-26T09:00:00Z",
        "assigned_hosts": ["workstation-01"],
        "vm_count": 5
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20
  }
}
```

#### 创建用户
```http
POST /api/users
Authorization: Bearer <token>
Content-Type: application/json
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名，3-20字符 |
| `email` | string | 是 | 邮箱地址 |
| `password` | string | 是 | 密码，至少6字符 |
| `is_admin` | boolean | 否 | 是否管理员，默认false |
| `is_active` | boolean | 否 | 是否激活，默认true |
| `email_verified` | boolean | 否 | 邮箱是否已验证，默认false |
| `can_create_vm` | boolean | 否 | 是否可以创建虚拟机，默认false |
| `can_modify_vm` | boolean | 否 | 是否可以修改虚拟机，默认false |
| `can_delete_vm` | boolean | 否 | 是否可以删除虚拟机，默认false |
| `quota_cpu` | integer | 否 | CPU配额，默认0（无限制） |
| `quota_ram` | integer | 否 | 内存配额(MB)，默认0 |
| `quota_ssd` | integer | 否 | 存储配额(GB)，默认0 |
| `assigned_hosts` | array | 否 | 分配的主机列表 |

#### 获取用户详情
```http
GET /api/users/{user_id}
Authorization: Bearer <token>
```

#### 更新用户信息
```http
PUT /api/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json
```

#### 删除用户
```http
DELETE /api/users/{user_id}
Authorization: Bearer <token>
```

### 用户资源管理

#### 修改密码
```http
POST /api/users/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "old-password",
  "new_password": "new-password",
  "confirm_password": "new-password"
}
```

#### 修改邮箱
```http
POST /api/users/change-email
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_email": "newemail@example.com"
}
```

#### 忘记密码
```http
POST /api/system/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### 重置密码
```http
POST /api/system/reset-password
Content-Type: application/json

{
  "token": "reset-token-from-email",
  "new_password": "new-password",
  "confirm_password": "new-password"
}
```

---

## 🔧 高级功能

### 资源配额管理

#### 手动重新计算用户配额
```http
POST /api/system/recalculate-quotas
Authorization: Bearer <token>
```

### 操作系统镜像管理

#### 获取主机OS镜像列表
```http
GET /api/client/os-images/{hs_name}
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "ubuntu": [
      {
        "name": "Ubuntu 22.04 Server",
        "file": "ubuntu-22.04-server.iso",
        "size_mb": 1456,
        "version": "22.04.3",
        "architecture": "x86_64"
      }
    ],
    "centos": [
      {
        "name": "CentOS 7 Minimal",
        "file": "centos-7-x86_64-minimal.iso",
        "size_mb": 988,
        "version": "7.9.2009",
        "architecture": "x86_64"
      }
    ]
  }
}
```

### 虚拟机所有权管理

#### 获取虚拟机所有者列表
```http
GET /api/client/owners/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
```

#### 添加虚拟机所有者
```http
POST /api/client/owners/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "user2",
  "permission": "read_write"
}
```

#### 删除虚拟机所有者
```http
DELETE /api/client/owners/{hs_name}/{vm_uuid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "user2"
}
```

#### 移交虚拟机所有权
```http
POST /api/client/owners/{hs_name}/{vm_uuid}/transfer
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_owner": "user2",
  "transfer_disks": true,
  "transfer_backups": true
}
```

---

## ❌ 错误码详解

### 通用错误码

| 错误码 | HTTP状态 | 说明 | 解决方案 |
|--------|----------|------|----------|
| 1001 | 404 | 主机不存在 | 检查主机名称是否正确 |
| 1002 | 404 | 虚拟机不存在 | 检查虚拟机UUID是否正确 |
| 1003 | 503 | 主机连接失败 | 检查网络连接和凭据 |
| 1004 | 500 | 虚拟机创建失败 | 检查参数和资源限制 |
| 1005 | 500 | 虚拟机操作失败 | 查看详细错误信息 |
| 1006 | 409 | 资源冲突 | 资源已被占用或状态不允许 |
| 1007 | 422 | 参数验证失败 | 检查参数格式和约束 |

### 认证授权错误码

| 错误码 | HTTP状态 | 说明 | 解决方案 |
|--------|----------|------|----------|
| 2001 | 401 | Token无效 | 重新获取有效Token |
| 2002 | 401 | Token已过期 | 重新登录获取新Token |
| 2003 | 403 | 权限不足 | 联系管理员分配权限 |
| 2004 | 401 | 用户名或密码错误 | 检查登录凭据 |
| 2005 | 403 | 用户已被禁用 | 联系管理员启用账户 |
| 2006 | 403 | 邮箱未验证 | 检查邮箱并完成验证 |

### 资源限制错误码

| 错误码 | HTTP状态 | 说明 | 解决方案 |
|--------|----------|------|----------|
| 3001 | 409 | CPU配额超限 | 减少CPU分配或申请更高配额 |
| 3002 | 409 | 内存配额超限 | 减少内存分配或申请更高配额 |
| 3003 | 409 | 存储配额超限 | 减少存储分配或申请更高配额 |
| 3004 | 409 | 虚拟机数量超限 | 删除不需要的虚拟机 |
| 3005 | 409 | 网络端口冲突 | 使用其他端口号 |

### 系统错误码

| 错误码 | HTTP状态 | 说明 | 解决方案 |
|--------|----------|------|----------|
| 9001 | 500 | 数据库连接失败 | 检查数据库文件权限 |
| 9002 | 500 | 配置文件损坏 | 恢复或重新生成配置 |
| 9003 | 500 | 日志写入失败 | 检查日志目录权限 |
| 9004 | 503 | 服务暂时不可用 | 稍后重试或联系管理员 |

---

## 📚 最佳实践

### 1. API调用建议

- **使用HTTPS**: 生产环境务必使用HTTPS加密传输
- **合理缓存**: 对频繁查询的数据使用本地缓存
- **批量操作**: 多个相似操作用批量接口减少请求次数
- **错误处理**: 始终检查响应状态码和错误消息
- **限流保护**: 避免过于频繁的API调用

### 2. 安全建议

- **定期更换Token**: 建议每30天更换一次API Token
- **最小权限原则**: 为用户分配完成任务所需的最小权限
- **IP白名单**: 限制管理界面的访问IP范围
- **审计日志**: 定期检查操作日志发现异常行为
- **强密码策略**: 要求用户使用复杂密码并定期更换

### 3. 性能优化

- **分页查询**: 大量数据使用分页避免单次返回过多数据
- **异步操作**: 耗时操作使用异步方式避免超时
- **连接池**: 使用连接池复用数据库连接
- **索引优化**: 确保数据库表的查询字段有适当索引
- **资源监控**: 监控CPU、内存使用避免资源耗尽

---

## 📞 技术支持

- **API测试工具**: 推荐使用 Postman 或 Insomnia
- **在线测试**: https://api.openidcs.org/docs （如有）
- **GitHub Issues**: https://github.com/OpenIDCSTeam/OpenIDCS-Client/issues
- **技术交流群**: QQ群 123456789
- **邮件支持**: api-support@openidcs.org

---

<div align="center">

**📖 API文档版本: v2.0**  
**📅 最后更新: 2025-01-26**  
**📝 作者: OpenIDC Team**

⭐ 如果这份文档对您有帮助，请给项目点个Star！

</div>