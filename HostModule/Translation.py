import os
import json
import logging

class Translation:
    def __init__(self):
        self.lan_map = {}  # 存储所有语言的翻译数据 {language: {key: value}}
        self.translate_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "HostConfig", "translates")
        self.logger = logging.getLogger(__name__)
        
    # 启动时扫描并加载所有语言文件 =================
    def load_all_languages(self):
        """扫描translates目录，加载所有.po文件"""
        try:
            if not os.path.exists(self.translate_dir):
                self.logger.warning(f"翻译目录不存在: {self.translate_dir}")
                return
            
            # 扫描所有.po文件
            for filename in os.listdir(self.translate_dir):
                if filename.endswith('.po'):
                    lang_code = filename[:-3]  # 去掉.po后缀
                    filepath = os.path.join(self.translate_dir, filename)
                    self.load_language_file(lang_code, filepath)
                    
            self.logger.info(f"已加载 {len(self.lan_map)} 种语言: {list(self.lan_map.keys())}")
        except Exception as e:
            self.logger.error(f"加载语言文件失败: {e}")

    # 读取单个翻译文件 =================
    def load_language_file(self, lang_code, filepath):
        """读取指定语言文件并解析到内存"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 解析.po文件格式
            translations = self.parse_po_file(content)
            self.lan_map[lang_code] = translations
            self.logger.info(f"已加载语言 {lang_code}: {len(translations)} 条翻译")
        except Exception as e:
            self.logger.error(f"读取语言文件 {filepath} 失败: {e}")

    # 解析.po文件格式 =================
    def parse_po_file(self, content):
        """解析.po文件内容，返回翻译字典"""
        translations = {}
        lines = content.split('\n')
        
        current_key = None
        current_value = []
        in_msgid = False
        in_msgstr = False
        
        for line in lines:
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
                
            # msgid开始
            if line.startswith('msgid "'):
                if current_key and current_value:
                    translations[current_key] = ''.join(current_value)
                current_key = line[7:-1]  # 提取msgid内容
                current_value = []
                in_msgid = True
                in_msgstr = False
                
            # msgstr开始
            elif line.startswith('msgstr "'):
                current_value = [line[8:-1]]  # 提取msgstr内容
                in_msgid = False
                in_msgstr = True
                
            # 多行字符串
            elif line.startswith('"') and line.endswith('"'):
                if in_msgstr:
                    current_value.append(line[1:-1])
                elif in_msgid:
                    current_key += line[1:-1]
        
        # 处理最后一条
        if current_key and current_value:
            translations[current_key] = ''.join(current_value)
            
        return translations

    # 获取翻译文本 =================
    def get_text(self, key, lang="zh-cn", default=None):
        """
        获取指定语言的翻译文本
        :param key: 翻译键（中文原文）
        :param lang: 语言代码，默认zh-cn
        :param default: 如果找不到翻译，返回的默认值
        :return: 翻译后的文本
        """
        if lang not in self.lan_map:
            return default if default is not None else key
            
        return self.lan_map[lang].get(key, default if default is not None else key)
    
    # 获取所有可用语言 =================
    def get_available_languages(self):
        """返回所有已加载的语言代码列表"""
        return list(self.lan_map.keys())
    
    # 获取指定语言的所有翻译 =================
    def get_language_data(self, lang="zh-cn"):
        """返回指定语言的所有翻译数据，用于前端"""
        return self.lan_map.get(lang, {})
    
    # 保存翻译到文件 =================
    def save_language_file(self, lang_code, translations):
        """将翻译数据保存为.po文件"""
        try:
            filepath = os.path.join(self.translate_dir, f"{lang_code}.po")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # 写入文件头
                f.write('# Translation file for OpenIDCS\n')
                f.write(f'# Language: {lang_code}\n')
                f.write('\n')
                
                # 写入翻译条目
                for key, value in sorted(translations.items()):
                    f.write(f'msgid "{key}"\n')
                    f.write(f'msgstr "{value}"\n')
                    f.write('\n')
                    
            self.logger.info(f"已保存语言文件: {filepath}")
        except Exception as e:
            self.logger.error(f"保存语言文件失败: {e}")


# 全局翻译实例
_translation_instance = None

def get_translation():
    """获取全局翻译实例"""
    global _translation_instance
    if _translation_instance is None:
        _translation_instance = Translation()
        _translation_instance.load_all_languages()
    return _translation_instance

def t(key, lang="zh-cn", default=None):
    """快捷翻译函数"""
    return get_translation().get_text(key, lang, default)
