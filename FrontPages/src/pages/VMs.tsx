import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import {
  Card,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Spin,
  Empty,
  Row,
  Col,
  Breadcrumb,
  Divider,
  Tooltip,
  Checkbox,
  Alert,
  Typography
} from 'antd'
import {
  PlusOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
  RadarChartOutlined,
  DesktopOutlined,
  PoweroffOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  RedoOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'
import api from '@/services/api'

const { Text } = Typography

/**
 * 虚拟机配置接口
 */
interface VMConfig {
  vm_uuid: string
  os_name: string
  os_pass?: string
  vc_pass?: string
  vc_port?: number
  cpu_num: number
  mem_num: number
  hdd_num: number
  gpu_num?: number
  gpu_mem?: number
  speed_u?: number
  speed_d?: number
  nat_num?: number
  flu_num?: number
  web_num?: number
  nic_all: Record<string, NicConfig>
}

/**
 * 网卡配置接口
 */
interface NicConfig {
  nic_type: string
  ip4_addr?: string
  ip6_addr?: string
  mac_addr?: string
}

/**
 * 虚拟机状态接口
 */
interface VMStatus {
  ac_status: string
}

/**
 * 虚拟机数据接口
 */
interface VM {
  config: VMConfig
  status: VMStatus[]
}

/**
 * 主机配置接口
 */
interface HostConfig {
  filter_name: string
  system_maps: Record<string, [string, number]>
  images_maps: Record<string, string>
  server_type: string
  ban_init: string[]
  ban_edit: string[]
  messages: string[]
}

/**
 * 用户配额接口
 */
interface UserQuota {
  quota_cpu: number
  used_cpu: number
  quota_ram: number
  used_ram: number
  quota_ssd: number
  used_ssd: number
  quota_nat_ips: number
  used_nat_ips: number
  quota_pub_ips: number
  used_pub_ips: number
  quota_traffic: number
  used_traffic: number
  quota_upload_bw: number
  used_upload_bw: number
  quota_download_bw: number
  used_download_bw: number
  quota_nat: number
  used_nat: number
  quota_web: number
  used_web: number
}

/**
 * 虚拟机列表页面
 */
function VMs() {
  const navigate = useNavigate()
  const { hostName } = useParams<{ hostName: string }>()
  const [vms, setVMs] = useState<Record<string, VM>>({})
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [powerModalVisible, setPowerModalVisible] = useState(false)
  const [editMode, setEditMode] = useState<'add' | 'edit'>('add')
  const [currentVmUuid, setCurrentVmUuid] = useState('')
  const [hostConfig, setHostConfig] = useState<HostConfig | null>(null)
  const [userQuota, setUserQuota] = useState<UserQuota | null>(null)
  const [form] = Form.useForm()
  const [nicList, setNicList] = useState<Array<{ key: number; name: string }>>([])
  const [nicCounter, setNicCounter] = useState(0)
  const [selectedOsMinDisk, setSelectedOsMinDisk] = useState(0)

  // 删除确认模态框状态
  const [deleteModalVisible, setDeleteModalVisible] = useState(false)
  const [deleteConfirmInput, setDeleteConfirmInput] = useState('')
  const [deleteTargetUuid, setDeleteTargetUuid] = useState('')

  // 编辑保存确认模态框状态
  const [saveConfirmModalVisible, setSaveConfirmModalVisible] = useState(false)
  const [forceShutdownConfirmed, setForceShutdownConfirmed] = useState(false)
  const [pendingSubmitValues, setPendingSubmitValues] = useState<any>(null)

  // 状态文字映射
  const statusMap: Record<string, { text: string; color: string; pulse?: boolean }> = {
    STOPPED: { text: '已停止', color: 'default' },
    STARTED: { text: '运行中', color: 'success', pulse: true },
    SUSPEND: { text: '已暂停', color: 'warning' },
    ON_STOP: { text: '停止中', color: 'processing' },
    ON_OPEN: { text: '启动中', color: 'processing' },
    CRASHED: { text: '已崩溃', color: 'error' },
    UNKNOWN: { text: '未知', color: 'default' },
  }

  /**
   * 加载主机信息（获取system_maps等配置）
   */
  const loadHostInfo = async () => {
    if (!hostName) return
    try {
      const result = await api.get(`/api/client/os-images/${hostName}`)
      if (result.code === 200) {
        setHostConfig(result.data)
      }
    } catch (error) {
      console.error('加载主机信息失败:', error)
    }
  }

  /**
   * 加载用户配额信息
   */
  const loadUserQuota = async () => {
    try {
      const result = await api.get('/api/users/current')
      if (result.code === 200) {
        setUserQuota(result.data)
      }
    } catch (error) {
      console.error('获取用户配额失败:', error)
    }
  }

  /**
   * 加载虚拟机列表
   */
  const loadVMs = async () => {
    if (!hostName) return
    try {
      setLoading(true)
      const result = await api.get(`/api/client/detail/${hostName}`)
      if (result.code === 200) {
        setVMs(result.data || {})
      }
    } catch (error) {
      message.error('加载虚拟机列表失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 扫描虚拟机
   */
  const handleScan = async () => {
    if (!hostName) return
    try {
      const hide = message.loading('正在扫描虚拟机...', 0)
      const result = await api.post(`/api/client/scaner/${hostName}`, {})
      hide()
      if (result.code === 200) {
        const { scanned = 0, added = 0 } = result.data || {}
        message.success(`扫描完成！扫描到 ${scanned} 台虚拟机，新增 ${added} 台`)
        loadVMs()
      } else {
        message.error(result.msg || '扫描失败')
      }
    } catch (error) {
      message.error('扫描虚拟机失败')
    }
  }

  useEffect(() => {
    loadHostInfo()
    loadUserQuota()
    loadVMs()
  }, [hostName])

  /**
   * 生成随机字符串（包含字母和数字）
   */
  const generateRandomString = (length: number): string => {
    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    const numbers = '0123456789'
    
    // 确保至少包含一个字母和一个数字
    let result = ''
    result += letters.charAt(Math.floor(Math.random() * letters.length))
    result += numbers.charAt(Math.floor(Math.random() * numbers.length))
    
    const allChars = letters + numbers
    for (let i = result.length; i < length; i++) {
      result += allChars.charAt(Math.floor(Math.random() * allChars.length))
    }
    return result.split('').sort(() => Math.random() - 0.5).join('')
  }

  /**
   * 生成随机VNC端口
   */
  const generateRandomVncPort = (): number => {
    return Math.floor(Math.random() * (6999 - 5900 + 1)) + 5900
  }

  /**
   * 密码复杂度验证
   */
  const validatePassword = (_: any, value: string) => {
    if (!value) {
      return Promise.resolve() // 允许空密码（如果不强制）
    }
    if (value.length < 8) {
      return Promise.reject(new Error('密码长度至少8位'))
    }
    const hasLetter = /[a-zA-Z]/.test(value)
    const hasNumber = /[0-9]/.test(value)
    if (!hasLetter || !hasNumber) {
      return Promise.reject(new Error('密码必须包含字母和数字'))
    }
    return Promise.resolve()
  }

  /**
   * 检查字段是否被禁用
   */
  const isFieldDisabled = (fieldName: string) => {
    if (!hostConfig) return false
    const banList = editMode === 'add' ? hostConfig.ban_init : hostConfig.ban_edit
    return banList && banList.includes(fieldName)
  }

  /**
   * 检查资源配额
   */
  const checkResourceQuota = (): { canCreate: boolean; errors: string[] } => {
    if (!userQuota) return { canCreate: true, errors: [] }
    const errors: string[] = []
    if (userQuota.quota_cpu <= 0 || userQuota.used_cpu >= userQuota.quota_cpu) {
      errors.push('CPU配额不足')
    }
    if (userQuota.quota_ram <= 0 || userQuota.used_ram >= userQuota.quota_ram) {
      errors.push('内存配额不足')
    }
    if (userQuota.quota_ssd <= 0 || userQuota.used_ssd >= userQuota.quota_ssd) {
      errors.push('硬盘配额不足')
    }
    const availableNatIps = userQuota.quota_nat_ips - userQuota.used_nat_ips
    const availablePubIps = userQuota.quota_pub_ips - userQuota.used_pub_ips
    if (availableNatIps <= 0 && availablePubIps <= 0) {
      errors.push('无可用IP配额')
    }
    return { canCreate: errors.length === 0, errors }
  }

  /**
   * 打开创建虚拟机对话框
   */
  const handleOpenCreate = () => {
    const quotaCheck = checkResourceQuota()
    if (!quotaCheck.canCreate) {
      Modal.error({
        title: '配额不足',
        content: `无法创建虚拟机：${quotaCheck.errors.join('，')}`,
      })
      return
    }

    setEditMode('add')
    setForceShutdownConfirmed(false)
    form.resetFields()
    
    // 生成随机UUID和密码
    const randomUuid = generateRandomString(8)
    const randomPass = generateRandomString(8)
    const randomPort = generateRandomVncPort()
    
    form.setFieldsValue({
      vm_uuid_suffix: randomUuid,
      os_pass: randomPass,
      vc_pass: randomPass,
      vc_port: randomPort,
      cpu_num: 2,
      mem_num: 2048,
      hdd_num: 20480,
      gpu_num: 0,
      gpu_mem: 128,
      speed_u: 100,
      speed_d: 100,
      flu_num: 102400,
      nat_num: 100,
      web_num: 100,
    })

    // 自动根据配额添加默认网卡
    if (userQuota) {
      const availableNatIps = userQuota.quota_nat_ips - userQuota.used_nat_ips
      const availablePubIps = userQuota.quota_pub_ips - userQuota.used_pub_ips
      let defaultType = 'nat'
      if (availableNatIps <= 0 && availablePubIps > 0) {
        defaultType = 'pub'
      }
      setNicList([{ key: 0, name: 'ethernet0', type: defaultType }])
      setNicCounter(1)
      form.setFieldsValue({
        nic_name_0: 'ethernet0',
        nic_type_0: defaultType
      })
    } else {
      setNicList([{ key: 0, name: 'ethernet0', type: 'nat' }])
      setNicCounter(1)
    }
    
    setModalVisible(true)
  }

  /**
   * 打开编辑虚拟机对话框
   */
  const handleOpenEdit = async (uuid: string) => {
    if (!hostName) return
    try {
      const result = await api.get(`/api/client/detail/${hostName}/${uuid}`)
      if (result.code === 200) {
        const vm = result.data
        const config = vm.config || {}
        
        setEditMode('edit')
        setForceShutdownConfirmed(false)
        setCurrentVmUuid(uuid)
        
        // 分离UUID前缀和后缀
        const prefix = hostConfig?.filter_name || ''
        const prefixWithHyphen = prefix ? (prefix.endsWith('-') ? prefix : prefix + '-') : ''
        let suffix = uuid
        if (prefixWithHyphen && uuid.startsWith(prefixWithHyphen)) {
          suffix = uuid.substring(prefixWithHyphen.length)
        }
        
        // 设置最小磁盘要求
        if (hostConfig?.system_maps && config.os_name) {
          const entry = Object.values(hostConfig.system_maps).find(([img]) => img === config.os_name)
          if (entry) {
            setSelectedOsMinDisk(entry[1] || 0)
          }
        }

        form.setFieldsValue({
          vm_uuid_suffix: suffix,
          os_name: config.os_name,
          os_pass: config.os_pass,
          vc_pass: config.vc_pass,
          vc_port: config.vc_port,
          cpu_num: config.cpu_num,
          mem_num: config.mem_num,
          hdd_num: config.hdd_num,
          gpu_num: config.gpu_num,
          gpu_mem: config.gpu_mem,
          speed_u: config.speed_u,
          speed_d: config.speed_d,
          nat_num: config.nat_num,
          flu_num: config.flu_num,
          web_num: config.web_num,
        })

        // 加载网卡配置
        const nicAll = config.nic_all || {}
        const nics = Object.entries(nicAll).map(([name, nicConfig], index) => ({
          key: index,
          name,
          type: nicConfig.nic_type
        }))
        setNicList(nics)
        setNicCounter(nics.length)
        
        // 设置网卡表单值
        Object.entries(nicAll).forEach(([name, nicConfig], index) => {
          form.setFieldsValue({
            [`nic_name_${index}`]: name,
            [`nic_type_${index}`]: nicConfig.nic_type,
            [`nic_ip_${index}`]: nicConfig.ip4_addr,
            [`nic_ip6_${index}`]: nicConfig.ip6_addr,
          })
        })
        
        setModalVisible(true)
      }
    } catch (error) {
      message.error('加载虚拟机信息失败')
    }
  }

  /**
   * 添加网卡
   */
  const handleAddNic = () => {
    // 检查配额
    if (userQuota) {
      const currentNatIps = nicList.filter(n => n.type === 'nat').length
      const currentPubIps = nicList.filter(n => n.type === 'pub').length
      const availableNatIps = userQuota.quota_nat_ips - userQuota.used_nat_ips
      const availablePubIps = userQuota.quota_pub_ips - userQuota.used_pub_ips
      
      if (currentNatIps >= availableNatIps && currentPubIps >= availablePubIps) {
         message.warning('IP配额已用完，无法添加更多网卡')
         return
      }
      
      let nextType = 'nat'
      if (currentNatIps >= availableNatIps) nextType = 'pub'
      
      setNicList([...nicList, { key: nicCounter, name: `ethernet${nicCounter}`, type: nextType }])
      // 设置默认值
      setTimeout(() => {
        form.setFieldsValue({
            [`nic_name_${nicCounter}`]: `ethernet${nicCounter}`,
            [`nic_type_${nicCounter}`]: nextType
        })
      }, 0)
    } else {
        setNicList([...nicList, { key: nicCounter, name: `ethernet${nicCounter}`, type: 'nat' }])
    }
    setNicCounter(nicCounter + 1)
  }

  /**
   * 移除网卡
   */
  const handleRemoveNic = (key: number) => {
    setNicList(nicList.filter(nic => nic.key !== key))
  }

  /**
   * 提交虚拟机表单
   */
  const handleSubmit = async (values: any) => {
    if (!hostName) return

    // 编辑模式需要二次确认
    if (editMode === 'edit') {
      setPendingSubmitValues(values)
      setForceShutdownConfirmed(false)
      setSaveConfirmModalVisible(true)
      return
    }

    await processSubmit(values)
  }

  /**
   * 处理实际的提交逻辑
   */
  const processSubmit = async (values: any) => {
    try {
      // 构建完整UUID
      const prefix = hostConfig?.filter_name || ''
      const prefixWithHyphen = prefix ? (prefix.endsWith('-') ? prefix : prefix + '-') : ''
      const fullUuid = prefixWithHyphen + values.vm_uuid_suffix

      // 收集网卡配置
      const nicAll: Record<string, NicConfig> = {}
      nicList.forEach((nic) => {
        const nicName = values[`nic_name_${nic.key}`] || nic.name
        nicAll[nicName] = {
          nic_type: values[`nic_type_${nic.key}`] || 'nat',
          ip4_addr: values[`nic_ip_${nic.key}`] || '',
          ip6_addr: values[`nic_ip6_${nic.key}`] || '',
        }
      })

      const vmData: VMConfig = {
        vm_uuid: fullUuid,
        os_name: values.os_name,
        os_pass: values.os_pass,
        vc_pass: values.vc_pass,
        vc_port: values.vc_port,
        cpu_num: values.cpu_num,
        mem_num: values.mem_num,
        hdd_num: values.hdd_num,
        gpu_num: values.gpu_num,
        gpu_mem: values.gpu_mem,
        speed_u: values.speed_u,
        speed_d: values.speed_d,
        nat_num: values.nat_num,
        flu_num: values.flu_num,
        web_num: values.web_num,
        nic_all: nicAll,
      }

      if (editMode === 'add') {
        const hide = message.loading('正在创建虚拟机...', 0)
        const result = await api.post(`/api/client/create/${hostName}`, vmData)
        hide()
        if (result.code === 200) {
          message.success('虚拟机创建成功')
          setModalVisible(false)
          loadVMs()
        } else {
          message.error(result.msg || '创建失败')
        }
      } else {
        const result = await api.put(`/api/client/update/${hostName}/${currentVmUuid}`, vmData)
        if (result.code === 200) {
          message.success('虚拟机配置已保存')
          setModalVisible(false)
          setSaveConfirmModalVisible(false)
          loadVMs()
        } else {
          message.error(result.msg || '保存失败')
        }
      }
    } catch (error) {
      message.error('操作失败')
    }
  }

  /**
   * 确认保存编辑
   */
  const handleConfirmSave = () => {
    if (pendingSubmitValues) {
      processSubmit(pendingSubmitValues)
    }
  }

  /**
   * 打开电源操作对话框
   */
  const handleOpenPower = (uuid: string) => {
    setCurrentVmUuid(uuid)
    setPowerModalVisible(true)
  }

  /**
   * 执行电源操作
   */
  const handlePowerAction = async (action: string) => {
    if (!hostName || !currentVmUuid) return
    
    setPowerModalVisible(false)
    
    const actionMap: Record<string, string> = {
      start: '启动',
      stop: '关机',
      hard_stop: '强制关机',
      reset: '重启',
      hard_reset: '强制重启',
      pause: '暂停',
      resume: '恢复',
    }
    
    try {
      const hide = message.loading(`正在${actionMap[action]}虚拟机...`, 0)
      const result = await api.post(`/api/client/powers/${hostName}/${currentVmUuid}`, { action })
      hide()
      if (result.code === 200) {
        message.success(`${actionMap[action]}操作成功`)
        loadVMs()
      } else {
        message.error(result.msg || '操作失败')
      }
    } catch (error) {
      message.error('操作失败')
    }
  }

  /**
   * 删除虚拟机
   */
  const handleDelete = (uuid: string) => {
    Modal.confirm({
      title: '确认删除',
      content: (
        <div>
          <p>此操作将永久删除虚拟机 "<strong style={{ color: '#ff4d4f' }}>{uuid}</strong>" 且不可恢复</p>
          <p style={{ marginTop: 8, fontSize: 12, color: '#666' }}>请输入虚拟机名称以确认删除</p>
        </div>
      ),
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        if (!hostName) return
        try {
          const hide = message.loading('正在删除虚拟机...', 0)
          const result = await api.delete(`/api/client/delete/${hostName}/${uuid}`)
          hide()
          if (result.code === 200) {
            message.success('虚拟机已删除')
            loadVMs()
          } else {
            message.error(result.msg || '删除失败')
          }
        } catch (error) {
          message.error('删除失败')
        }
      },
    })
  }

  /**
   * 打开VNC控制台
   */
  const handleOpenVnc = async (uuid: string) => {
    if (!hostName) return
    try {
      const hide = message.loading('正在获取VNC控制台地址...', 0)
      const result = await api.get(`/api/client/remote/${hostName}/${uuid}`)
      hide()
      if (result.code === 200 && result.data) {
        window.open(result.data, `vnc_${uuid}`, 'width=1024,height=768')
      } else {
        message.error('无法获取VNC控制台地址')
      }
    } catch (error) {
      message.error('连接失败')
    }
  }

  /**
   * 格式化内存显示
   */
  const formatMemory = (mb?: number): string => {
    if (!mb) return '0 MB'
    if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`
    return `${mb} MB`
  }

  /**
   * 格式化磁盘显示
   */
  const formatDisk = (mb?: number): string => {
    if (!mb) return '0 MB'
    if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`
    return `${mb} MB`
  }

  /**
   * 渲染虚拟机卡片
   */
  const renderVMCard = (uuid: string, vm: VM) => {
    const config = vm.config || {}
    const statusList = vm.status || []
    const firstStatus = statusList.length > 0 ? statusList[0] : { ac_status: 'UNKNOWN' }
    const powerStatus = firstStatus.ac_status || 'UNKNOWN'
    const statusInfo = statusMap[powerStatus] || statusMap.UNKNOWN

    const nicAll = config.nic_all || {}
    const firstNic = Object.values(nicAll)[0] || {}
    const ipv4 = firstNic.ip4_addr || '-'
    const ipv6 = firstNic.ip6_addr || '-'
    const macAddr = firstNic.mac_addr || '-'

    return (
      <Col xs={24} lg={12} key={uuid}>
        <Card
          hoverable
          style={{ height: '100%' }}
          styles={{ body: { padding: 16 } }}
        >
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <div
                  style={{
                    width: 48,
                    height: 48,
                    background: 'linear-gradient(135deg, #9333ea 0%, #7e22ce 100%)',
                    borderRadius: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 8px rgba(147, 51, 234, 0.3)',
                  }}
                >
                  <DesktopOutlined style={{ fontSize: 24, color: '#fff' }} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{uuid}</h3>
                  <p style={{ margin: 0, fontSize: 12, color: '#666' }}>{config.os_name || '未知系统'}</p>
                </div>
              </div>
              <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
            </div>
          </div>

          {/* 基础资源信息 */}
          <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
            <Col span={12}>
              <div style={{ fontSize: 12, color: '#666' }}>
                CPU: <strong>{config.cpu_num || 0} 核</strong>
              </div>
            </Col>
            <Col span={12}>
              <div style={{ fontSize: 12, color: '#666' }}>
                内存: <strong>{formatMemory(config.mem_num)}</strong>
              </div>
            </Col>
            <Col span={12}>
              <div style={{ fontSize: 12, color: '#666' }}>
                硬盘: <strong>{formatDisk(config.hdd_num)}</strong>
              </div>
            </Col>
            <Col span={12}>
              <div style={{ fontSize: 12, color: '#666' }}>
                显存: <strong>{formatMemory(config.gpu_mem)}</strong>
              </div>
            </Col>
          </Row>

          {/* 端口信息 */}
          <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 8, marginBottom: 16 }}>
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <div style={{ fontSize: 12, color: '#666' }}>
                  NAT端口: <strong>{config.nat_num || 0}个</strong>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ fontSize: 12, color: '#666' }}>
                  Web代理: <strong>{config.web_num || 0}个</strong>
                </div>
              </Col>
            </Row>
          </div>

          {/* 网卡信息 */}
          <div style={{ padding: 12, background: '#e6f4ff', border: '1px solid #91caff', borderRadius: 8, marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#0958d9', marginBottom: 8 }}>网卡信息</div>
            <div style={{ fontSize: 11 }}>
              <div style={{ marginBottom: 4 }}>
                <span style={{ color: '#666', width: 48, display: 'inline-block' }}>IPv4:</span>
                <span style={{ fontFamily: 'monospace', color: '#333' }}>{ipv4}</span>
              </div>
              <div style={{ marginBottom: 4 }}>
                <span style={{ color: '#666', width: 48, display: 'inline-block' }}>IPv6:</span>
                <span style={{ fontFamily: 'monospace', color: '#333' }}>{ipv6 !== '-' ? ipv6 : '未配置'}</span>
              </div>
              <div>
                <span style={{ color: '#666', width: 48, display: 'inline-block' }}>MAC:</span>
                <span style={{ fontFamily: 'monospace', color: '#333' }}>{macAddr}</span>
              </div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/hosts/${hostName}/vms/${uuid}`)}
            >
              查看详情
            </Button>
            <Space size="small">
              <Tooltip title="VNC控制台">
                <Button
                  size="small"
                  icon={<DesktopOutlined />}
                  onClick={() => handleOpenVnc(uuid)}
                />
              </Tooltip>
              <Tooltip title="电源管理">
                <Button
                  size="small"
                  icon={<PoweroffOutlined />}
                  onClick={() => handleOpenPower(uuid)}
                />
              </Tooltip>
              <Tooltip title="编辑">
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleOpenEdit(uuid)}
                />
              </Tooltip>
              <Tooltip title="删除">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(uuid)}
                />
              </Tooltip>
            </Space>
          </div>
        </Card>
      </Col>
    )
  }

  const vmCount = Object.keys(vms).length

  return (
    <div>
      {/* 面包屑导航 */}
      <Breadcrumb 
        style={{ marginBottom: 16 }}
        items={[
          {
            title: <Link to="/hosts">主机管理</Link>,
          },
          {
            title: hostName,
          },
        ]}
      />

      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 'bold', margin: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
          <DesktopOutlined style={{ color: '#9333ea' }} />
          虚拟机管理
        </h1>
        <p style={{ color: '#666', margin: '8px 0 0 0' }}>
          管理主机 <strong>{hostName}</strong> 下的所有虚拟机
        </p>
      </div>

      {/* 操作栏 */}
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <Space wrap>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
              创建虚拟机
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadVMs}>
              刷新
            </Button>
            <Button icon={<RadarChartOutlined />} onClick={handleScan}>
              扫描虚拟机
            </Button>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/hosts')}>
              返回主机列表
            </Button>
          </Space>
          <div style={{ color: '#666', fontSize: 14 }}>
            共 <strong style={{ color: '#333' }}>{vmCount}</strong> 台虚拟机
          </div>
        </div>
      </Card>

      {/* 虚拟机列表 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 64 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16, color: '#666' }}>加载中...</p>
        </div>
      ) : vmCount === 0 ? (
        <Card>
          <Empty
            description="暂无虚拟机"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
              创建第一台虚拟机
            </Button>
          </Empty>
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {Object.entries(vms).map(([uuid, vm]) => renderVMCard(uuid, vm))}
        </Row>
      )}

      {/* 创建/编辑虚拟机对话框 */}
      <Modal
        title={editMode === 'add' ? '创建虚拟机' : '编辑虚拟机'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={800}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          {/* 服务器消息提示 */}
          {hostConfig?.messages && hostConfig.messages.length > 0 && (
            <Alert
              message="服务器配置提示"
              description={
                <ul style={{ paddingLeft: 20, margin: 0 }}>
                  {hostConfig.messages.map((msg, idx) => (
                    <li key={idx}>{msg}</li>
                  ))}
                </ul>
              }
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {/* 基本信息 */}
          <Divider orientation="left">基本信息</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="虚拟机UUID"
                required
              >
                <Input.Group compact>
                  <Input
                    style={{ width: '30%' }}
                    value={hostConfig?.filter_name ? `${hostConfig.filter_name}-` : ''}
                    disabled
                  />
                  <Form.Item
                    name="vm_uuid_suffix"
                    noStyle
                    rules={[{ required: true, message: '请输入UUID' }]}
                  >
                    <Input style={{ width: '50%' }} placeholder="随机生成" disabled={editMode === 'edit'} />
                  </Form.Item>
                  {editMode === 'add' && (
                    <Button
                      style={{ width: '20%' }}
                      onClick={() => form.setFieldsValue({ vm_uuid_suffix: generateRandomString(8) })}
                    >
                      随机
                    </Button>
                  )}
                </Input.Group>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="os_name"
                label="操作系统"
                rules={[{ required: true, message: '请选择操作系统' }]}
              >
                <Select 
                  placeholder="请选择" 
                  disabled={isFieldDisabled('os_name')}
                  onChange={(value) => {
                    if (hostConfig?.system_maps) {
                      const entry = Object.values(hostConfig.system_maps).find(([img]) => img === value)
                      if (entry) {
                        const minDisk = entry[1] || 0
                        setSelectedOsMinDisk(minDisk)
                        form.validateFields(['hdd_num'])
                      }
                    }
                  }}
                >
                  {hostConfig?.system_maps &&
                    Object.entries(hostConfig.system_maps).map(([osName, [imageFile]]) => (
                      <Select.Option key={imageFile} value={imageFile}>
                        {osName}
                      </Select.Option>
                    ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item 
                name="os_pass" 
                label="系统密码" 
                rules={[{ validator: validatePassword }]}
              >
                <Input.Password placeholder="设置系统登录密码" disabled={isFieldDisabled('os_pass')} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item 
                name="vc_pass" 
                label="VNC密码" 
                rules={[{ validator: validatePassword }]}
              >
                <Input.Password placeholder="VNC远程密码" disabled={isFieldDisabled('vc_pass')} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="vc_port" label="VNC端口">
                <InputNumber min={1} max={65535} style={{ width: '100%' }} placeholder="VNC端口" disabled={isFieldDisabled('vc_port')} />
              </Form.Item>
            </Col>
            <Col span={2}>
              <Form.Item label=" ">
                <Button
                  onClick={() => {
                    const randomPass = generateRandomString(8)
                    form.setFieldsValue({
                      os_pass: randomPass,
                      vc_pass: randomPass,
                      vc_port: generateRandomVncPort(),
                    })
                  }}
                  disabled={isFieldDisabled('os_pass') && isFieldDisabled('vc_pass')}
                >
                  随机
                </Button>
              </Form.Item>
            </Col>
          </Row>

          {/* 资源配置 */}
          <Divider orientation="left">资源配置</Divider>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="cpu_num" label="CPU核心数" rules={[{ required: true }]}>
                <InputNumber min={1} style={{ width: '100%' }} disabled={isFieldDisabled('cpu_num')} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="mem_num" label="内存(MB)" rules={[{ required: true }]}>
                <InputNumber min={512} style={{ width: '100%' }} disabled={isFieldDisabled('mem_num')} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item 
                name="hdd_num" 
                label="硬盘(MB)" 
                rules={[
                  { required: true },
                  { 
                    validator: (_, value) => {
                      if (!value) return Promise.resolve()
                      const minMB = selectedOsMinDisk * 1024
                      if (value < minMB) {
                        return Promise.reject(new Error(`最小要求: ${selectedOsMinDisk}GB (${minMB}MB)`))
                      }
                      return Promise.resolve()
                    }
                  }
                ]}
                extra={selectedOsMinDisk > 0 ? `最小要求: ${selectedOsMinDisk}GB` : ''}
              >
                <InputNumber min={10240} style={{ width: '100%' }} disabled={isFieldDisabled('hdd_num')} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="gpu_num" label="GPU数量">
                <InputNumber min={0} style={{ width: '100%' }} disabled={isFieldDisabled('gpu_num')} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="gpu_mem" label="显存(MB)">
                <InputNumber min={0} style={{ width: '100%' }} disabled={isFieldDisabled('gpu_mem')} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="speed_u" label="上行带宽(Mbps)">
                <InputNumber min={1} style={{ width: '100%' }} disabled={isFieldDisabled('speed_u')} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="speed_d" label="下行带宽(Mbps)">
                <InputNumber min={1} style={{ width: '100%' }} disabled={isFieldDisabled('speed_d')} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="flu_num" label="流量(MB)">
                <InputNumber min={0} style={{ width: '100%' }} disabled={isFieldDisabled('flu_num')} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="nat_num" label="NAT端口数">
                <InputNumber min={0} style={{ width: '100%' }} disabled={isFieldDisabled('nat_num')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="web_num" label="Web代理数">
                <InputNumber min={0} style={{ width: '100%' }} disabled={isFieldDisabled('web_num')} />
              </Form.Item>
            </Col>
          </Row>

          {/* 网络配置 */}
          <Divider orientation="left">网络配置</Divider>
          {userQuota && (
            <Alert 
               message={
                   <Space>
                       <Text>IP配额状态:</Text>
                       <Text type={userQuota.quota_nat_ips - userQuota.used_nat_ips <= 0 && userQuota.quota_pub_ips - userQuota.used_pub_ips <= 0 ? 'danger' : 'success'}>
                           {userQuota.quota_nat_ips - userQuota.used_nat_ips <= 0 && userQuota.quota_pub_ips - userQuota.used_pub_ips <= 0 ? 'IP配额已用尽' : 'IP配额充足'}
                       </Text>
                       <Text type="secondary" style={{ fontSize: 12 }}>
                           (内网: {userQuota.used_nat_ips}/{userQuota.quota_nat_ips}, 公网: {userQuota.used_pub_ips}/{userQuota.quota_pub_ips})
                       </Text>
                   </Space>
               }
               type={userQuota.quota_nat_ips - userQuota.used_nat_ips <= 0 && userQuota.quota_pub_ips - userQuota.used_pub_ips <= 0 ? 'error' : 'success'}
               showIcon
               style={{ marginBottom: 12 }}
            />
          )}
          
          {nicList.map((nic) => (
            <Row gutter={8} key={nic.key} style={{ marginBottom: 8 }}>
              <Col span={6}>
                <Form.Item name={`nic_name_${nic.key}`} initialValue={nic.name} noStyle>
                  <Input placeholder="网卡名称" disabled />
                </Form.Item>
              </Col>
              <Col span={4}>
                <Form.Item name={`nic_type_${nic.key}`} initialValue="nat" noStyle>
                  <Select 
                    onChange={(val) => {
                        const updatedList = nicList.map(n => n.key === nic.key ? { ...n, type: val } : n)
                        setNicList(updatedList)
                    }}
                  >
                    <Select.Option 
                        value="nat" 
                        disabled={nic.type !== 'nat' && userQuota && userQuota.used_nat_ips >= userQuota.quota_nat_ips}
                    >
                        内网 {userQuota && userQuota.used_nat_ips >= userQuota.quota_nat_ips && nic.type !== 'nat' ? '(配额不足)' : ''}
                    </Select.Option>
                    <Select.Option 
                        value="pub"
                        disabled={nic.type !== 'pub' && userQuota && userQuota.used_pub_ips >= userQuota.quota_pub_ips}
                    >
                        公网 {userQuota && userQuota.used_pub_ips >= userQuota.quota_pub_ips && nic.type !== 'pub' ? '(配额不足)' : ''}
                    </Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={5}>
                <Form.Item name={`nic_ip_${nic.key}`} noStyle>
                  <Input placeholder="IPv4地址" />
                </Form.Item>
              </Col>
              <Col span={7}>
                <Form.Item name={`nic_ip6_${nic.key}`} noStyle>
                  <Input placeholder="IPv6地址" />
                </Form.Item>
              </Col>
              <Col span={2}>
                <Button danger size="small" onClick={() => handleRemoveNic(nic.key)}>
                  删除
                </Button>
              </Col>
            </Row>
          ))}
          <Button type="dashed" onClick={handleAddNic} block disabled={isFieldDisabled('nic_all')}>
            添加网卡
          </Button>
        </Form>
      </Modal>

      {/* 电源操作对话框 */}
      <Modal
        title="电源操作"
        open={powerModalVisible}
        onCancel={() => setPowerModalVisible(false)}
        footer={null}
        width={400}
      >
        <p style={{ marginBottom: 16 }}>选择对虚拟机 "<strong>{currentVmUuid}</strong>" 执行的操作：</p>
        <Row gutter={[12, 12]}>
          <Col span={12}>
            <Button
              block
              type="primary"
              style={{ background: '#52c41a' }}
              icon={<PlayCircleOutlined />}
              onClick={() => handlePowerAction('start')}
            >
              启动
            </Button>
          </Col>
          <Col span={12}>
            <Button
              block
              style={{ background: '#faad14', color: '#fff' }}
              icon={<PauseCircleOutlined />}
              onClick={() => handlePowerAction('stop')}
            >
              关机
            </Button>
          </Col>
          <Col span={12}>
            <Button
              block
              type="primary"
              icon={<RedoOutlined />}
              onClick={() => handlePowerAction('reset')}
            >
              重启
            </Button>
          </Col>
          <Col span={12}>
            <Button
              block
              style={{ background: '#8c8c8c', color: '#fff' }}
              icon={<PauseCircleOutlined />}
              onClick={() => handlePowerAction('pause')}
            >
              暂停
            </Button>
          </Col>
          <Col span={12}>
            <Button
              block
              style={{ background: '#722ed1', color: '#fff' }}
              icon={<PlayCircleOutlined />}
              onClick={() => handlePowerAction('resume')}
            >
              恢复
            </Button>
          </Col>
          <Col span={12}>
            <Button
              block
              danger
              icon={<PoweroffOutlined />}
              onClick={() => handlePowerAction('hard_stop')}
            >
              强制关机
            </Button>
          </Col>
          <Col span={12}>
            <Button
              block
              danger
              icon={<ThunderboltOutlined />}
              onClick={() => handlePowerAction('hard_reset')}
            >
              强制重启
            </Button>
          </Col>
        </Row>
      </Modal>

      {/* 保存确认对话框 */}
      <Modal
        title="保存确认"
        open={saveConfirmModalVisible}
        onCancel={() => setSaveConfirmModalVisible(false)}
        onOk={handleConfirmSave}
        okText="确认保存"
        okButtonProps={{ disabled: !forceShutdownConfirmed }}
        cancelText="取消"
      >
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
           <InfoCircleOutlined style={{ color: '#faad14', fontSize: 22, marginTop: 4 }} />
           <div>
              <p style={{ fontWeight: 500, fontSize: 16, marginBottom: 8 }}>确定要保存对虚拟机 "{currentVmUuid}" 的配置修改吗？</p>
              <div style={{ marginTop: 12, padding: 12, background: '#fff1f0', border: '1px solid #ffa39e', borderRadius: 4 }}>
                 <Checkbox 
                    checked={forceShutdownConfirmed}
                    onChange={(e) => setForceShutdownConfirmed(e.target.checked)}
                    style={{ color: '#cf1322', fontWeight: 'bold' }}
                 >
                    我已确认强制关闭虚拟机
                 </Checkbox>
              </div>
           </div>
        </div>
      </Modal>
    </div>
  )
}

export default VMs