# OpenIDCS-Client API 文档

<div align="center">

完整的 REST API 参考文档

[基础信息](#基础信息) • [认证授权](#认证授权) • [系统管理](#系统管理) • [主机管理](#主机管理) • [虚拟机管理](#虚拟机管理) • [错误码](#错误码)

</div>

## 📖 基础信息

### 服务器地址

```
http://localhost:1880
```

### 认证方式

本 API 使用 Token 认证。在请求头中携带 Token：

```
Authorization: Bearer <token>
```

### 响应格式

所有 API 响应均采用 JSON 格式：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

### 状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token 无效或过期） |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 🔐 认证授权

### 登录

```http
POST /login
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**响应示例**：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user_id": 1,
    "username": "admin",
    "is_admin": true
  }
}
```

### 登出

```http
POST /logout
```

### 获取当前用户信息

```http
GET /api/users/current
```

**响应示例**：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "is_admin": true,
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

---

## ⚙️ 系统管理

### 获取系统状态

```http
GET /api/system/stats
```

**响应示例**：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "hosts_count": 5,
    "vms_count": 42,
    "users_count": 10,
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "disk_usage": 52.3
  }
}
```

### 获取系统日志

```http
GET /api/system/logger/detail
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | integer | 否 | 返回条数，默认 100 |

### 获取系统设置

```http
GET /api/system/settings
```

### 更新系统设置

```http
POST /api/system/settings
```

### 获取支持的引擎类型

```http
GET /api/system/engine
```

**响应示例**：

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    "VmwareWork",
    "vSphereESXi",
    "Containers",
    "LXD",
    "OCInterface"
  ]
}
```

### Token 管理

#### 获取当前 Token

```http
GET /api/token/current
```

#### 设置 Token

```http
POST /api/token/set
```

#### 重置 Token

```http
POST /api/token/reset
```

---

## 🖥️ 主机管理

### 获取主机列表

```http
GET /api/server/detail
```

**响应示例**：

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "server_name": "esxi-host-01",
      "server_type": "vSphereESXi",
      "server_addr": "192.168.1.100",
      "status": "online",
      "vms_count": 10,
      "cpu_usage": 45.2,
      "memory_usage": 67.8
    }
  ]
}
```

### 获取单个主机详情

```http
GET /api/server/detail/<hs_name>
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| hs_name | string | 主机名称 |

### 创建主机

```http
POST /api/server/create
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| server_name | string | 是 | 主机名称 |
| server_type | string | 是 | 主机类型（VmwareWork/vSphereESXi等） |
| server_addr | string | 是 | 主机地址 |
| server_user | string | 是 | 用户名 |
| server_pass | string | 是 | 密码 |

### 更新主机

```http
PUT /api/server/update/<hs_name>
```

### 删除主机

```http
DELETE /api/server/delete/<hs_name>
```

### 主机电源管理

```http
POST /api/server/powers/<hs_name>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 操作类型（start/stop/restart） |

### 获取主机状态

```http
GET /api/server/status/<hs_name>
```

### 扫描主机虚拟机

```http
POST /api/server/backup/scan/<hs_name>
```

---

## 📦 虚拟机管理

### 获取虚拟机列表

```http
GET /api/client/detail/<hs_name>
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| hs_name | string | 主机名称 |

**响应示例**：

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "vm_uuid": "vm-001",
      "vm_name": "Ubuntu Server",
      "os_name": "ubuntu-22.04",
      "cpu_num": 2,
      "ram_num": 4096,
      "hdd_num": 50,
      "status": "running",
      "power_state": "powered_on"
    }
  ]
}
```

### 获取虚拟机详情

```http
GET /api/client/detail/<hs_name>/<vm_uuid>
```

### 创建虚拟机

```http
POST /api/client/create/<hs_name>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| vm_uuid | string | 是 | 虚拟机 UUID |
| os_name | string | 是 | 操作系统名称 |
| cpu_num | integer | 是 | CPU 核心数 |
| ram_num | integer | 是 | 内存大小（MB） |
| hdd_num | integer | 是 | 磁盘大小（GB） |

### 更新虚拟机

```http
PUT /api/client/update/<hs_name>/<vm_uuid>
```

### 删除虚拟机

```http
DELETE /api/client/delete/<hs_name>/<vm_uuid>
```

### 虚拟机电源管理

```http
POST /api/client/powers/<hs_name>/<vm_uuid>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 操作类型（S_START/H_CLOSE/S_RESET/S_PAUSE） |

**操作类型说明**：

| 操作 | 说明 |
|------|------|
| S_START | 启动虚拟机 |
| H_CLOSE | 关闭虚拟机 |
| S_RESET | 重启虚拟机 |
| S_PAUSE | 挂起虚拟机 |

### 获取虚拟机状态

```http
GET /api/client/status/<hs_name>/<vm_uuid>
```

### 获取控制台访问地址

```http
GET /api/client/remote/<hs_name>/<vm_uuid>
```

**响应示例**：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "console_url": "http://192.168.1.100:6080/vnc_auto.html?token=xxx",
    "terminal_url": "http://192.168.1.100:7681/?arg=xxx&token=yyy"
  }
}
```

### 设置虚拟机密码

