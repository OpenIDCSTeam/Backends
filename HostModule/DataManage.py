import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from MainObject.Config.HSConfig import HSConfig
from MainObject.Config.VMConfig import VMConfig
from MainObject.Public.ZMessage import ZMessage


class HostDatabase:
    """HostManage SQLite数据库操作类"""
    
    def __init__(self, db_path: str = "./DataSaving/hostmanage.db"):
        """
        初始化数据库连接
        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.ensure_directory_exists()
        self.init_database()
    
    def ensure_directory_exists(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 启用字典式访问
        return conn
    
    def init_database(self):
        """初始化数据库表结构"""
        # 修正SQL文件路径，使用项目根目录下的HostConfig文件夹
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sql_file_path = os.path.join(project_root, "HostConfig", "HostManage.sql")
        
        if os.path.exists(sql_file_path):
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            conn = self.get_connection()
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
    
    def get_global_config(self) -> Dict[str, Any]:
        """获取全局配置"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT bearer, saving FROM hs_global WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return {
                    "bearer": row["bearer"],
                    "saving": row["saving"]
                }
            else:
                # 如果没有配置记录，插入默认配置
                default_bearer = ""
                default_saving = "./DataSaving"
                conn.execute(
                    "INSERT INTO hs_global (id, bearer, saving) VALUES (1, ?, ?)",
                    (default_bearer, default_saving)
                )
                conn.commit()
                print("[HostDatabase] 已创建默认全局配置")
                return {"bearer": default_bearer, "saving": default_saving}
        finally:
            conn.close()
    
    def update_global_config(self, bearer: str = None, saving: str = None):
        """更新全局配置"""
        updates = []
        params = []
        
        if bearer is not None:
            updates.append("bearer = ?")
            params.append(bearer)
        if saving is not None:
            updates.append("saving = ?")
            params.append(saving)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(1)  # WHERE id = 1
            
            sql = f"UPDATE hs_global SET {', '.join(updates)} WHERE id = ?"
            conn = self.get_connection()
            try:
                conn.execute(sql, params)
                conn.commit()
            except Exception as e:
                print(f"更新全局配置错误: {e}")
                conn.rollback()
            finally:
                conn.close()
    
    # ==================== 主机配置操作 ====================
    
    def save_host_config(self, hs_name: str, hs_config: HSConfig) -> bool:
        """保存主机配置"""
        conn = self.get_connection()
        try:
            sql = """
            INSERT OR REPLACE INTO hs_config 
            (hs_name, server_type, server_addr, server_user, server_pass, 
             filter_name, images_path, system_path, backup_path, extern_path,
             launch_path, network_nat, network_pub, i_kuai_addr, i_kuai_user, 
             i_kuai_pass, ports_start, ports_close, remote_port, system_maps, 
             public_addr, extend_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            params = (
                hs_name,
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
    
    def get_host_config(self, hs_name: str) -> Optional[Dict[str, Any]]:
        """获取主机配置"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM hs_config WHERE hs_name = ?", (hs_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()
    
    def get_all_host_configs(self) -> List[Dict[str, Any]]:
        """获取所有主机配置"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM hs_config")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def delete_host_config(self, hs_name: str) -> bool:
        """删除主机配置"""
        conn = self.get_connection()
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
    
    def save_hs_status(self, hs_name: str, hs_status_list: List[Any]) -> bool:
        """保存主机状态"""
        conn = self.get_connection()
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
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT status_data FROM hs_status WHERE hs_name = ?", (hs_name,))
            results = []
            for row in cursor.fetchall():
                results.append(json.loads(row["status_data"]))
            return results
        finally:
            conn.close()
    
    # ==================== 主机存储配置操作 ====================
    

    

    
    # ==================== 虚拟机存储配置操作 ====================
    
    def save_vm_saving(self, hs_name: str, vm_saving: Dict[str, VMConfig]) -> bool:
        """保存虚拟机存储配置"""
        conn = self.get_connection()
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
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT vm_uuid, vm_config FROM vm_saving WHERE hs_name = ?", (hs_name,))
            result = {}
            for row in cursor.fetchall():
                result[row["vm_uuid"]] = json.loads(row["vm_config"])
            return result
        finally:
            conn.close()
    
    # ==================== 虚拟机状态操作 ====================
    
    def save_vm_status(self, hs_name: str, vm_status: Dict[str, List[Any]]) -> bool:
        """保存虚拟机状态"""
        conn = self.get_connection()
        try:
            # 清除旧状态
            conn.execute("DELETE FROM vm_status WHERE hs_name = ?", (hs_name,))
            
            # 插入新状态
            sql = "INSERT INTO vm_status (hs_name, vm_uuid, status_data) VALUES (?, ?, ?)"
            for vm_uuid, status_list in vm_status.items():
                status_data = json.dumps([status.__dict__() if hasattr(status, '__dict__') else status for status in status_list])
                conn.execute(sql, (hs_name, vm_uuid, status_data))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"保存虚拟机状态错误: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_vm_status(self, hs_name: str) -> Dict[str, List[Any]]:
        """获取虚拟机状态"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT vm_uuid, status_data FROM vm_status WHERE hs_name = ?", (hs_name,))
            result = {}
            for row in cursor.fetchall():
                result[row["vm_uuid"]] = json.loads(row["status_data"])
            return result
        finally:
            conn.close()
    
    # ==================== 虚拟机任务操作 ====================
    
    def save_vm_tasker(self, hs_name: str, vm_tasker: List[Any]) -> bool:
        """保存虚拟机任务"""
        conn = self.get_connection()
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
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT task_data FROM vm_tasker WHERE hs_name = ?", (hs_name,))
            results = []
            for row in cursor.fetchall():
                results.append(json.loads(row["task_data"]))
            return results
        finally:
            conn.close()
    
    # ==================== 日志记录操作 ====================
    
    def save_logger(self, hs_name: str, save_logs: List[ZMessage]) -> bool:
        """保存日志记录"""
        conn = self.get_connection()
        try:
            # 清除旧日志
            if hs_name:
                conn.execute("DELETE FROM hs_logger WHERE hs_name = ?", (hs_name,))
            else:
                conn.execute("DELETE FROM hs_logger WHERE hs_name IS NULL")
            
            # 插入新日志
            sql = "INSERT INTO hs_logger (hs_name, log_data, log_level) VALUES (?, ?, ?)"
            for log in save_logs:
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
    
    def get_logger(self, hs_name: str = None) -> List[Any]:
        """获取日志记录"""
        conn = self.get_connection()
        try:
            if hs_name:
                cursor = conn.execute("SELECT log_data, created_at FROM hs_logger WHERE hs_name = ? ORDER BY created_at", (hs_name,))
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
    
    def save_host_full_data(self, hs_name: str, host_data: Dict[str, Any]) -> bool:
        """保存主机的完整数据"""
        try:
            success = True
            
            # 保存主机配置
            if 'hs_config' in host_data:
                hs_config = HSConfig(**host_data['hs_config'])
                success &= self.save_host_config(hs_name, hs_config)
            
            # 保存主机状态
            if 'hs_status' in host_data:
                success &= self.save_hs_status(hs_name, host_data['hs_status'])
            

            
            # 保存虚拟机存储配置
            if 'vm_saving' in host_data:
                vm_saving = {}
                for uuid, config in host_data['vm_saving'].items():
                    vm_saving[uuid] = VMConfig(**config) if isinstance(config, dict) else config
                success &= self.save_vm_saving(hs_name, vm_saving)
            
            # 保存虚拟机状态
            if 'vm_status' in host_data:
                success &= self.save_vm_status(hs_name, host_data['vm_status'])
            
            # 保存虚拟机任务
            if 'vm_tasker' in host_data:
                success &= self.save_vm_tasker(hs_name, host_data['vm_tasker'])
            
            # 保存日志记录
            if 'save_logs' in host_data:
                save_logs = []
                for log in host_data['save_logs']:
                    save_logs.append(ZMessage(**log) if isinstance(log, dict) else log)
                success &= self.save_logger(hs_name, save_logs)
            
            return success
        except Exception as e:
            print(f"保存主机完整数据错误: {e}")
            return False
    
    def get_host_full_data(self, hs_name: str) -> Dict[str, Any]:
        """获取主机的完整数据"""
        return {
            "hs_config": self.get_host_config(hs_name),
            "hs_status": self.get_hs_status(hs_name),
            "vm_saving": self.get_vm_saving(hs_name),
            "vm_status": self.get_vm_status(hs_name),
            "vm_tasker": self.get_vm_tasker(hs_name),
            "save_logs": self.get_logger(hs_name)
        }