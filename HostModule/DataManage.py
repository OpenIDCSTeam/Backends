import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Public.ZMessage import ZMessage


class HostDatabase:
    """HostManage SQLite数据库操作类"""

    def __init__(self, path: str = "./DataSaving/hostmanage.db"):
        self.db_path = path
        self.dir_db_loader()
        self.set_db_sqlite()

    # ==================== 数据库初始化 =====================
    def dir_db_loader(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def get_db_sqlite(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 启用字典式访问
        return conn

    def set_db_sqlite(self):
        """初始化数据库表结构"""
        # 修正SQL文件路径，使用项目根目录下的HostConfig文件夹
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sql_file_path = os.path.join(project_root, "HostConfig", "HostManage.sql")

        if os.path.exists(sql_file_path):
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            conn = self.get_db_sqlite()
            try:
                # 分割SQL脚本，逐条执行以更好地处理ALTER TABLE错误
                sql_statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]

                for sql in sql_statements:
                    try:
                        conn.execute(sql)
                    except sqlite3.OperationalError as e:
                        # 忽略ALTER TABLE的重复字段错误
                        if "duplicate column name" in str(e).lower():
                            print(f"字段已存在，跳过: {e}")
                            continue
                        else:
                            raise e

                conn.commit()
                print(f"[HostDatabase] 数据库初始化完成: {self.db_path}")
            except Exception as e:
                print(f"数据库初始化错误: {e}")
                conn.rollback()
            finally:
                conn.close()
        else:
            print(f"[HostDatabase] 警告: SQL文件不存在: {sql_file_path}")
            print(f"[HostDatabase] 当前工作目录: {os.getcwd()}")
            print(f"[HostDatabase] 项目根目录: {project_root}")

    # ==================== 全局配置操作 ====================

    def get_ap_config(self) -> Dict[str, Any]:
        """获取全局配置（键值对方式）"""
        conn = self.get_db_sqlite()
        try:
            cursor = conn.execute("SELECT id, data FROM hs_global")
            rows = cursor.fetchall()

            # 将键值对转换为字典
            config = {}
            for row in rows:
                config[row["id"]] = row["data"]

            # 如果没有配置记录，插入默认配置
            if not config:
                default_items = [
                    ("bearer", ""),
                    ("saving", "./DataSaving")
                ]
                for key, value in default_items:
                    conn.execute(
                        "INSERT INTO hs_global (id, data) VALUES (?, ?)",
                        (key, value)
                    )
                    config[key] = value
                conn.commit()
                print("[HostDatabase] 已创建默认全局配置")

            return config
        finally:
            conn.close()

    def set_ap_config(self, bearer: str = None, saving: str = None):
        """更新全局配置（键值对方式）"""
        if bearer is None and saving is None:
            return

        conn = self.get_db_sqlite()
        try:
            # 更新指定的配置项
            if bearer is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO hs_global (id, data) VALUES (?, ?)",
                    ("bearer", bearer)
                )
            if saving is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO hs_global (id, data) VALUES (?, ?)",
                    ("saving", saving)
                )
            conn.commit()
        except Exception as e:
            print(f"更新全局配置错误: {e}")
            conn.rollback()
        finally:
            conn.close()

    # ==================== 主机配置操作 ====================

    def set_hs_config(self, hs_name: str, hs_config: HSConfig) -> bool:
        """保存主机配置"""
        conn = self.get_db_sqlite()
        try:
            sql = """
            INSERT OR REPLACE INTO hs_config 
            (hs_name, server_name, server_type, server_addr, server_user, server_pass, 
             filter_name, images_path, system_path, backup_path, extern_path,
             launch_path, network_nat, network_pub, i_kuai_addr, i_kuai_user, 
             i_kuai_pass, ports_start, ports_close, remote_port, system_maps, 
             public_addr, extend_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            params = (
                hs_name,
                hs_config.server_name,
                hs_config.server_type,
                hs_config.server_addr,
                hs_config.server_user,
                hs_config.server_pass,
                hs_config.filter_name,
                hs_config.images_path,
                hs_config.system_path,
                hs_config.backup_path,
                hs_config.extern_path,
                hs_config.launch_path,
                hs_config.network_nat,
                hs_config.network_pub,
                hs_config.i_kuai_addr,
                hs_config.i_kuai_user,
                hs_config.i_kuai_pass,
                hs_config.ports_start,
                hs_config.ports_close,
                hs_config.remote_port,
                json.dumps(hs_config.system_maps) if hs_config.system_maps else "{}",
                json.dumps(hs_config.public_addr) if hs_config.public_addr else "[]",
                json.dumps(hs_config.extend_data) if hs_config.extend_data else "{}"
            )
            conn.execute(sql, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"保存主机配置错误: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_hs_config(self, hs_name: str) -> Optional[Dict[str, Any]]:
        """获取主机配置"""
        conn = self.get_db_sqlite()
        try:
            cursor = conn.execute("SELECT * FROM hs_config WHERE hs_name = ?", (hs_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def all_hs_config(self) -> List[Dict[str, Any]]:
        """获取所有主机配置"""
        conn = self.get_db_sqlite()
        try:
            cursor = conn.execute("SELECT * FROM hs_config")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def del_hs_config(self, hs_name: str) -> bool:
        """删除主机配置"""
        conn = self.get_db_sqlite()
        try:
            conn.execute("DELETE FROM hs_config WHERE hs_name = ?", (hs_name,))
            conn.commit()
            return True
        except Exception as e:
            print(f"删除主机配置错误: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    # ==================== 主机状态操作 ====================

    def add_hs_status(self, hs_name: str, status: Any) -> bool:
        """
        添加单个主机状态（立即保存到数据库）
        :param hs_name: 主机名称
        :param status: 状态对象（HWStatus）
        :return: 是否成功
        """
        try:
            # 获取现有状态
            all_status = self.get_hs_status(hs_name)

            # 转换状态对象为字典
            status_dict = status.__dict__() if hasattr(status, '__dict__') else status
            all_status.append(status_dict)

            # 限制状态历史记录数量（保留最近100条）
            if len(all_status) > 100:
                all_status = all_status[-100:]

            # 立即保存到数据库
            return self.set_hs_status(hs_name, all_status)
        except Exception as e:
            print(f"[DataManage] 添加主机状态失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def set_hs_status(self, hs_name: str, hs_status_list: List[Any]) -> bool:
        """保存主机状态"""
        conn = self.get_db_sqlite()
        try:
            # 清除旧状态
            conn.execute("DELETE FROM hs_status WHERE hs_name = ?", (hs_name,))

            # 插入新状态
            sql = "INSERT INTO hs_status (hs_name, status_data) VALUES (?, ?)"
            for status in hs_status_list:
                status_data = json.dumps(status.__dict__() if hasattr(status, '__dict__') else status)
                conn.execute(sql, (hs_name, status_data))

            conn.commit()
            return True
        except Exception as e:
            print(f"保存主机状态错误: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_hs_status(self, hs_name: str) -> List[Any]:
        """获取主机状态"""
        conn = self.get_db_sqlite()
        try:
            cursor = conn.execute("SELECT status_data FROM hs_status WHERE hs_name = ?", (hs_name,))
            results = []
            for row in cursor.fetchall():
                results.append(json.loads(row["status_data"]))
            return results
        finally:
            conn.close()

    # ==================== 虚拟配置操作 ====================

    def set_vm_saving(self, hs_name: str, vm_saving: Dict[str, VMConfig]) -> bool:
        """保存虚拟机存储配置"""
        conn = self.get_db_sqlite()
        try:
            # 清除旧配置
            conn.execute("DELETE FROM vm_saving WHERE hs_name = ?", (hs_name,))

            # 插入新配置
            sql = "INSERT INTO vm_saving (hs_name, vm_uuid, vm_config) VALUES (?, ?, ?)"
            for vm_uuid, vm_config in vm_saving.items():
                config_data = json.dumps(vm_config.__dict__() if hasattr(vm_config, '__dict__') else vm_config)
                conn.execute(sql, (hs_name, vm_uuid, config_data))

            conn.commit()
            return True
        except Exception as e:
            print(f"保存虚拟机存储配置错误: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_vm_saving(self, hs_name: str) -> Dict[str, Any]:
        """获取虚拟机存储配置"""
        conn = self.get_db_sqlite()
        try:
            cursor = conn.execute("SELECT vm_uuid, vm_config FROM vm_saving WHERE hs_name = ?", (hs_name,))
            result = {}
            for row in cursor.fetchall():
                result[row["vm_uuid"]] = json.loads(row["vm_config"])
            return result
        finally:
            conn.close()

    # ==================== 虚拟状态操作 ====================
    def add_vm_status(self, hs_name: str, vm_uuid: str, status: Any) -> bool:
        """
        添加单个虚拟机状态（立即保存到数据库）
        :param hs_name: 主机名称
        :param vm_uuid: 虚拟机UUID
        :param status: 状态对象（HWStatus）
        :return: 是否成功
        """
        try:
            # 获取现有状态
            all_status = self.get_vm_status(hs_name)

            # 添加新状态到列表
            if vm_uuid not in all_status:
                all_status[vm_uuid] = []

            # 转换状态对象为字典
            status_dict = status.__dict__() if hasattr(status, '__dict__') else status
            all_status[vm_uuid].append(status_dict)

            # 限制状态历史记录数量（保留最近100条）
            if len(all_status[vm_uuid]) > 100:
                all_status[vm_uuid] = all_status[vm_uuid][-100:]

            # 立即保存到数据库
            return self.set_vm_status(hs_name, all_status)
        except Exception as e:
            print(f"[DataManage] 添加虚拟机状态失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def set_vm_status(self, hs_name: str, vm_status: Dict[str, List[Any]]) -> bool:
        """保存虚拟机状态"""
        conn = self.get_db_sqlite()
        try:
            print(f"[DataManage] 开始保存虚拟机状态，主机: {hs_name}, 虚拟机数量: {len(vm_status)}")

            # 清除旧状态
            delete_result = conn.execute("DELETE FROM vm_status WHERE hs_name = ?", (hs_name,))
            print(f"[DataManage] 已清除旧状态，删除行数: {delete_result.rowcount}")

            # 插入新状态
            sql = "INSERT INTO vm_status (hs_name, vm_uuid, status_data) VALUES (?, ?, ?)"
            insert_count = 0
            for vm_uuid, status_list in vm_status.items():
                status_data = json.dumps(
                    [status.__dict__() if hasattr(status, '__dict__') else status for status in status_list])
                print(
                    f"[DataManage] 插入虚拟机 {vm_uuid} 状态，记录数: {len(status_list)}, 数据长度: {len(status_data)}")
                conn.execute(sql, (hs_name, vm_uuid, status_data))
                insert_count += 1

            conn.commit()
            print(f"[DataManage] 虚拟机状态保存成功，共插入 {insert_count} 条记录")
            return True
        except Exception as e:
            print(f"[DataManage] 保存虚拟机状态错误: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_vm_status(self, hs_name: str) -> Dict[str, List[Any]]:
        """获取虚拟机状态"""
        conn = self.get_db_sqlite()
        try:
            cursor = conn.execute("SELECT vm_uuid, status_data FROM vm_status WHERE hs_name = ?", (hs_name,))
            result = {}
            for row in cursor.fetchall():
                result[row["vm_uuid"]] = json.loads(row["status_data"])
            return result
        finally:
            conn.close()

    # ==================== 虚拟机任务操作 ====================
    def set_vm_tasker(self, hs_name: str, vm_tasker: List[Any]) -> bool:
        """保存虚拟机任务"""
        conn = self.get_db_sqlite()
        try:
            # 清除旧任务
            conn.execute("DELETE FROM vm_tasker WHERE hs_name = ?", (hs_name,))

            # 插入新任务
            sql = "INSERT INTO vm_tasker (hs_name, task_data) VALUES (?, ?)"
            for tasker in vm_tasker:
                task_data = json.dumps(tasker.__dict__() if hasattr(tasker, '__dict__') else tasker)
                conn.execute(sql, (hs_name, task_data))

            conn.commit()
            return True
        except Exception as e:
            print(f"保存虚拟机任务错误: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_vm_tasker(self, hs_name: str) -> List[Any]:
        """获取虚拟机任务"""
        conn = self.get_db_sqlite()
        try:
            cursor = conn.execute("SELECT task_data FROM vm_tasker WHERE hs_name = ?", (hs_name,))
            results = []
            for row in cursor.fetchall():
                results.append(json.loads(row["task_data"]))
            return results
        finally:
            conn.close()

    # ==================== 日志记录操作 ====================
    def add_hs_logger(self, hs_name: str, logs: ZMessage) -> bool:
        """
        添加单条日志（立即保存到数据库）
        :param hs_name: 主机名称（可为None表示全局日志）
        :param logs: 日志对象（ZMessage）
        :return: 是否成功
        """
        conn = self.get_db_sqlite()
        try:
            log_data = json.dumps(logs.__dict__() if hasattr(logs, '__dict__') else logs)
            log_level = getattr(logs, 'level', 'INFO') if hasattr(logs, 'level') else 'INFO'

            sql = "INSERT INTO hs_logger (hs_name, log_data, log_level) VALUES (?, ?, ?)"
            conn.execute(sql, (hs_name, log_data, log_level))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DataManage] 添加日志失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def del_hs_logger(self, hs_name: str, days: int = 7) -> int:
        """
        清理指定天数之前的日志
        :param hs_name: 主机名称（可为None表示全局日志）
        :param days: 保留天数
        :return: 删除的日志条数
        """
        conn = self.get_db_sqlite()
        try:
            sql = """
                  DELETE
                  FROM hs_logger
                  WHERE (hs_name = ? OR (hs_name IS NULL AND ? IS NULL))
                    AND created_at < datetime('now', '-' || ? || ' days') \
                  """
            cursor = conn.execute(sql, (hs_name, hs_name, days))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
        except Exception as e:
            print(f"[DataManage] 清理日志失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def set_hs_logger(self, hs_name: str, logs: List[ZMessage]) -> bool:
        """保存日志记录"""
        conn = self.get_db_sqlite()
        try:
            # 清除旧日志
            if hs_name:
                conn.execute("DELETE FROM hs_logger WHERE hs_name = ?", (hs_name,))
            else:
                conn.execute("DELETE FROM hs_logger WHERE hs_name IS NULL")

            # 插入新日志
            sql = "INSERT INTO hs_logger (hs_name, log_data, log_level) VALUES (?, ?, ?)"
            for log in logs:
                log_data = json.dumps(log.__dict__() if hasattr(log, '__dict__') else log)
                log_level = getattr(log, 'level', 'INFO') if hasattr(log, 'level') else 'INFO'
                conn.execute(sql, (hs_name, log_data, log_level))

            conn.commit()
            return True
        except Exception as e:
            print(f"保存日志记录错误: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_hs_logger(self, hs_name: str = None) -> List[Any]:
        """获取日志记录"""
        conn = self.get_db_sqlite()
        try:
            if hs_name:
                cursor = conn.execute(
                    "SELECT log_data, created_at FROM hs_logger WHERE hs_name = ? ORDER BY created_at", (hs_name,))
            else:
                # 获取所有日志，而不仅仅是hs_name为NULL的日志
                cursor = conn.execute("SELECT log_data, created_at FROM hs_logger ORDER BY created_at")

            results = []
            for row in cursor.fetchall():
                log_data = json.loads(row["log_data"])
                log_data['created_at'] = row["created_at"]
                results.append(log_data)
            return results
        finally:
            conn.close()

    # ==================== 完整数据保存和加载 ====================
    def set_ap_server(self, hs_name: str, host_data: Dict[str, Any]) -> bool:
        """保存主机的完整数据"""
        try:
            success = True

            # 保存主机配置
            if 'hs_config' in host_data:
                hs_config = HSConfig(**host_data['hs_config'])
                success &= self.set_hs_config(hs_name, hs_config)

            # 保存主机状态
            if 'hs_status' in host_data:
                success &= self.set_hs_status(hs_name, host_data['hs_status'])

            # 保存虚拟机存储配置
            if 'vm_saving' in host_data:
                vm_saving = {}
                for uuid, config in host_data['vm_saving'].items():
                    vm_saving[uuid] = VMConfig(**config) if isinstance(config, dict) else config
                success &= self.set_vm_saving(hs_name, vm_saving)

            # 保存虚拟机状态
            if 'vm_status' in host_data:
                success &= self.set_vm_status(hs_name, host_data['vm_status'])

            # 保存虚拟机任务
            if 'vm_tasker' in host_data:
                success &= self.set_vm_tasker(hs_name, host_data['vm_tasker'])

            # 保存日志记录
            if 'save_logs' in host_data:
                save_logs = []
                for log in host_data['save_logs']:
                    save_logs.append(ZMessage(**log) if isinstance(log, dict) else log)
                success &= self.set_hs_logger(hs_name, save_logs)

            return success
        except Exception as e:
            print(f"保存主机完整数据错误: {e}")
            return False

    def get_ap_server(self, hs_name: str) -> Dict[str, Any]:
        """获取主机的完整数据"""
        return {
            "hs_config": self.get_hs_config(hs_name),
            "hs_status": self.get_hs_status(hs_name),
            "vm_saving": self.get_vm_saving(hs_name),
            "vm_status": self.get_vm_status(hs_name),
            "vm_tasker": self.get_vm_tasker(hs_name),
            "save_logs": self.get_hs_logger(hs_name)
        }
