import { useEffect, useState } from 'react'
import { Table, Button, Space, Tag, Modal, Form, Input, InputNumber, message, Select, Card, Row, Col, Checkbox } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, GlobalOutlined, LockOutlined, UnlockOutlined, CloudServerOutlined } from '@ant-design/icons'
import api from '@/utils/apis.ts'
import type { ColumnsType } from 'antd/es/table'

/**
 * Web代理数据接口
 */
interface WebProxy {
  host_name: string
  vm_uuid: string
  vm_name: string
  proxy_index: number
  domain: string
  backend_ip: string
  backend_port: number
  ssl_enabled: boolean
  description: string
}

/**
 * 主机数据接口
 */
interface Host {
  server_name: string
  server_type: string
}

/**
 * 虚拟机数据接口
 */
interface VM {
  vm_uuid: string
  vm_name: string
}

/**
 * Web反向代理管理页面
 */
function HttpProxys() {
  // 状态管理
  const [proxys, setProxys] = useState<WebProxy[]>([])
  const [filteredProxys, setFilteredProxys] = useState<WebProxy[]>([])
  const [hosts, setHosts] = useState<Host[]>([])
  const [vms, setVms] = useState<{ [key: string]: VM[] }>({})
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [isEdit, setIsEdit] = useState(false)
  const [editingProxy, setEditingProxy] = useState<WebProxy | null>(null)
  
  // 筛选条件
  const [searchText, setSearchText] = useState('')
  const [hostFilter, setHostFilter] = useState('')
  const [protocolFilter, setProtocolFilter] = useState('')
  
  const [form] = Form.useForm()

  /**
   * 加载主机列表
   */
  const loadHosts = async () => {
    try {
      const response = await api.getHosts()
      if (response.code === 200) {
        // 确保hosts始终是数组
        const hostData = response.data
        setHosts(Array.isArray(hostData) ? hostData : [])
      }
    } catch (error) {
      console.error('加载主机列表失败:', error)
      setHosts([]) // 出错时设置为空数组
    }
  }

  /**
   * 加载指定主机的虚拟机列表
   */
  const loadVMsForHost = async (hostName: string) => {
    try {
      const response = await api.getVMs(hostName)
      if (response.code === 200) {
        setVms(prev => ({ ...prev, [hostName]: response.data || [] }))
        return response.data || []
      }
    } catch (error) {
      console.error('加载虚拟机列表失败:', error)
    }
    return []
  }

  /**
   * 加载代理列表
   */
  const loadProxys = async () => {
    try {
      setLoading(true)
      
      // 临时方案：通过遍历主机和虚拟机来获取代理列表
      // TODO: 等待后端实现 /api/client/proxys/list 接口后可以直接调用
      const proxyList: WebProxy[] = []
      
      // 获取所有主机
      const hostsResponse = await api.getHosts()
      if (hostsResponse.code === 200) {
        const hostList = Array.isArray(hostsResponse.data) ? hostsResponse.data : []
        
        // 遍历每个主机获取虚拟机列表
        for (const host of hostList) {
          try {
            const vmsResponse = await api.getVMs(host.server_name)
            if (vmsResponse.code === 200 && Array.isArray(vmsResponse.data)) {
              // 遍历每个虚拟机获取代理配置
              for (const vm of vmsResponse.data) {
                try {
                  const proxysResponse = await api.getProxyConfigs(host.server_name, vm.vm_uuid)
                  if (proxysResponse.code === 200 && Array.isArray(proxysResponse.data)) {
                    // 将代理配置添加到列表中
                    proxysResponse.data.forEach((proxy: any) => {
                      proxyList.push({
                        host_name: host.server_name,
                        vm_uuid: vm.vm_uuid,
                        vm_name: vm.vm_name || vm.vm_uuid,
                        proxy_index: proxy.proxy_index,
                        domain: proxy.domain,
                        backend_ip: proxy.backend_ip || '',
                        backend_port: proxy.backend_port,
                        ssl_enabled: proxy.ssl_enabled || false,
                        description: proxy.description || ''
                      })
                    })
                  }
                } catch (error) {
                  // 忽略单个虚拟机的错误，继续处理其他虚拟机
                  console.error(`获取虚拟机 ${vm.vm_uuid} 的代理配置失败:`, error)
                }
              }
            }
          } catch (error) {
            // 忽略单个主机的错误，继续处理其他主机
            console.error(`获取主机 ${host.server_name} 的虚拟机列表失败:`, error)
          }
        }
      }
      
      setProxys(proxyList)
      setFilteredProxys(proxyList)
    } catch (error) {
      console.error('加载代理列表失败:', error)
      message.error('加载代理列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHosts()
    loadProxys()
  }, [])

  /**
   * 筛选代理列表
   */
  useEffect(() => {
    let filtered = [...proxys]
    
    // 搜索筛选
    if (searchText) {
      const search = searchText.toLowerCase()
      filtered = filtered.filter(proxy => 
        proxy.domain.toLowerCase().includes(search) ||
        proxy.vm_name.toLowerCase().includes(search)
      )
    }
    
    // 主机筛选
    if (hostFilter) {
      filtered = filtered.filter(proxy => proxy.host_name === hostFilter)
    }
    
    // 协议筛选
    if (protocolFilter) {
      if (protocolFilter === 'https') {
        filtered = filtered.filter(proxy => proxy.ssl_enabled)
      } else if (protocolFilter === 'http') {
        filtered = filtered.filter(proxy => !proxy.ssl_enabled)
      }
    }
    
    setFilteredProxys(filtered)
  }, [searchText, hostFilter, protocolFilter, proxys])

  /**
   * 计算统计数据
   */
  const statistics = {
    total: proxys.length,
    http: proxys.filter(p => !p.ssl_enabled).length,
    https: proxys.filter(p => p.ssl_enabled).length,
    hosts: new Set(proxys.map(p => p.host_name)).size
  }

  /**
   * 显示添加模态框
   */
  const showAddModal = () => {
    setIsEdit(false)
    setEditingProxy(null)
    form.resetFields()
    setModalVisible(true)
  }

  /**
   * 显示编辑模态框
   */
  const showEditModal = (proxy: WebProxy) => {
    setIsEdit(true)
    setEditingProxy(proxy)
    
    // 加载该主机的虚拟机列表
    loadVMsForHost(proxy.host_name).then(() => {
      form.setFieldsValue({
        host_name: proxy.host_name,
        vm_uuid: proxy.vm_uuid,
        domain: proxy.domain,
        backend_ip: proxy.backend_ip,
        backend_port: proxy.backend_port,
        ssl_enabled: proxy.ssl_enabled,
        description: proxy.description
      })
    })
    
    setModalVisible(true)
  }

  /**
   * 处理主机选择变化
   */
  const handleHostChange = (hostName: string) => {
    form.setFieldValue('vm_uuid', undefined)
    if (hostName) {
      loadVMsForHost(hostName)
    }
  }

  /**
   * 创建或更新代理
   */
  const handleSubmit = async (values: any) => {
    try {
      if (isEdit && editingProxy) {
        // 编辑模式
        const response = await api.updateWebProxy(
          editingProxy.host_name,
          editingProxy.vm_uuid,
          editingProxy.proxy_index,
          {
            domain: values.domain,
            backend_ip: values.backend_ip || '',
            backend_port: values.backend_port,
            ssl_enabled: values.ssl_enabled || false,
            description: values.description || ''
          }
        )
        if (response.code === 200) {
          message.success('代理更新成功')
          setModalVisible(false)
          form.resetFields()
          loadProxys()
        } else {
          message.error(response.msg || '更新失败')
        }
      } else {
        // 添加模式
        const response = await api.createWebProxy(
          values.host_name,
          values.vm_uuid,
          {
            domain: values.domain,
            backend_ip: values.backend_ip || '',
            backend_port: values.backend_port,
            ssl_enabled: values.ssl_enabled || false,
            description: values.description || ''
          }
        )
        if (response.code === 200) {
          message.success('代理创建成功')
          setModalVisible(false)
          form.resetFields()
          loadProxys()
        } else {
          message.error(response.msg || '创建失败')
        }
      }
    } catch (error) {
      message.error(isEdit ? '更新代理失败' : '创建代理失败')
    }
  }

  /**
   * 删除代理
   */
  const handleDelete = async (proxy: WebProxy) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个反向代理配置吗？',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await api.deleteWebProxy(
            proxy.host_name,
            proxy.vm_uuid,
            proxy.proxy_index
          )
          if (response.code === 200) {
            message.success('删除成功')
            loadProxys()
          } else {
            message.error(response.msg || '删除失败')
          }
        } catch (error) {
          message.error('删除代理失败')
        }
      }
    })
  }

  /**
   * 表格列配置
   */
  const columns: ColumnsType<WebProxy> = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
      render: (domain: string, record: WebProxy) => (
        <a
          href={`http${record.ssl_enabled ? 's' : ''}://${domain}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#2563eb', fontWeight: 500 }}
        >
          {domain}
        </a>
      )
    },
    {
      title: '主机',
      dataIndex: 'host_name',
      key: 'host_name',
      render: (name: string) => <Tag>{name}</Tag>
    },
    {
      title: '虚拟机',
      dataIndex: 'vm_name',
      key: 'vm_name',
      render: (name: string) => <Tag color="default">{name}</Tag>
    },
    {
      title: '后端地址',
      key: 'backend',
      render: (_, record: WebProxy) => (
        <code style={{ fontSize: '0.875rem' }}>
          {record.backend_ip || 'auto'}:{record.backend_port}
        </code>
      )
    },
    {
      title: '协议',
      key: 'protocol',
      render: (_, record: WebProxy) => (
        <Tag
          icon={record.ssl_enabled ? <LockOutlined /> : <UnlockOutlined />}
          color={record.ssl_enabled ? 'success' : 'default'}
        >
          {record.ssl_enabled ? 'HTTPS' : 'HTTP'}
        </Tag>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => <span style={{ color: '#6b7280' }}>{desc || '-'}</span>
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record: WebProxy) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#1f2937', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
            <GlobalOutlined style={{ color: '#2563eb', fontSize: '2rem' }} />
            Web反向代理管理
          </h1>
          <p style={{ color: '#6b7280', marginTop: '8px', marginBottom: 0 }}>管理所有虚拟机的Web反向代理配置</p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={showAddModal}
          size="large"
        >
          添加反向代理
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ color: '#6b7280', fontSize: '0.875rem', margin: 0 }}>总代理数</p>
                <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', margin: '4px 0 0 0' }}>
                  {statistics.total}
                </p>
              </div>
              <GlobalOutlined style={{ fontSize: '2.5rem', color: '#3b82f6' }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ color: '#6b7280', fontSize: '0.875rem', margin: 0 }}>HTTP代理</p>
                <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', margin: '4px 0 0 0' }}>
                  {statistics.http}
                </p>
              </div>
              <UnlockOutlined style={{ fontSize: '2.5rem', color: '#6b7280' }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ color: '#6b7280', fontSize: '0.875rem', margin: 0 }}>HTTPS代理</p>
                <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', margin: '4px 0 0 0' }}>
                  {statistics.https}
                </p>
              </div>
              <LockOutlined style={{ fontSize: '2.5rem', color: '#10b981' }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ color: '#6b7280', fontSize: '0.875rem', margin: 0 }}>主机数</p>
                <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', margin: '4px 0 0 0' }}>
                  {statistics.hosts}
                </p>
              </div>
              <CloudServerOutlined style={{ fontSize: '2.5rem', color: '#8b5cf6' }} />
            </div>
          </Card>
        </Col>
      </Row>

      {/* 筛选和搜索 */}
      <Card style={{ marginBottom: '24px' }}>
        <Space size="middle" style={{ width: '100%', flexWrap: 'wrap' }}>
          <Input
            placeholder="搜索域名、虚拟机名称..."
            style={{ width: 300 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
          />
          <Select
            placeholder="所有主机"
            style={{ width: 150 }}
            value={hostFilter || undefined}
            onChange={setHostFilter}
            allowClear
          >
            {Array.isArray(hosts) && hosts.map(host => (
              <Select.Option key={host.server_name} value={host.server_name}>
                {host.server_name}
              </Select.Option>
            ))}
          </Select>
          <Select
            placeholder="所有协议"
            style={{ width: 120 }}
            value={protocolFilter || undefined}
            onChange={setProtocolFilter}
            allowClear
          >
            <Select.Option value="http">HTTP</Select.Option>
            <Select.Option value="https">HTTPS</Select.Option>
          </Select>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadProxys}
          >
            刷新
          </Button>
        </Space>
      </Card>

      {/* 代理列表表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredProxys}
          rowKey={(record) => `${record.host_name}-${record.vm_uuid}-${record.proxy_index}`}
          loading={loading}
          locale={{
            emptyText: (
              <div style={{ padding: '48px 0', textAlign: 'center' }}>
                <GlobalOutlined style={{ fontSize: '5rem', color: '#d1d5db' }} />
                <p style={{ color: '#6b7280', marginTop: '16px', fontSize: '1.125rem' }}>暂无反向代理配置</p>
                <Button type="primary" onClick={showAddModal} style={{ marginTop: '16px' }}>
                  添加第一个代理
                </Button>
              </div>
            )
          }}
        />
      </Card>

      {/* 添加/编辑代理模态框 */}
      <Modal
        title={isEdit ? '编辑反向代理' : '添加反向代理'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        width={600}
        okText={isEdit ? '保存' : '添加'}
        cancelText="取消"
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="host_name"
            label="主机"
            rules={[{ required: true, message: '请选择主机' }]}
          >
            <Select
              placeholder="请选择主机"
              onChange={handleHostChange}
              disabled={isEdit}
            >
              {Array.isArray(hosts) && hosts.map(host => (
                <Select.Option key={host.server_name} value={host.server_name}>
                  {host.server_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="vm_uuid"
            label="虚拟机"
            rules={[{ required: true, message: '请选择虚拟机' }]}
          >
            <Select
              placeholder="请先选择主机"
              disabled={isEdit || !form.getFieldValue('host_name')}
            >
              {(vms[form.getFieldValue('host_name')] || []).map(vm => (
                <Select.Option key={vm.vm_uuid} value={vm.vm_uuid}>
                  {vm.vm_name || vm.vm_uuid}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="domain"
            label="域名"
            rules={[{ required: true, message: '请输入域名' }]}
          >
            <Input placeholder="example.com" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="backend_ip"
                label="后端IP"
              >
                <Input placeholder="自动获取" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="backend_port"
                label="后端端口"
                rules={[{ required: true, message: '请输入后端端口' }]}
                initialValue={80}
              >
                <InputNumber
                  min={1}
                  max={65535}
                  style={{ width: '100%' }}
                  placeholder="80"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea
              rows={3}
              placeholder="可选的描述信息"
            />
          </Form.Item>

          <Form.Item
            name="ssl_enabled"
            valuePropName="checked"
          >
            <Checkbox>启用HTTPS (SSL/TLS)</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default HttpProxys
