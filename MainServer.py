# -*- coding: utf-8 -*-
# OpenIDCS Flask Server ###########################################################
# 提供主机和虚拟机管理的Web界面和API接口
################################################################################
import sys
import os
# 打包后修正 sys.path，确保 HostModule 等包可被正确导入
# Nuitka onefile 模式下，解压目录在临时路径，需将其加入 sys.path
if getattr(sys, 'frozen', False):
    _bundle_dir = os.path.dirname(sys.executable)
    if _bundle_dir not in sys.path:
        sys.path.insert(0, _bundle_dir)

import warnings
# 屏蔽 paramiko 使用旧版 TripleDES 路径产生的废弃警告
warnings.filterwarnings("ignore", category=DeprecationWarning, module="paramiko")
warnings.filterwarnings("ignore", message=".*TripleDES.*", category=UserWarning)
import time
import secrets
import threading
import platform
import subprocess
import traceback
import json
import ipaddress
import mimetypes
from functools import wraps
from flask import Flask, request, jsonify, session, redirect, url_for, g, send_from_directory

# 全局修复 Windows 上的 MIME 类型问题
# Windows 注册表可能将 .js 映射为 text/plain，导致浏览器拒绝加载模块脚本
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/javascript', '.mjs')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('font/ttf', '.ttf')
mimetypes.add_type('image/svg+xml', '.svg')

from loguru import logger
from HostModule.HostManager import HostManage
from HostModule.RestManager import RestManager
from HostModule.UserManager import UserManager, require_login, require_admin, check_host_access, check_vm_permission, check_resource_quota, EmailService, init_bearer_validator, init_db_getter
from HostModule.DataManager import DataManager

# 获取项目根目录，兼容开发环境和打包后的环境
if getattr(sys, 'frozen', False):
    # PyInstaller onefile 模式：资源解压在 _MEIPASS 临时目录
    # cx_Freeze / Nuitka 等目录模式：资源在可执行文件所在目录
    if hasattr(sys, '_MEIPASS'):
        project_root = sys._MEIPASS
    else:
        project_root = os.path.dirname(sys.executable)
else:
    # 开发环境：从当前文件所在目录查找
    project_root = os.path.dirname(os.path.abspath(__file__))

# 配置模板和静态文件目录
# WebDesigns: 传统 Jinja2 模板（用于兼容旧页面）
# static: React 前端构建产物
template_folder = os.path.join(project_root, 'WebDesigns')
static_folder = os.path.join(project_root, 'static')

app = Flask(__name__, template_folder=template_folder, static_folder=None, static_url_path='')
app.config.update(
    MAX_CONTENT_LENGTH=100 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('OPENIDCS_HTTPS', '').lower() in ('1', 'true', 'yes'),
    PERMANENT_SESSION_LIFETIME=3600,
)

# CSRF防护配置 ################################################################
# 对所有状态变更请求（POST/PUT/DELETE）验证自定义头部 X-Requested-With
# 浏览器跨域请求无法携带自定义头部（除非CORS允许），从而防止CSRF攻击
# 前端React应用在请求拦截器中统一添加此头部
_CSRF_EXEMPT_PATHS = ('/api/login', '/api/register', '/api/verify-email',
                      '/api/system/forgot-password', '/api/forgot-password',
                      '/api/system/reset-password', '/api/client/templogin')  # 匿名接口由独立凭据校验保护

@app.before_request
def csrf_protection():
    """CSRF防护：对状态变更请求验证X-Requested-With头部"""
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    # Bearer Token认证的请求免CSRF（API客户端）
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return None
    # 免检路径
    if request.path in _CSRF_EXEMPT_PATHS:
        return None
    # Cookie 认证的状态变更请求必须携带自定义头部。
    # 不能仅凭 application/json 放行：文本表单和错误 CORS 配置都可能绕过该假设。
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return jsonify({
            'code': 403,
            'msg': 'CSRF验证失败，缺少有效的X-Requested-With头部',
            'data': None,
            'timestamp': int(time.time())
        }), 403
    return None


@app.after_request
def add_security_headers(response):
    """为所有响应增加浏览器安全基线，降低点击劫持、MIME嗅探和信息泄露风险。"""
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    response.headers.setdefault(
        'Content-Security-Policy',
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self' ws: wss:; frame-ancestors 'self'; "
        "base-uri 'self'; form-action 'self'"
    )
    if request.path.startswith('/api/'):
        response.headers.setdefault('Cache-Control', 'no-store')
    if app.config.get('SESSION_COOKIE_SECURE'):
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response

# 登录速率限制 ################################################################
# 使用内存+数据库双层存储：内存用于快速查询，数据库用于持久化（重启不丢失）
_login_fail_records: dict = {}  # {ip: {'count': int, 'lock_until': float}}
_LOGIN_MAX_FAILS = 5       # 最大失败次数
_LOGIN_LOCK_SECONDS = 300  # 锁定时长（秒）
_login_lock = threading.Lock()


def _get_real_client_ip() -> str:
    """安全获取客户端真实IP，防止X-Forwarded-For伪造
    
    策略：仅信任最后一个代理添加的IP（即X-Forwarded-For的最右侧非私有IP），
    如果所有IP都是私有地址或无X-Forwarded-For，则使用remote_addr
    """
    
    xff = request.headers.get('X-Forwarded-For', '')
    if not xff:
        return request.remote_addr or '127.0.0.1'
    
    # X-Forwarded-For格式: client, proxy1, proxy2
    # 从右向左找第一个非私有IP（最右侧是最近的可信代理添加的）
    ips = [ip.strip() for ip in xff.split(',') if ip.strip()]
    
    # 如果只有一个IP（单层代理），直接使用
    if len(ips) == 1:
        return ips[0]
    
    # 多层代理：从右向左找第一个公网IP
    for ip in reversed(ips):
        try:
            addr = ipaddress.ip_address(ip)
            if not addr.is_private and not addr.is_loopback:
                return ip
        except ValueError:
            continue
    
    # 所有IP都是私有的，使用最左侧（原始客户端）
    return ips[0]


def _check_login_rate_limit(ip: str) -> tuple:
    """检查登录速率限制，返回 (是否允许, 剩余锁定秒数)"""
    with _login_lock:
        record = _login_fail_records.get(ip)
        if not record:
            return True, 0
        lock_until = record.get('lock_until', 0)
        if lock_until and time.time() < lock_until:
            return False, int(lock_until - time.time())
        # 锁定已过期，清除记录
        if lock_until and time.time() >= lock_until:
            _login_fail_records.pop(ip, None)
        return True, 0


def _record_login_fail(ip: str):
    """记录登录失败，超过阈值则锁定（同时持久化到数据库）"""
    with _login_lock:
        record = _login_fail_records.setdefault(ip, {'count': 0, 'lock_until': 0})
        record['count'] += 1
        if record['count'] >= _LOGIN_MAX_FAILS:
            record['lock_until'] = time.time() + _LOGIN_LOCK_SECONDS
            logger.warning(f"[安全] IP {ip} 登录失败 {record['count']} 次，锁定 {_LOGIN_LOCK_SECONDS} 秒")
            # 持久化锁定记录到数据库
            try:
                conn = db.get_db_sqlite()
                conn.execute(
                    "INSERT OR REPLACE INTO hs_global (id, data) VALUES (?, ?)",
                    (f"ip_lock:{ip}", json.dumps({'lock_until': record['lock_until'], 'count': record['count']}))
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"持久化IP锁定记录失败: {e}")


def _clear_login_fail(ip: str):
    """登录成功后清除失败记录"""
    with _login_lock:
        _login_fail_records.pop(ip, None)
    # 清除数据库中的锁定记录
    try:
        conn = db.get_db_sqlite()
        conn.execute("DELETE FROM hs_global WHERE id = ?", (f"ip_lock:{ip}",))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _verify_turnstile(token: str) -> bool:
    """验证Cloudflare Turnstile token，返回是否通过"""
    import requests as _requests
    try:
        settings = db.get_system_settings()
        if settings.get('turnstile_enabled') != '1':
            return True  # 未启用验证码，直接通过
        secret_key = settings.get('turnstile_secret_key', '')
        if not secret_key:
            return True  # 未配置密钥，直接通过
        if not token:
            return False  # 启用了但未提供token
        resp = _requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={'secret': secret_key, 'response': token},
            timeout=10
        )
        result = resp.json()
        return result.get('success', False)
    except Exception as e:
        logger.error(f"[Turnstile] 验证异常: {e}")
        return False


def _check_turnstile_if_enabled(data) -> tuple:
    """检查Turnstile验证码（如果启用），返回 (是否通过, 错误响应或None)"""
    settings = db.get_system_settings()
    if settings.get('turnstile_enabled') != '1':
        return True, None
    turnstile_token = data.get('turnstile_token', '') if data else ''
    if not _verify_turnstile(turnstile_token):
        return False, api_response_wrapper(400, '验证码验证失败，请重试')
    return True, None


def _load_login_fail_records():
    """启动时从数据库加载未过期的IP锁定记录"""
    try:
        conn = db.get_db_sqlite()
        cursor = conn.execute("SELECT id, data FROM hs_global WHERE id LIKE 'ip_lock:%'")
        now = time.time()
        for row in cursor.fetchall():
            ip = row['id'].replace('ip_lock:', '')
            data = json.loads(row['data'])
            if data.get('lock_until', 0) > now:
                _login_fail_records[ip] = data
            else:
                # 已过期，清除
                conn.execute("DELETE FROM hs_global WHERE id = ?", (row['id'],))
        conn.commit()
        conn.close()
        if _login_fail_records:
            logger.info(f"[安全] 从数据库恢复 {len(_login_fail_records)} 条IP锁定记录")
    except Exception as e:
        logger.debug(f"加载IP锁定记录失败: {e}")

# 全局主机管理实例（延迟初始化，在init_app()中创建，避免Nuitka将主脚本编译为DLL）
hs_manage = None

# 数据库实例（延迟初始化）
db = None

# 持久化Flask secret_key：从数据库读取，避免重启后所有Session失效
def _init_secret_key():
    """从数据库获取或生成持久化的Flask secret_key"""
    config = db.get_ap_config()
    secret_key = config.get('flask_secret_key', '')
    if not secret_key:
        secret_key = secrets.token_hex(32)
        # 写入数据库持久化
        conn = db.get_db_sqlite()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO hs_global (id, data) VALUES (?, ?)",
                ("flask_secret_key", secret_key)
            )
            conn.commit()
            logger.info("[安全] 已生成并持久化Flask secret_key")
        except Exception as e:
            logger.error(f"持久化secret_key失败: {e}")
        finally:
            conn.close()
    return secret_key

# 全局REST管理器实例（延迟初始化）
rest_manager = None

