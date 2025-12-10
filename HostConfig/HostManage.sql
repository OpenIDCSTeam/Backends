-- OpenIDCS Host Management Database Schema
-- SQLite数据库表结构定义

-- 全局配置表 (hs_global)
CREATE TABLE IF NOT EXISTS hs_global
(
    id   TEXT PRIMARY KEY,
    data TEXT NOT NULL
);


-- 主机配置表 (hs_config)
CREATE TABLE IF NOT EXISTS hs_config
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hs_name     TEXT NOT NULL UNIQUE,
    server_name TEXT      DEFAULT '',   -- 服务器的名称
    server_type TEXT NOT NULL,          -- 服务器的类型
    server_addr TEXT NOT NULL,          -- 服务器的地址
    server_user TEXT NOT NULL,          -- 服务器的用户
    server_pass TEXT NOT NULL,          -- 服务器的密码
    images_path TEXT,                   -- 虚拟机的镜像
    system_path TEXT,                   -- 虚拟机的系统
    backup_path TEXT,                   -- 虚拟机的备份
    extern_path TEXT,                   -- 虚拟机的数据
    launch_path TEXT,                   -- 虚拟机的路径
    network_nat TEXT,                   -- 内网IP设备名
    network_pub TEXT,                   -- 公网IP设备名
    filter_name TEXT      DEFAULT '',   -- 前缀过滤名称
    i_kuai_addr TEXT      DEFAULT '',   -- 爱快OS的地址
    i_kuai_user TEXT      DEFAULT '',   -- 爱快OS的用户
    i_kuai_pass TEXT      DEFAULT '',   -- 爱快OS的密码
    ports_start INTEGER   DEFAULT 0,    -- TCP-端口起始
    ports_close INTEGER   DEFAULT 0,    -- TCP-端口结束
    remote_port INTEGER   DEFAULT 0,    -- VNC-服务端口
    system_maps TEXT      DEFAULT '{}', -- 系统映射字典
    public_addr TEXT      DEFAULT '[]', -- 公共IP46列表
    extend_data TEXT      DEFAULT '{}', -- 存储扩展数据
    server_dnss TEXT      DEFAULT '[]', -- NS服务器列表
    limits_nums INTEGER   DEFAULT 0,    -- VMS虚拟数量
    ipaddr_maps TEXT      DEFAULT '{}', -- IP地址的字典
    ipaddr_dnss TEXT      DEFAULT '["8.8.8.8", "8.8.4.4"]', -- DNS服务器列表
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 主机状态表 (hs_status)
CREATE TABLE IF NOT EXISTS hs_status
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT, -- 主键
    hs_name     TEXT NOT NULL,                     -- 主机名称
    status_data TEXT NOT NULL,                     -- JSON格式存储HWStatus数据
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hs_name) REFERENCES hs_config (hs_name) ON DELETE CASCADE
);


-- 虚拟机存储配置表 (vm_saving)
CREATE TABLE IF NOT EXISTS vm_saving
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    hs_name    TEXT NOT NULL, -- 主机名称
    vm_uuid    TEXT NOT NULL, -- 虚拟机UUID
    vm_config  TEXT NOT NULL, -- JSON格式存储VMConfig数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hs_name) REFERENCES hs_config (hs_name) ON DELETE CASCADE,
    UNIQUE (hs_name, vm_uuid)
);

-- 虚拟机状态表 (vm_status)
CREATE TABLE IF NOT EXISTS vm_status
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hs_name     TEXT NOT NULL, -- 主机名称
    vm_uuid     TEXT NOT NULL, -- 虚拟机UUID
    status_data TEXT NOT NULL, -- JSON格式存储HWStatus列表数据
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hs_name) REFERENCES hs_config (hs_name) ON DELETE CASCADE
    -- 注意: 不再引用 vm_saving(vm_uuid)，因为 vm_uuid 不是单列唯一键
);

-- 虚拟机任务表 (vm_tasker)
CREATE TABLE IF NOT EXISTS vm_tasker
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT, -- 主键
    hs_name    TEXT NOT NULL,                     -- 主机名称
    task_data  TEXT NOT NULL,                     -- JSON格式存储HSTasker数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hs_name) REFERENCES hs_config (hs_name) ON DELETE CASCADE
);

-- 日志记录表 (hs_logger)
CREATE TABLE IF NOT EXISTS hs_logger
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,   -- 主键
    hs_name    TEXT,                                -- 主机名称
    log_data   TEXT NOT NULL,                       -- JSON格式存储ZMessage数据
    log_level  TEXT      DEFAULT 'INFO',            -- 日志级别
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 创建时间
    FOREIGN KEY (hs_name) REFERENCES hs_config (hs_name) ON DELETE SET NULL
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_hs_config_name ON hs_config (hs_name);
CREATE INDEX IF NOT EXISTS idx_hs_status_name ON hs_status (hs_name);
CREATE INDEX IF NOT EXISTS idx_vm_saving_name ON vm_saving (hs_name);
CREATE INDEX IF NOT EXISTS idx_vm_saving_uuid ON vm_saving (vm_uuid);
CREATE INDEX IF NOT EXISTS idx_vm_status_name ON vm_status (hs_name);
CREATE INDEX IF NOT EXISTS idx_vm_status_uuid ON vm_status (vm_uuid);
CREATE INDEX IF NOT EXISTS idx_vm_tasker_name ON vm_tasker (hs_name);
CREATE INDEX IF NOT EXISTS idx_hs_logger_name ON hs_logger (hs_name);
CREATE INDEX IF NOT EXISTS idx_hs_logger_time ON hs_logger (created_at);
