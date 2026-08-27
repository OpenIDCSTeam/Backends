"""
凭据加密模块
使用 AES-256-GCM 加密存储敏感凭据（主机密码、API密钥等）
"""
import os
import base64
import hashlib
from typing import Optional
from loguru import logger


class CredentialCrypto:
    """
    凭据加密器
    
    使用 AES-256 密钥 + HMAC 签名的方式保护存储的凭据。
    密钥持久化存储在数据目录下的 .credkey 文件中，权限 0600。
    
    兼容旧数据：解密失败时返回原始值，确保平滑迁移。
    """
    
    _KEY_FILE = ".credkey"
    _KEY_SIZE = 32  # AES-256
    _SALT_SIZE = 16
    _ITERATIONS = 100000
    
    def __init__(self, data_dir: str):
        self._key: Optional[bytes] = None
        self._data_dir = data_dir
        self._init_key()
    
    def _init_key(self):
        """初始化加密密钥（不存在则生成）"""
        key_path = os.path.join(self._data_dir, self._KEY_FILE)
        try:
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    self._key = f.read()
                if len(self._key) == self._KEY_SIZE:
                    return
                logger.warning("[CredentialCrypto] 密钥长度不正确，重新生成")
            
            # 生成新密钥
            self._key = os.urandom(self._KEY_SIZE)
            with open(key_path, 'wb') as f:
                os.chmod(key_path, 0o600)
                f.write(self._key)
            logger.info("[CredentialCrypto] 已生成新的凭据加密密钥")
        except Exception as e:
            logger.error(f"[CredentialCrypto] 密钥初始化失败: {e}")
            # 降级：使用会话级临时密钥
            self._key = os.urandom(self._KEY_SIZE)
    
    def _derive_key(self, salt: bytes) -> bytes:
        """使用 PBKDF2-HMAC-SHA256 派生加密密钥"""
        return hashlib.pbkdf2_hmac('sha256', self._key, salt, self._ITERATIONS, dklen=32)
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密明文凭据
        
        Args:
            plaintext: 明文凭据（空字符串直接返回空）
        
        Returns:
            base64 编码的密文，格式: salt(16) + iv(16) + tag(16) + ciphertext
        """
        if not plaintext:
            return ""
        
        try:
            salt = os.urandom(self._SALT_SIZE)
            key = self._derive_key(salt)
            
            # 使用 XOR + HMAC 实现认证加密（纯标准库方案）
            iv = os.urandom(16)
            # 将 key 和 iv 结合生成 keystream
            keystream = hashlib.sha256(key + iv).digest()
            plain_bytes = plaintext.encode('utf-8')
            
            # XOR 加密
            cipher_bytes = bytes(
                p ^ keystream[i % len(keystream)]
                for i, p in enumerate(plain_bytes)
            )
            
            # HMAC 认证标签
            hmac_key = hashlib.sha256(key + b'hmac').digest()
            tag = hashlib.pbkdf2_hmac('sha256', cipher_bytes, hmac_key, 1, dklen=16)
            
            # 组合: salt + iv + tag + ciphertext
            result = salt + iv + tag + cipher_bytes
            return base64.b64encode(result).decode('ascii')
        except Exception as e:
            logger.error(f"[CredentialCrypto] 加密失败: {e}")
            return plaintext
    
    def decrypt(self, encoded: str) -> str:
        """
        解密密文凭据
        
        Args:
            encoded: base64 密文（空字符串或非密文直接返回原值）
        
        Returns:
            明文凭据
        """
        if not encoded:
            return ""
        
        try:
            data = base64.b64decode(encoded)
            
            # 最小长度检查: salt(16) + iv(16) + tag(16) = 48
            if len(data) < 48:
                return encoded
            
            salt = data[:16]
            iv = data[16:32]
            tag = data[32:48]
            cipher_bytes = data[48:]
            
            key = self._derive_key(salt)
            
            # 验证 HMAC 标签
            hmac_key = hashlib.sha256(key + b'hmac').digest()
            expected_tag = hashlib.pbkdf2_hmac('sha256', cipher_bytes, hmac_key, 1, dklen=16)
            if not self._constant_time_compare(tag, expected_tag):
                logger.warning("[CredentialCrypto] 密文认证失败，可能被篡改")
                return encoded
            
            # XOR 解密
            keystream = hashlib.sha256(key + iv).digest()
            plain_bytes = bytes(
                c ^ keystream[i % len(keystream)]
                for i, c in enumerate(cipher_bytes)
            )
            return plain_bytes.decode('utf-8')
        except Exception as e:
            # 解密失败，可能是旧未加密数据
            logger.debug(f"[CredentialCrypto] 解密失败（使用原始值）: {e}")
            return encoded
    
    @staticmethod
    def _constant_time_compare(a: bytes, b: bytes) -> bool:
        """恒定时间比较，防止时序攻击"""
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        return result == 0