# 认证装饰器（保持向后兼容）###################################################
# 需要登录或Bearer Token认证的装饰器
################################################################################
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 检查Bearer Token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token and token == hs_manage.bearer:
                # Token登录，注入管理员用户信息到请求上下文
                g.current_user = {
                    'id': 1,
                    'username': 'admin',
                    'is_admin': True,
                    'is_token_login': True,
                    'assigned_hosts': []
                }
                return f(*args, **kwargs)
            # 临时token（财务系统插件跳转）：格式为 temp:<sha256>
            if token and token.startswith('temp:'):
                temp_key = token[5:]
                user_data = rest_manager.get_temp_user_data(temp_key)
                if user_data:
                    g.current_user = user_data
                    return f(*args, **kwargs)
        # 检查Session登录
        if session.get('logged_in'):
            return f(*args, **kwargs)
        # API请求返回JSON错误
        if request.is_json or request.path.startswith('/api/'):
            return rest_manager.api_response(401, '未授权访问', None)
        # 页面请求重定向到登录页
        return redirect(url_for('login'))
    return decorated


def get_current_user():
    """获取当前用户信息，优先从请求上下文(Bearer Token)取，再从Session取
    注意：此函数与RestManager._get_current_user逻辑一致，统一使用UserManager
    """
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user
    return UserManager.get_current_user_from_session()


# 统一API响应格式包装器 #######################################################
def api_response_wrapper(code=200, msg='成功', data=None):
    return rest_manager.api_response(code, msg, data)


# 页面路由 ####################################################################
# React 前端路由处理
# 对于所有非 API 路由，返回 React 的 index.html，让前端路由接管

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """
    提供 React 前端服务
    - 如果请求的是 API 路由，交给 API 处理器
    - 如果请求的是静态文件且存在，返回静态文件
    - 否则返回 index.html，让 React Router 处理路由
    """
    # API 路由由其他路由处理器接管
    if path.startswith('api/'):
        return {'error': 'API endpoint not found'}, 404
    
    # 检查是否是静态文件请求
    static_file_path = os.path.join(static_folder, path)
    if path and os.path.isfile(static_file_path):
        # 使用 send_from_directory 正确处理 MIME 类型
        response = send_from_directory(static_folder, path)
        
        # 显式设置JavaScript文件的MIME类型（修复Windows上的MIME类型问题）
        if path.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        elif path.endswith('.mjs'):
            response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        elif path.endswith('.css'):
            response.headers['Content-Type'] = 'text/css; charset=utf-8'
        elif path.endswith('.json'):
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        elif path.endswith('.woff2'):
            response.headers['Content-Type'] = 'font/woff2'
        elif path.endswith('.woff'):
            response.headers['Content-Type'] = 'font/woff'
        elif path.endswith('.ttf'):
            response.headers['Content-Type'] = 'font/ttf'
        
        return response
    
    # 返回 React 的 index.html
    index_path = os.path.join(static_folder, 'index.html')
    if os.path.isfile(index_path):
        return send_from_directory(static_folder, 'index.html')
    else:
        # 如果 React 前端未构建，返回提示信息
        return '''
        <html>
            <head><title>OpenIDCS - 前端未构建</title></head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>⚠️ React 前端未构建</h1>
                <p>请先构建 React 前端：</p>
                <pre style="background: #f5f5f5; padding: 20px; border-radius: 5px; display: inline-block; text-align: left;">
cd FrontPages
npm install
npm run build
cd ..
mkdir -p static
cp -r FrontPages/dist/* static/
                </pre>
                <p>或使用打包脚本：</p>
                <pre style="background: #f5f5f5; padding: 20px; border-radius: 5px; display: inline-block; text-align: left;">
cd AllBuilder
python build_pyinstaller.py  # 所有平台
                </pre>
            </body>
        </html>
        ''', 503


# 获取Turnstile公开配置（无需认证） ################################################
@app.route('/api/public/turnstile-config', methods=['GET'])
def get_turnstile_config():
    """获取Turnstile验证码公开配置（仅返回site_key和是否启用，不返回secret_key）"""
    try:
        settings = db.get_system_settings()
        return api_response_wrapper(200, 'success', {
            'enabled': settings.get('turnstile_enabled') == '1',
            'site_key': settings.get('turnstile_site_key', ''),
        })
    except Exception as e:
        logger.error(f"获取Turnstile配置失败: {e}")
        return api_response_wrapper(500, '获取配置失败')


# 登录API ####################################################################
@app.route('/api/login', methods=['POST'])
def login():
    try:
        # 速率限制检查（使用安全的IP获取方式，防止X-Forwarded-For伪造）
        client_ip = _get_real_client_ip()
        allowed, remaining = _check_login_rate_limit(client_ip)
        if not allowed:
            return api_response_wrapper(429, f'登录失败次数过多，请 {remaining} 秒后再试')

        # POST登录处理
        data = request.get_json() or request.form

        # Turnstile验证码检查
        passed, err_resp = _check_turnstile_if_enabled(data)
        if not passed:
            return err_resp

        login_type = data.get('login_type', 'token')
        
        if login_type == 'user':
            # 用户名密码登录
            username = data.get('username', '')
            password = data.get('password', '')
            
            if not username or not password:
                return api_response_wrapper(400, '用户名和密码不能为空')
            
            # 查询用户
            user_data = db.get_user_by_username(username)
            if not user_data:
                _record_login_fail(client_ip)
                return api_response_wrapper(401, '用户名或密码错误')
            
            # 验证密码
            if not UserManager.verify_password(password, user_data['password']):
                _record_login_fail(client_ip)
                return api_response_wrapper(401, '用户名或密码错误')
            
            # 检查用户是否启用
            if not user_data['is_active']:
                return api_response_wrapper(403, '用户已被禁用')
            
            # 检查邮箱验证状态
            system_settings = db.get_system_settings()
            if system_settings.get('email_verification_enabled') == '1' and not user_data['email_verified']:
                return api_response_wrapper(403, '请先验证邮箱后再登录')
            
            # 设置session
            UserManager.set_user_session(user_data, is_token_login=False)
            
            # 更新最后登录时间
            db.update_user_last_login(user_data['id'])
            
            # 登录成功，清除失败记录
            _clear_login_fail(client_ip)
            
            # 构建返回的用户信息（移除敏感字段）
            user_info = dict(user_data)
            user_info.pop('password', None)
            user_info.pop('verify_token', None)
            if isinstance(user_info.get('assigned_hosts'), str):
                try:
                    user_info['assigned_hosts'] = json.loads(user_info['assigned_hosts'])
                except Exception:
                    user_info['assigned_hosts'] = []
            
            return api_response_wrapper(200, '登录成功', {'redirect': '/admin', 'user_info': user_info})
        
        else:
            # Token登录
            token = data.get('token', '')
            if token and token == hs_manage.bearer:
                # 获取真实的admin用户信息
                admin_user_data = db.get_user_by_username('admin')
                if admin_user_data:
                    # 确保admin用户是启用状态
                    if not admin_user_data.get('is_active', 1):
                        return api_response_wrapper(403, 'Admin用户已被禁用')
                    
                    # 设置session，标记为token登录
                    UserManager.set_user_session(admin_user_data, is_token_login=True)
                    
                    # 更新最后登录时间
                    db.update_user_last_login(admin_user_data['id'])
                    
                    # 登录成功，清除失败记录
                    _clear_login_fail(client_ip)
                    
                    # 构建返回的用户信息（移除敏感字段）
                    admin_info = dict(admin_user_data)
                    admin_info.pop('password', None)
                    admin_info.pop('verify_token', None)
                    if isinstance(admin_info.get('assigned_hosts'), str):
                        try:
                            admin_info['assigned_hosts'] = json.loads(admin_info['assigned_hosts'])
                        except Exception:
                            admin_info['assigned_hosts'] = []
                    
                    return api_response_wrapper(200, '登录成功', {'redirect': '/admin', 'user_info': admin_info})
                else:
                    # 如果admin用户不存在，创建临时的admin session（兼容原有逻辑）
                    temp_admin_data = {
                        'id': 1,
                        'username': 'admin',
                        'is_admin': 1,
                        'is_active': 1,
                        'assigned_hosts': []
                    }
                    UserManager.set_user_session(temp_admin_data, is_token_login=True)
                    _clear_login_fail(client_ip)
                    return api_response_wrapper(200, '登录成功', {'redirect': '/admin', 'user_info': temp_admin_data})
            
            # Token错误，记录失败
            _record_login_fail(client_ip)
            return api_response_wrapper(401, 'Token错误')
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return api_response_wrapper(500, '登录失败，请稍后重试')


# 退出登录API ################################################################
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return api_response_wrapper(200, '退出成功')





# 用户注册API ################################################################
@app.route('/api/register', methods=['POST'])
def register():
    try:
        # POST注册处理
        data = request.get_json() or request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')

        # Turnstile验证码检查
        passed, err_resp = _check_turnstile_if_enabled(data)
        if not passed:
            return err_resp
        
        # 验证输入
        if not username or not email or not password:
            return api_response_wrapper(400, '用户名、邮箱和密码不能为空')
        
        if len(username) < 3 or len(username) > 20:
            return api_response_wrapper(400, '用户名长度必须在3-20个字符之间')
        
        # 禁止使用admin作为用户名
        if username.lower() == 'admin':
            return api_response_wrapper(400, '不能使用admin作为用户名')
        
        if len(password) < 6:
            return api_response_wrapper(400, '密码长度至少6个字符')
        
        # 检查用户名是否已存在
        if db.get_user_by_username(username):
            return api_response_wrapper(400, '用户名已存在')
        
        # 检查邮箱是否已存在
        if db.get_user_by_email(email):
            return api_response_wrapper(400, '邮箱已被注册')
        
        # 加密密码
        hashed_password = UserManager.hash_password(password)
        
        # 创建用户
        settings = db.get_system_settings()
        
        # 获取默认资源配置
        default_quotas = {
            'quota_cpu': int(settings.get('default_quota_cpu', 2)),
            'quota_ram': int(settings.get('default_quota_ram', 4)),
            'quota_ssd': int(settings.get('default_quota_ssd', 20)),
            'quota_gpu': int(settings.get('default_quota_gpu', 0)),
            'quota_nat_ports': int(settings.get('default_quota_nat_ports', 5)),
            'quota_web_proxy': int(settings.get('default_quota_web_proxy', 0)),
            'quota_bandwidth_up': int(settings.get('default_quota_bandwidth_up', 10)),
            'quota_bandwidth_down': int(settings.get('default_quota_bandwidth_down', 10)),
            'quota_traffic': int(settings.get('default_quota_traffic', 100)),
            # 默认权限
            'can_create_vm': settings.get('default_can_create_vm', '1') == '1',
            'can_modify_vm': settings.get('default_can_modify_vm', '1') == '1',
            'can_delete_vm': settings.get('default_can_delete_vm', '1') == '1',
            'user_permission': int(settings.get('default_user_permission', 56791)),
            'is_admin': 0,  # 新用户默认不是管理员
            'is_active': 1,  # 新用户默认启用
            'assigned_hosts': '[]'  # 默认无分配主机
        }
        
        user_id = db.create_user(username, hashed_password, email, **default_quotas)
        if not user_id:
            return api_response_wrapper(500, '注册失败，请重试')
        
        # 检查是否需要邮箱验证
        settings = db.get_system_settings()
        if settings.get('email_verification_enabled') == '1':
            # 生成验证token
            verify_token = UserManager.generate_token()
            db.set_user_verify_token(user_id, verify_token)
            
            # 发送验证邮件
            email_service = EmailService(
                api_key=settings.get('resend_apikey', ''),
                from_email=settings.get('resend_email', '')
            )
            base_url = settings.get('base_url', '').rstrip('/')
            if not base_url:
                base_url = request.host_url.rstrip('/')
            verify_url = f"{base_url}/verify_email?token={verify_token}"
            email_service.send_verification_email(email, username, verify_url)
            
            return api_response_wrapper(200, '注册成功！请查收验证邮件')
        else:
            # 直接验证邮箱
            db.verify_user_email(user_id)
            return api_response_wrapper(200, '注册成功！请登录')
    except Exception as e:
        logger.error(f"注册失败: {e}")
        return api_response_wrapper(500, f'注册失败: {str(e)}')


