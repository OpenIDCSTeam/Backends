# OpenIDCS 国际化系统使用指南

## 简介

OpenIDCS 国际化系统提供了**全自动、零配置**的页面翻译功能，支持自动检测浏览器语言、用户手动切换语言，以及动态内容的自动翻译。

## 特性

- ✅ **全自动翻译**：无需手动标记元素，自动翻译页面所有文本内容
- ✅ **零配置使用**：引入 JS 文件即可，无需修改现有 HTML
- ✅ **智能识别**：自动跳过脚本、样式、代码等不需要翻译的内容
- ✅ **自动语言检测**：首次访问时自动检测浏览器语言（中文/英文）
- ✅ **语言持久化**：用户选择的语言保存在 localStorage
- ✅ **动态内容翻译**：使用 MutationObserver 自动翻译动态添加的内容
- ✅ **多属性支持**：自动翻译文本、placeholder、title、value、aria-label、alt 等
- ✅ **JavaScript API**：提供 `t()` 函数用于 JS 代码中的翻译

## 快速开始

### 1. 引入 JS 文件

在 HTML 页面中引入 `i18n.js`（已在 `base.html` 中引入）：

```html
<script src="/static/i18n.js"></script>
```

### 2. 就这样！

**无需任何额外配置**，系统会自动翻译页面上的所有文本内容。

```html
<!-- 这些内容会自动翻译，无需添加任何属性 -->
<h1>欢迎使用</h1>
<p>这是一段描述文本</p>
<button>保存</button>
<button>取消</button>
<input type="text" placeholder="请输入用户名">
```

### 3. 排除不需要翻译的内容（可选）

如果某些内容不需要翻译，可以添加以下标记：

```html
<!-- 方法1: 使用 translate="no" 属性 -->
<div translate="no">
    这段内容不会被翻译
</div>

<!-- 方法2: 使用 no-translate 或 notranslate 类名 -->
<div class="no-translate">
    这段内容不会被翻译
</div>

<!-- 方法3: 用于代码块 -->
<pre class="notranslate">
    const code = "这段代码不会被翻译";
</pre>
```

## 自动翻译的内容

系统会自动翻译以下内容：

### 1. 文本内容
```html
<h1>标题</h1>
<p>段落文本</p>
<span>行内文本</span>
<div>块级文本</div>
<button>按钮文本</button>
<a href="#">链接文本</a>
<li>列表项</li>
<td>表格单元格</td>
```

### 2. 元素属性
```html
<!-- placeholder -->
<input type="text" placeholder="请输入内容">

<!-- title -->
<button title="点击保存">保存</button>

<!-- value -->
<input type="submit" value="提交">

<!-- aria-label -->
<button aria-label="关闭对话框">×</button>

<!-- alt -->
<img src="logo.png" alt="公司标志">
```

### 3. 复杂结构
```html
<!-- 带图标的按钮 -->
<button>
    <span class="iconify" data-icon="mdi:save"></span>
    保存
</button>

<!-- 表格 -->
<table>
    <thead>
        <tr>
            <th>名称</th>
            <th>状态</th>
            <th>操作</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>虚拟机-001</td>
            <td>运行中</td>
            <td>
                <button>编辑</button>
                <button>删除</button>
            </td>
        </tr>
    </tbody>
</table>
```

## 自动跳过的内容

系统会智能跳过以下内容，无需手动标记：

- ✅ `<script>` 标签内容
- ✅ `<style>` 标签内容
- ✅ `<noscript>` 标签内容
- ✅ 纯数字、纯符号
- ✅ 空白文本
- ✅ 可编辑内容（contenteditable）
- ✅ 带有 `translate="no"` 属性的元素
- ✅ 带有 `no-translate` 或 `notranslate` 类名的元素

## JavaScript API

### 翻译函数

在 JavaScript 代码中使用 `t()` 函数进行翻译：

```javascript
// 基本用法
const message = t('保存成功');

// 带默认值
const message = t('未知错误', 'Unknown Error');

// 在 SweetAlert2 中使用
Swal.fire({
    title: t('确认删除'),
    text: t('此操作不可恢复'),
    icon: 'warning',
    confirmButtonText: t('确定'),
    cancelButtonText: t('取消')
});

// 在动态生成的 HTML 中使用
const html = `
    <div>
        <h3>${t('标题')}</h3>
        <p>${t('内容')}</p>
    </div>
`;
document.body.innerHTML += html;
// 新添加的内容会自动翻译
```

### 切换语言

```javascript
// 切换到英文
await i18n.changeLanguage('en-us');

// 切换到中文
await i18n.changeLanguage('zh-cn');
```

### 获取当前语言

```javascript
const currentLang = i18n.getCurrentLanguage();
console.log('当前语言:', currentLang); // 'zh-cn' 或 'en-us'
```

### 重新翻译页面

```javascript
// 手动触发重新翻译（通常不需要，系统会自动处理）
i18n.retranslate();
```

### 监听语言变化事件

