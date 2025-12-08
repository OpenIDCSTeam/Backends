# OpenIDCS API 接口文档

## API 规范说明

所有API接口遵循以下格式：
- `/api/system/<option>/<key?>` - 系统级接口
- `/api/server/<option>/<key?>` - 主机级接口  
- `/api/client/<option>/<key?>` - 虚拟机级接口

其中 `option` 和 `key` 均为6字符单词（如：create、delete、reload、unload、powers、status、update等）

## 响应格式

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

---

## 1. 系统管理API (`/api/system`)

| 接口路径 | 方法 | Option | 说明 | 请求参数 | 响应数据 |
|---------|------|--------|------|---------|---------|
| `/api/system/treset` | POST | treset | 重置访问Token | 无 | `{token: string}` |
| `/api/system/tsetup` | POST | tsetup | 设置指定Token | `{token: string}` | `{token: string}` |
| `/api/system/tquery` | GET | tquery | 获取当前Token | 无 | `{token: string}` |
| `/api/system/saving` | POST | saving | 保存系统配置 | 无 | 无 |
| `/api/system/loader` | POST | loader | 加载系统配置 | 无 | 无 |
| `/api/system/statis` | GET | statis | 获取系统统计信息 | 无 | `{host_count, vm_count, running_vm_count}` |
| `/api/system/engine` | GET | engine | 获取支持的引擎类型 | 无 | `{[engine_type]: {...}}` |

---

## 2. 主机管理API (`/api/server`)

| 接口路径 | 方法 | Option | 说明 | 请求参数 | 响应数据 |
|---------|------|--------|------|---------|---------|
| `/api/server/listup` | GET | listup | 获取所有主机列表 | 无 | `{[hs_name]: {...}}` |
| `/api/server/detail/<hs_name>` | GET | detail | 获取主机详情 | `?status=true` (可选) | `{name, type, config, status...}` |
| `/api/server/create` | POST | create | 添加主机 | `{name, type, config}` | 无 |
| `/api/server/update/<hs_name>` | PUT | update | 修改主机配置 | `{config}` | 无 |
| `/api/server/delete/<hs_name>` | DELETE | delete | 删除主机 | 无 | 无 |
| `/api/server/powers/<hs_name>` | POST | powers | 主机电源控制 | `{enable: bool}` | 无 |
| `/api/server/status/<hs_name>` | GET | status | 获取主机状态 | `?refresh=true` (可选) | `{status, source, cached_at...}` |

---

## 3. 虚拟机管理API (`/api/client`)

| 接口路径 | 方法 | Option | 说明 | 请求参数 | 响应数据 |
|---------|------|--------|------|---------|---------|
| `/api/client/listup/<hs_name>` | GET | listup | 获取主机下所有虚拟机 | 无 | `{[vm_uuid]: {...}}` |
| `/api/client/detail/<hs_name>/<vm_uuid>` | GET | detail | 获取虚拟机详情 | 无 | `{uuid, config, status}` |
| `/api/client/create/<hs_name>` | POST | create | 创建虚拟机 | `{vm_uuid, os_name, cpu_num...}` | 无 |
| `/api/client/update/<hs_name>/<vm_uuid>` | PUT | update | 修改虚拟机配置 | `{config}` | 无 |
| `/api/client/delete/<hs_name>/<vm_uuid>` | DELETE | delete | 删除虚拟机 | 无 | 无 |
| `/api/client/powers/<hs_name>/<vm_uuid>` | POST | powers | 虚拟机电源控制 | `{action: start/stop/reset...}` | 无 |
| `/api/client/status/<hs_name>/<vm_uuid>` | GET | status | 获取虚拟机状态 | 无 | `[{...}]` |
| `/api/client/scaner/<hs_name>` | POST | scaner | 扫描主机上的虚拟机 | `{prefix: string}` (可选) | `{scanned, added}` |
| `/api/client/upload` | POST | upload | 虚拟机上报状态 | `?nic=<mac_addr>` | 无 |
| `/api/client/vncons/<hs_name>/<vm_uuid>` | GET | vncons | 获取VNC控制台地址 | 无 | `string` |