# 验证邮箱 ####################################################################
@app.route('/verify_email')
def verify_email():
    try:
        token = request.args.get('token', '')
        if not token:
            return redirect('/?verified=error&msg=invalid_link')
        
        user_data = db.get_user_by_verify_token(token)
        if not user_data:
            return redirect('/?verified=error&msg=expired')
        
        # 验证邮箱
        if db.verify_user_email(user_data['id']):
            return redirect('/?verified=success')
        else:
            return redirect('/?verified=error&msg=failed')
    except Exception as e:
        logger.error(f"验证邮箱失败: {e}")
        return redirect('/?verified=error&msg=exception')

@app.route('/verify-email-change')
def verify_email_change():
    """验证邮箱变更"""
    try:
        token = request.args.get('token', '')
        if not token:
            return redirect('/profile?email_changed=error&msg=invalid_link')
        
        # 解析token中的邮箱地址
        import base64
        try:
            if ':' not in token:
                return redirect('/profile?email_changed=error&msg=invalid_format')
            
            email_base64, random_value = token.split(':', 1)
            
            # 解码base64邮箱
            email_bytes = base64.urlsafe_b64decode(email_base64 + '=' * (-len(email_base64) % 4))
            new_email = email_bytes.decode()
        except Exception as e:
            logger.error(f"邮箱验证token解码失败: {e}")
            return redirect('/profile?email_changed=error&msg=decode_failed')
        
        # 直接根据verify_token字段查找用户
        user_data = db.get_user_by_verify_token(token)
        if not user_data:
            return redirect('/profile?email_changed=error&msg=expired')
        if not new_email:
            return redirect('/profile?email_changed=error&msg=invalid_email')
        
        # 再次检查邮箱是否已被其他用户使用
        existing_user = db.get_user_by_email(new_email)
        if existing_user and existing_user['id'] != user_data['id']:
            return redirect('/profile?email_changed=error&msg=email_taken')
        
        # 更新用户邮箱
        success = db.update_user(user_data['id'], email=new_email)
        if success:
            # 清除验证token
            db.set_user_verify_token(user_data['id'], '')
            return redirect('/profile?email_changed=success')
        else:
            return redirect('/profile?email_changed=error&msg=update_failed')
            
    except Exception as e:
        logger.error(f"验证邮箱变更失败: {e}")
        return redirect('/profile?email_changed=error&msg=exception')

@app.route('/api/users/change-password', methods=['POST'])
@require_login
def change_password():
    """修改密码"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'code': 401, 'msg': '未登录'})
        
        data = request.get_json()
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not new_password or not confirm_password:
            return jsonify({'code': 400, 'msg': '请填写完整信息'})
        
        if new_password != confirm_password:
            return jsonify({'code': 400, 'msg': '新密码与确认密码不一致'})
        
        if len(new_password) < 6:
            return jsonify({'code': 400, 'msg': '新密码长度不能少于6位'})
        
        # 更新密码
        success = db.update_user_password(user_id, UserManager.hash_password(new_password))
        if success:
            return jsonify({'code': 200, 'msg': '密码修改成功'})
        else:
            return jsonify({'code': 500, 'msg': '密码修改失败'})
            
    except Exception as e:
        logger.error(f"密码修改失败: {e}")
        return jsonify({'code': 500, 'msg': '密码修改失败'})


@app.route('/api/users/change-email', methods=['POST'])
@require_login
def change_email():
    """修改邮箱"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'code': 401, 'msg': '未登录'})
        
        data = request.get_json()
        new_email = data.get('new_email')
        
        if not new_email:
            return jsonify({'code': 400, 'msg': '请输入新邮箱地址'})
        
        # 验证邮箱格式
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, new_email):
            return jsonify({'code': 400, 'msg': '请输入有效的邮箱地址'})
        
        # 检查邮箱是否已被其他用户使用
        existing_user = db.get_user_by_email(new_email)
        if existing_user and existing_user['id'] != user_id:
            return jsonify({'code': 400, 'msg': '该邮箱已被其他用户使用'})
        
        # 获取当前用户信息用于生成token
        current_user = db.get_user_by_id(user_id)
        if not current_user:
            return jsonify({'code': 404, 'msg': '用户不存在'})
        
        # 生成包含base64邮箱和随机值的验证token
        import hashlib
        import time
        import base64
        
        # 生成随机值
        import secrets
        random_value = secrets.token_urlsafe(32)
        
        # 将邮箱地址进行base64编码作为token前半部分
        email_base64 = base64.urlsafe_b64encode(new_email.encode()).decode().rstrip('=')
        
        # 组合token: base64邮箱 + 随机值
        token = f"{email_base64}:{random_value}"
        
        # 将完整的token存储到verify_token字段
        db.set_user_verify_token(user_id, token)
        
        # 发送验证邮件
        settings = db.get_system_settings()
        if settings.get('resend_apikey') and settings.get('resend_email'):
            email_service = EmailService(
                api_key=settings.get('resend_apikey', ''),
                from_email=settings.get('resend_email', '')
            )
            
            # 生成验证链接，包含token
            verify_url = f"{request.host_url}verify-email-change?token={token}"
            
            # 获取用户名
            username = current_user.get('username', '用户')
            
            # 发送邮件
            if email_service.send_email_change_verification_email(new_email, username, verify_url):
                return jsonify({'code': 200, 'msg': '验证邮件已发送，请查收并点击验证链接完成邮箱修改'})
            else:
                return jsonify({'code': 500, 'msg': '验证邮件发送失败，请重试'})
        else:
            return jsonify({'code': 500, 'msg': '邮件服务未启用'})
            
    except Exception as e:
        logger.error(f"邮箱修改失败: {e}")
        return jsonify({'code': 500, 'msg': '邮箱修改失败，请重试'})


@app.route('/api/system/forgot-password', methods=['POST'])
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """找回密码"""
    try:
        data = request.get_json()
        email = data.get('email')

        # Turnstile验证码检查
        passed, err_resp = _check_turnstile_if_enabled(data)
        if not passed:
            return err_resp
        
        if not email:
            return jsonify({'code': 400, 'msg': '请输入邮箱地址'})
        
        # 检查是否启用了邮件验证
        system_settings = db.get_system_settings()
        if system_settings.get('email_verification_enabled') != '1':
            return jsonify({'code': 400, 'msg': '系统未启用邮件验证功能'})
        
        # 查找用户
        user_data = db.get_user_by_email(email)
        if not user_data:
            return jsonify({'code': 404, 'msg': '该邮箱未注册'})
        
        # 生成重置token
        reset_token = UserManager.generate_token()
        db.set_password_reset_token(user_data['id'], reset_token)
        
        # 发送重置邮件
        email_service = EmailService(
            api_key=system_settings.get('resend_apikey', ''),
            from_email=system_settings.get('resend_email', '')
        )
        reset_link = f"{request.host_url}reset-password?token={reset_token}"
        
        try:
            email_service.send_password_reset_email(email, user_data['username'], reset_link)
            return jsonify({'code': 200, 'msg': '密码重置邮件已发送，请查收'})
        except Exception as e:
            logger.error(f"发送重置邮件失败: {e}")
            return jsonify({'code': 500, 'msg': '发送重置邮件失败'})
        
    except Exception as e:
        logger.error(f"找回密码失败: {e}")
        return jsonify({'code': 500, 'msg': '找回密码失败'})



@app.route('/api/system/reset-password', methods=['POST'])
def reset_password():
    """重置密码"""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not token or not new_password or not confirm_password:
            return jsonify({'code': 400, 'msg': '请填写完整信息'})
        
        if new_password != confirm_password:
            return jsonify({'code': 400, 'msg': '密码与确认密码不一致'})
        
        if len(new_password) < 6:
            return jsonify({'code': 400, 'msg': '密码长度不能少于6位'})
        
        # 验证token
        user_data = db.get_user_by_reset_token(token)
        if not user_data:
            return jsonify({'code': 400, 'msg': '重置链接已过期或无效'})
        
        # 更新密码
        success = db.update_user_password(user_data['id'], UserManager.hash_password(new_password))
        if success:
            # 删除已使用的token
            db.delete_password_reset_token(token)
            return jsonify({'code': 200, 'msg': '密码重置成功'})
        else:
            return jsonify({'code': 500, 'msg': '密码重置失败'})
            
    except Exception as e:
        logger.error(f"密码重置失败: {e}")
        return jsonify({'code': 500, 'msg': '密码重置失败'})



# ============================================================================
# 系统管理API - /api/system/<option>
# ============================================================================

# 引擎类型 ########################################################################
@app.route('/api/system/engine', methods=['GET'])
@require_auth
def api_get_engine_types():
    """获取支持的主机引擎类型"""
    return rest_manager.get_engine_types()


# 保存配置 ########################################################################
@app.route('/api/system/saving', methods=['POST'])
@require_auth
def api_save_system():
    """保存系统配置"""
    return rest_manager.save_system()


# 保存配置（别名） ##################################################################
@app.route('/api/system/save', methods=['POST'])
@require_auth
def api_save_system_alias():
    """保存系统配置（别名路由）"""
    return rest_manager.save_system()


# 加载配置 ########################################################################
@app.route('/api/system/loader', methods=['POST'])
@require_auth
def api_load_system():
    """加载系统配置"""
    return rest_manager.load_system()


# 加载配置（别名） ##################################################################
@app.route('/api/system/load', methods=['POST'])
@require_auth
def api_load_system_alias():
    """加载系统配置（别名路由）"""
    return rest_manager.load_system()


# 系统统计 ########################################################################
@app.route('/api/system/statis', methods=['GET'])
@require_auth
def api_get_system_stats():
    """获取系统统计信息"""
    return rest_manager.get_system_stats()


# 获取当前Token ####################################################################
@app.route('/api/token/current', methods=['GET'])
@require_auth
def api_get_current_token():
    """获取当前的API Token"""
    try:
        return api_response_wrapper(200, '获取Token成功', {'token': hs_manage.bearer})
    except Exception as e:
        logger.error(f"获取Token失败: {e}")
        return api_response_wrapper(500, f'获取Token失败: {str(e)}')


