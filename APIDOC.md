# OpenIDCS API 文档

## 认证

所有API请求需要通过以下方式之一进行认证：

1. **Bearer Token**：在HTTP头中添加 `Authorization: Bearer <token>`
2. **Session登录**：通过 `/login` 接口登录后使用Session

## 响应格式

所有API返回统一的JSON格式：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

## 系统管理

### 重置Token

```
POST /api/system/resets
```

生成新的访问Token。

### 设置Token

```
POST /api/system/create
```

设置指定的Token。

**请求体：**
```json
{
  "token": "your-custom-token"
}
```

### 获取Token

```
GET /api/system/tquery
```

获取当前的访问Token。

### 获取引擎类型

```
GET /api/system/engine
```

获取支持的虚拟化引擎类型列表。

### 保存配置

```
POST /api/system/saving
```

保存系统配置到磁盘。

### 加载配置

```
POST /api/system/loader
```

从磁盘加载系统配置。

### 系统统计

```
GET /api/system/statis
```

获取系统统计信息（主机数量、虚拟机数量等）。

### 获取日志

```
GET /api/system/logger/detail
```

获取系统日志记录。

**查询参数：**
- `page`: 页码（可选）
- `limit`: 每页数量（可选）

### 获取任务

```
GET /api/system/tasker
```

获取任务记录。

## 主机管理

### 主机列表

```
GET /api/server/detail
```

获取所有主机列表。

### 主机详情

```
GET /api/server/detail/<hs_name>
```

获取指定主机的详细信息。

### 添加主机

```
POST /api/server/create
```

添加新主机。

**请求体：**
```json
{
  "server_name": "host1",
  "server_addr": "192.168.1.100",
  "server_user": "admin",
  "server_pass": "password",
  "engine_type": "VMWareSetup",
  "system_path": "D:/VMs",
  "images_path": "D:/Images",
  "launch_path": "C:/Program Files (x86)/VMware/VMware Workstation"
}
```

### 修改主机

```
PUT /api/server/update/<hs_name>
```

修改主机配置。

### 删除主机

```
DELETE /api/server/delete/<hs_name>
```

删除指定主机。

### 主机电源控制

```
POST /api/server/powers/<hs_name>
```

启用或禁用主机。

**请求体：**
```json
{
  "action": "enable"
}
```

可选值：`enable`, `disable`

### 主机状态

```
GET /api/server/status/<hs_name>
```

获取主机当前状态（CPU、内存、磁盘使用情况）。

## 虚拟机管理

### 虚拟机列表

```
GET /api/client/detail/<hs_name>
```

获取指定主机下的所有虚拟机。

### 虚拟机详情

```
GET /api/client/detail/<hs_name>/<vm_uuid>
```

获取指定虚拟机的详细信息。

### 创建虚拟机

```
POST /api/client/create/<hs_name>
```

在指定主机上创建虚拟机。

**请求体：**
```json
{
  "vm_uuid": "vm-001",
  "vm_name": "测试虚拟机",
  "os_name": "Windows 10 x64",
  "cpu_num": 2,
  "ram_num": 4096,
  "hdd_num": 50,
  "nic_all": {
    "eth0": {
      "net_mode": "nat",
      "ip4_addr": "192.168.1.100",
      "mac_addr": "00:50:56:00:00:01"
    }
  }
}
```

### 修改虚拟机

```
PUT /api/client/update/<hs_name>/<vm_uuid>
```

修改虚拟机配置。

### 删除虚拟机

```
DELETE /api/client/delete/<hs_name>/<vm_uuid>
```

删除指定虚拟机。

### 虚拟机电源控制

```
POST /api/client/powers/<hs_name>/<vm_uuid>
```

控制虚拟机电源状态。

**请求体：**
```json
{
  "action": "start"
}
```

可选值：
- `start`: 启动
- `stop`: 停止
- `suspend`: 挂起
- `reset`: 重启
- `shutdown`: 关机

