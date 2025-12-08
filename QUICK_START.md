# OpenIDCS 优化后快速开始指南

## 📦 安装依赖

```bash
# 安装所需的Python包
pip install -r requirements.txt
```

需要安装的包：
- `Flask==3.0.0` - Web框架
- `loguru==0.7.2` - 日志系统
- `requests==2.31.0` - HTTP请求库

---

## 🚀 启动服务

```bash
python HostServer.py
```

启动后会显示：
```
============================================================
OpenIDCS Server 启动中...
访问地址: http://127.0.0.1:1880
访问Token: <your_token>
============================================================
```

---

## 📝 新功能说明

### 1. Loguru 日志系统

**日志文件位置**：`./logs/{hs_name}.log`

**日志特性**：
- ✅ 自动轮转（10MB）
- ✅ 自动保留（7天）
- ✅ 自动压缩（zip）
- ✅ 每个主机独立日志文件

**日志格式**：
```
2024-12-08 12:00:00 | INFO | [host1] VMCreate: 虚拟机创建成功
2024-12-08 12:01:00 | ERROR | [host1] VMDelete: 虚拟机不存在
```

### 2. 自动保存机制

**自动保存**：
- 每5分钟自动保存一次
- 后台守护线程运行
- 不阻塞主程序

**立即保存**：
- 关键操作后立即保存
- 添加日志后立即保存
- 虚拟机配置修改后立即保存

### 3. 日志清理功能

**自动清理**：
- 默认保留7天的日志
- 可自定义保留天数
- 清理后自动保存

**手动清理**：

```python
# 清理7天前的日志
removed_count = server.LogClean(days=7)

# 清理30天前的日志
removed_count = server.LogClean(days=30)
```

### 4. 新API接口规范

**API分类**：
- `/api/system/<option>` - 系统管理
- `/api/server/<option>/<key?>` - 主机管理
- `/api/client/<option>/<key?>` - 虚拟机管理

**常用接口示例**：

```bash
# 获取系统统计
curl -H "Authorization: Bearer <token>" \
  http://localhost:1880/api/system/statis

# 获取主机列表
curl -H "Authorization: Bearer <token>" \
  http://localhost:1880/api/server/listup

# 获取虚拟机列表
curl -H "Authorization: Bearer <token>" \
  http://localhost:1880/api/client/listup/host1

# 创建虚拟机
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_uuid":"test-vm","os_name":"windows10x64","cpu_num":4,"mem_num":4096}' \
  http://localhost:1880/api/client/create/host1

# 启动虚拟机
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action":"start"}' \
  http://localhost:1880/api/client/powers/host1/test-vm
```

---

## 📚 文档说明

### 1. API_DOCUMENTATION.md
完整的API接口文档，包含：
- 所有接口的详细说明
- 请求参数和响应格式
- 使用示例
- 错误码说明

### 2. API_ROUTES_MAPPING.md
旧路由到新路由的映射表，方便：
- API迁移
- 兼容性处理
- 前端调用更新

### 3. OPTIMIZATION_SUMMARY.md
优化总结文档，包含：
- 所有优化内容
- 代码改动说明
- 后续工作建议
- 测试建议

---

## ⚠️ 注意事项

### 1. 日志目录
确保 `./logs/` 目录存在或程序有创建权限：
```bash
mkdir logs
```

### 2. 数据库文件
确保 `./DataSaving/` 目录存在：
```bash
mkdir DataSaving
```

### 3. Loguru 依赖
如果出现 `Unresolved reference 'loguru'` 错误，请安装：
```bash
pip install loguru
```

### 4. 定时任务
- 自动保存定时器使用守护线程
- 主程序退出时自动结束
- 不需要手动停止

---

## 🔧 配置建议

### 1. 修改自动保存间隔
在 `Template.py` 的 `_start_auto_save()` 方法中：

```python
# 修改为10分钟（600秒）
self.save_time = threading.Timer(600, auto_save_task)
```

### 2. 修改日志保留天数
在 `Template.py` 的 `_setup_logger()` 方法中：
```python
logger.add(
    log_file,
    retention="30 days",  # 修改为30天
    ...
)
```

### 3. 修改日志轮转大小
```python
logger.add(
    log_file,
    rotation="50 MB",  # 修改为50MB
    ...
)
```

---

## 🐛 故障排查

### 问题1：日志文件未生成
**原因**：日志目录不存在或无权限
**解决**：
```bash
mkdir logs
chmod 755 logs
```

### 问题2：自动保存失败
**原因**：数据库连接失败
**解决**：检查数据库配置和连接

### 问题3：API调用401错误
**原因**：Token未设置或错误
**解决**：
1. 查看启动日志获取Token
2. 在请求头中添加：`Authorization: Bearer <token>`

---

## 📊 监控建议

### 1. 查看日志
```bash
# 实时查看日志
tail -f logs/host1.log

# 查看错误日志
grep ERROR logs/host1.log

# 查看最近100行
tail -n 100 logs/host1.log
```

### 2. 检查自动保存
在日志中搜索：
```bash
grep "自动保存" logs/host1.log
```

### 3. 检查日志清理
在日志中搜索：
```bash
grep "清理了" logs/host1.log
```

---

## 🎯 下一步

1. **测试新功能**
   - 测试日志记录
   - 测试自动保存
   - 测试日志清理

2. **迁移API调用**
   - 参考 `API_ROUTES_MAPPING.md`
   - 更新前端调用
   - 测试新API接口

3. **完善定时任务**
   - 在 `HostManage.exe_cron()` 中添加日志清理
   - 添加其他定时任务

4. **性能优化**
   - 添加缓存层
   - 优化数据库查询
   - 添加异步任务队列

---

## 📞 技术支持

如有问题，请查看：
- `API_DOCUMENTATION.md` - API接口文档
- `OPTIMIZATION_SUMMARY.md` - 优化总结
- 日志文件：`./logs/{hs_name}.log`

---

**祝使用愉快！** 🎉
