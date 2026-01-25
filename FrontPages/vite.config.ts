import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Vite配置文件
// https://vitejs.dev/config/
export default defineConfig({
  // 使用React插件
  plugins: [react()],
  
  // 路径别名配置
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  
  // 开发服务器配置
  server: {
    port: 3000, // 开发服务器端口
    host: true, // 监听所有地址
    proxy: {
      // API代理配置，将/api请求代理到Flask后端服务器
      '/api': {
        target: 'http://localhost:1880', // Flask后端服务器地址（默认端口1880）
        changeOrigin: true,
        //rewrite: (path) => path.replace(/^\/api/, ''), // 重写路径，移除/api前缀
      },
      // 静态资源代理（如果需要访问后端的static目录）
      '/static': {
        target: 'http://localhost:1880',
        changeOrigin: true,
      },
    },
  },
  
  // 构建配置
  build: {
    outDir: 'dist', // 输出目录
    sourcemap: false, // 生产环境不生成sourcemap
    rollupOptions: {
      output: {
        // 代码分割配置
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'antd-vendor': ['antd', '@ant-design/icons'],
          'chart-vendor': ['echarts', 'echarts-for-react'],
        },
      },
    },
  },
})