---

## 4. 虚拟机网络配置API (`/api/client`)

| 接口路径 | 方法 | Option | 说明 | 请求参数 | 响应数据 |
|---------|------|--------|------|---------|---------|
| `/api/client/natget/<hs_name>/<vm_uuid>` | GET | natget | 获取NAT端口转发规则 | 无 | `[{protocol, external_port...}]` |
| `/api/client/natadd/<hs_name>/<vm_uuid>` | POST | natadd | 添加NAT端口转发规则 | `{protocol, external_port...}` | 无 |
| `/api/client/natdel/<hs_name>/<vm_uuid>/<rule_index>` | DELETE | natdel | 删除NAT端口转发规则 | 无 | 无 |
| `/api/client/iplist/<hs_name>/<vm_uuid>` | GET | iplist | 获取IP地址列表 | 无 | `[{type, address...}]` |
| `/api/client/ipadd_/<hs_name>/<vm_uuid>` | POST | ipadd_ | 添加IP地址 | `{type, address...}` | 无 |
| `/api/client/ipdel_/<hs_name>/<vm_uuid>/<ip_index>` | DELETE | ipdel_ | 删除IP地址 | 无 | 无 |

---

## 5. 虚拟机代理配置API (`/api/client`)

| 接口路径 | 方法 | Option | 说明 | 请求参数 | 响应数据 |
|---------|------|--------|------|---------|---------|
| `/api/client/pxyget/<hs_name>/<vm_uuid>` | GET | pxyget | 获取反向代理配置 | 无 | `[{domain, backend_ip...}]` |
| `/api/client/pxyadd/<hs_name>/<vm_uuid>` | POST | pxyadd | 添加反向代理配置 | `{domain, backend_ip...}` | 无 |
| `/api/client/pxydel/<hs_name>/<vm_uuid>/<proxy_index>` | DELETE | pxydel | 删除反向代理配置 | 无 | 无 |

---

## 6. 日志和任务API (`/api/system`)

| 接口路径 | 方法 | Option | 说明 | 请求参数 | 响应数据 |
|---------|------|--------|------|---------|---------|
| `/api/system/logget` | GET | logget | 获取日志记录 | `?hs_name=<name>&limit=<num>` | `[{actions, message...}]` |
| `/api/system/tasget` | GET | tasget | 获取任务记录 | `?hs_name=<name>&limit=<num>` | `[{...}]` |

---

## 电源操作类型 (powers action)

- `start` - 启动虚拟机
- `stop` - 正常关闭虚拟机
- `hard_stop` - 强制关闭虚拟机
- `reset` - 重启虚拟机
- `hard_reset` - 强制重启虚拟机
- `pause` - 暂停虚拟机
- `resume` - 恢复虚拟机

---

## 认证方式

### 1. Bearer Token (推荐用于API调用)
```
Authorization: Bearer <token>
```

### 2. Session (用于Web界面)
登录后自动设置Session Cookie

---

## 错误码说明

| 错误码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 使用示例

### 1. 获取所有主机列表
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:1880/api/server/listup
```

### 2. 创建虚拟机
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_uuid":"test-vm","os_name":"windows10x64","cpu_num":4,"mem_num":4096}' \
  http://localhost:1880/api/client/create/host1
```

### 3. 控制虚拟机电源
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action":"start"}' \
  http://localhost:1880/api/client/powers/host1/test-vm
```

---

## 注意事项

1. 所有需要认证的接口都需要提供有效的Token或Session
2. 虚拟机上报状态接口 (`/api/client/upload`) 无需认证
3. 建议使用 `?status=true` 参数时注意缓存机制，避免频繁调用
4. 日志和任务查询支持分页，默认返回最近100条记录
