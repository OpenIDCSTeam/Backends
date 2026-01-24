# OpenIDCS React前端项目

基于原始WebDesigns静态页面转换的React + TypeScript前端项目

## 🎯 项目特点

- ✅ **保持原有设计**：完全仿照WebDesigns中的静态页面设计和布局
- ✅ **现代技术栈**：React 18 + TypeScript + Vite
- ✅ **UI一致性**：使用TailwindCSS + DaisyUI保持原有样式风格
- ✅ **HTTP通信**：使用Axios与Flask后端RESTful API通信（移除Socket.io）
- ✅ **完整注释**：所有代码包含详细的中文注释
- ✅ **类型安全**：完整的TypeScript类型定义

## 📦 技术栈

### 核心框架
- **React 18.2.0** - UI框架
- **TypeScript 5.2.2** - 类型系统
- **Vite 5.0.8** - 构建工具

### UI组件
- **Ant Design 5.12.0** - 主要UI组件库
- **TailwindCSS 3.4.0** - CSS工具类（保持原有样式）
- **DaisyUI 4.4.24** - TailwindCSS组件库
- **@iconify/react 4.1.1** - 图标库

### 数据可视化
- **ECharts 5.4.3** - 图表库
- **echarts-for-react 3.0.2** - React封装

### 状态管理与HTTP
- **Zustand 4.4.7** - 轻量级状态管理
- **Axios 1.6.2** - HTTP客户端
- **React Router DOM 6.20.0** - 路由管理

### 其他工具
- **dayjs 1.11.10** - 日期处理
- **sweetalert2 11.10.3** - 弹窗提示

## 🚀 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

前端将运行在 `http://localhost:3000`

### 3. 启动Flask后端

在项目根目录：

```bash
python HostServer.py
```

后端将运行在 `http://localhost:1880`

### 4. 一键启动（Windows）

在项目根目录双击运行：

```bash
start.bat
```

## 📁 项目结构

```
FrontPages/
├── src/
│   ├── services/          # API服务层
│   │   └── api.ts         # 所有API接口封装
│   ├── types/             # TypeScript类型定义
│   │   └── index.ts       # 数据类型定义
│   ├── store/             # Zustand状态管理
│   │   └── userStore.ts   # 用户状态管理
│   ├── utils/             # 工具函数
│   │   └── request.ts     # Axios配置和拦截器
│   ├── pages/             # 页面组件
│   │   ├── Login.tsx      # 登录页面
│   │   ├── Register.tsx   # 注册页面
│   │   ├── Dashboard.tsx  # 仪表盘
│   │   ├── Hosts.tsx      # 主机管理
│   │   ├── VMs.tsx        # 虚拟机列表
│   │   ├── VMDetail.tsx   # 虚拟机详情
│   │   └── Users.tsx      # 用户管理
│   ├── layouts/           # 布局组件
│   │   └── MainLayout.tsx # 主布局（侧边栏+顶栏）
│   ├── components/        # 通用组件
│   ├── App.tsx            # 应用入口
│   ├── main.tsx           # React入口
│   └── index.css          # 全局样式
├── public/                # 静态资源
├── index.html             # HTML模板
├── package.json           # 项目配置
├── vite.config.ts         # Vite配置
├── tailwind.config.js     # TailwindCSS配置
├── tsconfig.json          # TypeScript配置
├── DEPLOYMENT_GUIDE.md    # 部署指南
└── README.md              # 本文件
```

## 🔌 前后端对接

### API代理配置

开发环境下，Vite自动将 `/api` 请求代理到Flask后端：

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:1880',
    changeOrigin: true,
  },
}
```

### 认证流程

1. 用户登录 → 获取Token
2. Token存储在localStorage
3. 每个API请求自动携带Token
4. 后端验证Token并返回数据

### API调用示例

```typescript
import { getHosts, createVM } from '@/services/api';

// 获取主机列表
const response = await getHosts();
console.log(response.data);

// 创建虚拟机
await createVM('host-name', {
  vm_uuid: 'xxx',
  vm_name: 'test-vm',
  cpu_num: 2,
  mem_num: 4096,
  hdd_num: 50,
  os_name: 'ubuntu-22.04',
});
```

## 🎨 样式说明

### 保持原有设计

前端完全仿照 `WebDesigns/` 目录下的静态页面：

- ✅ 相同的颜色方案和主题
- ✅ 相同的布局结构（侧边栏+顶栏）
- ✅ 相同的卡片样式和动画效果
- ✅ 相同的按钮和表单样式
- ✅ 相同的响应式设计

### TailwindCSS工具类

使用与原页面相同的TailwindCSS类名：

```tsx
<div className="bg-white rounded-lg border border-gray-200 p-6 card-hover">
  <h2 className="text-xl font-bold text-gray-800">标题</h2>
</div>
```

## 📝 开发规范

### 代码注释

所有代码包含完整的中文注释：

```typescript
/**
 * 获取主机列表
 * @returns 主机列表数据
 */
export const getHosts = (): Promise<ApiResponse<Record<string, Host>>> => {
  return http.get('/server/detail');
};
```

### 类型定义

所有数据类型都有完整的TypeScript定义：

```typescript
export interface VM {
  vm_uuid: string;        // 虚拟机UUID
  vm_name: string;        // 虚拟机名称
  cpu_num: number;        // CPU核心数
  mem_num: number;        // 内存大小(MB)
  status: 'running' | 'stopped' | 'suspended' | 'error';
}
```

## 🛠️ 可用脚本

```bash
# 开发模式（热更新）
npm run dev

# 生产构建
npm run build

# 预览构建产物
npm run preview

# 代码检查
npm run lint
```

## 📚 相关文档

- [部署指南](./DEPLOYMENT_GUIDE.md) - 详细的启动和对接说明
- [API文档](../ProjectDoc/APIDOC_ALL.md) - Flask后端API完整文档
- [项目架构](../ProjectDoc/PROJECT_OVERVIEW.md) - 整体项目架构说明

## 🔧 常见问题

### 1. 前端无法连接后端

确保Flask后端已启动在端口1880：

```bash
python HostServer.py
```

### 2. 依赖安装失败

尝试清除缓存后重新安装：

```bash
rm -rf node_modules package-lock.json
npm install
```

### 3. 端口被占用

修改 `vite.config.ts` 中的端口：

```typescript
server: {
  port: 3001,  // 改为其他端口
}
```

## 📄 许可证

本项目采用 MIT 许可证

## 👥 贡献

欢迎提交Issue和Pull Request

---

**最后更新**：2026-01-23  
**版本**：v1.0.0