import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Modal, message, Alert } from 'antd'
import { UserOutlined, LockOutlined, KeyOutlined, LoginOutlined, MailOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { useUserStore } from '@/store/userStore'
import api from '@/services/api'

/**
 * 登录表单数据接口
 */
interface LoginForm {
  username: string
  password: string
}

/**
 * Token登录表单数据接口
 */
interface TokenLoginForm {
  token: string
}

/**
 * 找回密码表单数据接口
 */
interface ForgotPasswordForm {
  email: string
}

/**
 * 登录页面组件
 */
function Login() {
  const navigate = useNavigate()
  const { setUser, setToken } = useUserStore()
  const [loading, setLoading] = useState(false)
  const [loginType, setLoginType] = useState<'user' | 'token'>('user') // 登录方式：用户登录或Token登录
  const [errorMsg, setErrorMsg] = useState('') // 错误提示信息
  const [forgotPasswordVisible, setForgotPasswordVisible] = useState(false) // 找回密码模态框显示状态
  const [forgotPasswordLoading, setForgotPasswordLoading] = useState(false) // 找回密码加载状态
  const [userForm] = Form.useForm() // 用户登录表单实例
  const [tokenForm] = Form.useForm() // Token登录表单实例
  const [forgotPasswordForm] = Form.useForm() // 找回密码表单实例

  /**
   * 处理用户名密码登录提交
   */
  const handleUserLogin = async (values: LoginForm) => {
    try {
      setLoading(true)
      setErrorMsg('')
      
      // 调用登录API
      const response = await api.login({
        login_type: 'user',
        username: values.username,
        password: values.password,
      })
      
      // 保存用户信息和token
      if (response.data?.token) {
        setToken(response.data.token)
      }
      if (response.data?.user_info) {
        setUser(response.data.user_info)
      }
      
      message.success('登录成功')
      navigate('/dashboard')
    } catch (error: any) {
      const errorMessage = error?.response?.data?.msg || '登录失败，请检查用户名和密码'
      setErrorMsg(errorMessage)
      // 4秒后自动隐藏错误提示
      setTimeout(() => setErrorMsg(''), 4000)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 处理Token登录提交
   */
  const handleTokenLogin = async (values: TokenLoginForm) => {
    try {
      setLoading(true)
      setErrorMsg('')
      
      // 调用登录API
      const response = await api.login({
        login_type: 'token',
        token: values.token,
      })
      
      // 保存用户信息和token
      if (response.data?.token) {
        setToken(response.data.token)
      }
      if (response.data?.user_info) {
        setUser(response.data.user_info)
      }
      
      message.success('登录成功')
      navigate('/dashboard')
    } catch (error: any) {
      const errorMessage = error?.response?.data?.msg || 'Token登录失败，请检查Token是否正确'
      setErrorMsg(errorMessage)
      // 4秒后自动隐藏错误提示
      setTimeout(() => setErrorMsg(''), 4000)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 切换登录方式
   */
  const switchLoginType = (type: 'user' | 'token') => {
    setLoginType(type)
    setErrorMsg('')
  }

  /**
   * 打开找回密码模态框
   */
  const openForgotPasswordModal = () => {
    setForgotPasswordVisible(true)
    forgotPasswordForm.resetFields()
  }

  /**
   * 关闭找回密码模态框
   */
  const closeForgotPasswordModal = () => {
    setForgotPasswordVisible(false)
    forgotPasswordForm.resetFields()
  }

  /**
   * 处理找回密码提交
   */
  const handleForgotPassword = async (values: ForgotPasswordForm) => {
    try {
      setForgotPasswordLoading(true)
      
      // 调用找回密码API
      await api.forgotPassword(values.email)
      
      message.success('重置邮件已发送，请查收')
      // 3秒后自动关闭模态框
      setTimeout(() => {
        closeForgotPasswordModal()
      }, 3000)
    } catch (error: any) {
      const errorMessage = error?.response?.data?.msg || '发送失败，请重试'
      message.error(errorMessage)
    } finally {
      setForgotPasswordLoading(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(to bottom right, #eff6ff, #eef2ff, #faf5ff)',
      }}
    >
      {/* 登录卡片 */}
      <div
        style={{
          background: 'white',
          borderRadius: '16px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          padding: '32px',
          width: '100%',
          maxWidth: '448px',
        }}
      >
        {/* 标题区域 */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          {/* Logo图标 */}
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
            <div
              style={{
                background: 'linear-gradient(to bottom right, #3b82f6, #6366f1)',
                padding: '16px',
                borderRadius: '16px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
              }}
            >
              <svg
                style={{ width: 48, height: 48, color: 'white' }}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
                />
              </svg>
            </div>
          </div>
          <h1 style={{ fontSize: '30px', fontWeight: 'bold', color: '#1f2937', marginBottom: 8 }}>
            OpenIDCS
          </h1>
          <p style={{ color: '#6b7280', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <LockOutlined style={{ fontSize: 16 }} />
            虚拟化管理平台
          </p>
        </div>

        {/* 登录方式切换Tab */}
        <div
          style={{
            display: 'flex',
            gap: '8px',
            marginBottom: 24,
            background: '#f3f4f6',
            padding: '4px',
            borderRadius: '8px',
          }}
        >
          <button
            onClick={() => switchLoginType('user')}
            style={{
              flex: 1,
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.3s',
              background: loginType === 'user' ? 'linear-gradient(to right, #2563eb, #4f46e5)' : 'transparent',
              color: loginType === 'user' ? 'white' : '#374151',
              fontWeight: 500,
            }}
          >
            <UserOutlined style={{ marginRight: 4 }} />
            用户登录
          </button>
          <button
            onClick={() => switchLoginType('token')}
            style={{
              flex: 1,
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.3s',
              background: loginType === 'token' ? 'linear-gradient(to right, #2563eb, #4f46e5)' : 'transparent',
              color: loginType === 'token' ? 'white' : '#374151',
              fontWeight: 500,
            }}
          >
            <KeyOutlined style={{ marginRight: 4 }} />
            Token登录
          </button>
        </div>

        {/* 用户名密码登录表单 */}
        {loginType === 'user' && (
          <Form
            form={userForm}
            name="userLogin"
            onFinish={handleUserLogin}
            autoComplete="off"
            layout="vertical"
          >
            {/* 用户名输入框 */}
            <Form.Item
              label={
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 500 }}>
                  <UserOutlined style={{ color: '#3b82f6' }} />
                  用户名
                </span>
              }
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                size="large"
                placeholder="请输入用户名"
                autoComplete="username"
                style={{
                  borderRadius: '8px',
                  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                }}
              />
            </Form.Item>

            {/* 密码输入框 */}
            <Form.Item
              label={
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 500 }}>
                  <LockOutlined style={{ color: '#3b82f6' }} />
                  密码
                </span>
              }
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                size="large"
                placeholder="请输入密码"
                autoComplete="current-password"
                style={{
                  borderRadius: '8px',
                  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                }}
              />
            </Form.Item>

            {/* 错误提示 */}
            {errorMsg && (
              <Alert
                message={errorMsg}
                type="error"
                showIcon
                style={{ marginBottom: 16, borderRadius: '8px' }}
              />
            )}

            {/* 登录按钮 */}
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                icon={<LoginOutlined />}
                style={{
                  background: 'linear-gradient(to right, #2563eb, #6366f1)',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  height: '48px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
              >
                登 录
              </Button>
            </Form.Item>

            {/* 底部链接 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
              <Link to="/register" style={{ color: '#2563eb' }}>
                还没有账号？立即注册
              </Link>
              <a onClick={openForgotPasswordModal} style={{ color: '#2563eb', cursor: 'pointer' }}>
                忘记密码？
              </a>
            </div>
          </Form>
        )}

        {/* Token登录表单 */}
        {loginType === 'token' && (
          <Form
            form={tokenForm}
            name="tokenLogin"
            onFinish={handleTokenLogin}
            autoComplete="off"
            layout="vertical"
          >
            {/* Token输入框 */}
            <Form.Item
              label={
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 500 }}>
                  <KeyOutlined style={{ color: '#3b82f6' }} />
                  访问Token
                </span>
              }
              name="token"
              rules={[{ required: true, message: '请输入访问Token' }]}
            >
              <Input.Password
                size="large"
                placeholder="请输入访问Token"
                style={{
                  borderRadius: '8px',
                  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                }}
              />
            </Form.Item>

            {/* 错误提示 */}
            {errorMsg && (
              <Alert
                message={errorMsg}
                type="error"
                showIcon
                style={{ marginBottom: 16, borderRadius: '8px' }}
              />
            )}

            {/* 登录按钮 */}
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                icon={<LoginOutlined />}
                style={{
                  background: 'linear-gradient(to right, #2563eb, #6366f1)',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  height: '48px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
              >
                登 录
              </Button>
            </Form.Item>

            {/* Token提示信息 */}
            <div
              style={{
                marginTop: 24,
                textAlign: 'center',
                fontSize: '14px',
                color: '#6b7280',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 4,
                  background: '#eff6ff',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid #dbeafe',
                }}
              >
                <InfoCircleOutlined style={{ color: '#3b82f6' }} />
                启动服务时会在控制台显示访问Token
              </div>
            </div>
          </Form>
        )}
      </div>

      {/* 找回密码模态框 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                background: '#2563eb',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <MailOutlined style={{ color: 'white', fontSize: 20 }} />
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 600 }}>找回密码</div>
              <div style={{ fontSize: 14, fontWeight: 400, color: '#6b7280' }}>通过邮件重置您的密码</div>
            </div>
          </div>
        }
        open={forgotPasswordVisible}
        onCancel={closeForgotPasswordModal}
        footer={null}
        width={480}
      >
        <Form
          form={forgotPasswordForm}
          onFinish={handleForgotPassword}
          layout="vertical"
          style={{ marginTop: 24 }}
        >
          {/* 邮箱输入框 */}
          <Form.Item
            label="邮箱地址"
            name="email"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
            extra="我们将向此邮箱发送密码重置链接"
          >
            <Input
              size="large"
              placeholder="请输入注册时使用的邮箱"
              style={{ borderRadius: '8px' }}
            />
          </Form.Item>

          {/* 按钮组 */}
          <Form.Item style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', gap: 12, paddingTop: 8 }}>
              <Button
                onClick={closeForgotPasswordModal}
                size="large"
                style={{ flex: 1, borderRadius: '8px' }}
              >
                取消
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={forgotPasswordLoading}
                size="large"
                icon={<MailOutlined />}
                style={{
                  flex: 1,
                  background: '#2563eb',
                  borderRadius: '8px',
                }}
              >
                发送重置邮件
              </Button>
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Login
