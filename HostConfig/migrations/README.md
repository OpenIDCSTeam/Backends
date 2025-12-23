# 数据库迁移说明

## 概述

本目录包含数据库迁移脚本和工具，用于管理数据库结构的变更。

## 目录结构

```
HostConfig/
├── HostManage.sql          # 完整的数据库表结构定义
├── HostManage.db           # SQLite数据库文件
├── migrate.py              # 数据库迁移工具
└── migrations/             # 迁移脚本目录
    └── 001_add_images_maps.sql  # 添加images_maps字段的迁移
```

## 迁移文件命名规范

迁移文件应遵循以下命名规范：

```
<序号>_<描述>.sql
```

例如：
- `001_add_images_maps.sql` - 添加images_maps字段
- `002_add_index_on_vm_uuid.sql` - 添加vm_uuid索引
- `003_modify_column_type.sql` - 修改列类型

## 使用方法

### 1. 执行迁移

在项目根目录下运行：

```bash
# Python版本
python HostConfig/migrate.py

# 或者直接运行
python -m HostConfig.migrate
```

### 2. 查看迁移状态

迁移工具会自动创建 `schema_migrations` 表来跟踪已应用的迁移：

```sql
SELECT * FROM schema_migrations ORDER BY applied_at;
```

### 3. 手动执行迁移（不推荐）

如果需要手动执行迁移，可以使用SQLite命令行：

```bash
sqlite3 HostConfig/HostManage.db < HostConfig/migrations/001_add_images_maps.sql
```

## 当前迁移列表

### 001_add_images_maps.sql

**日期**: 2025-12-23  
**描述**: 为 `hs_config` 表添加 `images_maps` 字段

**变更内容**:
- 添加 `images_maps TEXT DEFAULT '{}'` 字段
- 用于存储ISO镜像映射关系：`{"显示名称": "文件名.iso"}`

**示例数据**:
```json
{
  "Ubuntu 22.04 Server": "ubuntu-22.04-server.iso",
  "Windows 10 Pro": "windows10-pro.iso",
  "CentOS 7": "centos7-minimal.iso"
}
```

## 创建新迁移

### 步骤

1. 在 `migrations/` 目录下创建新的SQL文件
2. 使用递增的序号命名（如 `002_xxx.sql`）
3. 编写SQL语句
4. 运行迁移工具测试

### 迁移模板

```sql
-- ============================================
-- 数据库迁移脚本: <描述>
-- ============================================
-- 版本: <序号>
-- 日期: <YYYY-MM-DD>
-- 描述: <详细描述>
-- ============================================

-- 你的SQL语句
ALTER TABLE table_name ADD COLUMN column_name TYPE DEFAULT value;

-- 验证
SELECT '<迁移名称> completed successfully' AS status;
```

## 注意事项

1. **备份数据库**: 在执行迁移前，建议备份数据库文件
2. **测试环境**: 先在测试环境验证迁移脚本
3. **幂等性**: 迁移脚本应该是幂等的（可重复执行）
4. **向后兼容**: 尽量保持向后兼容，避免删除字段
5. **事务处理**: 迁移工具会自动处理事务

## 回滚

目前不支持自动回滚。如需回滚：

1. 恢复数据库备份
2. 或手动编写回滚SQL并执行

## 故障排除

### 问题：字段已存在错误

**错误信息**: `duplicate column name: images_maps`

**解决方案**: 这是正常的，迁移工具会自动跳过已存在的字段。

### 问题：迁移工具找不到数据库

**错误信息**: `数据库文件不存在`

**解决方案**: 确保在项目根目录下运行迁移工具，或检查数据库路径配置。

### 问题：权限错误

**错误信息**: `Permission denied`

**解决方案**: 确保对数据库文件和目录有读写权限。

## 相关文件

- `MainObject/Config/HSConfig.py` - HSConfig类定义（包含images_maps字段）
- `GoVersions/internal/database/database.go` - Go版本的数据库初始化
- `HostModule/DataManage.py` - 数据库管理模块

## 更新日志

### 2025-12-23
- 创建迁移工具和目录结构
- 添加 001_add_images_maps.sql 迁移脚本
- 更新 HostManage.sql 主表结构
- 更新 Go 版本数据库初始化代码
