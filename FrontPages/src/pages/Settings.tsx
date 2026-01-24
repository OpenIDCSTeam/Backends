import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Switch, message, InputNumber, Checkbox, Alert } from 'antd'
import { EyeOutlined, EyeInvisibleOutlined, CopyOutlined, ReloadOutlined, SaveOutlined, FolderOpenOutlined, MailOutlined } from '@ant-design/icons'
import api from '@/services/api'

const { TextArea } = Input

/**
 * 系统设置页面
 */
function Settings() {
  const [loading, setLoading] = useState(false)
  const [tokenVisible, setTokenVisible] = useState(false)
  const [currentToken, setCurrentToken] = useState('')
  const [systemInfo, setSystemInfo] = useState({ host_count: 0, vm_count: 0 })
  const [registrationForm] = Form.useForm()
  const [emailForm] = Form.useForm()
  const [testEmailForm] = Form.useForm()

  /**
   * 页面加载时获取数据
   */
  useEffect(() => {
    loadCurrentToken()
    loadSystemInfo()
    loadSystemSettings()
  }, [])

  /**
   * 加载当前Token
   */
  const loadCurrentToken = async () => {
    try {
      const res = await api.getCurrentToken()
      if (res.code === 200) {
        setCurrentToken(res.data.token)
      }
    } catch (error) {
      console.error('加载Token失败:', error)
    }
  }

  /**
   * 加载系统信息
   */
  const loadSystemInfo = async () => {
    try {
      const res = await api.getSystemStats()
      if (res.code === 200) {
        setSystemInfo(res.data)
      }
    } catch (error) {
      console.error('加载系统信息失败:', error)
    }
  }

  /**
   * 加载系统设置
   */
  const loadSystemSettings = async () => {
    try {
      const res = await api.getSystemSettings()
      if (res.code === 200) {
        const settings = res.data
        // 设置注册表单
        registrationForm.setFieldsValue({
          registration_enabled: settings.registration_enabled === '1',
          email_verification_enabled: settings.email_verification_enabled === '1',
          default_quota_cpu: parseInt(settings.default_quota_cpu) || 2,
          default_quota_ram: parseInt(settings.default_quota_ram) || 4,
          default_quota_ssd: parseInt(settings.default_quota_ssd) || 20,
          default_quota_gpu: parseInt(settings.default_quota_gpu) || 0,
          default_quota_nat_ports: parseInt(settings.default_quota_nat_ports) || 5,
          default_quota_web_proxy: parseInt(settings.default_quota_web_proxy) || 0,
          default_quota_bandwidth_up: parseInt(settings.default_quota_bandwidth_up) || 10,
          default_quota_bandwidth_down: parseInt(settings.default_quota_bandwidth_down) || 10,
          default_quota_traffic: parseInt(settings.default_quota_traffic) || 100,
          default_can_create_vm: settings.default_can_create_vm !== '0',
          default_can_modify_vm: settings.default_can_modify_vm !== '0',
          default_can_delete_vm: settings.default_can_delete_vm !== '0',
        })
        // 设置邮件表单
        emailForm.setFieldsValue({
          resend_email: settings.resend_email || '',
          resend_domain: settings.resend_domain || '',
          resend_apikey: settings.resend_apikey || '',
        })
      }
    } catch (error) {
      console.error('加载系统设置失败:', error)
    }
  }

  /**
   * 切换Token可见性
   */
  const toggleTokenVisibility = () => {
    setTokenVisible(!tokenVisible)
  }

  /**
   * 复制Token
   */
  const copyToken = () => {
    navigator.clipboard.writeText(currentToken)
    message.success('Token已复制到剪贴板')
  }

  /**
   * 设置新Token
   */
  const setNewToken = async (values: { newToken: string }) => {
    try {
      setLoading(true)
      const res = await api.setToken(values.newToken)
      if (res.code === 200) {
        setCurrentToken(res.data.token)
        message.success('Token设置成功')
      } else {
        message.error(res.msg || '设置失败')
      }
    } catch (error) {
      message.error('设置Token失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 重置Token
   */
  const resetToken = async () => {
    try {
      setLoading(true)
      const res = await api.resetToken()
      if (res.code === 200) {
        setCurrentToken(res.data.token)
        message.success(`Token已重置: ${res.data.token}`)
      } else {
        message.error(res.msg || '重置失败')
      }
    } catch (error) {
      message.error('重置Token失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 保存配置
   */
  const saveConfig = async () => {
    try {
      setLoading(true)
      const res = await api.saveSystemConfig()
      if (res.code === 200) {
        message.success('配置已保存')
      } else {
        message.error(res.msg || '保存失败')
      }
    } catch (error) {
      message.error('保存配置失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 重新加载配置
   */
  const loadConfig = async () => {
    try {
      setLoading(true)
      const res = await api.loadSystemConfig()
      if (res.code === 200) {
        message.success('配置已重新加载')
        loadSystemInfo()
      } else {
        message.error(res.msg || '加载失败')
      }
    } catch (error) {
      message.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 保存注册设置
   */
  const saveRegistrationSettings = async (values: any) => {
    try {
      setLoading(true)
      const data = {
        registration_enabled: values.registration_enabled ? '1' : '0',
        email_verification_enabled: values.email_verification_enabled ? '1' : '0',
        default_quota_cpu: values.default_quota_cpu.toString(),
        default_quota_ram: values.default_quota_ram.toString(),
        default_quota_ssd: values.default_quota_ssd.toString(),
        default_quota_gpu: values.default_quota_gpu.toString(),
        default_quota_nat_ports: values.default_quota_nat_ports.toString(),
        default_quota_web_proxy: values.default_quota_web_proxy.toString(),
        default_quota_bandwidth_up: values.default_quota_bandwidth_up.toString(),
        default_quota_bandwidth_down: values.default_quota_bandwidth_down.toString(),
        default_quota_traffic: values.default_quota_traffic.toString(),
        default_can_create_vm: values.default_can_create_vm ? '1' : '0',
        default_can_modify_vm: values.default_can_modify_vm ? '1' : '0',
        default_can_delete_vm: values.default_can_delete_vm ? '1' : '0',
      }
      const res = await api.updateSystemSettings(data)
      if (res.code === 200) {
        message.success('注册设置已保存')
      } else {
        message.error(res.msg || '保存失败')
      }
    } catch (error) {
      message.error('保存注册设置失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 保存邮件设置
   */
  const saveEmailSettings = async (values: any) => {
    try {
      setLoading(true)
      const res = await api.updateSystemSettings(values)
      if (res.code === 200) {
        message.success('邮件配置已保存')
      } else {
        message.error(res.msg || '保存失败')
      }
    } catch (error) {
      message.error('保存邮件配置失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 发送测试邮件
   */
  const sendTestEmail = async (values: any) => {
    try {
      setLoading(true)
      const emailValues = emailForm.getFieldsValue()
      const data = {
        test_email: values.test_email,
        subject: values.subject,
        body: values.body,
        resend_email: emailValues.resend_email,
        resend_apikey: emailValues.resend_apikey,
      }
      const res = await api.sendTestEmail(data)
      if (res.code === 200) {
        message.success('测试邮件发送成功，请查收')
      } else {
        message.error(res.msg || '发送测试邮件失败')
      }
    } catch (error) {
      message.error('发送测试邮件失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
          <span className="text-gray-600">⚙️</span>
          系统设置
        </h1>
        <p className="text-gray-600 mt-1">管理访问Token和系统配置</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Token管理 */}
        <Card title={<span><span className="text-blue-600">🔑</span> 访问Token管理</span>} className="shadow-sm">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">当前Token</label>
              <div className="flex gap-2">
                <Input
                  type={tokenVisible ? 'text' : 'password'}
                  value={tokenVisible ? currentToken : '••••••••••••••••'}
                  readOnly
                  className="flex-1"
                />
                <Button icon={tokenVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />} onClick={toggleTokenVisibility} />
                <Button icon={<CopyOutlined />} onClick={copyToken} />
              </div>
            </div>

            <div className="border-t pt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">设置新Token</label>
              <Form onFinish={setNewToken}>
                <div className="flex gap-2">
                  <Form.Item name="newToken" className="flex-1 mb-0">
                    <Input placeholder="留空则自动生成随机Token" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading}>设置</Button>
                </div>
              </Form>
            </div>

            <Button type="default" danger block icon={<ReloadOutlined />} onClick={resetToken} loading={loading}>
              重置Token
            </Button>

            <Alert
              message="安全提示"
              description="重置Token后，所有使用旧Token的API调用都将失效。请确保更新所有相关配置。"
              type="warning"
              showIcon
            />
          </div>
        </Card>

        {/* API文档 */}
        <Card title={<span><span className="text-green-600">🔌</span> API接口说明</span>} className="shadow-sm">
          <div className="space-y-3 text-sm">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="font-medium text-gray-800 mb-1">认证方式</p>
              <p className="text-gray-600">在请求头中添加：</p>
              <code className="block mt-1 bg-gray-200 px-2 py-1 rounded text-xs">
                Authorization: Bearer YOUR_TOKEN
              </code>
            </div>

            <div className="border-t pt-3">
              <p className="font-medium text-gray-800 mb-2">主要接口</p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">GET</span>
                  <code className="text-xs text-gray-600">/api/hosts</code>
                  <span className="text-xs text-gray-500">- 获取主机列表</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">POST</span>
                  <code className="text-xs text-gray-600">/api/hosts</code>
                  <span className="text-xs text-gray-500">- 添加主机</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">GET</span>
                  <code className="text-xs text-gray-600">/api/hosts/{'{name}'}/vms</code>
                  <span className="text-xs text-gray-500">- 获取虚拟机列表</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">POST</span>
                  <code className="text-xs text-gray-600">/api/hosts/{'{name}'}/vms</code>
                  <span className="text-xs text-gray-500">- 创建虚拟机</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">POST</span>
                  <code className="text-xs text-gray-600">/api/hosts/{'{name}'}/vms/{'{uuid}'}/power</code>
                  <span className="text-xs text-gray-500">- 电源操作</span>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* 数据管理 */}
        <Card title={<span><span className="text-purple-600">💾</span> 数据管理</span>} className="shadow-sm">
          <div className="space-y-3">
            <Button
              block
              icon={<SaveOutlined />}
              onClick={saveConfig}
              loading={loading}
              className="h-auto py-3 text-left"
            >
              <div className="ml-2">
                <p className="text-sm font-semibold">保存配置</p>
                <p className="text-xs text-gray-600">将当前配置保存到文件</p>
              </div>
            </Button>

            <Button
              block
              icon={<FolderOpenOutlined />}
              onClick={loadConfig}
              loading={loading}
              className="h-auto py-3 text-left"
            >
              <div className="ml-2">
                <p className="text-sm font-semibold">重新加载配置</p>
                <p className="text-xs text-gray-600">从文件重新加载配置</p>
              </div>
            </Button>
          </div>
        </Card>

        {/* 系统信息 */}
        <Card title={<span><span className="text-gray-600">ℹ️</span> 系统信息</span>} className="shadow-sm">
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">系统名称</span>
              <span className="font-medium text-gray-800">OpenIDCS</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">版本</span>
              <span className="font-medium text-gray-800">1.0.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">主机数量</span>
              <span className="font-medium text-gray-800">{systemInfo.host_count}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">虚拟机数量</span>
              <span className="font-medium text-gray-800">{systemInfo.vm_count}</span>
            </div>
          </div>
        </Card>

        {/* 用户注册设置 */}
        <Card title={<span><span className="text-indigo-600">👥</span> 用户注册设置</span>} className="shadow-sm">
          <Form form={registrationForm} onFinish={saveRegistrationSettings} layout="vertical">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">开放注册</p>
                  <p className="text-xs text-gray-600">允许新用户注册账号</p>
                </div>
                <Form.Item name="registration_enabled" valuePropName="checked" className="mb-0">
                  <Switch />
                </Form.Item>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">邮箱验证</p>
                  <p className="text-xs text-gray-600">注册时需要验证邮箱</p>
                </div>
                <Form.Item name="email_verification_enabled" valuePropName="checked" className="mb-0">
                  <Switch />
                </Form.Item>
              </div>

              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-800 mb-3">新用户默认资源配额</h4>
                <div className="grid grid-cols-2 gap-3">
                  <Form.Item name="default_quota_cpu" label="CPU核心" className="mb-2">
                    <InputNumber min={0} max={32} className="w-full" />
                  </Form.Item>
                  <Form.Item name="default_quota_ram" label="内存(GB)" className="mb-2">
                    <InputNumber min={0} max={128} className="w-full" />
                  </Form.Item>
                  <Form.Item name="default_quota_ssd" label="磁盘(GB)" className="mb-2">
                    <InputNumber min={0} max={1000} className="w-full" />
                  </Form.Item>
                  <Form.Item name="default_quota_gpu" label="GPU" className="mb-2">
                    <InputNumber min={0} max={8} className="w-full" />
                  </Form.Item>
                  <Form.Item name="default_quota_nat_ports" label="NAT端口" className="mb-2">
                    <InputNumber min={0} max={100} className="w-full" />
                  </Form.Item>
                  <Form.Item name="default_quota_web_proxy" label="Web代理" className="mb-2">
                    <InputNumber min={0} max={10} className="w-full" />
                  </Form.Item>
                  <Form.Item name="default_quota_bandwidth_up" label="上行带宽(Mbps)" className="mb-2">
                    <InputNumber min={0} max={1000} className="w-full" />
                  </Form.Item>
                  <Form.Item name="default_quota_bandwidth_down" label="下行带宽(Mbps)" className="mb-2">
                    <InputNumber min={0} max={1000} className="w-full" />
                  </Form.Item>
                  <Form.Item name="default_quota_traffic" label="每月流量(GB)" className="mb-2 col-span-2">
                    <InputNumber min={0} max={10000} className="w-full" />
                  </Form.Item>
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-800 mb-3">新用户默认权限</h4>
                <div className="space-y-2">
                  <Form.Item name="default_can_create_vm" valuePropName="checked" className="mb-0">
                    <Checkbox>允许创建虚拟机</Checkbox>
                  </Form.Item>
                  <Form.Item name="default_can_modify_vm" valuePropName="checked" className="mb-0">
                    <Checkbox>允许修改虚拟机</Checkbox>
                  </Form.Item>
                  <Form.Item name="default_can_delete_vm" valuePropName="checked" className="mb-0">
                    <Checkbox>允许删除虚拟机</Checkbox>
                  </Form.Item>
                </div>
              </div>

              <Button type="primary" htmlType="submit" block loading={loading} icon={<SaveOutlined />}>
                保存设置
              </Button>
            </div>
          </Form>
        </Card>

        {/* 邮件服务配置 */}
        <Card title={<span><span className="text-red-600">📧</span> 邮件服务配置</span>} className="shadow-sm">
          <Alert
            message={
              <span>
                Resend 邮件服务，访问{' '}
                <a href="https://resend.com" target="_blank" rel="noopener noreferrer" className="underline">
                  resend.com
                </a>{' '}
                获取API Key
              </span>
            }
            type="info"
            className="mb-4"
          />

          <Form form={emailForm} onFinish={saveEmailSettings} layout="vertical">
            <Form.Item name="resend_email" label="发件邮箱">
              <Input placeholder="noreply@yourdomain.com" />
            </Form.Item>

            <Form.Item name="resend_domain" label="发送域名">
              <Input placeholder="yourdomain.com" />
            </Form.Item>

            <Form.Item name="resend_apikey" label="API Key">
              <Input.Password placeholder="re_xxxxxxxxxxxxxxxx" />
            </Form.Item>

            <Button type="primary" htmlType="submit" block loading={loading} icon={<SaveOutlined />}>
              保存配置
            </Button>
          </Form>

          <div className="border-t mt-4 pt-4">
            <h4 className="text-sm font-medium text-gray-800 mb-3">测试邮件发送</h4>
            <Form form={testEmailForm} onFinish={sendTestEmail} layout="vertical">
              <Form.Item name="test_email" label="收件邮箱" rules={[{ required: true, type: 'email', message: '请输入有效的邮箱地址' }]}>
                <Input placeholder="test@example.com" />
              </Form.Item>

              <Form.Item name="subject" label="邮件标题" initialValue="OpenIDCS - 测试邮件">
                <Input placeholder="OpenIDCS - 测试邮件" />
              </Form.Item>

              <Form.Item name="body" label="邮件正文" initialValue="您好，这是一封来自 OpenIDCS 系统的测试邮件。如果您收到这封邮件，说明邮件服务配置正常。————OpenIDCS 系统">
                <TextArea rows={4} placeholder="请输入邮件正文内容..." />
              </Form.Item>

              <Button type="primary" htmlType="submit" block loading={loading} icon={<MailOutlined />} className="bg-green-600 hover:bg-green-700">
                发送测试邮件
              </Button>
            </Form>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default Settings
