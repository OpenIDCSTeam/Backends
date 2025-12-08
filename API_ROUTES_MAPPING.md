# API 路由映射表

## 从旧路由到新路由的映射关系

### 系统管理API

| 旧路由 | 新路由 | 说明 |
|-------|--------|------|
| `/api/token/reset` | `/api/system/treset` | 重置Token |
| `/api/token/set` | `/api/system/tsetup` | 设置Token |
| `/api/token/current` | `/api/system/tquery` | 获取Token |
| `/api/system/save` | `/api/system/saving` | 保存配置 |
| `/api/system/load` | `/api/system/loader` | 加载配置 |
| `/api/system/stats` | `/api/system/statis` | 系统统计 |
| `/api/engine/types` | `/api/system/engine` | 引擎类型 |
| `/api/logs` | `/api/system/logget` | 获取日志 |
| `/api/tasks` | `/api/system/tasget` | 获取任务 |

### 主机管理API

| 旧路由 | 新路由 | 说明 |
|-------|--------|------|
| `GET /api/hosts` | `/api/server/listup` | 主机列表 |
| `GET /api/hosts/<hs_name>` | `/api/server/detail/<hs_name>` | 主机详情 |
| `POST /api/hosts` | `/api/server/create` | 添加主机 |
| `PUT /api/hosts/<hs_name>` | `/api/server/update/<hs_name>` | 修改主机 |
| `DELETE /api/hosts/<hs_name>` | `/api/server/delete/<hs_name>` | 删除主机 |
| `/api/hosts/<hs_name>/power` | `/api/server/powers/<hs_name>` | 电源控制 |
| `/api/hosts/<hs_name>/status` | `/api/server/status/<hs_name>` | 主机状态 |

### 虚拟机管理API

| 旧路由 | 新路由 | 说明 |
|-------|--------|------|
| `GET /api/hosts/<hs_name>/vms` | `/api/client/listup/<hs_name>` | 虚拟机列表 |
| `GET /api/hosts/<hs_name>/vms/<vm_uuid>` | `/api/client/detail/<hs_name>/<vm_uuid>` | 虚拟机详情 |
| `POST /api/hosts/<hs_name>/vms` | `/api/client/create/<hs_name>` | 创建虚拟机 |
| `PUT /api/hosts/<hs_name>/vms/<vm_uuid>` | `/api/client/update/<hs_name>/<vm_uuid>` | 修改虚拟机 |
| `DELETE /api/hosts/<hs_name>/vms/<vm_uuid>` | `/api/client/delete/<hs_name>/<vm_uuid>` | 删除虚拟机 |
| `/api/hosts/<hs_name>/vms/<vm_uuid>/power` | `/api/client/powers/<hs_name>/<vm_uuid>` | 电源控制 |
| `/api/hosts/<hs_name>/vms/<vm_uuid>/status` | `/api/client/status/<hs_name>/<vm_uuid>` | 虚拟机状态 |
| `/api/hosts/<hs_name>/vms/scan` | `/api/client/scaner/<hs_name>` | 扫描虚拟机 |
| `/api/vboxs/upload` | `/api/client/upload` | 上报状态 |
| `/api/hosts/<hs_name>/vms/<vm_uuid>/vconsole` | `/api/client/vncons/<hs_name>/<vm_uuid>` | VNC控制台 |

### 虚拟机网络配置API

| 旧路由 | 新路由 | 说明 |
|-------|--------|------|
| `GET /api/hosts/<hs_name>/vms/<vm_uuid>/nat` | `/api/client/natget/<hs_name>/<vm_uuid>` | 获取NAT规则 |
| `POST /api/hosts/<hs_name>/vms/<vm_uuid>/nat` | `/api/client/natadd/<hs_name>/<vm_uuid>` | 添加NAT规则 |
| `DELETE /api/hosts/<hs_name>/vms/<vm_uuid>/nat/<rule_index>` | `/api/client/natdel/<hs_name>/<vm_uuid>/<rule_index>` | 删除NAT规则 |
| `GET /api/hosts/<hs_name>/vms/<vm_uuid>/ip` | `/api/client/iplist/<hs_name>/<vm_uuid>` | 获取IP列表 |
| `POST /api/hosts/<hs_name>/vms/<vm_uuid>/ip` | `/api/client/ipadd_/<hs_name>/<vm_uuid>` | 添加IP地址 |
| `DELETE /api/hosts/<hs_name>/vms/<vm_uuid>/ip/<ip_index>` | `/api/client/ipdel_/<hs_name>/<vm_uuid>/<ip_index>` | 删除IP地址 |

### 虚拟机代理配置API

| 旧路由 | 新路由 | 说明 |
|-------|--------|------|
| `GET /api/hosts/<hs_name>/vms/<vm_uuid>/proxy` | `/api/client/pxyget/<hs_name>/<vm_uuid>` | 获取代理配置 |
| `POST /api/hosts/<hs_name>/vms/<vm_uuid>/proxy` | `/api/client/pxyadd/<hs_name>/<vm_uuid>` | 添加代理配置 |
| `DELETE /api/hosts/<hs_name>/vms/<vm_uuid>/proxy/<proxy_index>` | `/api/client/pxydel/<hs_name>/<vm_uuid>/<proxy_index>` | 删除代理配置 |

---

## 重构说明

1. **系统API** (`/api/system`) - 所有系统级操作，包括Token管理、配置管理、统计信息等
2. **主机API** (`/api/server`) - 所有主机级操作，包括主机的增删改查、电源控制等
3. **虚拟机API** (`/api/client`) - 所有虚拟机级操作，包括虚拟机的增删改查、电源控制、网络配置等

## Option命名规范

所有option都是6字符单词：
- `create` - 创建
- `delete` - 删除
- `update` - 更新
- `listup` - 列表
- `detail` - 详情
- `powers` - 电源
- `status` - 状态
- `loader` - 加载
- `saving` - 保存
- `scaner` - 扫描
- `upload` - 上传
- `treset` - Token重置
- `tsetup` - Token设置
- `tquery` - Token查询
- `statis` - 统计
- `engine` - 引擎
- `logget` - 日志获取
- `tasget` - 任务获取
- `natget` - NAT获取
- `natadd` - NAT添加
- `natdel` - NAT删除
- `iplist` - IP列表
- `ipadd_` - IP添加
- `ipdel_` - IP删除
- `pxyget` - 代理获取
- `pxyadd` - 代理添加
- `pxydel` - 代理删除
- `vncons` - VNC控制台

## 兼容性说明

建议保留旧路由一段时间，在响应中添加警告信息提示使用新路由。

示例：
```python
@app.route('/api/hosts', methods=['GET'])
@require_auth
def get_hosts_old():
    """旧接口，保留兼容性"""
    response = api_response(200, 'success (deprecated, use /api/server/listup)', data)
    response.headers['X-Deprecated'] = 'true'
    response.headers['X-New-Endpoint'] = '/api/server/listup'
    return response
```