### VNC控制台

```
GET /api/client/remote/<hs_name>/<vm_uuid>
```

获取虚拟机VNC控制台访问URL。

### 修改密码

```
POST /api/client/password/<hs_name>/<vm_uuid>
```

修改虚拟机操作系统密码。

**请求体：**
```json
{
  "password": "new-password"
}
```

### 虚拟机状态

```
GET /api/client/status/<hs_name>/<vm_uuid>
```

获取虚拟机当前状态。

### 扫描虚拟机

```
POST /api/client/scaner/<hs_name>
```

扫描主机上的所有虚拟机并同步到系统。

### 上报状态

```
POST /api/client/upload
```

虚拟机上报状态数据（无需认证）。

**请求体：**
```json
{
  "vm_uuid": "vm-001",
  "cpu_usage": 45.2,
  "mem_usage": 2048,
  "disk_usage": 30.5
}
```

## 网络配置

### NAT端口转发

#### 获取NAT规则

```
GET /api/client/natget/<hs_name>/<vm_uuid>
```

获取虚拟机的NAT端口转发规则列表。

#### 添加NAT规则

```
POST /api/client/natadd/<hs_name>/<vm_uuid>
```

添加NAT端口转发规则。

**请求体：**
```json
{
  "protocol": "tcp",
  "external_port": 8080,
  "internal_port": 80,
  "internal_ip": "192.168.1.100"
}
```

#### 删除NAT规则

```
DELETE /api/client/natdel/<hs_name>/<vm_uuid>/<rule_index>
```

删除指定的NAT规则。

### IP地址管理

#### 获取IP列表

```
GET /api/client/ipaddr/detail/<hs_name>/<vm_uuid>
```

获取虚拟机的IP地址列表。

#### 添加IP地址

```
POST /api/client/ipaddr/create/<hs_name>/<vm_uuid>
```

为虚拟机添加IP地址。

**请求体：**
```json
{
  "interface": "eth0",
  "ip_address": "192.168.1.101",
  "netmask": "255.255.255.0",
  "gateway": "192.168.1.1"
}
```

#### 删除IP地址

```
DELETE /api/client/ipaddr/delete/<hs_name>/<vm_uuid>/<ip_index>
```

删除指定的IP地址。

### 反向代理

#### 获取代理配置

```
GET /api/client/proxys/detail/<hs_name>/<vm_uuid>
```

获取虚拟机的反向代理配置列表。

#### 添加代理配置

```
POST /api/client/proxys/create/<hs_name>/<vm_uuid>
```

添加反向代理配置。

**请求体：**
```json
{
  "domain": "example.com",
  "target_port": 80,
  "ssl_enabled": false
}
```

#### 删除代理配置

```
DELETE /api/client/proxys/delete/<hs_name>/<vm_uuid>/<proxy_index>
```

删除指定的反向代理配置。

## 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 使用示例

### Python

```python
import requests

# 设置Token
headers = {
    'Authorization': 'Bearer your-token-here'
}

# 获取主机列表
response = requests.get('http://localhost:1880/api/server/detail', headers=headers)
hosts = response.json()

# 创建虚拟机
vm_config = {
    'vm_uuid': 'vm-001',
    'vm_name': '测试虚拟机',
    'cpu_num': 2,
    'ram_num': 4096,
    'hdd_num': 50
}
response = requests.post(
    'http://localhost:1880/api/client/create/host1',
    json=vm_config,
    headers=headers
)
```

### cURL

```bash
# 获取主机列表
curl -H "Authorization: Bearer your-token-here" \
  http://localhost:1880/api/server/detail

# 启动虚拟机
curl -X POST \
  -H "Authorization: Bearer your-token-here" \
  -H "Content-Type: application/json" \
  -d '{"action":"start"}' \
  http://localhost:1880/api/client/powers/host1/vm-001
```