```http
POST /api/client/password/<hs_name>/<vm_uuid>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| password | string | 是 | 新密码 |

### 扫描虚拟机

```http
POST /api/client/scaner/<hs_name>
```

---

## 🌐 网络管理

### 获取虚拟机 IP 地址

```http
GET /api/client/ipaddr/detail/<hs_name>/<vm_uuid>
```

### 添加 IP 地址

```http
POST /api/client/ipaddr/create/<hs_name>/<vm_uuid>
```

### 删除 IP 地址

```http
DELETE /api/client/ipaddr/delete/<hs_name>/<vm_uuid>/<ip_index>
```

### 获取 NAT 规则

```http
GET /api/client/natget/<hs_name>/<vm_uuid>
```

### 添加 NAT 规则

```http
POST /api/client/natadd/<hs_name>/<vm_uuid>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| host_port | integer | 是 | 主机端口 |
| vm_port | integer | 是 | 虚拟机端口 |
| protocol | string | 是 | 协议（tcp/udp） |

### 删除 NAT 规则

```http
DELETE /api/client/natdel/<hs_name>/<vm_uuid>/<rule_index>
```

### 获取反向代理配置

```http
GET /api/client/proxys/detail/<hs_name>/<vm_uuid>
```

### 添加反向代理

```http
POST /api/client/proxys/create/<hs_name>/<vm_uuid>
```

### 删除反向代理

```http
DELETE /api/client/proxys/delete/<hs_name>/<vm_uuid>/<proxy_index>
```

---

## 💾 存储管理

### 挂载磁盘

```http
POST /api/client/hdd/mount/<hs_name>/<vm_uuid>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hdd_name | string | 是 | 磁盘名称 |
| hdd_size | integer | 是 | 磁盘大小（GB） |

### 卸载磁盘

```http
POST /api/client/hdd/unmount/<hs_name>/<vm_uuid>
```

### 删除磁盘

```http
DELETE /api/client/hdd/delete/<hs_name>/<vm_uuid>
```

### 挂载 ISO

```http
POST /api/client/iso/mount/<hs_name>/<vm_uuid>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| iso_name | string | 是 | ISO 文件名 |

### 卸载 ISO

```http
DELETE /api/client/iso/unmount/<hs_name>/<vm_uuid>/<iso_name>
```

---

## 🗄️ 备份管理

### 创建备份

```http
POST /api/client/backup/create/<hs_name>/<vm_uuid>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| description | string | 否 | 备份描述 |

### 恢复备份

```http
POST /api/client/backup/restore/<hs_name>/<vm_uuid>
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| backup_name | string | 是 | 备份文件名 |

### 删除备份

```http
DELETE /api/client/backup/delete/<hs_name>/<vm_uuid>
```

### 扫描备份

```http
POST /api/server/backup/scan/<hs_name>
```

---

## 👥 用户管理

### 获取用户列表

```http
GET /api/users
```

### 创建用户

```http
POST /api/users
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |
| email | string | 是 | 邮箱 |
| is_admin | boolean | 否 | 是否管理员 |

### 获取用户详情

```http
GET /api/users/<user_id>
```

### 更新用户

```http
PUT /api/users/<user_id>
```

### 删除用户

```http
DELETE /api/users/<user_id>
```

### 修改密码

```http
POST /api/users/change-password
```

### 修改邮箱

```http
POST /api/users/change-email
```

---

## 🔧 工具函数

### 获取 OS 镜像列表

```http
GET /api/client/os-images/<hs_name>
```

**响应示例**：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "ubuntu": [
      {
        "name": "Ubuntu 22.04 Server",
        "file": "ubuntu-22.04-server.iso"
      }
    ],
    "centos": [
      {
        "name": "CentOS 7",
        "file": "centos-7-minimal.iso"
      }
    ]
  }
}
```

### 重新计算配额

```http
POST /api/system/recalculate-quotas
```

---

## ❌ 错误码

### 通用错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权（Token 无效或过期） |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 业务错误码

| 错误码 | 说明 |
|--------|------|
| 1001 | 主机不存在 |
| 1002 | 虚拟机不存在 |
| 1003 | 主机连接失败 |
| 1004 | 虚拟机创建失败 |
| 1005 | 虚拟机操作失败 |
| 2001 | 用户名已存在 |
| 2002 | 用户不存在 |
| 2003 | 密码错误 |
| 3001 | Token 无效 |
| 3002 | Token 过期 |

---

## 📚 附录

### 主机类型列表

| 类型 | 说明 |
|------|------|
| `VmwareWork` | VMware Workstation |
| `vSphereESXi` | VMware ESXi |
| `Containers` | LXC 容器 |
| `LXD` | LXD 容器 |
| `OCInterface` | Docker/Podman 容器 |

### 虚拟机状态列表

| 状态 | 说明 |
|------|------|
| `running` | 运行中 |
| `stopped` | 已停止 |
| `paused` | 已暂停 |
| `creating` | 创建中 |
| `deleting` | 删除中 |

### 电源操作列表

| 操作 | 说明 |
|------|------|
| `S_START` | 启动 |
| `H_CLOSE` | 关闭 |
| `S_RESET` | 重启 |
| `S_PAUSE` | 挂起 |

---

## 📝 更新日志

### v1.0.0 (2025-01-26)

- 初始版本
- 包含所有核心 API 接口

---

<div align="center">

如有问题或建议，请提交 Issue

</div>
