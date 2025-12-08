# OpenIDCS API 接口表格（APIfox导入用）

## 系统管理API

| 接口名称 | 方法 | 路径 | 说明 |
|---------|------|------|------|
| 重置Token | POST | /api/system/resets | 重置访问Token |
| 设置Token | POST | /api/system/create | 设置指定Token |
| 获取Token | GET | /api/system/tquery | 获取当前Token |
| 保存配置 | POST | /api/system/saving | 保存系统配置 |
| 加载配置 | POST | /api/system/loader | 加载系统配置 |
| 系统统计 | GET | /api/system/statis | 获取系统统计信息 |
| 引擎类型 | GET | /api/system/engine | 获取支持的引擎类型 |
| 获取日志 | GET | /api/system/logger/detail | 获取日志记录 |
| 获取任务 | GET | /api/system/tasker | 获取任务记录 |

## 主机管理API

| 接口名称 | 方法 | 路径 | 说明 |
|---------|------|------|------|
| 主机列表 | GET | /api/server/detail | 获取所有主机列表 |
| 主机详情 | GET | /api/server/detail/{hs_name} | 获取主机详情 |
| 添加主机 | POST | /api/server/create | 添加主机 |
| 修改主机 | PUT | /api/server/update/{hs_name} | 修改主机配置 |
| 删除主机 | DELETE | /api/server/delete/{hs_name} | 删除主机 |
| 电源控制 | POST | /api/server/powers/{hs_name} | 主机电源控制 |
| 主机状态 | GET | /api/server/status/{hs_name} | 获取主机状态 |

## 虚拟机管理API

| 接口名称 | 方法 | 路径 | 说明 |
|---------|------|------|------|
| 虚拟机列表 | GET | /api/client/detail/{hs_name} | 获取主机下所有虚拟机 |
| 虚拟机详情 | GET | /api/client/detail/{hs_name}/{vm_uuid} | 获取虚拟机详情 |
| 创建虚拟机 | POST | /api/client/create/{hs_name} | 创建虚拟机 |
| 修改虚拟机 | PUT | /api/client/update/{hs_name}/{vm_uuid} | 修改虚拟机配置 |
| 删除虚拟机 | DELETE | /api/client/delete/{hs_name}/{vm_uuid} | 删除虚拟机 |
| 电源控制 | POST | /api/client/powers/{hs_name}/{vm_uuid} | 虚拟机电源控制 |
| 虚拟机状态 | GET | /api/client/status/{hs_name}/{vm_uuid} | 获取虚拟机状态 |
| 扫描虚拟机 | POST | /api/client/scaner/{hs_name} | 扫描主机上的虚拟机 |
| 上报状态 | POST | /api/client/upload | 虚拟机上报状态 |
| VNC控制台 | GET | /api/client/remote/{hs_name}/{vm_uuid} | 获取VNC控制台地址 |

## 虚拟机网络配置API

| 接口名称 | 方法 | 路径 | 说明 |
|---------|------|------|------|
| 获取NAT规则 | GET | /api/client/natget/{hs_name}/{vm_uuid} | 获取NAT端口转发规则 |
| 添加NAT规则 | POST | /api/client/natadd/{hs_name}/{vm_uuid} | 添加NAT端口转发规则 |
| 删除NAT规则 | DELETE | /api/client/natdel/{hs_name}/{vm_uuid}/{rule_index} | 删除NAT端口转发规则 |
| 获取IP列表 | GET | /api/client/ipaddr/detail/{hs_name}/{vm_uuid} | 获取IP地址列表 |
| 添加IP地址 | POST | /api/client/ipaddr/create/{hs_name}/{vm_uuid} | 添加IP地址 |
| 删除IP地址 | DELETE | /api/client/ipaddr/delete/{hs_name}/{vm_uuid}/{ip_index} | 删除IP地址 |

## 虚拟机代理配置API

| 接口名称 | 方法 | 路径 | 说明 |
|---------|------|------|------|
| 获取代理配置 | GET | /api/client/proxys/detail/{hs_name}/{vm_uuid} | 获取反向代理配置 |
| 添加代理配置 | POST | /api/client/proxys/create/{hs_name}/{vm_uuid} | 添加反向代理配置 |
| 删除代理配置 | DELETE | /api/client/proxys/delete/{hs_name}/{vm_uuid}/{proxy_index} | 删除反向代理配置 |

---

## 认证方式

所有接口（除 `/api/client/upload` 外）都需要认证：

**Header:**
```
Authorization: Bearer <token>
```

---

## 响应格式

所有接口统一返回格式：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

**错误码：**
- 200: 成功
- 400: 请求参数错误
- 401: 未授权访问
- 404: 资源不存在
- 500: 服务器内部错误

---

## 常用请求参数

### 创建虚拟机
```json
{
  "vm_uuid": "test-vm",
  "os_name": "windows10x64",
  "cpu_num": 4,
  "mem_num": 4096,
  "hdd_num": 10240,
  "nic_all": {
    "ethernet0": {
      "ip4_addr": "192.168.1.100",
      "nic_type": "nat"
    }
  }
}
```

### 电源控制
```json
{
  "action": "start"
}
```

**action可选值：**
- start: 启动
- stop: 正常关闭
- hard_stop: 强制关闭
- reset: 重启
- hard_reset: 强制重启
- pause: 暂停
- resume: 恢复

### 添加NAT规则
```json
{
  "protocol": "tcp",
  "external_port": 8080,
  "internal_port": 80,
  "internal_ip": "192.168.1.100",
  "description": "Web服务"
}
```

### 添加IP地址
```json
{
  "type": "ipv4",
  "address": "192.168.1.100",
  "netmask": "255.255.255.0",
  "gateway": "192.168.1.1",
  "nic": "ethernet0",
  "description": "主IP"
}
```

### 添加代理配置
```json
{
  "domain": "example.com",
  "backend_ip": "192.168.1.100",
  "backend_port": 80,
  "ssl_enabled": true,
  "ssl_type": "letsencrypt",
  "description": "网站代理"
}
```

---

## 查询参数

### 获取主机详情
```
GET /api/server/detail/{hs_name}?status=true
```
- `status=true`: 获取详细状态信息（可选）

### 获取主机状态
```
GET /api/server/status/{hs_name}?refresh=true
```
- `refresh=true`: 强制刷新缓存（可选）

### 获取日志
```
GET /api/system/logget?hs_name=host1&limit=100
```
- `hs_name`: 主机名称（可选）
- `limit`: 返回数量，默认100（可选）

### 获取任务
```
GET /api/system/tasget?hs_name=host1&limit=100
```
- `hs_name`: 主机名称（可选）
- `limit`: 返回数量，默认100（可选）

### 虚拟机上报状态
```
POST /api/client/upload?nic=00:11:22:33:44:55
```
- `nic`: MAC地址（必需）

---

## 基础URL

```
http://localhost:1880
```

或

```
http://127.0.0.1:1880
```
