import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import ResetPassword from './pages/ResetPassword'
import Dashboard from './pages/Dashboard'
import VMs from './pages/VMs'
import VMDetail from './pages/VMDetail'
import Hosts from './pages/Hosts'
import Users from './pages/Users'
import Tasks from './pages/Tasks'
import Logs from './pages/Logs'
import Settings from './pages/Settings'
import Profile from './pages/Profile'
import WebProxys from './pages/WebProxys'
import UserDashboard from './pages/user/UserDashboard'
import UserVMs from './pages/user/UserVMs'
import UserWebProxys from './pages/user/UserWebProxys'
import UserNAT from './pages/user/UserNAT'
import { useUserStore } from '@/store/userStore'

/**
 * 应用主组件
 * 配置路由和页面导航
 */
function App() {
  const { user } = useUserStore()
  const defaultRoute = user?.is_admin ? '/dashboard' : '/user/dashboard'

  return (
    <BrowserRouter>
      <Routes>
        {/* 公开路由 - 无需登录 */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        
        {/* 受保护路由 - 需要登录 */}
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to={defaultRoute} replace />} />
          
          {/* 系统界面 (管理员) */}
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="hosts" element={<Hosts />} />
          <Route path="hosts/:hostName/vms" element={<VMs />} />
          <Route path="hosts/:hostName/vms/:uuid" element={<VMDetail />} />
          <Route path="vms" element={<UserVMs />} /> {/* 全局容器管理 */}
          <Route path="users" element={<Users />} />
          <Route path="tasks" element={<Tasks />} />
          <Route path="logs" element={<Logs />} />
          <Route path="settings" element={<Settings />} />
          <Route path="web-proxys" element={<WebProxys />} />
          <Route path="nat-rules" element={<UserNAT />} /> {/* 暂时指向UserNAT，后续可能需要管理员版的NAT管理 */}

          {/* 用户界面 */}
          <Route path="user">
            <Route path="dashboard" element={<UserDashboard />} />
            <Route path="vms" element={<UserVMs />} />
            <Route path="proxys" element={<UserWebProxys />} />
            <Route path="nat" element={<UserNAT />} />
          </Route>

          <Route path="profile" element={<Profile />} />
        </Route>
        
        {/* 404重定向 */}
        <Route path="*" element={<Navigate to={defaultRoute} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