```javascript
window.addEventListener('languageChanged', (event) => {
    console.log('语言已切换为:', event.detail.language);
    // 执行自定义逻辑，如重新加载数据
});
```

## 高级用法

### 动态内容翻译

系统会自动翻译动态添加的内容，无需手动调用：

```javascript
// 使用 innerHTML
document.getElementById('container').innerHTML = `
    <div>
        <h3>新标题</h3>
        <p>新内容</p>
    </div>
`;
// 自动翻译

// 使用 createElement
const newElement = document.createElement('div');
newElement.innerHTML = '<p>新内容</p>';
document.body.appendChild(newElement);
// 自动翻译

// 使用 jQuery
$('#container').html('<div>新内容</div>');
// 自动翻译
```

### AJAX 加载的内容

```javascript
// 使用 fetch
fetch('/api/data')
    .then(response => response.json())
    .then(data => {
        document.getElementById('content').innerHTML = data.html;
        // 自动翻译
    });

// 使用 jQuery
$.get('/api/data', function(data) {
    $('#content').html(data.html);
    // 自动翻译
});
```

### 模态框和弹窗

```javascript
// SweetAlert2
Swal.fire({
    title: t('操作成功'),
    text: t('数据已保存'),
    icon: 'success'
});

// 自定义模态框
const modal = document.createElement('div');
modal.innerHTML = `
    <div class="modal">
        <h3>确认操作</h3>
        <p>您确定要执行此操作吗？</p>
        <button>确定</button>
        <button>取消</button>
    </div>
`;
document.body.appendChild(modal);
// 自动翻译
```

## 后端 API

系统需要后端提供以下 API：

### 1. 获取可用语言列表

```
GET /api/i18n/languages
```

响应示例：
```json
{
    "code": 200,
    "data": [
        {
            "code": "zh-cn",
            "name": "Chinese (Simplified)",
            "native": "简体中文"
        },
        {
            "code": "en-us",
            "name": "English (US)",
            "native": "English"
        }
    ]
}
```

### 2. 获取翻译数据

```
GET /api/i18n/translations/{lang}
```

响应示例：
```json
{
    "code": 200,
    "data": {
        "欢迎使用": "Welcome",
        "保存": "Save",
        "取消": "Cancel",
        "确认删除": "Confirm Delete",
        "此操作不可恢复": "This action cannot be undone",
        "请输入用户名": "Please enter username",
        "点击保存": "Click to save"
    }
}
```

## 最佳实践

### 1. 翻译数据准备

确保后端翻译数据包含页面上所有需要翻译的文本：

```json
{
    "欢迎使用": "Welcome",
    "保存": "Save",
    "取消": "Cancel",
    "编辑": "Edit",
    "删除": "Delete",
    "确定": "OK",
    "请输入用户名": "Please enter username",
    "请输入密码": "Please enter password"
}
```

### 2. 避免翻译代码和数据

对于代码、数据、专有名词等，使用 `translate="no"` 标记：

```html
<!-- ✅ 正确 -->
<div>
    <span>虚拟机名称</span>: 
    <span translate="no">VM-001</span>
</div>

<!-- ✅ 正确 -->
<pre class="notranslate">
const config = {
    name: "OpenIDCS",
    version: "1.0.0"
};
</pre>
```

### 3. 性能优化

- 翻译数据应该在后端缓存
- 避免频繁切换语言
- 对于大量动态内容，考虑批量加载

### 4. 用户体验

```javascript
// 在切换语言时显示加载提示
async function switchLanguage(lang) {
    Swal.fire({
        title: t('正在切换语言'),
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    await i18n.changeLanguage(lang);
    
    Swal.close();
    Swal.fire({
        title: t('切换成功'),
        icon: 'success',
        timer: 1500
    });
}
```

## 故障排查

### 翻译不生效

1. 检查是否正确引入 `i18n.js`
2. 检查浏览器控制台是否有错误
3. 检查后端 API 是否正常返回数据
4. 检查翻译键是否存在于翻译数据中
5. 检查元素是否被标记为 `translate="no"`

### 部分内容不翻译

1. 检查是否是纯数字或纯符号（会自动跳过）
2. 检查是否在 `<script>` 或 `<style>` 标签内
3. 检查是否有 `no-translate` 类名
4. 检查翻译数据中是否包含该文本

### 动态内容不翻译

1. 确保动态内容添加到了 DOM 中
2. 检查是否有 JavaScript 错误
3. 等待几毫秒后检查（MutationObserver 有轻微延迟）
4. 尝试手动调用 `i18n.retranslate()`

### 语言切换不生效

1. 检查 localStorage 是否被禁用
2. 检查后端 API 是否返回正确的翻译数据
3. 清除浏览器缓存后重试

## 示例页面

完整的示例页面可以参考 `base.html` 和其他页面模板。

## 支持的语言

当前系统支持的语言由后端配置决定，默认支持：

- 简体中文 (zh-cn)
- 英文 (en-us)

如需添加更多语言，请在后端添加相应的翻译文件。
