# OpenIDCS API 接口文档（完整版）

## 接口总览

本系统共有 **35个API接口**，分为三大类：
- **系统管理API** (9个): `/api/system/<option>`
- **主机管理API** (7个): `/api/server/<option>/<key?>`
- **虚拟机管理API** (19个): `/api/client/<option>/<key?>`

---

## 1. 系统管理API (System Management)

| 序号 | 接口路径 | 方法 | Option | 功能描述 | 认证 |
|------|---------|------|--------|---------|------|
| 1 | `/api/system/treset` | POST | treset | 重置访问Token | ✅ |
| 2 | `/api/system/tsetup` | POST | tsetup | 设置指定Token | ✅ |
| 3 | `/api/system/tquery` | GET | tquery | 获取当前Token | ✅ |
| 4 | `/api/system/saving` | POST | saving | 保存系统配置 | ✅ |
| 5 | `/api/system/loader` | POST | loader | 加载系统配置 | ✅ |
| 6 | `/api/system/statis` | GET | statis | 获取系统统计信息 | ✅ |
| 7 | `/api/system/engine` | GET | engine | 获取支持的引擎类型 | ✅ |
| 8 | `/api/system/logget` | GET | logget | 获取日志记录 | ✅ |
| 9 | `/api/system/tasget` | GET | tasget | 获取任务记录 | ✅ |

---

## 2. 主机管理API (Server Management)

| 序号 | 接口路径 | 方法 | Option | 功能描述 | 认证 |
|------|---------|------|--------|---------|------|
| 10 | `/api/server/listup` | GET | listup | 获取所有主机列表 | ✅ |
| 11 | `/api/server/detail/<hs_name>` | GET | detail | 获取单个主机详情 | ✅ |
| 12 | `/api/server/create` | POST | create | 添加主机 | ✅ |
| 13 | `/api/server/update/<hs_name>` | PUT | update | 修改主机配置 | ✅ |
| 14 | `/api/server/delete/<hs_name>` | DELETE | delete | 删除主机 | ✅ |
| 15 | `/api/server/powers/<hs_name>` | POST | powers | 主机电源控制 | ✅ |
| 16 | `/api/server/status/<hs_name>` | GET | status | 获取主机状态 | ✅ |

---

## 3. 虚拟机管理API (Client/VM Management)

### 3.1 基础管理 (6个)

| 序号 | 接口路径 | 方法 | Option | 功能描述 | 认证 |
|------|---------|------|--------|---------|------|
| 17 | `/api/client/listup/<hs_name>` | GET | listup | 获取主机下所有虚拟机 | ✅ |
| 18 | `/api/client/detail/<hs_name>/<vm_uuid>` | GET | detail | 获取单个虚拟机详情 | ✅ |
| 19 | `/api/client/create/<hs_name>` | POST | create | 创建虚拟机 | ✅ |
| 20 | `/api/client/update/<hs_name>/<vm_uuid>` | PUT | update | 修改虚拟机配置 | ✅ |
| 21 | `/api/client/delete/<hs_name>/<vm_uuid>` | DELETE | delete | 删除虚拟机 | ✅ |
| 22 | `/api/client/powers/<hs_name>/<vm_uuid>` | POST | powers | 虚拟机电源控制 | ✅ |

### 3.2 状态与控制 (4个)

| 序号 | 接口路径 | 方法 | Option | 功能描述 | 认证 |
|------|---------|------|--------|---------|------|
| 23 | `/api/client/status/<hs_name>/<vm_uuid>` | GET | status | 获取虚拟机状态 | ✅ |
| 24 | `/api/client/vncons/<hs_name>/<vm_uuid>` | GET | vncons | 获取VNC控制台URL | ✅ |
| 25 | `/api/client/scaner/<hs_name>` | POST | scaner | 扫描主机上的虚拟机 | ✅ |
| 26 | `/api/client/upload` | POST | upload | 虚拟机上报状态数据 | ❌ |

### 3.3 NAT端口转发 (3个)

| 序号 | 接口路径 | 方法 | Option | 功能描述 | 认证 |
|------|---------|------|--------|---------|------|
| 27 | `/api/client/natget/<hs_name>/<vm_uuid>` | GET | natget | 获取NAT端口转发规则 | ✅ |
| 28 | `/api/client/natadd/<hs_name>/<vm_uuid>` | POST | natadd | 添加NAT端口转发规则 | ✅ |
| 29 | `/api/client/natdel/<hs_name>/<vm_uuid>/<rule_index>` | DELETE | natdel | 删除NAT端口转发规则 | ✅ |

### 3.4 IP地址管理 (3个)

| 序号 | 接口路径 | 方法 | Option | 功能描述 | 认证 |
|------|---------|------|--------|---------|------|
| 30 | `/api/client/iplist/<hs_name>/<vm_uuid>` | GET | iplist | 获取虚拟机IP地址列表 | ✅ |
| 31 | `/api/client/ipadd_/<hs_name>/<vm_uuid>` | POST | ipadd_ | 添加虚拟机IP地址 | ✅ |
| 32 | `/api/client/ipdel_/<hs_name>/<vm_uuid>/<ip_index>` | DELETE | ipdel_ | 删除虚拟机IP地址 | ✅ |