# 设置Token ########################################################################
@app.route('/api/token/set', methods=['POST'])
@require_auth
def api_set_token():
    """设置新的API Token"""
    try:
        data = request.get_json()
        new_token = data.get('token', '')
        
        if not new_token:
            return api_response_wrapper(400, 'Token不能为空')
        
        # 设置新的Token
        hs_manage.set_pass(new_token)
        
        return api_response_wrapper(200, 'Token设置成功', {'token': hs_manage.bearer})
    except Exception as e:
        logger.error(f"设置Token失败: {e}")
        return api_response_wrapper(500, f'设置Token失败: {str(e)}')


# 重置Token ########################################################################
@app.route('/api/token/reset', methods=['POST'])
@require_auth
def api_reset_token():
    """重置API Token（生成新的随机Token）"""
    try:
        # 重置Token（不传参数会自动生成新Token）
        new_token = hs_manage.set_pass()
        
        return api_response_wrapper(200, 'Token重置成功', {'token': new_token})
    except Exception as e:
        logger.error(f"重置Token失败: {e}")
        return api_response_wrapper(500, f'重置Token失败: {str(e)}')


# 获取系统统计信息 ##################################################################
@app.route('/api/system/stats', methods=['GET'])
@require_auth
def api_get_stats():
    """获取系统统计信息（主机数量、虚拟机数量）"""
    try:
        host_count = len(hs_manage.engine)
        vm_count = sum(len(server.vm_saving) for server in hs_manage.engine.values())
        
        return api_response_wrapper(200, '获取统计信息成功', {
            'host_count': host_count,
            'vm_count': vm_count
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return api_response_wrapper(500, f'获取统计信息失败: {str(e)}')


# 获取日志 ########################################################################
@app.route('/api/system/logger/detail', methods=['GET'])
@require_auth
def api_get_logs():
    """获取日志记录"""
    return rest_manager.get_logs()


# 清空日志 ########################################################################
@app.route('/api/system/logger/clear', methods=['POST'])
@require_auth
def api_clear_logs():
    """清空日志记录"""
    return rest_manager.clear_logs()


# 获取任务 ########################################################################
@app.route('/api/system/tasker', methods=['GET'])
@require_auth
def api_get_tasks():
    """获取任务记录"""
    return rest_manager.get_tasks()


# ============================================================================
# 异步任务管理API - /api/system/async_task
# ============================================================================

# 获取异步任务列表 ##################################################################
@app.route('/api/system/async_task/list', methods=['GET'])
@require_auth
def api_get_async_task_list():
    """获取异步任务列表（支持过滤和分页）"""
    return rest_manager.get_async_task_list()


# 获取异步任务统计 ##################################################################
@app.route('/api/system/async_task/stats', methods=['GET'])
@require_auth
def api_get_async_task_stats():
    """获取异步任务统计信息"""
    return rest_manager.get_async_task_stats()


# 查询单个异步任务状态 ##############################################################
@app.route('/api/system/async_task/<task_id>', methods=['GET'])
@require_auth
def api_get_async_task(task_id):
    """查询单个异步任务状态"""
    return rest_manager.get_async_task(task_id)


# 强行结束异步任务 ##################################################################
@app.route('/api/system/async_task/<task_id>/stop', methods=['POST'])
@require_auth
def api_stop_async_task(task_id):
    """强行结束异步任务"""
    return rest_manager.stop_async_task(task_id)


# 重新运行异步任务 ##################################################################
@app.route('/api/system/async_task/<task_id>/retry', methods=['POST'])
@require_auth
def api_retry_async_task(task_id):
    """重新运行已停止的异步任务"""
    return rest_manager.retry_async_task(task_id)


# ============================================================================
# 主机管理API - /api/server/<option>/<key?>
# ============================================================================

# 主机列表 ########################################################################
@app.route('/api/server/detail', methods=['GET'])
@require_auth
def api_get_hosts():
    """获取主机列表（管理员看所有，普通用户看assigned_hosts）"""
    # 获取当前用户信息（Bearer Token或Session）
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    
    # Token登录或管理员返回所有主机
    if current_user.get('is_token_login') or current_user.get('is_admin'):
        return rest_manager.get_hosts()
    
    # 普通用户只返回assigned_hosts中的主机
    assigned_hosts = current_user.get('assigned_hosts', [])
    all_hosts_result = rest_manager.get_hosts()
    
    # 解析返回结果
    if hasattr(all_hosts_result, 'json'):
        all_hosts_data = all_hosts_result.json
    else:
        all_hosts_data = all_hosts_result
    
    if all_hosts_data.get('code') == 200:
        all_hosts = all_hosts_data.get('data', {})
        filtered_hosts = {k: v for k, v in all_hosts.items() if k in assigned_hosts}
        return api_response_wrapper(200, '成功', filtered_hosts)
    
    return all_hosts_result


# 主机详情 ########################################################################
@app.route('/api/server/detail/<hs_name>', methods=['GET'])
@require_admin
def api_get_host(hs_name):
    """获取单个主机详情"""
    return rest_manager.get_host(hs_name)


# 获取主机操作系统镜像列表（普通用户可访问）########################################
@app.route('/api/client/os-images/<hs_name>', methods=['GET'])
@require_auth
def api_get_os_images(hs_name):
    """获取主机的操作系统镜像列表（普通用户可访问）"""
    # 获取当前用户信息
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    
    # 检查主机访问权限
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    
    return rest_manager.get_os_images(hs_name)


# 获取主机GPU设备列表（普通用户可访问）############################################
@app.route('/api/client/gpu-list/<hs_name>', methods=['GET'])
@require_auth
def api_get_gpu_list(hs_name):
    """获取主机的GPU设备列表（普通用户可访问）"""
    # 获取当前用户信息
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    
    # 检查主机访问权限
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    
    return rest_manager.get_gpu_list(hs_name)


# 获取主机PCI设备列表 ##############################################################
@app.route('/api/client/pci-list/<hs_name>', methods=['GET'])
@require_auth
def api_get_pci_list(hs_name):
    """获取主机可直通PCI设备列表"""
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    return rest_manager.get_pci_list(hs_name)


# PCI设备直通操作 ##################################################################
@app.route('/api/client/pci/setup/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_setup_pci(hs_name, vm_uuid):
    """PCI设备直通操作（需要关机）"""
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    # 检查修改权限
    has_perm, perm_msg = check_vm_permission('modify', current_user)
    if not has_perm:
        return api_response_wrapper(403, perm_msg or '没有PCI直通操作权限')
    return rest_manager.setup_pci(hs_name, vm_uuid)


# 获取主机USB设备列表 ##############################################################
@app.route('/api/client/usb-list/<hs_name>', methods=['GET'])
@require_auth
def api_get_usb_list(hs_name):
    """获取主机可用USB设备列表"""
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    return rest_manager.get_usb_list(hs_name)


# USB设备直通操作 ##################################################################
@app.route('/api/client/usb/setup/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_setup_usb(hs_name, vm_uuid):
    """USB设备直通操作（无需关机）"""
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    # 检查修改权限
    has_perm, perm_msg = check_vm_permission('modify', current_user)
    if not has_perm:
        return api_response_wrapper(403, perm_msg or '没有USB直通操作权限')
    return rest_manager.setup_usb(hs_name, vm_uuid)


# 获取虚拟机启动项列表 ##############################################################
@app.route('/api/client/efi-list/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_efi_list(hs_name, vm_uuid):
    """获取虚拟机启动项列表"""
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    # efi_edits细粒度权限在RestManager内部检查
    return rest_manager.get_efi_list(hs_name, vm_uuid)


# 设置虚拟机启动项顺序 ##############################################################
@app.route('/api/client/efi/setup/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_setup_efi(hs_name, vm_uuid):
    """调整虚拟机启动项顺序"""
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    # efi_edits细粒度权限在RestManager内部检查
    return rest_manager.setup_efi(hs_name, vm_uuid)


# 添加主机 ########################################################################
@app.route('/api/server/create', methods=['POST'])
@require_admin
def api_add_host():
    """添加主机"""
    return rest_manager.add_host()


# 修改主机 ########################################################################
@app.route('/api/server/update/<hs_name>', methods=['PUT'])
@require_admin
def api_update_host(hs_name):
    """修改主机配置"""
    return rest_manager.update_host(hs_name)


# 删除主机 ########################################################################
@app.route('/api/server/delete/<hs_name>', methods=['DELETE'])
@require_admin
def api_delete_host(hs_name):
    """删除主机"""
    return rest_manager.delete_host(hs_name)


# 电源控制 ########################################################################
@app.route('/api/server/powers/<hs_name>', methods=['POST'])
@require_admin
def api_host_enable(hs_name):
    """主机启用控制（启用/禁用）"""
    return rest_manager.host_enable(hs_name)


# 主机状态 ########################################################################
@app.route('/api/server/status/<hs_name>', methods=['GET'])
@require_auth
def api_get_host_status(hs_name):
    """获取主机状态"""
    return rest_manager.get_host_status(hs_name)


# 获取套餐列表 ####################################################################
@app.route('/api/server/plan/<hs_name>', methods=['GET'])
@require_auth
def api_get_server_plan(hs_name):
    """获取主机套餐列表（已认证用户可访问，用于创建虚拟机时选择套餐）"""
    return rest_manager.get_server_plan(hs_name)


# 设置套餐（新增/更新） ############################################################
@app.route('/api/server/plan/<hs_name>', methods=['POST'])
@require_admin
def api_set_server_plan(hs_name):
    """新增或更新主机套餐"""
    return rest_manager.set_server_plan(hs_name)


# 删除套餐 ########################################################################
@app.route('/api/server/plan/<hs_name>/<plan_name>', methods=['DELETE'])
@require_admin
def api_del_server_plan(hs_name, plan_name):
    """删除主机套餐"""
    return rest_manager.del_server_plan(hs_name, plan_name)


# ============================================================================
# 财务系统对接API - /api/server/areas | /api/server/plans | /api/server/ports
# ============================================================================

# 获取区域列表（财务系统 ListAreas 接口）##########################################
@app.route('/api/server/areas', methods=['GET'])
@require_auth
def api_get_server_areas():
    """获取所有主机的区域列表（去重），用于财务系统 ListAreas 对接"""
    return rest_manager.get_areas()


# 获取套餐规格列表（财务系统 ListPackages 接口）####################################
@app.route('/api/server/plans/<hs_name>', methods=['GET'])
@require_auth
def api_get_server_plans(hs_name):
    """获取指定主机的套餐规格列表，用于财务系统 ListPackages 对接"""
    return rest_manager.get_plans(hs_name)


# 获取可分配端口列表（财务系统 FindPortCandidates 接口）############################
@app.route('/api/server/ports/<hs_name>', methods=['GET'])
@require_auth
def api_get_available_ports(hs_name):
    """获取指定主机的可分配端口列表，用于财务系统 FindPortCandidates 对接"""
    return rest_manager.get_available_ports(hs_name)


# ============================================================================
# 虚拟机管理API - /api/client/<option>/<key?>
# ============================================================================

# 虚拟机列表 ########################################################################
@app.route('/api/client/detail/<hs_name>', methods=['GET'])
@require_auth
def api_get_vms(hs_name):
    """获取主机下所有虚拟机"""
    # 检查主机访问权限
    current_user = get_current_user()
    if not current_user:
        return api_response_wrapper(401, '未授权访问')
    
    # Token登录或管理员有所有权限
    if current_user.get('is_token_login') or current_user.get('is_admin'):
        return rest_manager.get_vms(hs_name)
    
    # 检查主机访问权限
    if not check_host_access(hs_name, current_user):
        return api_response_wrapper(403, '没有访问该主机的权限')
    
    return rest_manager.get_vms(hs_name)


# 虚拟机详情 ########################################################################
@app.route('/api/client/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm(hs_name, vm_uuid):
    """获取单个虚拟机详情"""
    return rest_manager.get_vm(hs_name, vm_uuid)


# 创建虚拟机 ########################################################################
@app.route('/api/client/create/<hs_name>', methods=['POST'])
@require_auth
def api_create_vm(hs_name):
    """创建虚拟机"""
    return rest_manager.create_vm(hs_name)


# 修改虚拟机 ########################################################################
@app.route('/api/client/update/<hs_name>/<vm_uuid>', methods=['PUT'])
@require_auth
def api_update_vm(hs_name, vm_uuid):
    """修改虚拟机配置"""
    return rest_manager.update_vm(hs_name, vm_uuid)


# 删除虚拟机 ########################################################################
@app.route('/api/client/delete/<hs_name>/<vm_uuid>', methods=['DELETE'])
@require_auth
def api_delete_vm(hs_name, vm_uuid):
    """删除虚拟机"""
    return rest_manager.delete_vm(hs_name, vm_uuid)


# 虚拟机所有者管理 ########################################################################
@app.route('/api/client/owners/<hs_name>/<vm_uuid>', methods=['GET'])
@app.route('/api/client/owners/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_owners(hs_name, vm_uuid):
    """获取虚拟机所有者列表"""
    return rest_manager.get_vm_owners(hs_name, vm_uuid)


@app.route('/api/client/owners/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_add_vm_owner(hs_name, vm_uuid):
    """添加虚拟机所有者"""
    return rest_manager.add_vm_owner(hs_name, vm_uuid)


@app.route('/api/client/owners/<hs_name>/<vm_uuid>', methods=['DELETE'])
@require_auth
def api_remove_vm_owner(hs_name, vm_uuid):
    """删除虚拟机所有者"""
    return rest_manager.remove_vm_owner(hs_name, vm_uuid)


@app.route('/api/client/owners/<hs_name>/<vm_uuid>/permission', methods=['PUT'])
@require_auth
def api_update_vm_owner_permission(hs_name, vm_uuid):
    """更新虚拟机所有者权限"""
    return rest_manager.update_vm_owner_permission(hs_name, vm_uuid)


@app.route('/api/client/owners/<hs_name>/<vm_uuid>/transfer', methods=['POST'])
@require_auth
def api_transfer_vm_ownership(hs_name, vm_uuid):
    """移交虚拟机所有权"""
    return rest_manager.transfer_vm_ownership(hs_name, vm_uuid)


# 电源控制 ########################################################################
@app.route('/api/client/powers/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_vm_power(hs_name, vm_uuid):
    """虚拟机电源控制"""
    return rest_manager.vm_power(hs_name, vm_uuid)


# 重装系统 ########################################################################
@app.route('/api/client/reinstall/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_vm_reinstall(hs_name, vm_uuid):
    """虚拟机重装系统"""
    return rest_manager.vm_reinstall(hs_name, vm_uuid)


# VNC控制台 ########################################################################
@app.route('/api/client/remote/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_vm_console(hs_name, vm_uuid):
    """获取虚拟机VNC控制台URL"""
    return rest_manager.vm_console(hs_name, vm_uuid)


# 临时凭据（财务系统插件使用）########################################################
@app.route('/api/client/temptoken/<hs_name>/<vm_uuid>', methods=['GET'])
def api_get_temp_token(hs_name, vm_uuid):
    """生成临时访问凭据，供财务系统插件跳转登录（需Bearer Token，有效期5分钟）"""
    return rest_manager.get_temp_token(hs_name, vm_uuid)


# 临时凭据登录跳转 ##################################################################
@app.route('/api/client/templogin', methods=['GET', 'POST'])
def api_temp_token_login():
    """使用临时凭据登录并跳转到虚拟机管理控制台"""
    return rest_manager.temp_token_login()


# 虚拟机截图 ########################################################################
@app.route('/api/client/screenshot/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_vm_screenshot(hs_name, vm_uuid):
    """获取虚拟机截图"""
    return rest_manager.vm_screenshot(hs_name, vm_uuid)


# 修改密码 ########################################################################
@app.route('/api/client/password/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_vm_password(hs_name, vm_uuid):
    """修改虚拟机密码"""
    return rest_manager.vm_password(hs_name, vm_uuid)

@app.route('/api/client/reset/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_vm_reset_password(hs_name, vm_uuid):
    """修改虚拟机密码（兼容旧路由）"""
    return rest_manager.vm_password(hs_name, vm_uuid)


# 虚拟机状态 ########################################################################
@app.route('/api/client/status/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_status(hs_name, vm_uuid):
    """获取虚拟机状态"""
    return rest_manager.get_vm_status(hs_name, vm_uuid)


# 扫描虚拟机 ########################################################################
@app.route('/api/client/scaner/<hs_name>', methods=['POST'])
@require_auth
def api_scan_vms(hs_name):
    """扫描主机上的虚拟机"""
    return rest_manager.scan_vms(hs_name)


# 上报状态 ########################################################################
@app.route('/api/client/upload', methods=['POST'])
def api_vm_upload():
    """虚拟机上报状态数据（无需认证）"""
    return rest_manager.vm_upload()


# 命令执行结果回传 ########################################################################
@app.route('/api/client/cmd_result', methods=['POST'])
def api_vm_cmd_result():
    """虚拟机命令执行结果回传（无需认证，由CloudInit回调）"""
    return rest_manager.vm_cmd_result()


# 下发命令到虚拟机 ########################################################################
@app.route('/api/client/cmd_send/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_vm_cmd_send(hs_name, vm_uuid):
    """下发命令到虚拟机（前端调用，等待CloudInit握手时下发）"""
    return rest_manager.vm_cmd_send(hs_name, vm_uuid)


# 获取命令执行结果 ########################################################################
@app.route('/api/client/cmd_status/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_vm_cmd_status(hs_name, vm_uuid):
    """获取虚拟机最近一次命令执行结果"""
    return rest_manager.vm_cmd_status(hs_name, vm_uuid)


# ============================================================================
# 虚拟机网络配置API - NAT端口转发
# ============================================================================

# 获取NAT规则 ########################################################################
@app.route('/api/client/natget/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_nat_rules(hs_name, vm_uuid):
    """获取虚拟机NAT端口转发规则"""
    return rest_manager.get_vm_nat_rules(hs_name, vm_uuid)


# 添加NAT规则 ########################################################################
@app.route('/api/client/natadd/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_add_vm_nat_rule(hs_name, vm_uuid):
    """添加虚拟机NAT端口转发规则"""
    return rest_manager.add_vm_nat_rule(hs_name, vm_uuid)


# 删除NAT规则 ########################################################################
@app.route('/api/client/natdel/<hs_name>/<vm_uuid>/<int:rule_index>', methods=['DELETE'])
@require_auth
def api_delete_vm_nat_rule(hs_name, vm_uuid, rule_index):
    """删除虚拟机NAT端口转发规则"""
    return rest_manager.delete_vm_nat_rule(hs_name, vm_uuid, rule_index)


# ============================================================================
# 虚拟机网络配置API - IP地址管理
# ============================================================================

# 获取IP列表 ########################################################################
@app.route('/api/client/ipaddr/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_ip_addresses(hs_name, vm_uuid):
    """获取虚拟机IP地址列表"""
    return rest_manager.get_vm_ip_addresses(hs_name, vm_uuid)


# 添加IP地址 ########################################################################
@app.route('/api/client/ipaddr/create/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_add_vm_ip_address(hs_name, vm_uuid):
    """添加虚拟机IP地址"""
    return rest_manager.add_vm_ip_address(hs_name, vm_uuid)


# 删除IP地址 ########################################################################
@app.route('/api/client/ipaddr/delete/<hs_name>/<vm_uuid>/<int:ip_index>', methods=['DELETE'])
@require_auth
def api_delete_vm_ip_address(hs_name, vm_uuid, ip_index):
    """删除虚拟机IP地址"""
    return rest_manager.delete_vm_ip_address(hs_name, vm_uuid, ip_index)


# RESTful风格的IP地址管理API ########################################################################
@app.route('/api/hosts/<hs_name>/vms/<vm_uuid>/ip_addresses', methods=['GET'])
@require_auth
def api_get_vm_ip_addresses_rest(hs_name, vm_uuid):
    """获取虚拟机网卡列表（RESTful风格）"""
    return rest_manager.get_vm_ip_addresses(hs_name, vm_uuid)


@app.route('/api/hosts/<hs_name>/vms/<vm_uuid>/ip_addresses', methods=['POST'])
@require_auth
def api_add_vm_ip_address_rest(hs_name, vm_uuid):
    """添加虚拟机网卡（RESTful风格）"""
    return rest_manager.add_vm_ip_address(hs_name, vm_uuid)


@app.route('/api/hosts/<hs_name>/vms/<vm_uuid>/ip_addresses/<nic_name>', methods=['PUT'])
@require_auth
def api_update_vm_ip_address_rest(hs_name, vm_uuid, nic_name):
    """修改虚拟机网卡配置（RESTful风格）"""
    return rest_manager.update_vm_ip_address(hs_name, vm_uuid, nic_name)


@app.route('/api/hosts/<hs_name>/vms/<vm_uuid>/ip_addresses/<nic_name>', methods=['DELETE'])
@require_auth
def api_delete_vm_ip_address_rest(hs_name, vm_uuid, nic_name):
    """删除虚拟机网卡（RESTful风格）"""
    return rest_manager.delete_vm_ip_address(hs_name, vm_uuid, nic_name)


# ============================================================================
# 虚拟机网络配置API - 反向代理管理
# ============================================================================

# 获取所有代理配置 ####################################################################
@app.route('/api/client/proxys/list', methods=['GET'])
@require_auth
def api_list_all_user_proxys():
    """获取当前用户的所有反向代理配置列表"""
    return rest_manager.list_all_user_proxys()


# 获取代理配置 ########################################################################
@app.route('/api/client/proxys/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_proxy_configs(hs_name, vm_uuid):
    """获取虚拟机反向代理配置列表"""
    return rest_manager.get_vm_proxy_configs(hs_name, vm_uuid)


# 添加代理配置 ########################################################################
@app.route('/api/client/proxys/create/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_add_vm_proxy_config(hs_name, vm_uuid):
    """添加虚拟机反向代理配置"""
    return rest_manager.add_vm_proxy_config(hs_name, vm_uuid)


# 删除代理配置 ########################################################################
@app.route('/api/client/proxys/delete/<hs_name>/<vm_uuid>/<int:proxy_index>', methods=['DELETE'])
@require_auth
def api_delete_vm_proxy_config(hs_name, vm_uuid, proxy_index):
    """删除虚拟机反向代理配置"""
    return rest_manager.delete_vm_proxy_config(hs_name, vm_uuid, proxy_index)


# ============================================================================
# 管理员级别 - Web反向代理管理API
# ============================================================================

# 获取所有反向代理配置 ################################################################
@app.route('/api/admin/proxys/list', methods=['GET'])
@require_admin
def api_admin_list_all_proxys():
    """管理员获取所有反向代理配置列表"""
    return rest_manager.admin_list_all_proxys()


# 获取指定主机的所有反向代理 ##########################################################
@app.route('/api/admin/proxys/list/<hs_name>', methods=['GET'])
@require_admin
def api_admin_list_host_proxys(hs_name):
    """管理员获取指定主机的所有反向代理配置"""
    return rest_manager.admin_list_host_proxys(hs_name)


# 获取指定虚拟机的反向代理 ############################################################
@app.route('/api/admin/proxys/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_admin
def api_admin_get_vm_proxys(hs_name, vm_uuid):
    """管理员获取指定虚拟机的反向代理配置"""
    return rest_manager.admin_get_vm_proxys(hs_name, vm_uuid)


# 添加反向代理配置 ####################################################################
@app.route('/api/admin/proxys/create/<hs_name>/<vm_uuid>', methods=['POST'])
@require_admin
def api_admin_add_proxy(hs_name, vm_uuid):
    """管理员添加反向代理配置"""
    return rest_manager.admin_add_proxy(hs_name, vm_uuid)


# 更新反向代理配置 ####################################################################
@app.route('/api/admin/proxys/update/<hs_name>/<vm_uuid>/<int:proxy_index>', methods=['PUT'])
@require_admin
def api_admin_update_proxy(hs_name, vm_uuid, proxy_index):
    """管理员更新反向代理配置"""
    return rest_manager.admin_update_proxy(hs_name, vm_uuid, proxy_index)


# 删除反向代理配置 ####################################################################
@app.route('/api/admin/proxys/delete/<hs_name>/<vm_uuid>/<int:proxy_index>', methods=['DELETE'])
@require_admin
def api_admin_delete_proxy(hs_name, vm_uuid, proxy_index):
    """管理员删除反向代理配置"""
    return rest_manager.admin_delete_proxy(hs_name, vm_uuid, proxy_index)


# ============================================================================
# 数据盘管理API
# ============================================================================
@app.route('/api/client/hdd/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_hdds(hs_name, vm_uuid):
    """获取虚拟机数据盘列表"""
    return rest_manager.get_vm_hdds(hs_name, vm_uuid)

@app.route('/api/client/hdd/mount/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_mount_vm_hdd(hs_name, vm_uuid):
    """挂载数据盘到虚拟机"""
    return rest_manager.mount_vm_hdd(hs_name, vm_uuid)


@app.route('/api/client/hdd/unmount/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_unmount_vm_hdd(hs_name, vm_uuid):
    """卸载虚拟机数据盘"""
    return rest_manager.unmount_vm_hdd(hs_name, vm_uuid)


@app.route('/api/client/hdd/transfer/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_transfer_vm_hdd(hs_name, vm_uuid):
    """移交数据盘所有权"""
    return rest_manager.transfer_vm_hdd(hs_name, vm_uuid)


@app.route('/api/client/hdd/delete/<hs_name>/<vm_uuid>', methods=['DELETE'])
@require_auth
def api_delete_vm_hdd(hs_name, vm_uuid):
    """删除虚拟机数据盘"""
    return rest_manager.delete_vm_hdd(hs_name, vm_uuid)


# ============================================================================
# ISO管理API
# ============================================================================
@app.route('/api/client/isos/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_isos(hs_name, vm_uuid):
    """获取虚拟机ISO挂载列表"""
    return rest_manager.get_vm_isos(hs_name, vm_uuid)

@app.route('/api/client/iso/mount/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_mount_vm_iso(hs_name, vm_uuid):
    """挂载ISO镜像到虚拟机"""
    return rest_manager.mount_vm_iso(hs_name, vm_uuid)


@app.route('/api/client/iso/unmount/<hs_name>/<vm_uuid>/<iso_name>', methods=['DELETE'])
@require_auth
def api_unmount_vm_iso(hs_name, vm_uuid, iso_name):
    """卸载虚拟机ISO镜像"""
    return rest_manager.unmount_vm_iso(hs_name, vm_uuid, iso_name)


# ============================================================================
# USB管理API
# ============================================================================
@app.route('/api/client/usb/mount/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_mount_vm_usb(hs_name, vm_uuid):
    """挂载USB设备到虚拟机"""
    return rest_manager.mount_vm_usb(hs_name, vm_uuid)


@app.route('/api/client/usb/delete/<hs_name>/<vm_uuid>/<usb_key>', methods=['DELETE'])
@require_auth
def api_unmount_vm_usb(hs_name, vm_uuid, usb_key):
    """卸载虚拟机USB设备"""
    return rest_manager.unmount_vm_usb(hs_name, vm_uuid, usb_key)


# ============================================================================
# 备份管理API
# ============================================================================
@app.route('/api/client/backup/detail/<hs_name>/<vm_uuid>', methods=['GET'])
@require_auth
def api_get_vm_backups(hs_name, vm_uuid):
    """获取虚拟机备份列表"""
    return rest_manager.get_vm_backups(hs_name, vm_uuid)

@app.route('/api/client/backup/create/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_create_vm_backup(hs_name, vm_uuid):
    """创建虚拟机备份"""
    return rest_manager.create_vm_backup(hs_name, vm_uuid)


@app.route('/api/client/backup/restore/<hs_name>/<vm_uuid>', methods=['POST'])
@require_auth
def api_restore_vm_backup(hs_name, vm_uuid):
    """还原虚拟机备份"""
    return rest_manager.restore_vm_backup(hs_name, vm_uuid)


@app.route('/api/client/backup/delete/<hs_name>/<vm_uuid>', methods=['DELETE'])
@require_auth
def api_delete_vm_backup(hs_name, vm_uuid):
    """删除虚拟机备份"""
    return rest_manager.delete_vm_backup(hs_name, vm_uuid)


@app.route('/api/server/backup/scan/<hs_name>', methods=['POST'])
@require_auth
def api_scan_backups(hs_name):
    """扫描主机备份文件"""
    return rest_manager.scan_backups(hs_name)


# ============================================================================
# 用户管理API - /api/users
# ============================================================================

@app.route('/api/system/recalculate-quotas', methods=['POST'])
@require_auth
def api_recalculate_quotas():
    """手动触发用户资源配额重新计算"""
    try:
        hs_manage.recalculate_user_quotas()
        return api_response_wrapper(200, '资源配额重新计算完成')
    except Exception as e:
        logger.error(f"手动重新计算资源配额失败: {e}")
        return api_response_wrapper(500, f'重新计算失败: {str(e)}')


@app.route('/api/users/current', methods=['GET'])
@require_auth
def api_get_current_user():
    """获取当前用户信息"""
    try:
        # 检查Bearer Token（Token登录视为管理员）
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            # 临时token（财务系统插件跳转）
            if token.startswith('temp:'):
                user_data = rest_manager.get_temp_user_data(token[5:])
                if user_data:
                    return api_response_wrapper(200, '获取成功', UserManager.build_user_response(user_data))
                return api_response_wrapper(401, '临时凭据无效或已过期')
            if token == hs_manage.bearer:
                return api_response_wrapper(200, '获取成功',
                    UserManager.build_admin_response(assigned_hosts=list(hs_manage.engine.keys())))

        # 检查Session登录
        if session.get('logged_in'):
            # 临时Token登录（财务系统插件跳转），返回虚拟用户信息（受限权限）
            if session.get('temp_login'):
                return api_response_wrapper(200, '获取成功',
                    UserManager.build_temp_user_response(
                        username=session.get('username', ''),
                        hs_name=session.get('temp_hs_name', ''),
                        vm_uuid=session.get('temp_vm_uuid', '')
                    ))
            user_id = session.get('user_id')
            user_data = db.get_user_by_id(user_id)
            if user_data:
                # 计算IP使用量
                if rest_manager and hs_manage:
                    ip_usage = rest_manager._calculate_user_ip_usage(user_data.get('username', ''))
                    
                    # 添加IP使用量信息到用户数据
                    user_data['used_nat_ips'] = ip_usage['used_nat_ips']
                    user_data['used_pub_ips'] = ip_usage['used_pub_ips']
                
                # 移除敏感信息
                user_data.pop('password', None)
                user_data.pop('verify_token', None)
                # 解析JSON字段
                if isinstance(user_data.get('assigned_hosts'), str):
                    try:
                        user_data['assigned_hosts'] = json.loads(user_data['assigned_hosts'])
                    except Exception as e:
                        logger.warning(f"解析用户assigned_hosts失败: {e}")
                        user_data['assigned_hosts'] = []
                
                # 过滤掉未启用的主机（所有用户均生效）
                if hs_manage:
                    enabled_hosts = []
                    for hs_name in user_data.get('assigned_hosts', []):
                        server = hs_manage.get_host(hs_name)
                        if server:
                            enable_host = getattr(server.hs_config, 'enable_host', True) if server.hs_config else True
                            if enable_host:
                                enabled_hosts.append(hs_name)
                    user_data['assigned_hosts'] = enabled_hosts
                
                return api_response_wrapper(200, '获取成功', user_data)
        
        return api_response_wrapper(401, '未授权访问')
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {e}")
        return api_response_wrapper(500, f'获取失败: {str(e)}')


@app.route('/api/users', methods=['GET'])
@require_admin
def api_get_users():
    """获取所有用户列表"""
    try:
        users = db.get_all_users()
        # 移除敏感信息
        for user in users:
            user.pop('password', None)
            user.pop('verify_token', None)
            # 解析JSON字段
            if isinstance(user.get('assigned_hosts'), str):
                try:
                    user['assigned_hosts'] = json.loads(user['assigned_hosts'])
                except Exception as e:
                    logger.warning(f"解析用户assigned_hosts失败: {e}")
                    user['assigned_hosts'] = []
        return api_response_wrapper(200, '获取成功', users)
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return api_response_wrapper(500, f'获取失败: {str(e)}')


@app.route('/api/users', methods=['POST'])
@require_admin
def api_create_user():
    """创建新用户"""
    try:
        data = request.get_json()
        if not data:
            return api_response_wrapper(400, '无效的请求数据')
        
        # 获取必需字段
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # 验证必需字段
        if not username or not email or not password:
            return api_response_wrapper(400, '用户名、邮箱和密码不能为空')
        
        if len(username) < 3 or len(username) > 20:
            return api_response_wrapper(400, '用户名长度必须在3-20个字符之间')
        
        # 禁止使用admin作为用户名
        if username.lower() == 'admin':
            return api_response_wrapper(400, '不能使用admin作为用户名')
        
        if len(password) < 6:
            return api_response_wrapper(400, '密码长度至少6个字符')
        
        # 检查用户名是否已存在
        if db.get_user_by_username(username):
            return api_response_wrapper(400, '用户名已存在')
        
        # 检查邮箱是否已存在
        if db.get_user_by_email(email):
            return api_response_wrapper(400, '邮箱已被注册')
        
        # 加密密码
        hashed_password = UserManager.hash_password(password)
        
        # 创建用户（只传入基本字段）
        user_id = db.create_user(username, hashed_password, email)
        if not user_id:
            return api_response_wrapper(500, '创建用户失败，请重试')
        
        # 准备要更新的其他字段
        update_data = {
            'is_admin': data.get('is_admin', 0),
            'is_active': data.get('is_active', 1),
            'can_create_vm': data.get('can_create_vm', 0),
            'can_modify_vm': data.get('can_modify_vm', 0),
            'can_delete_vm': data.get('can_delete_vm', 0),
            'can_free_config': data.get('can_free_config', 0),
            'quota_cpu': data.get('quota_cpu', 0),
            'quota_ram': data.get('quota_ram', 0),
            'quota_ssd': data.get('quota_ssd', 0),
            'quota_gpu': data.get('quota_gpu', 0),
            'quota_nat_ports': data.get('quota_nat_ports', 0),
            'quota_web_proxy': data.get('quota_web_proxy', 0),
            'quota_bandwidth_up': data.get('quota_bandwidth_up', 0),
            'quota_bandwidth_down': data.get('quota_bandwidth_down', 0),
            'quota_traffic': data.get('quota_traffic', 0),
            'assigned_hosts': data.get('assigned_hosts', [])
        }
        
        # 更新用户的权限和配额信息
        success = db.update_user(user_id, **update_data)
        if not success:
            # 如果更新失败，删除已创建的用户
            db.delete_user(user_id)
            return api_response_wrapper(500, '更新用户权限和配额失败')
        
        # 直接验证邮箱（管理员创建的用户不需要邮箱验证）
        db.verify_user_email(user_id)
        
        return api_response_wrapper(200, '用户创建成功', {'user_id': user_id})
        
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        return api_response_wrapper(500, '创建失败，请稍后重试')


@app.route('/api/users/<int:user_id>', methods=['GET'])
@require_admin
def api_get_user(user_id):
    """获取单个用户信息"""
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            return api_response_wrapper(404, '用户不存在')
        
        # 移除敏感信息
        user.pop('password', None)
        user.pop('verify_token', None)
        
        # 解析JSON字段
        if isinstance(user.get('assigned_hosts'), str):
            try:
                user['assigned_hosts'] = json.loads(user['assigned_hosts'])
            except Exception as e:
                logger.warning(f"解析用户assigned_hosts失败: {e}")
                user['assigned_hosts'] = []
        
        return api_response_wrapper(200, '获取成功', user)
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        traceback.print_exc()
        return api_response_wrapper(500, f'获取失败: {str(e)}')


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_admin
def api_update_user(user_id):
    """更新用户信息"""
    try:
        data = request.get_json()
        if not data:
            return api_response_wrapper(400, '无效的请求数据')
        
        # 处理密码字段：为空则不更新，非空则hash后再存储
        if 'password' in data:
            if data['password']:
                data['password'] = UserManager.hash_password(data['password'])
            else:
                del data['password']
        
        # 更新用户
        success = db.update_user(user_id, **data)
        if success:
            return api_response_wrapper(200, '更新成功')
        else:
            return api_response_wrapper(500, '更新失败')
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        return api_response_wrapper(500, f'更新失败: {str(e)}')


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_admin
def api_delete_user(user_id):
    """删除用户"""
    try:
        success = db.delete_user(user_id)
        if success:
            return api_response_wrapper(200, '删除成功')
        else:
            return api_response_wrapper(500, '删除失败')
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        return api_response_wrapper(500, f'删除失败: {str(e)}')


# ============================================================================
# 系统设置API
# ============================================================================

@app.route('/api/system/test-email', methods=['POST'])
@require_admin
def test_email():
    """测试邮件发送"""
    try:
        data = request.get_json()
        test_email = data.get('test_email')
        subject = data.get('subject', 'OpenIDCS - 测试邮件')
        body = data.get('body', '这是一封测试邮件')
        resend_email = data.get('resend_email')
        resend_apikey = data.get('resend_apikey')
        
        if not test_email or not resend_email or not resend_apikey:
            return jsonify({'code': 400, 'msg': '请提供完整的邮件配置信息'})
        
        if not subject or not body:
            return jsonify({'code': 400, 'msg': '请提供邮件标题和正文'})
        
        # 验证邮箱格式
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, test_email) or not re.match(email_pattern, resend_email):
            return jsonify({'code': 400, 'msg': '邮箱地址格式不正确'})
        
        # 发送测试邮件
        email_service = EmailService(
            api_key=resend_apikey,
            from_email=resend_email
        )
        
        success = email_service.send_test_email(test_email, subject, body)
        if success:
            return jsonify({'code': 200, 'msg': '测试邮件发送成功'})
        else:
            return jsonify({'code': 500, 'msg': '测试邮件发送失败'})
            
    except Exception as e:
        logger.error(f"测试邮件发送失败: {e}")
        return jsonify({'code': 500, 'msg': '测试邮件发送失败'})

@app.route('/api/system/settings', methods=['GET'])
@require_admin
def api_get_system_settings():
    """获取系统设置"""
    try:
        settings = db.get_system_settings()
        return api_response_wrapper(200, '获取成功', settings)
    except Exception as e:
        logger.error(f"获取系统设置失败: {e}")
        return api_response_wrapper(500, f'获取失败: {str(e)}')


@app.route('/api/system/settings', methods=['POST'])
@require_admin
def api_update_system_settings():
    """更新系统设置"""
    try:
        data = request.get_json()
        if not data:
            return api_response_wrapper(400, '无效的请求数据')
        
        success = db.update_system_settings(**data)
        if success:
            return api_response_wrapper(200, '更新成功')
        else:
            return api_response_wrapper(500, '更新失败')
    except Exception as e:
        logger.error(f"更新系统设置失败: {e}")
        return api_response_wrapper(500, f'更新失败: {str(e)}')


# ============================================================================
# 同步API - /api/sync
# ============================================================================

@app.route('/api/sync/push/<hs_name>', methods=['POST'])
@require_auth
def api_sync_push(hs_name):
    """接收远程推送的虚拟机数据并写入本地同名主机"""
    try:
        server = hs_manage.get_host(hs_name)
        if not server:
            return api_response_wrapper(404, f'主机 {hs_name} 不存在')
        
        data = request.get_json()
        if not data or 'vms' not in data:
            return api_response_wrapper(400, '无效的推送数据')
        
        remote_vms = data['vms']
        updated_count = 0
        
        for vm_uuid, vm_info in remote_vms.items():
            config_data = vm_info if isinstance(vm_info, dict) else {}
            if not config_data:
                continue
            
            if vm_uuid in server.vm_saving:
                # 已存在：智能合并配置（远端为空不覆盖本地，本地为空则从远端补充）
                local_vm = server.vm_saving[vm_uuid]
                # 更新基本配置（远端非空才覆盖）
                for key in ['cpu_num', 'mem_num', 'hdd_num', 'gpu_mem',
                            'os_name', 'speed_u', 'speed_d', 'nat_num', 'web_num']:
                    if key in config_data:
                        remote_val = config_data[key]
                        # 远端字段为空/零值时，不覆盖本地已有值
                        if not remote_val and remote_val != 0:
                            continue
                        setattr(local_vm, key, remote_val)
                # 合并所有者信息：远端有而本地没有的用户补充进来
                remote_own = config_data.get('own_all', {})
                if remote_own and isinstance(remote_own, dict):
                    from MainObject.Config.UserMask import UserMask
                    for username, mask_data in remote_own.items():
                        if username not in local_vm.own_all:
                            if isinstance(mask_data, dict):
                                local_vm.own_all[username] = UserMask(**mask_data)
                            elif isinstance(mask_data, int):
                                local_vm.own_all[username] = UserMask(mask_data)
                            else:
                                local_vm.own_all[username] = UserMask.full()
                # 合并网卡信息：远端有而本地没有的网卡补充进来
                remote_nic = config_data.get('nic_all', {})
                if remote_nic and isinstance(remote_nic, dict):
                    from MainObject.Config.NCConfig import NCConfig
                    for nic_name, nic_data in remote_nic.items():
                        if nic_name not in local_vm.nic_all:
                            if isinstance(nic_data, dict):
                                local_vm.nic_all[nic_name] = NCConfig(**nic_data)
                            else:
                                local_vm.nic_all[nic_name] = nic_data
                        else:
                            # 本地已有该网卡，补充本地为空的IP字段
                            local_nic = local_vm.nic_all[nic_name]
                            if isinstance(nic_data, dict):
                                for ip_key in ['ip4_addr', 'ip6_addr', 'mac_addr']:
                                    remote_ip_val = nic_data.get(ip_key, '')
                                    local_ip_val = getattr(local_nic, ip_key, '')
                                    if remote_ip_val and not local_ip_val:
                                        setattr(local_nic, ip_key, remote_ip_val)
                # 合并端口转发：远端有而本地为空时补充
                remote_nat = config_data.get('nat_all', [])
                if remote_nat and not local_vm.nat_all:
                    from MainObject.Config.PortData import PortData
                    local_vm.nat_all = []
                    for nat in remote_nat:
                        if isinstance(nat, dict):
                            nat_obj = PortData()
                            nat_obj.__load__(**nat)
                            local_vm.nat_all.append(nat_obj)
                # 合并反向代理：远端有而本地为空时补充
                remote_web = config_data.get('web_all', [])
                if remote_web and not local_vm.web_all:
                    from MainObject.Config.WebProxy import WebProxy
                    local_vm.web_all = []
                    for web in remote_web:
                        if isinstance(web, dict):
                            web_obj = WebProxy()
                            web_obj.__load__(**web)
                            local_vm.web_all.append(web_obj)
                updated_count += 1
            else:
                # 不存在：新建虚拟机配置
                from MainObject.Config.VMConfig import VMConfig
                new_vm = VMConfig(**config_data)
                new_vm.vm_uuid = vm_uuid
                server.vm_saving[vm_uuid] = new_vm
                updated_count += 1
        
        if updated_count > 0:
            server.data_set()
        
        return api_response_wrapper(200, f'同步成功，更新了 {updated_count} 台虚拟机')
    except Exception as e:
        logger.error(f"同步推送失败: {e}")
        return api_response_wrapper(500, f'同步推送失败: {str(e)}')


# 获取系统网卡IPv4地址列表 ##############################################################
@app.route('/api/system/ipv4', methods=['GET'])
@require_auth
def api_get_system_ipv4():
    """获取当前主机所有网卡的IPv4地址列表（用于财务系统 FindPortCandidates 接口）"""
    return rest_manager.get_system_ipv4()


# ============================================================================
# 国际化/语言API
# ============================================================================

# 获取可用语言列表 ##################################################################
@app.route('/api/i18n/languages', methods=['GET'])
def api_get_available_languages():
    """获取所有可用的语言列表（无需认证）"""
    try:
        from HostModule.Translation import get_translation
        translation = get_translation()
        languages = translation.get_available_languages()
        
        # 返回语言列表及其显示名称
        # 语言代码到本地化名称的映射
        language_names = {
            'zh-cn': {'name': '简体中文', 'native': '简体中文'},
            'zh-tw': {'name': '繁體中文', 'native': '繁體中文'},
            'en-us': {'name': 'English', 'native': 'English'},
            'ja-jp': {'name': '日本語', 'native': '日本語'},
            'ko-kr': {'name': '한국어', 'native': '한국어'},
            'ar-ar': {'name': 'العربية', 'native': 'العربية'},
            'de-de': {'name': 'Deutsch', 'native': 'Deutsch'},
            'es-es': {'name': 'Español', 'native': 'Español'},
            'fr-fr': {'name': 'Français', 'native': 'Français'},
            'it-it': {'name': 'Italiano', 'native': 'Italiano'},
            'pt-br': {'name': 'Português', 'native': 'Português'},
            'ru-ru': {'name': 'Русский', 'native': 'Русский'},
            'hi-in': {'name': 'हिन्दी', 'native': 'हिन्दी'},
            'bn-bd': {'name': 'বাংলা', 'native': 'বাংলা'},
            'ur-pk': {'name': 'اردو', 'native': 'اردو'},
        }
        
        language_info = []
        for lang in languages:
            if lang in language_names:
                language_info.append({
                    'code': lang, 
                    'name': language_names[lang]['name'], 
                    'native': language_names[lang]['native']
                })
            else:
                # 对于未定义的语言，使用语言代码作为显示名称
                language_info.append({'code': lang, 'name': lang, 'native': lang})
        
        return api_response_wrapper(200, '获取成功', language_info)
    except Exception as e:
        logger.error(f"获取语言列表失败: {e}")
        return api_response_wrapper(500, f'获取失败: {str(e)}')


# 获取指定语言的翻译数据 ##############################################################
@app.route('/api/i18n/translations/<lang_code>', methods=['GET'])
def api_get_translations(lang_code):
    """获取指定语言的所有翻译数据（无需认证）"""
    try:
        from HostModule.Translation import get_translation
        translation = get_translation()
        translations = translation.get_language_data(lang_code)
        
        if not translations:
            return api_response_wrapper(404, f'语言 {lang_code} 不存在')
        
        return api_response_wrapper(200, '获取成功', translations)
    except Exception as e:
        logger.error(f"获取翻译数据失败: {e}")
        return api_response_wrapper(500, f'获取失败: {str(e)}')


# ============================================================================
# 定时任务
# ============================================================================
def cron_scheduler():
    """定时任务调度器，每分钟执行一次exe_cron"""
    try:
        hs_manage.exe_cron()
    except Exception as e:
        traceback.print_exc()
        logger.error(f"[Cron] 执行定时任务出错: {e}")

    # 设置下一次执行（60秒后）
    timer = threading.Timer(60, cron_scheduler)
    timer.daemon = True  # 设为守护线程，主程序退出时自动结束
    timer.start()


def start_cron_scheduler():
    """启动定时任务调度器，立即执行一次并开始定时循环（非阻塞）"""

    def initial_run():
        """初始执行，在单独线程中运行以避免阻塞启动"""
        try:
            hs_manage.exe_cron()
            logger.info("[Cron] 初始执行完成")
        except Exception as e:
            logger.error(f"[Cron] 初始执行出错: {e}")

        # 初始执行完成后，60秒后开始定时循环
        timer = threading.Timer(60, cron_scheduler)
        timer.daemon = True
        timer.start()

    logger.info("[Cron] 启动定时任务调度器...")
    # 在单独线程中执行初始化，不阻塞主程序启动
    init_thread = threading.Thread(target=initial_run, daemon=True)
    init_thread.start()
    logger.info("[Cron] 定时任务已启动（后台运行），每60秒执行一次")


# ============================================================================
# 启动服务
# ============================================================================
def init_app():
    """初始化应用"""
    global hs_manage, db, rest_manager

    # 初始化核心对象（必须在此处创建，避免模块级代码导致Nuitka将主脚本编译为DLL）
    logger.info("正在初始化核心对象...")
    hs_manage = HostManage()
    db = DataManager()

    # 初始化Flask secret_key
    app.secret_key = _init_secret_key()

    # 从数据库恢复IP锁定记录
    _load_login_fail_records()

    # 初始化REST管理器
    rest_manager = RestManager(hs_manage, db)

    # 注入Bearer Token验证器
    init_bearer_validator(lambda: hs_manage.bearer)
    init_db_getter(lambda: db)

    # 加载已保存的配置
    try:
        logger.info("正在加载系统配置...")
        hs_manage.all_load()
        logger.info("系统配置加载完成")
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        # 如果是多进程相关错误，记录详细信息但不阻止启动
        if "multiprocessing" in str(e) or "process" in str(e).lower():
            logger.warning("检测到多进程相关错误，将在用户访问时重试加载")

    # 初始化翻译模块
    try:
        logger.info("正在加载翻译文件...")
        from HostModule.Translation import get_translation
        translation = get_translation()
        logger.info(f"翻译文件加载完成，已加载 {len(translation.get_available_languages())} 种语言")
    except Exception as e:
        logger.error(f"加载翻译文件失败: {e}")

    # 如果没有Token，生成一个
    if not hs_manage.bearer:
        hs_manage.set_pass()
        # Token脱敏日志
        _t = hs_manage.bearer
        if _t and len(_t) > 10:
            _mt = _t[:6] + '*' * (len(_t) - 10) + _t[-4:]
        else:
            _mt = _t
        logger.info(f"已生成访问Token: {_mt}")

    # 初始化admin用户（如果不存在）
    try:
        admin_user = hs_manage.saving.get_user_by_username('admin')
        if not admin_user:
            # 使用token作为admin的密码
            admin_password = UserManager.hash_password(hs_manage.bearer)
            user_id = hs_manage.saving.create_user(
                username='admin',
                password=admin_password,
                email='admin@localhost',
                is_admin=True,
                is_active=True,
                email_verified=True,
                can_create_vm=True,
                can_modify_vm=True,
                can_delete_vm=True,
                # 设置默认配额（管理员不受限制）
                quota_cpu=9999,
                quota_ram=9999,
                quota_ssd=9999,
                quota_gpu=9999,
                quota_nat_ports=9999,
                quota_web_proxy=9999,
                quota_nat_ips=9999,
                quota_pub_ips=9999,
                quota_bandwidth_up=9999,
                quota_bandwidth_down=9999,
                quota_traffic=9999,
                assigned_hosts=[]
            )
            if user_id:
                logger.info(f"已创建admin用户，用户名: admin, 密码: {hs_manage.bearer}")
            else:
                logger.error("创建admin用户失败")
        else:
            logger.info("admin用户已存在，跳过创建")
    except Exception as e:
        logger.error(f"初始化admin用户失败: {e}")

    # 启动定时任务调度器
    try:
        start_cron_scheduler()
        logger.info("定时任务调度器启动成功")
    except Exception as e:
        logger.error(f"启动定时任务调度器失败: {e}")


if __name__ == '__main__':
    try:
        # 在Windows系统上支持多进程
        import multiprocessing
        multiprocessing.freeze_support()
        
        # ===== 启动前清理残留的旧 Server 进程 =====
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "idcs_caddy"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                subprocess.run(
                    ["pkill", "-f", "idcs_caddy"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception:
            pass  # 忽略清理失败（可能没有残留进程）
        
        # 检测是否为打包后的环境
        is_frozen = getattr(sys, 'frozen', False)
        
        # ===== 首先配置 logger，确保日志系统正常工作 =====
        # 移除默认的 handler
        logger.remove()
        
        # 确保日志目录存在
        log_dir = os.path.join(project_root, 'DataSaving', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 添加控制台输出（始终显示）
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )
        
        # 添加总日志文件输出（所有日志汇总）
        log_file = os.path.join(log_dir, "log-kernel.log")
        logger.add(
            log_file,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            level="DEBUG"
        )
        
        # 添加平台日志（排除主机模块和Flask请求日志）
        logger.add(
            os.path.join(log_dir, "log-server.log"),
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            level="INFO",
            filter=lambda record: (
                record["name"] in ("__main__", "HostModule.HostManager", "HostModule.DataManager", "HostModule.UserManager")
                or record["name"].startswith("HostModule.")
            ) and "HostServer." not in record["name"]
        )
        
        # 添加Flask/Werkzeug请求日志
        logger.add(
            os.path.join(log_dir, "log-webapi.log"),
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            level="DEBUG",
            filter=lambda record: record["name"] in ("werkzeug", "flask", "flask.app")
        )
        
        logger.info("=" * 60)
        logger.info("OpenIDCS Server 启动")
        logger.info(f"运行模式: {'打包模式 (Nuitka)' if is_frozen else '开发模式'}")
        logger.info(f"Python 版本: {sys.version}")
        logger.info(f"工作目录: {os.getcwd()}")
        logger.info(f"项目根目录: {project_root}")
        logger.info("=" * 60)
        
        # 初始化应用
        logger.info("正在初始化应用...")
        if is_frozen or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            init_app()
            logger.info(f"\n{'=' * 60}")
            logger.info(f"OpenIDCS Server 启动中...")
            logger.info(f"运行模式: {'打包模式' if is_frozen else '开发模式'}")
            logger.info(f"访问地址: http://127.0.0.1:1880")
            # Token脱敏：只显示前6位和后4位，中间用*替代
            _token = hs_manage.bearer
            if _token and len(_token) > 10:
                _masked_token = _token[:6] + '*' * (len(_token) - 10) + _token[-4:]
            else:
                _masked_token = _token
            logger.info(f"访问Token（已脱敏）: {_masked_token}")
            logger.info(f"{'=' * 60}\n")
        else:
            logger.info("检测到调试重载父进程，跳过初始化，等待子进程启动")
        
        # 打包后禁用调试模式，避免 Nuitka 兼容性问题
        if is_frozen:
            logger.info("使用生产模式启动 Flask 服务器...")
            app.run(host='0.0.0.0', port=1880, debug=False, use_reloader=False)
        else:
            # 调试器只能由开发者显式开启，避免源码部署时暴露 Werkzeug 调试控制台
            debug_enabled = os.environ.get('OPENIDCS_DEBUG', '').lower() in ('1', 'true', 'yes')
            logger.info(f"使用源码模式启动 Flask 服务器（调试模式: {debug_enabled}）...")
            app.run(
                host='0.0.0.0',
                port=1880,
                debug=debug_enabled,
                use_reloader=debug_enabled,
                reloader_type='watchdog' if debug_enabled else 'stat'
            )
    except KeyboardInterrupt:
        logger.info("\n程序被用户中断")
    except OSError as e:
        if e.winerror == 10038:
            # Windows 上 reloader 重启时 socket 已关闭，忽略此错误
            pass
        else:
            raise
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n程序启动失败: {e}")
        logger.error(f"错误详情:\n{traceback.format_exc()}")
        # 打包模式下，等待用户按键后再退出，以便查看错误信息
        if getattr(sys, 'frozen', False):
            input("\n按回车键退出...")
        sys.exit(1)