### 3.5 反向代理配置 (3个)

| 序号 | 接口路径 | 方法 | Option | 功能描述 | 认证 |
|------|---------|------|--------|---------|------|
| 33 | `/api/client/pxyget/<hs_name>/<vm_uuid>` | GET | pxyget | 获取反向代理配置列表 | ✅ |
| 34 | `/api/client/pxyadd/<hs_name>/<vm_uuid>` | POST | pxyadd | 添加反向代理配置 | ✅ |
| 35 | `/api/client/pxydel/<hs_name>/<vm_uuid>/<proxy_index>` | DELETE | pxydel | 删除反向代理配置 | ✅ |

---

## APIfox 导入格式（简化版）

```
系统管理
POST   /api/system/treset    重置Token
POST   /api/system/tsetup    设置Token
GET    /api/system/tquery    获取Token
POST   /api/system/saving    保存配置
POST   /api/system/loader    加载配置
GET    /api/system/statis    系统统计
GET    /api/system/engine    引擎类型
GET    /api/system/logget    获取日志
GET    /api/system/tasget    获取任务

主机管理
GET    /api/server/listup              主机列表
GET    /api/server/detail/:hs_name     主机详情
POST   /api/server/create              添加主机
PUT    /api/server/update/:hs_name     修改主机
DELETE /api/server/delete/:hs_name     删除主机
POST   /api/server/powers/:hs_name     电源控制
GET    /api/server/status/:hs_name     主机状态

虚拟机管理
GET    /api/client/listup/:hs_name                    虚拟机列表
GET    /api/client/detail/:hs_name/:vm_uuid           虚拟机详情
POST   /api/client/create/:hs_name                    创建虚拟机
PUT    /api/client/update/:hs_name/:vm_uuid           修改虚拟机
DELETE /api/client/delete/:hs_name/:vm_uuid           删除虚拟机
POST   /api/client/powers/:hs_name/:vm_uuid           电源控制
GET    /api/client/status/:hs_name/:vm_uuid           虚拟机状态
GET    /api/client/vncons/:hs_name/:vm_uuid           VNC控制台
POST   /api/client/scaner/:hs_name                    扫描虚拟机
POST   /api/client/upload                             上报状态

虚拟机网络配置
GET    /api/client/natget/:hs_name/:vm_uuid                  获取NAT规则
POST   /api/client/natadd/:hs_name/:vm_uuid                  添加NAT规则
DELETE /api/client/natdel/:hs_name/:vm_uuid/:rule_index     删除NAT规则
GET    /api/client/iplist/:hs_name/:vm_uuid                  IP列表
POST   /api/client/ipadd_/:hs_name/:vm_uuid                  添加IP
DELETE /api/client/ipdel_/:hs_name/:vm_uuid/:ip_index       删除IP
GET    /api/client/pxyget/:hs_name/:vm_uuid                  获取代理配置
POST   /api/client/pxyadd/:hs_name/:vm_uuid                  添加代理配置
DELETE /api/client/pxydel/:hs_name/:vm_uuid/:proxy_index    删除代理配置
```

---

## Option 命名规范

所有 `option` 均为 **6字符** 单词：

| Option | 含义 | 使用场景 |
|--------|------|---------|
| treset | Token Reset | Token重置 |
| tsetup | Token Setup | Token设置 |
| tquery | Token Query | Token查询 |
| saving | Save | 保存配置 |
| loader | Load | 加载配置 |
| statis | Statistics | 统计信息 |
| engine | Engine | 引擎类型 |
| logget | Log Get | 获取日志 |
| tasget | Task Get | 获取任务 |
| listup | List Up | 列表查询 |
| detail | Detail | 详情查询 |
| create | Create | 创建资源 |
| update | Update | 更新资源 |
| delete | Delete | 删除资源 |
| powers | Power | 电源控制 |
| status | Status | 状态查询 |
| vncons | VNC Console | VNC控制台 |
| scaner | Scanner | 扫描资源 |
| upload | Upload | 上报数据 |
| natget | NAT Get | 获取NAT |
| natadd | NAT Add | 添加NAT |
| natdel | NAT Delete | 删除NAT |
| iplist | IP List | IP列表 |
| ipadd_ | IP Add | 添加IP |
| ipdel_ | IP Delete | 删除IP |
| pxyget | Proxy Get | 获取代理 |
| pxyadd | Proxy Add | 添加代理 |
| pxydel | Proxy Delete | 删除代理 |

---

## 认证说明

- ✅ 需要认证：需要在请求头中携带 `Authorization: Bearer <token>`
- ❌ 无需认证：公开接口，无需携带Token

---

## 响应格式

所有API统一返回格式：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

- `code`: 状态码（200成功，400客户端错误，404未找到，500服务器错误）
- `msg`: 消息描述
- `data`: 返回数据（可为对象、数组或null）

---

**生成时间**: 2025-12-08  
**版本**: v1.0  
**总接口数**: 35个
