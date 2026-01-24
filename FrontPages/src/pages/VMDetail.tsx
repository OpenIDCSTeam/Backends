import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Tabs,
  Button,
  Space,
  Tag,
  Table,
  Progress,
  message,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Breadcrumb,
  Tooltip,
  Row,
  Col,
  Statistic,
  Alert,
  Checkbox,
  Divider
} from 'antd'
import {
  HomeOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  PoweroffOutlined,
  EditOutlined,
  DeleteOutlined,
  DesktopOutlined,
  KeyOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  CopyOutlined,
  PlusOutlined,
  RollbackOutlined,
  CloudSyncOutlined,
  UsergroupAddOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import api from '@/services/api'
import { t } from '@/utils/i18n'

/**
 * 虚拟机详情数据接口
 */
interface VMDetail {
  vm_uuid: string
  vm_name: string
  os_name: string
  os_pass: string
  vnc_pass: string
  status: any[]
  cpu_num: number
  mem_num: number
  hdd_num: number
  gpu_num: number
  speed_up: number
  speed_down: number
  nat_num: number
  web_num: number
  traffic: number
  ipv4_address?: string
  ipv6_address?: string
  public_address?: string
  cpu_usage?: number
  mem_usage?: number
  hdd_usage?: number
  gpu_usage?: number
  net_usage?: number
  nat_usage?: number
  web_usage?: number
  traffic_usage?: number
}

/**
 * 网卡信息接口
 */
interface NICInfo {
  nic_name: string
  nic_type: string
  mac_address: string
  ip_address: string
  ip6_address: string
  subnet_mask: string
  gateway: string
}

/**
 * NAT规则接口
 */
interface NATRule {
  id: number
  protocol: string
  public_port: number
  private_port: number
  internal_ip?: string
  description?: string
}

/**
 * IP地址接口
 */
interface IPAddress {
  nic_name: string
  ip_address: string
  ip6_address?: string
  ip_type: string
  subnet_mask?: string
  gateway?: string
}

/**
 * 反向代理接口
 */
interface ProxyRule {
  id: number
  domain: string
  target_port: number
  ssl_enabled: boolean
  backend_ip?: string
  description?: string
}

/**
 * 数据盘接口
 */
interface HDDInfo {
  hdd_index: number
  hdd_num: number
  hdd_path: string
}

/**
 * ISO接口
 */
interface ISOInfo {
  iso_index: number
  iso_path: string
}

/**
 * 备份接口
 */
interface BackupInfo {
  backup_index: number
  backup_name: string
  backup_path: string
  created_time: string
  size: string
}

/**
 * 用户分享接口
 */
interface OwnerInfo {
  username: string
  role: string
  is_admin?: boolean
  email?: string
}

/**
 * 主机配置接口
 */
interface HostConfig {
  system_maps: Record<string, [string, number]>
  images_maps?: Record<string, string>
  tab_lock?: string[]
}

/**
 * 虚拟机详情页面
 */
function VMDetail() {
  const { hostName, uuid } = useParams<{ hostName: string; uuid: string }>()
  const navigate = useNavigate()
  
  // 状态管理
  const [vm, setVM] = useState<VMDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('info')
  const [showPassword, setShowPassword] = useState(false)
  const [showVncPassword, setShowVncPassword] = useState(false)
  const [nics, setNics] = useState<NICInfo[]>([])
  const [natRules, setNatRules] = useState<NATRule[]>([])
  const [ipAddresses, setIpAddresses] = useState<IPAddress[]>([])
  const [proxyRules, setProxyRules] = useState<ProxyRule[]>([])
  const [timeRange, setTimeRange] = useState(30)
  const [monitorData, setMonitorData] = useState<any>({
    cpu: [],
    memory: [],
    disk: [],
    gpu: [],
    netUp: [],
    netDown: [],
    labels: []
  })
  const [hostConfig, setHostConfig] = useState<HostConfig | null>(null)
  const [tabLockList, setTabLockList] = useState<string[]>([])
  
  // 模态框状态
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [passwordModalVisible, setPasswordModalVisible] = useState(false)
  const [natModalVisible, setNatModalVisible] = useState(false)
  const [ipModalVisible, setIpModalVisible] = useState(false)
  const [proxyModalVisible, setProxyModalVisible] = useState(false)
  const [hddModalVisible, setHddModalVisible] = useState(false)
  const [isoModalVisible, setIsoModalVisible] = useState(false)
  const [backupModalVisible, setBackupModalVisible] = useState(false)
  const [ownerModalVisible, setOwnerModalVisible] = useState(false)
  const [reinstallModalVisible, setReinstallModalVisible] = useState(false)
  const [transferHddModalVisible, setTransferHddModalVisible] = useState(false)
  const [transferOwnershipModalVisible, setTransferOwnershipModalVisible] = useState(false)
  const [editIpModalVisible, setEditIpModalVisible] = useState(false)
  const [mountHddModalVisible, setMountHddModalVisible] = useState(false)
  const [unmountHddModalVisible, setUnmountHddModalVisible] = useState(false)
  
  const [ipQuota, setIpQuota] = useState<any>(null)
  const [hdds, setHdds] = useState<HDDInfo[]>([])
  const [currentTransferHdd, setCurrentTransferHdd] = useState<HDDInfo | null>(null)
  const [currentMountHdd, setCurrentMountHdd] = useState<HDDInfo | null>(null)
  const [currentUnmountHdd, setCurrentUnmountHdd] = useState<HDDInfo | null>(null)
  const [currentEditIp, setCurrentEditIp] = useState<IPAddress | null>(null)
  const [transferTargetUuid, setTransferTargetUuid] = useState('')
  const [transferConfirmChecked, setTransferConfirmChecked] = useState(false)
  const [transferOwnerUsername, setTransferOwnerUsername] = useState('')
  const [transferOwnerConfirmChecked, setTransferOwnerConfirmChecked] = useState(false)
  const [keepAccessChecked, setKeepAccessChecked] = useState(false)
  
  const [saveConfirmModalVisible, setSaveConfirmModalVisible] = useState(false)
  const [saveConfirmChecked, setSaveConfirmChecked] = useState(false)
  const [pendingEditValues, setPendingEditValues] = useState<any>(null)

  const [isos, setIsos] = useState<ISOInfo[]>([])
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [owners, setOwners] = useState<OwnerInfo[]>([])
  
  const [form] = Form.useForm()
  const [ipForm] = Form.useForm()
  const [editIpForm] = Form.useForm()
  const [proxyForm] = Form.useForm()
  const [hddForm] = Form.useForm()
  const [isoForm] = Form.useForm()
  const [ownerForm] = Form.useForm()
  const [reinstallForm] = Form.useForm()
  const [backupForm] = Form.useForm()
  const [editVmForm] = Form.useForm()

  // 编辑模式下的网卡列表状态
  const [editNicList, setEditNicList] = useState<any[]>([])

  /**
   * 加载主机信息（获取system_maps等配置）
   */
  const loadHostInfo = async () => {
    if (!hostName) return
    try {
      const result = await api.getOSImages(hostName)
      if (result.code === 200) {
        const config = result.data as unknown as HostConfig
        setHostConfig(config)
        if (config.tab_lock) {
          setTabLockList(config.tab_lock)
        }
      }
    } catch (error) {
      console.error('加载主机信息失败:', error)
    }
  }

  /**
   * 加载虚拟机详情
   */
  const loadVMDetail = async () => {
    if (!hostName || !uuid) return
    
    try {
      setLoading(true)
      // 并行获取详情和状态
      const [detailRes, statusRes] = await Promise.all([
        api.getVMDetail(hostName, uuid),
        api.getVMStatus(hostName, uuid)
      ])

      if (detailRes.data) {
        const vmData = detailRes.data as unknown as VMDetail
        // 合并状态信息
        if (statusRes.data) {
            const statusData = Array.isArray(statusRes.data) ? statusRes.data : [statusRes.data]
            vmData.status = statusData
        }
        setVM(vmData)
      }
    } catch (error) {
      message.error('加载虚拟机详情失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 加载网卡信息
   */
  const loadNICs = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getVMIPAddresses(hostName, uuid)
      if (response.data && vm?.config?.nic_all) {
        const nicList: NICInfo[] = []
        Object.entries(vm.config.nic_all).forEach(([name, config]: [string, any]) => {
          nicList.push({
            nic_name: name,
            nic_type: config.nic_type === 'nat' ? '内网' : '公网',
            mac_address: config.mac_address || '-',
            ip_address: config.ip4_addr || '-',
            ip6_address: config.ip6_addr || '-',
            subnet_mask: config.subnet_mask || '-',
            gateway: config.gateway || '-',
          })
        })
        setNics(nicList)
      }
    } catch (error) {
      console.error('加载网卡信息失败', error)
    }
  }

  /**
   * 加载NAT规则
   */
  const loadNATRules = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getNATRules(hostName, uuid)
      if (response.data) {
        setNatRules(response.data as unknown as NATRule[])
      }
    } catch (error) {
      console.error('加载NAT规则失败', error)
    }
  }

  /**
   * 加载IP地址列表
   */
  const loadIPAddresses = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getVMIPAddresses(hostName, uuid)
      if (response.data) {
        setIpAddresses(response.data as unknown as IPAddress[])
      }
      // 同时加载IP配额信息 (从当前用户信息获取)
      const userResponse = await api.getCurrentUser()
      if (userResponse.data) {
        const user = userResponse.data
        // 使用内网IP配额作为主要显示
        const quota = user.quota_nat_ips || 0
        const used = user.used_nat_ips || 0
        const percent = quota > 0 ? Math.round((used / quota) * 100) : 0
        
        setIpQuota({
          ip_num: quota,
          ip_used: used,
          ip_percent: percent,
          // 保存完整用户数据以备后用
          user_data: user
        })
      }
    } catch (error) {
      console.error('加载IP地址失败', error)
    }
  }

  /**
   * 加载反向代理规则
   */
  const loadProxyRules = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getProxyConfigs(hostName, uuid)
      if (response.data) {
        setProxyRules(response.data as unknown as ProxyRule[])
      }
    } catch (error) {
      console.error('加载反向代理规则失败', error)
    }
  }

  /**
   * 处理监控数据
   */
  const processMonitorData = (statusList: any[], timeRangeMinutes: number) => {
    const data = {
      cpu: [] as number[],
      memory: [] as number[],
      disk: [] as number[],
      gpu: [] as number[],
      netUp: [] as number[],
      netDown: [] as number[],
      labels: [] as string[],
    }

    if (!statusList || statusList.length === 0) return data

    // 找到最新数据的on_update时间戳
    let latestTimestamp = 0
    statusList.forEach(status => {
      if (status.on_update && status.on_update > latestTimestamp) {
        latestTimestamp = status.on_update
      }
    })

    if (!latestTimestamp) latestTimestamp = Math.floor(Date.now() / 1000)

    // 分钟级别对齐
    const latestMinuteTimestamp = Math.floor(latestTimestamp / 60) * 60
    
    // 采样间隔
    let sampleInterval = 1
    if (timeRangeMinutes > 360 && timeRangeMinutes <= 1440) sampleInterval = 10
    else if (timeRangeMinutes > 1440) sampleInterval = 30

    const totalPoints = Math.ceil(timeRangeMinutes / sampleInterval)
    
    // 建立映射
    const dataMap = new Map()
    statusList.forEach(status => {
      if (status.on_update) {
        const minuteTimestamp = Math.floor(status.on_update / 60) * 60
        dataMap.set(minuteTimestamp, status)
      }
    })

    // 生成序列
    for (let i = 0; i < totalPoints; i++) {
      const minuteOffset = (totalPoints - 1 - i) * sampleInterval
      const minuteTimestamp = latestMinuteTimestamp - minuteOffset * 60
      
      const status = dataMap.get(minuteTimestamp)
      
      // 生成标签
      const time = new Date(minuteTimestamp * 1000)
      const hours = String(time.getHours()).padStart(2, '0')
      const minutes = String(time.getMinutes()).padStart(2, '0')
      if (timeRangeMinutes > 1440) {
        const month = String(time.getMonth() + 1).padStart(2, '0')
        const day = String(time.getDate()).padStart(2, '0')
        data.labels.push(`${month}/${day} ${hours}:${minutes}`)
      } else {
        data.labels.push(`${hours}:${minutes}`)
      }

      if (status) {
        data.cpu.push(status.cpu_usage || 0)
        const memPercent = status.mem_total > 0 ? (status.mem_usage / status.mem_total * 100) : 0
        data.memory.push(Number(memPercent.toFixed(2)))
        const hddPercent = status.hdd_total > 0 ? (status.hdd_usage / status.hdd_total * 100) : 0
        data.disk.push(Number(hddPercent.toFixed(2)))
        data.gpu.push(status.gpu_total || 0)
        data.netUp.push(status.network_u || 0)
        data.netDown.push(status.network_d || 0)
      } else {
        data.cpu.push(0)
        data.memory.push(0)
        data.disk.push(0)
        data.gpu.push(0)
        data.netUp.push(0)
        data.netDown.push(0)
      }
    }

    return data
  }

  /**
   * 加载监控数据
   */
  const loadMonitorData = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getVMMonitorData(hostName, uuid, timeRange)
      if (response.data && Array.isArray(response.data)) {
        const processedData = processMonitorData(response.data, timeRange)
        setMonitorData(processedData)
      } else {
         setMonitorData({
            cpu: [], memory: [], disk: [], gpu: [], netUp: [], netDown: [], labels: []
         })
      }
    } catch (error) {
      console.error('加载监控数据失败', error)
      setMonitorData({
        cpu: [],
        memory: [],
        disk: [],
        gpu: [],
        netUp: [],
        netDown: [],
        labels: []
      })
    }
  }

  /**
   * 加载数据盘列表
   */
  const loadHDDs = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getVMHDDs(hostName, uuid)
      if (response.data && response.data.config) {
        const hddConfig = response.data.config.hdd_all || {}
        const hddList = Object.entries(hddConfig).map(([key, value]: [string, any]) => ({
            hdd_path: key, // key is the path/name
            ...value
        }))
        setHdds(hddList)
      }
    } catch (error) {
      console.error('加载数据盘失败', error)
    }
  }

  /**
   * 加载ISO挂载列表
   */
  const loadISOs = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getVMISOs(hostName, uuid)
      if (response.data && response.data.config) {
        const isoConfig = response.data.config.iso_all || {}
        const isoList = Object.entries(isoConfig).map(([key, value]: [string, any]) => ({
            iso_key: key,
            ...value
        }))
        setIsos(isoList)
      }
    } catch (error) {
      console.error('加载ISO失败', error)
    }
  }

  /**
   * 加载备份列表
   */
  const loadBackups = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getVMBackups(hostName, uuid)
      if (response.data && response.data.config) {
        setBackups(response.data.config.backups || [])
      }
    } catch (error) {
      console.error('加载备份失败', error)
    }
  }

  /**
   * 加载用户分享列表
   */
  const loadOwners = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getVMOwners(hostName, uuid)
      if (response.data && response.data.owners) {
        setOwners(response.data.owners)
      }
    } catch (error) {
      console.error('加载用户分享失败', error)
    }
  }

  useEffect(() => {
    loadHostInfo()
    loadVMDetail()
    loadNICs()
    loadMonitorData()
    
    // 定时刷新（每30秒）
    const interval = setInterval(() => {
      loadVMDetail()
      loadMonitorData()
    }, 30000)
    
    return () => {
      clearInterval(interval)
    }
  }, [hostName, uuid])

  useEffect(() => {
    if (activeTab === 'nat') {
      loadNATRules()
    } else if (activeTab === 'ip') {
      loadIPAddresses()
    } else if (activeTab === 'proxy') {
      loadProxyRules()
    } else if (activeTab === 'hdd') {
      loadHDDs()
    } else if (activeTab === 'iso') {
      loadISOs()
    } else if (activeTab === 'backup') {
      loadBackups()
    } else if (activeTab === 'owners') {
      loadOwners()
    }
  }, [activeTab])

  useEffect(() => {
    loadMonitorData()
  }, [timeRange])

  // 当打开NAT模态框时，确保IP列表已加载
  useEffect(() => {
    if (natModalVisible && ipAddresses.length === 0) {
      loadIPAddresses()
    }
  }, [natModalVisible])

  /**
   * 虚拟机电源操作
   */
  const handlePowerAction = async (action: string) => {
    if (!hostName || !uuid) return
    
    try {
      await api.vmPower(hostName, uuid, action as any)
      message.success(t('操作成功'))
      setTimeout(loadVMDetail, 1000)
    } catch (error) {
      message.error(t('操作失败'))
    }
  }

  /**
   * 删除虚拟机
   */
  const handleDelete = () => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个虚拟机吗？此操作不可恢复！',
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        if (!hostName || !uuid) return
        
        try {
          await api.deleteVM(hostName, uuid)
          message.success('删除成功')
          navigate(`/hosts/${hostName}/vms`)
        } catch (error) {
          message.error('删除失败')
        }
      },
    })
  }

  /**
   * 打开VNC控制台
   */
  const handleOpenVNC = async () => {
    if (!hostName || !uuid) return
    
    try {
      const response = await api.getVMConsole(hostName, uuid)
      if (response.data?.console_url) {
        window.open(response.data.console_url, '_blank')
      }
    } catch (error) {
      message.error('打开控制台失败')
    }
  }

  /**
   * 复制密码
   */
  const handleCopyPassword = (password: string, type: string) => {
    navigator.clipboard.writeText(password)
    message.success(`${type}密码已复制`)
  }

  /**
   * 修改系统密码
   */
  const handleChangePassword = async (_values: any) => {
    if (!hostName || !uuid) return
    
    try {
      await api.changeVMPassword(hostName, uuid, { password: _values.new_password })
      message.success('密码修改成功')
      setPasswordModalVisible(false)
      loadVMDetail()
    } catch (error) {
      message.error('密码修改失败')
    }
  }

  /**
   * 添加IP地址
   */
  const handleAddIPAddress = async (_values: any) => {
    if (!hostName || !uuid) return
    
    try {
      await api.addIPAddress(hostName, uuid, _values)
      message.success(t('IP地址添加成功'))
      setIpModalVisible(false)
      ipForm.resetFields()
      loadIPAddresses()
    } catch (error) {
      message.error(t('IP地址添加失败'))
    }
  }

  /**
   * 删除IP地址
   */
  const handleDeleteIPAddress = async (nicName: string) => {
    if (!hostName || !uuid) return
    
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个IP地址吗？',
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.deleteIPAddress(hostName, uuid, nicName)
          message.success('IP地址删除成功')
          loadIPAddresses()
        } catch (error) {
          message.error('IP地址删除失败')
        }
      },
    })
  }

  /**
   * 添加反向代理
   */
  const handleAddProxy = async (_values: any) => {
    if (!hostName || !uuid) return
    
    try {
      await api.addProxyConfig(hostName, uuid, _values)
      message.success('反向代理添加成功')
      setProxyModalVisible(false)
      proxyForm.resetFields()
      loadProxyRules()
    } catch (error) {
      message.error('反向代理添加失败')
    }
  }

  /**
   * 删除反向代理
   */
  const handleDeleteProxy = async (proxyId: number) => {
    if (!hostName || !uuid) return
    
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个反向代理吗？',
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.deleteProxyConfig(hostName, uuid, proxyId)
          message.success('反向代理删除成功')
          loadProxyRules()
        } catch (error) {
          message.error('反向代理删除失败')
        }
      },
    })
  }

  /**
   * 添加数据盘
   */
  const handleAddHDD = async (_values: any) => {
    if (!hostName || !uuid) return
    
    // 验证名称：只能包含数字、字母和下划线
    const regex = /^[a-zA-Z0-9_]+$/
    if (!regex.test(_values.hdd_name)) {
        message.error('磁盘名称只能包含数字、字母和下划线')
        return
    }

    try {
        // 先创建
        await api.addHDD(hostName, uuid, { 
            hdd_size: _values.hdd_size * 1024, // GB to MB
            hdd_hint: _values.hdd_name // Name as hint/path
        })
        
        // 如果需要挂载，可以在这里自动挂载，或者让用户手动挂载
        // 老逻辑是：添加 -> 关闭模态框 -> 显示挂载确认框
        // 这里简化为直接添加，用户再点击挂载
        message.success('数据盘添加成功')
        setHddModalVisible(false)
        hddForm.resetFields()
        loadHDDs()
    } catch (error) {
      message.error('数据盘添加失败')
    }
  }

  /**
   * 挂载数据盘
   */
  const handleMountHDD = async () => {
    if (!hostName || !uuid || !currentMountHdd) return
    
    try {
        await api.post(`/api/client/hdd/mount/${hostName}/${uuid}`, {
            hdd_name: currentMountHdd.hdd_path,
            hdd_size: currentMountHdd.hdd_num,
            hdd_type: currentMountHdd.hdd_type
        })
        message.success('挂载成功')
        setMountHddModalVisible(false)
        loadHDDs()
    } catch (error) {
        message.error('挂载失败')
    }
  }

  /**
   * 卸载数据盘
   */
  const handleUnmountHDD = async () => {
    if (!hostName || !uuid || !currentUnmountHdd) return
    
    try {
        await api.post(`/api/client/hdd/unmount/${hostName}/${uuid}`, {
            hdd_name: currentUnmountHdd.hdd_path
        })
        message.success('卸载成功')
        setUnmountHddModalVisible(false)
        loadHDDs()
    } catch (error) {
        message.error('卸载失败')
    }
  }

  /**
   * 删除数据盘
   */
  const handleDeleteHDD = async (hddPath: string) => {
    if (!hostName || !uuid) return
    
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除数据盘 "${hddPath}" 吗？此操作不可恢复！`,
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          // 注意：后端API deleteHDD 接受的是 hddIndex，但这里可能是 path
          // 检查 api.deleteHDD 实现：/api/client/hdd/delete/${hsName}/${vmUuid}/${hddIndex}
          // 但老前端使用的是 POST /api/client/hdd/delete/... with body {hdd_name: ...}
          // 这里我们需要使用 delete with body，或者遵循后端新API
          // 假设后端 RestManager.py 的 remove_vm_hdd 需要 hdd_name
          await api.delete(`/api/client/hdd/delete/${hostName}/${uuid}`, { data: { hdd_name: hddPath } })
          message.success('数据盘删除成功')
          loadHDDs()
        } catch (error) {
          message.error('数据盘删除失败')
        }
      },
    })
  }

  /**
   * 打开移交数据盘对话框
   */
  const handleOpenTransferHDD = (hdd: HDDInfo) => {
    setCurrentTransferHdd(hdd)
    setTransferTargetUuid('')
    setTransferConfirmChecked(false)
    setTransferHddModalVisible(true)
  }

  /**
   * 执行数据盘移交
   */
  const handleTransferHDD = async () => {
    if (!hostName || !uuid || !currentTransferHdd) return
    
    try {
      await api.post(`/api/client/hdd/transfer/${hostName}/${uuid}`, {
          hdd_name: currentTransferHdd.hdd_path,
          target_vm: transferTargetUuid // Old frontend uses target_vm
      })
      message.success('数据盘移交指令已发送')
      setTransferHddModalVisible(false)
      setTimeout(() => window.location.reload(), 1500)
    } catch (error) {
      message.error('数据盘移交失败')
    }
  }

  /**
   * 挂载ISO
   */
  const handleAddISO = async (_values: any) => {
    if (!hostName || !uuid) return
    
    try {
      await api.addISO(hostName, uuid, { 
          iso_name: _values.iso_name,
          iso_file: _values.iso_file,
          iso_hint: _values.iso_hint
      })
      message.success('ISO挂载成功')
      setIsoModalVisible(false)
      isoForm.resetFields()
      loadISOs()
    } catch (error) {
      message.error('ISO挂载失败')
    }
  }

  /**
   * 卸载ISO
   */
  const handleDeleteISO = async (isoName: string) => {
    if (!hostName || !uuid) return
    
    Modal.confirm({
      title: '确认卸载',
      content: `确定要卸载 ISO "${isoName}" 吗？`,
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.deleteISO(hostName, uuid, isoName)
          message.success('ISO卸载成功')
          loadISOs()
        } catch (error) {
          message.error('ISO卸载失败')
        }
      },
    })
  }

  /**
   * 创建备份
   */
  const handleCreateBackup = async (_values: any) => {
    if (!hostName || !uuid) return
    
    try {
      await api.createVMBackup(hostName, uuid, { vm_tips: _values.backup_name })
      message.success('备份创建成功')
      setBackupModalVisible(false)
      backupForm.resetFields()
      loadBackups()
    } catch (error) {
      message.error('备份创建失败')
    }
  }

  /**
   * 恢复备份
   */
  const handleRestoreBackup = async (backupName: string) => {
    if (!hostName || !uuid) return
    
    Modal.confirm({
        title: '确认恢复',
        content: '恢复备份将覆盖当前系统数据，确定要继续吗？',
        okText: '确定',
        okType: 'danger',
        cancelText: '取消',
        onOk: async () => {
            try {
                await api.restoreVMBackup(hostName, uuid, backupName)
                message.success('恢复备份指令已发送')
                setTimeout(() => window.location.reload(), 3000)
            } catch (error) {
                message.error('恢复备份失败')
            }
        }
    })
  }

  /**
   * 删除备份
   */
  const handleDeleteBackup = async (backupName: string) => {
    if (!hostName || !uuid) return
    
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个备份吗？此操作不可恢复！',
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.deleteVMBackup(hostName, uuid, backupName)
          message.success('备份删除成功')
          loadBackups()
        } catch (error) {
          message.error('备份删除失败')
        }
      },
    })
  }

  /**
   * 添加用户分享
   */
  const handleAddOwner = async (_values: any) => {
    if (!hostName || !uuid) return
    
    try {
      await api.addVMOwner(hostName, uuid, { username: _values.username })
      message.success('用户添加成功')
      setOwnerModalVisible(false)
      ownerForm.resetFields()
      loadOwners()
    } catch (error) {
      message.error('用户添加失败')
    }
  }

  /**
   * 删除用户分享
   */
  const handleDeleteOwner = async (username: string) => {
    if (!hostName || !uuid) return
    
    Modal.confirm({
      title: '确认删除',
      content: `确定要移除用户 "${username}" 吗？`,
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.deleteVMOwner(hostName, uuid, username)
          message.success('用户删除成功')
          loadOwners()
        } catch (error) {
          message.error('用户删除失败')
        }
      },
    })
  }

  /**
   * 移交所有权
   */
  const handleTransferOwnership = async () => {
    if (!hostName || !uuid || !transferOwnerUsername) return

    try {
        await api.post(`/api/client/owners/${hostName}/${uuid}/transfer`, {
            new_owner: transferOwnerUsername,
            keep_access: keepAccessChecked,
            confirm_transfer: transferOwnerConfirmChecked
        })
        message.success('所有权移交成功')
        setTransferOwnershipModalVisible(false)
        setTimeout(() => window.location.reload(), 1500)
    } catch (error) {
        message.error('移交失败')
    }
  }

  /**
   * 重装系统
   */
  const handleReinstall = async (values: any) => {
    if (!hostName || !uuid) return
    
    try {
        await api.reinstallVM(hostName, uuid, values)
        message.success('重装系统指令已发送')
        setReinstallModalVisible(false)
        reinstallForm.resetFields()
    } catch (error) {
        message.error('重装系统失败')
    }
  }

  /**
   * 编辑虚拟机配置 - 预处理
   */
  const handleUpdateVM = async (values: any) => {
    // 验证系统密码复杂度
    if (values.os_pass) {
        const regex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/
        if (!regex.test(values.os_pass)) {
            message.error('系统密码必须至少8位，且包含字母和数字')
            return
        }
    }
    
    // 验证VNC密码复杂度
    if (values.vc_pass) {
        const regex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/
        if (!regex.test(values.vc_pass)) {
            message.error('VNC密码必须至少8位，且包含字母和数字')
            return
        }
    }

    setPendingEditValues(values)
    setSaveConfirmChecked(false)
    setSaveConfirmModalVisible(true)
  }

  /**
   * 确认更新虚拟机
   */
  const handleConfirmUpdateVM = async () => {
      if (!hostName || !uuid || !pendingEditValues) return
      
      try {
          // 构造网卡配置
          const nicAll: any = {}
          editNicList.forEach(nic => {
              if (nic.name) {
                  nicAll[nic.name] = {
                      nic_type: nic.type,
                      ip4_addr: nic.ip,
                      ip6_addr: nic.ip6
                  }
              }
          })

          // 映射字段名以匹配后端API需求
          const updateData = {
              ...pendingEditValues,
              speed_u: pendingEditValues.speed_up,
              speed_d: pendingEditValues.speed_down,
              nic_all: nicAll
          }
          // 删除旧字段名以免混淆
          delete updateData.speed_up
          delete updateData.speed_down

          await api.updateVM(hostName, uuid, updateData)
          message.success('配置更新成功')
          setSaveConfirmModalVisible(false)
          setEditModalVisible(false)
          setPendingEditValues(null)
          // 刷新页面以显示最新状态
          setTimeout(() => window.location.reload(), 1500)
      } catch (error) {
          message.error('配置更新失败')
      }
  }

  // 添加编辑网卡
  const addEditNic = () => {
      const newId = editNicList.length > 0 ? Math.max(...editNicList.map(n => n.id)) + 1 : 0
      setEditNicList([...editNicList, {
          id: newId,
          name: `ethernet${newId}`,
          type: 'nat',
          ip: '',
          ip6: ''
      }])
  }

  // 移除编辑网卡
  const removeEditNic = (id: number) => {
      setEditNicList(editNicList.filter(n => n.id !== id))
  }

  // 更新编辑网卡
  const updateEditNic = (id: number, field: string, value: any) => {
      setEditNicList(editNicList.map(n => n.id === id ? { ...n, [field]: value } : n))
  }

  /**
   * 添加NAT规则
   */
  const handleAddNATRule = async (values: any) => {
    if (!hostName || !uuid) return
    
    try {
      await api.addNATRule(hostName, uuid, values)
      message.success('NAT规则添加成功')
      setNatModalVisible(false)
      loadNATRules()
    } catch (error) {
      message.error('NAT规则添加失败')
    }
  }

  /**
   * 删除NAT规则
   */
  const handleDeleteNAT = async (ruleId: number) => {
    if (!hostName || !uuid) return
    
    try {
      await api.deleteNATRule(hostName, uuid, ruleId)
      message.success('NAT规则删除成功')
      loadNATRules()
    } catch (error) {
      message.error('NAT规则删除失败')
    }
  }

  /**
   * 获取状态标签颜色
   */
  const getStatusColor = (status: string) => {
    const statusMap: Record<string, string> = {
      running: 'success',
      stopped: 'default',
      paused: 'warning',
      error: 'error',
    }
    return statusMap[status] || 'default'
  }

  /**
   * 获取状态文本
   */
  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      running: '运行中',
      stopped: '已停止',
      paused: '已暂停',
      error: '错误',
    }
    return statusMap[status] || status
  }

  /**
   * 生成图表配置
   */
  const getChartOption = (title: string, data: number[], color: string, labels?: string[], unit: string = '%') => {
    return {
      title: {
        text: title,
        left: 'center',
        textStyle: { fontSize: 14, fontWeight: 'normal' },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
            const param = params[0];
            return `${param.axisValue}<br/>${param.marker}${param.seriesName}: ${param.value}${unit}`;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: labels && labels.length > 0 ? labels : (data || []).map((_, i) => `${(data || []).length - i}分钟前`),
      },
      yAxis: {
        type: 'value',
        max: unit === '%' ? 100 : undefined,
        axisLabel: { formatter: `{value}${unit}` },
      },
      series: [
        {
          name: title,
          type: 'line',
          smooth: true,
          data: data,
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: color + '80' },
                { offset: 1, color: color + '10' },
              ],
            },
          },
          lineStyle: { color: color },
          itemStyle: { color: color },
        },
      ],
    }
  }

  if (loading || !vm) {
    return <Card loading={loading}>加载中...</Card>
  }

  const config = vm.config || {}
  const statusList = vm.status || []
  const currentStatus = statusList.length > 0 ? statusList[0] : { ac_status: 'UNKNOWN' } as VMStatus
  
  // 计算使用率百分比
  const memPercent = currentStatus.mem_total && currentStatus.mem_total > 0 ? (currentStatus.mem_usage || 0) / currentStatus.mem_total * 100 : 0
  const hddPercent = currentStatus.hdd_total && currentStatus.hdd_total > 0 ? (currentStatus.hdd_usage || 0) / currentStatus.hdd_total * 100 : 0
  const gpuPercent = currentStatus.gpu_total && currentStatus.gpu_total > 0 ? (currentStatus.gpu_usage || 0) / currentStatus.gpu_total * 100 : 0

  return (
    <div className="p-6">
      {/* 面包屑导航 */}
      <Breadcrumb 
        className="mb-6"
        items={[
          {
            title: <HomeOutlined />,
          },
          {
            title: <a onClick={() => navigate('/hosts')}>主机管理</a>,
          },
          {
            title: <a onClick={() => navigate(`/hosts/${hostName}/vms`)}>{hostName}</a>,
          },
          {
            title: config.vm_uuid,
          },
        ]}
      />

      {/* 虚拟机头部信息 */}
      <Card className="mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
              <DesktopOutlined className="text-white text-3xl" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">{config.vm_uuid}</h1>
              <p className="text-gray-500">{config.os_name}</p>
              <div className="flex items-center gap-4 mt-2">
                <Space size="small">
                  <span className="text-xs text-gray-400">系统密码:</span>
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={config.os_pass}
                    readOnly
                    size="small"
                    style={{ width: 120 }}
                    variant="borderless"
                  />
                  <Tooltip title={showPassword ? '隐藏密码' : '显示密码'}>
                    <Button
                      type="text"
                      size="small"
                      icon={showPassword ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                      onClick={() => setShowPassword(!showPassword)}
                    />
                  </Tooltip>
                  <Tooltip title="复制密码">
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => handleCopyPassword(config.os_pass || '', '系统')}
                    />
                  </Tooltip>
                </Space>
                <Space size="small">
                  <span className="text-xs text-gray-400">VNC密码:</span>
                  <Input
                    type={showVncPassword ? 'text' : 'password'}
                    value={config.vc_pass}
                    readOnly
                    size="small"
                    style={{ width: 120 }}
                    variant="borderless"
                  />
                  <Tooltip title={showVncPassword ? '隐藏密码' : '显示密码'}>
                    <Button
                      type="text"
                      size="small"
                      icon={showVncPassword ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                      onClick={() => setShowVncPassword(!showVncPassword)}
                    />
                  </Tooltip>
                  <Tooltip title="复制VNC密码">
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => handleCopyPassword(config.vc_pass || '', 'VNC')}
                    />
                  </Tooltip>
                </Space>
              </div>
            </div>
          </div>
          <Tag color={getStatusColor(currentStatus.ac_status)} className="text-sm px-3 py-1">
            {getStatusText(currentStatus.ac_status)}
          </Tag>
        </div>
      </Card>

      {/* Tab导航 */}
      <Card className="mb-6">
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
          {
            key: 'info',
            label: '信息',
            children: (
              <>
                {/* IP地址信息 */}
                <Row gutter={16} className="mb-4">
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="虚拟机IPv4地址"
                        value={vm.ipv4_address || '-'}
                        valueStyle={{ fontSize: 16, fontFamily: 'monospace' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="虚拟机IPv6地址"
                        value={nics.length > 0 ? nics[0].ip6_address : (vm.ipv6_address || '-')}
                        valueStyle={{ fontSize: 14, fontFamily: 'monospace' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="外网访问IP"
                        value={vm.public_address || '-'}
                        valueStyle={{ fontSize: 16, fontFamily: 'monospace' }}
                      />
                    </Card>
                  </Col>
                </Row>

                {/* 虚拟机操作 */}
                <Card title="虚拟机操作" size="small" className="mb-4">
                  <Space wrap>
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={() => handlePowerAction('start')}
                      disabled={currentStatus.ac_status === 'STARTED'}
                    >
                      启动
                    </Button>
                    <Button
                      icon={<PauseCircleOutlined />}
                      onClick={() => handlePowerAction('stop')}
                      disabled={currentStatus.ac_status !== 'STARTED'}
                    >
                      关机
                    </Button>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={() => handlePowerAction('reset')}
                      disabled={currentStatus.ac_status !== 'STARTED'}
                    >
                      重启
                    </Button>
                    <Button
                      icon={<PauseCircleOutlined />}
                      onClick={() => handlePowerAction('pause')}
                      disabled={currentStatus.ac_status !== 'STARTED'}
                    >
                      暂停虚拟机
                    </Button>
                    <Button
                      icon={<PlayCircleOutlined />}
                      onClick={() => handlePowerAction('resume')}
                      disabled={currentStatus.ac_status !== 'SUSPEND'}
                    >
                      恢复虚拟机
                    </Button>
                    <Button
                      danger
                      icon={<PoweroffOutlined />}
                      onClick={() => handlePowerAction('hard_stop')}
                    >
                      强制关机
                    </Button>
                    <Button
                      danger
                      icon={<ReloadOutlined />}
                      onClick={() => handlePowerAction('hard_reset')}
                    >
                      强制重启
                    </Button>
                    <Button
                      icon={<EditOutlined />}
                      onClick={() => {
                        setEditModalVisible(true)
                        // 初始化编辑表单的网卡数据
                        if (vm?.config?.nic_all) {
                            const nics = Object.entries(vm.config.nic_all).map(([name, conf]: [string, any], index) => ({
                                id: index,
                                name: name,
                                type: conf.nic_type,
                                ip: conf.ip4_addr,
                                ip6: conf.ip6_addr
                            }))
                            setEditNicList(nics)
                        } else {
                            setEditNicList([])
                        }
                      }}
                    >
                      编辑配置
                    </Button>
                    <Button
                      icon={<RollbackOutlined />}
                      danger
                      onClick={() => setReinstallModalVisible(true)}
                    >
                      重装系统
                    </Button>
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={handleDelete}
                    >
                      删除虚拟机
                    </Button>
                    <Button
                      type="primary"
                      icon={<DesktopOutlined />}
                      onClick={handleOpenVNC}
                    >
                      VNC 控制台
                    </Button>
                    <Button
                      icon={<KeyOutlined />}
                      onClick={() => setPasswordModalVisible(true)}
                    >
                      修改系统密码
                    </Button>
                  </Space>
                </Card>

                {/* 资源配置信息 */}
                <Card title="资源配置" size="small" className="mb-4">
                  <Row gutter={[16, 16]}>
                    <Col span={8}>
                      <Card size="small" className="bg-gray-50">
                        <Statistic title="CPU核心" value={vm.cpu_num} suffix="核" />
                        <Progress percent={vm.cpu_usage || 0} status="active" />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" className="bg-gray-50">
                        <Statistic title="RAM内存" value={vm.mem_num} suffix="MB" />
                        <Progress percent={vm.mem_usage || 0} status="active" strokeColor="#52c41a" />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" className="bg-gray-50">
                        <Statistic title="HDD硬盘" value={vm.hdd_num} suffix="GB" />
                        <Progress percent={vm.hdd_usage || 0} strokeColor="#faad14" />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" className="bg-gray-50">
                        <Statistic title="GPU显存" value={vm.gpu_num} suffix="GB" />
                        <Progress percent={vm.gpu_usage || 0} strokeColor="#722ed1" />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" className="bg-gray-50">
                        <Statistic title="上行带宽" value={vm.speed_up} suffix="Mbps" />
                        <Progress percent={vm.net_usage || 0} strokeColor="#13c2c2" />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" className="bg-gray-50">
                        <Statistic title="下行带宽" value={vm.speed_down} suffix="Mbps" />
                        <Progress percent={vm.net_usage || 0} strokeColor="#1890ff" />
                      </Card>
                    </Col>
                  </Row>
                </Card>

                {/* 性能监控 */}
                <Card title="性能监控" size="small" className="mb-4">
                  <div className="mb-4 flex justify-end">
                    <Select 
                      value={timeRange} 
                      onChange={setTimeRange}
                      style={{ width: 120 }}
                      options={[
                        { value: 30, label: '最近30分钟' },
                        { value: 60, label: '最近1小时' },
                        { value: 360, label: '最近6小时' },
                        { value: 720, label: '最近12小时' },
                        { value: 1440, label: '最近24小时' },
                        { value: 10080, label: '最近7天' },
                      ]}
                    />
                  </div>
                  <Row gutter={[16, 16]}>
                    <Col span={8}>
                      <ReactECharts option={getChartOption('CPU使用率', monitorData.cpu, '#1890ff', monitorData.labels, '%')} style={{ height: 250 }} />
                    </Col>
                    <Col span={8}>
                      <ReactECharts option={getChartOption('内存使用率', monitorData.memory, '#52c41a', monitorData.labels, '%')} style={{ height: 250 }} />
                    </Col>
                    <Col span={8}>
                      <ReactECharts option={getChartOption('硬盘使用率', monitorData.disk, '#faad14', monitorData.labels, '%')} style={{ height: 250 }} />
                    </Col>
                    <Col span={8}>
                      <ReactECharts option={getChartOption('GPU显存', monitorData.gpu, '#722ed1', monitorData.labels, 'MB')} style={{ height: 250 }} />
                    </Col>
                    <Col span={8}>
                      <ReactECharts option={getChartOption('上行带宽', monitorData.netUp, '#13c2c2', monitorData.labels, 'Mbps')} style={{ height: 250 }} />
                    </Col>
                    <Col span={8}>
                      <ReactECharts option={getChartOption('下行带宽', monitorData.netDown, '#1890ff', monitorData.labels, 'Mbps')} style={{ height: 250 }} />
                    </Col>
                  </Row>
                </Card>
              </>
            ),
          },
          {
            key: 'nat',
            label: 'NAT端口转发',
            children: (
              <Card
                title="NAT端口转发规则"
                extra={
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setNatModalVisible(true)}
                  >
                    添加规则
                  </Button>
                }
              >
                <Table
                  rowKey="id"
                  dataSource={natRules}
                  columns={[
                    { title: '外网端口', dataIndex: 'public_port', key: 'public_port', width: 100 },
                    { title: '内网端口', dataIndex: 'private_port', key: 'private_port', width: 100 },
                    { title: '内网地址', dataIndex: 'internal_ip', key: 'internal_ip', width: 140 },
                    { title: '备注', dataIndex: 'description', key: 'description', ellipsis: true },
                    {
                      title: '操作',
                      key: 'action',
                      width: 80,
                      render: (_, record) => (
                        <Button
                          danger
                          size="small"
                          onClick={() => handleDeleteNAT(record.id)}
                        >
                          删除
                        </Button>
                      ),
                    },
                  ]}
                  pagination={false}
                />
              </Card>
            ),
          },
          {
            key: 'ip',
            label: 'IP地址管理',
            children: (
              <>
                {ipQuota && (
                  <Card size="small" className="mb-4">
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic title="IP配额" value={ipQuota.ip_num || 0} suffix="个" />
                      </Col>
                      <Col span={8}>
                        <Statistic title="已使用" value={ipQuota.ip_used || 0} suffix="个" />
                      </Col>
                      <Col span={8}>
                        <Progress percent={ipQuota.ip_percent || 0} status="active" />
                      </Col>
                    </Row>
                  </Card>
                )}
                <Card
                  title="IP地址管理"
                  extra={
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => setIpModalVisible(true)}
                    >
                      添加IP地址
                    </Button>
                  }
                >
                  <Table
                  rowKey={(record) => `${record.nic_name}-${record.ip_address}`}
                  dataSource={ipAddresses}
                  columns={[
                      { title: '网卡名称', dataIndex: 'nic_name', key: 'nic_name' },
                      { title: 'IPv4地址', dataIndex: 'ip_address', key: 'ip_address', width: 140 },
                      { title: 'IPv6地址', dataIndex: 'ip6_address', key: 'ip6_address', ellipsis: true },
                      { title: 'IP类型', dataIndex: 'ip_type', key: 'ip_type', width: 80 },
                      { title: '子网掩码', dataIndex: 'subnet_mask', key: 'subnet_mask', width: 140 },
                      { title: '网关', dataIndex: 'gateway', key: 'gateway', width: 140 },
                      {
                        title: '操作',
                        key: 'action',
                        width: 120,
                        render: (_, record) => (
                          <Space>
                            <Button 
                              danger 
                              size="small"
                              onClick={() => handleDeleteIPAddress(record.nic_name)}
                            >
                              删除
                            </Button>
                          </Space>
                        ),
                      },
                    ]}
                    pagination={false}
                    scroll={{ x: 1200 }}
                  />
                </Card>
              </>
            ),
          },
          {
            key: 'proxy',
            label: '反向代理',
            children: (
              <Card
                title="反向代理配置"
                extra={
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setProxyModalVisible(true)}
                  >
                    添加代理
                  </Button>
                }
              >
                <Table
                  rowKey="id"
                  dataSource={proxyRules}
                  columns={[
                    { title: '域名', dataIndex: 'domain', key: 'domain', ellipsis: true },
                    { title: '后端IP', dataIndex: 'backend_ip', key: 'backend_ip', width: 140 },
                    { title: '目标端口', dataIndex: 'target_port', key: 'target_port', width: 100 },
                    {
                      title: 'SSL',
                      dataIndex: 'ssl_enabled',
                      key: 'ssl_enabled',
                      width: 80,
                      render: (ssl) => (
                        <Tag color={ssl ? 'success' : 'default'}>
                          {ssl ? '已启用' : '未启用'}
                        </Tag>
                      ),
                    },
                    { title: '备注', dataIndex: 'description', key: 'description', ellipsis: true },
                    {
                      title: '操作',
                      key: 'action',
                      width: 120,
                      render: (_, record) => (
                        <Space>
                          <Button 
                            danger 
                            size="small"
                            onClick={() => handleDeleteProxy(record.id)}
                          >
                            删除
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                  pagination={false}
                  scroll={{ x: 1000 }}
                />
              </Card>
            ),
          },
          {
            key: 'hdd',
            label: '数据盘',
            children: (
              <Card
                title="数据盘管理"
                extra={
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setHddModalVisible(true)}
                  >
                    添加数据盘
                  </Button>
                }
              >
                <Table
                  rowKey="hdd_index"
                  dataSource={hdds}
                  columns={[
                    { title: '序号', dataIndex: 'hdd_index', key: 'hdd_index', width: 80 },
                    { title: '大小(GB)', dataIndex: 'hdd_num', key: 'hdd_num', width: 120 },
                    { title: '路径', dataIndex: 'hdd_path', key: 'hdd_path', ellipsis: true },
                    {
                      title: '操作',
                      key: 'action',
                      width: 100,
                      render: (_, record) => (
                        <Button
                          danger
                          size="small"
                          onClick={() => handleDeleteHDD(record.hdd_path)}
                        >
                          删除
                        </Button>
                      ),
                    },
                  ]}
                  pagination={false}
                />
              </Card>
            ),
          },
          {
            key: 'iso',
            label: 'ISO挂载',
            children: (
              <Card
                title="ISO挂载"
                extra={
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setIsoModalVisible(true)}
                  >
                    挂载ISO
                  </Button>
                }
              >
                <Table
                  rowKey="iso_key"
                  dataSource={isos}
                  columns={[
                    { title: '挂载名称', dataIndex: 'iso_name', key: 'iso_name', width: 120 },
                    { title: '文件名', dataIndex: 'iso_file', key: 'iso_file', ellipsis: true },
                    { title: '备注', dataIndex: 'iso_hint', key: 'iso_hint', ellipsis: true },
                    {
                      title: '操作',
                      key: 'action',
                      width: 100,
                      render: (_, record) => (
                        <Button
                          danger
                          size="small"
                          onClick={() => handleDeleteISO(record.iso_key)}
                        >
                          卸载
                        </Button>
                      ),
                    },
                  ]}
                  pagination={false}
                />
              </Card>
            ),
          },
          {
            key: 'backup',
            label: '备份管理',
            children: (
              <Card 
                title="备份管理"
                extra={
                    <Button 
                        type="primary" 
                        icon={<CloudSyncOutlined />} 
                        onClick={() => setBackupModalVisible(true)}
                    >
                        创建备份
                    </Button>
                }
              >
                <Table 
                    rowKey="backup_name"
                    dataSource={backups}
                    columns={[
                        { title: '备份名称', dataIndex: 'backup_name', key: 'backup_name' },
                        { 
                          title: '创建时间', 
                          dataIndex: 'backup_time', 
                          key: 'backup_time',
                          render: (time) => time ? new Date(time * 1000).toLocaleString('zh-CN') : '-'
                        },
                        { title: '备注', dataIndex: 'backup_hint', key: 'backup_hint' },
                        {
                            title: '操作',
                            key: 'action',
                            render: (_, record) => (
                                <Space>
                                    <Button size="small" onClick={() => handleRestoreBackup(record.backup_name)}>恢复</Button>
                                    <Button danger size="small" onClick={() => handleDeleteBackup(record.backup_name)}>删除</Button>
                                </Space>
                            )
                        }
                    ]}
                    pagination={false}
                />
              </Card>
            ),
          },
          {
            key: 'owners',
            label: '用户管理',
            children: (
              <Card 
                title="用户管理"
                extra={
                    <Button 
                        type="primary" 
                        icon={<UsergroupAddOutlined />} 
                        onClick={() => setOwnerModalVisible(true)}
                    >
                        添加用户
                    </Button>
                }
              >
                <Table 
                    rowKey="username"
                    dataSource={owners}
                    columns={[
                        { title: '用户名', dataIndex: 'username', key: 'username' },
                        { title: '角色', dataIndex: 'role', key: 'role' },
                        {
                            title: '操作',
                            key: 'action',
                            render: (_, record) => (
                                <Button danger size="small" onClick={() => handleDeleteOwner(record.username)}>删除</Button>
                            )
                        }
                    ]}
                    pagination={false}
                />
              </Card>
            ),
          },
        ]} />
      </Card>

      {/* 编辑虚拟机模态框 */}
      <Modal
        title="编辑虚拟机配置"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={() => editVmForm.submit()}
        width={700}
      >
        <Form form={editVmForm} onFinish={handleUpdateVM} layout="vertical">
          <Form.Item name="vm_uuid" hidden><Input /></Form.Item>
          
          <Row gutter={16}>
            <Col span={12}>
                <Form.Item label="操作系统" name="os_name" initialValue={config.os_name}>
                    <Select>
                        {hostConfig?.system_maps && Object.entries(hostConfig.system_maps).map(([name, val]) => {
                            // val can be [image, size] or just image string
                            const image = Array.isArray(val) ? val[0] : val
                            if (!image) return null
                            return <Select.Option key={name} value={image}>{name}</Select.Option>
                        })}
                    </Select>
                </Form.Item>
            </Col>
            <Col span={12}>
                <Form.Item label="VNC端口" name="vc_port" initialValue={config.vc_port}>
                    <InputNumber min={5900} max={65535} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
                <Form.Item label="系统密码" name="os_pass" initialValue={config.os_pass}>
                    <Input.Password placeholder="留空则不修改" />
                </Form.Item>
            </Col>
            <Col span={12}>
                <Form.Item label="VNC密码" name="vc_pass" initialValue={config.vc_pass}>
                    <Input.Password placeholder="留空则不修改" />
                </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
                <Form.Item label="CPU核心" name="cpu_num" initialValue={config.cpu_num}>
                    <InputNumber min={1} max={64} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
            <Col span={8}>
                <Form.Item label="内存(MB)" name="mem_num" initialValue={config.mem_num}>
                    <InputNumber min={512} max={1048576} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
            <Col span={8}>
                <Form.Item label="硬盘(GB)" name="hdd_num" initialValue={config.hdd_num}>
                    <InputNumber min={1} max={10240} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
                <Form.Item label="GPU数量" name="gpu_num" initialValue={config.gpu_num || 0}>
                    <InputNumber min={0} max={8} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
            <Col span={8}>
                <Form.Item label="上行带宽(Mbps)" name="speed_up" initialValue={config.speed_up || 100}>
                    <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
            <Col span={8}>
                <Form.Item label="下行带宽(Mbps)" name="speed_down" initialValue={config.speed_down || 100}>
                    <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={8}>
                <Form.Item label="NAT端口数" name="nat_num" initialValue={config.nat_num || 0}>
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
            <Col span={8}>
                <Form.Item label="Web代理数" name="web_num" initialValue={config.web_num || 0}>
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
            <Col span={8}>
                <Form.Item label="流量限制(GB)" name="flu_num" initialValue={config.flu_num || 0}>
                    <InputNumber min={0} max={100000} style={{ width: '100%' }} />
                </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">
            <div className="flex justify-between items-center w-full">
                <span>网卡配置</span>
                <Button type="dashed" size="small" onClick={addEditNic} icon={<PlusOutlined />}>添加网卡</Button>
            </div>
          </Divider>

          {editNicList.map((nic, index) => (
            <div key={nic.id} className="mb-4 p-3 bg-gray-50 rounded border border-gray-200 relative">
                <div className="absolute top-2 right-2">
                    <Button 
                        type="text" 
                        danger 
                        size="small"
                        icon={<DeleteOutlined />} 
                        onClick={() => removeEditNic(nic.id)} 
                    />
                </div>
                <Row gutter={8}>
                    <Col span={8}>
                        <div className="mb-2">
                            <span className="text-xs text-gray-500 block">网卡名称</span>
                            <Input 
                                value={nic.name} 
                                onChange={e => updateEditNic(nic.id, 'name', e.target.value)}
                                size="small"
                            />
                        </div>
                    </Col>
                    <Col span={8}>
                        <div className="mb-2">
                            <span className="text-xs text-gray-500 block">类型</span>
                            <Select 
                                value={nic.type} 
                                onChange={val => updateEditNic(nic.id, 'type', val)}
                                size="small"
                                style={{ width: '100%' }}
                            >
                                <Select.Option value="nat">NAT</Select.Option>
                                <Select.Option value="bridge">Bridge</Select.Option>
                            </Select>
                        </div>
                    </Col>
                    <Col span={8}>
                        <div className="mb-2">
                            <span className="text-xs text-gray-500 block">IPv4地址</span>
                            <Input 
                                value={nic.ip} 
                                onChange={e => updateEditNic(nic.id, 'ip', e.target.value)}
                                placeholder="自动分配"
                                size="small"
                            />
                        </div>
                    </Col>
                    <Col span={24}>
                        <div>
                            <span className="text-xs text-gray-500 block">IPv6地址 (可选)</span>
                            <Input 
                                value={nic.ip6} 
                                onChange={e => updateEditNic(nic.id, 'ip6', e.target.value)}
                                placeholder="自动分配"
                                size="small"
                            />
                        </div>
                    </Col>
                </Row>
            </div>
          ))}
        </Form>
      </Modal>

      {/* 保存确认模态框 */}
      <Modal
        title="保存确认"
        open={saveConfirmModalVisible}
        onCancel={() => setSaveConfirmModalVisible(false)}
        onOk={handleConfirmUpdateVM}
        okText="确认保存"
        okButtonProps={{ disabled: !saveConfirmChecked }}
        width={400}
      >
        <div className="mb-4">
            <p>确定要保存对虚拟机 "<strong>{uuid}</strong>" 的配置修改吗？</p>
        </div>
        <div className="p-3 bg-gray-50 border border-gray-200 rounded flex items-center justify-center">
            <Space>
                <input 
                    type="checkbox" 
                    id="saveConfirmCheck" 
                    checked={saveConfirmChecked}
                    onChange={(e) => setSaveConfirmChecked(e.target.checked)}
                    className="w-4 h-4 text-blue-600"
                />
                <label htmlFor="saveConfirmCheck" className="cursor-pointer select-none text-sm text-gray-700">我已确认强制关闭虚拟机</label>
            </Space>
        </div>
      </Modal>

      {/* 修改密码模态框 */}
      <Modal
        title="修改系统密码"
        open={passwordModalVisible}
        onCancel={() => setPasswordModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleChangePassword} layout="vertical">
          <Form.Item
            label="新密码"
            name="new_password"
            rules={[{ required: true, message: '请输入新密码' }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            label="确认密码"
            name="confirm_password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加NAT规则模态框 */}
      <Modal
        title="添加NAT规则"
        open={natModalVisible}
        onCancel={() => setNatModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleAddNATRule} layout="vertical">
          <Form.Item
            label="协议"
            name="protocol"
            rules={[{ required: true, message: '请选择协议' }]}
          >
            <Select>
              <Select.Option value="tcp">TCP</Select.Option>
              <Select.Option value="udp">UDP</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="公网端口"
            name="public_port"
            initialValue={0}
            help="留空或填0表示自动分配"
          >
            <InputNumber min={0} max={65535} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            label="内网端口"
            name="private_port"
            rules={[{ required: true, message: '请输入内网端口' }]}
          >
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="内网地址" name="internal_ip">
             <Select placeholder="请选择IP地址 (可选)">
                {/* 优先显示配置中的IP */}
                {nics.map(nic => {
                     if (!nic.ip_address) return null
                     return <Select.Option key={nic.nic_name} value={nic.ip_address}>{nic.ip_address} ({nic.nic_name})</Select.Option>
                 })}
                {/* 补充显示其他IP */}
                {ipAddresses.filter(ip => !nics.find(n => n.ip_address === ip.ip_address)).map(ip => {
                    if (!ip.ip_address) return null
                    return <Select.Option key={ip.ip_address} value={ip.ip_address}>{ip.ip_address} ({ip.nic_name})</Select.Option>
                })}
             </Select>
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加IP地址模态框 */}
      <Modal
        title="添加IP地址"
        open={ipModalVisible}
        onCancel={() => setIpModalVisible(false)}
        onOk={() => ipForm.submit()}
      >
        {ipQuota && (
            <div className="mb-4 p-3 bg-gray-50 rounded text-sm">
                <div className="flex justify-between mb-1">
                    <span>内网IP配额:</span>
                    <span className="font-mono">{ipQuota.ip_used}/{ipQuota.ip_num}</span>
                </div>
                {/* 假设公网配额也在user_data中 */}
                <div className="flex justify-between">
                    <span>公网IP配额:</span>
                    <span className="font-mono">{ipQuota.user_data?.used_pub_ips || 0}/{ipQuota.user_data?.quota_pub_ips || 0}</span>
                </div>
            </div>
        )}
        <Form form={ipForm} onFinish={handleAddIPAddress} layout="vertical">
            <Form.Item label="网卡类型" name="nic_type" initialValue="nat">
                <Select>
                    <Select.Option value="nat">内网(NAT)</Select.Option>
                    <Select.Option value="pub">公网(Public)</Select.Option>
                </Select>
            </Form.Item>
            <Form.Item label="IPv4地址" name="ip4_addr">
                <Input placeholder="留空自动分配" />
            </Form.Item>
            <Form.Item label="IPv6地址" name="ip6_addr">
                <Input placeholder="可选" />
            </Form.Item>
            <Form.Item label="网关" name="nic_gate">
                <Input placeholder="可选" />
            </Form.Item>
            <Form.Item label="子网掩码" name="nic_mask" initialValue="255.255.255.0">
                <Input />
            </Form.Item>
        </Form>
      </Modal>

      {/* 添加反向代理模态框 */}
      <Modal
        title="添加反向代理"
        open={proxyModalVisible}
        onCancel={() => setProxyModalVisible(false)}
        onOk={() => proxyForm.submit()}
      >
        <Form form={proxyForm} onFinish={handleAddProxy} layout="vertical">
            <Form.Item label="域名" name="domain" rules={[{ required: true, message: '请输入域名' }]}>
                <Input placeholder="example.com" />
            </Form.Item>
            <Form.Item label="后端IP" name="backend_ip" rules={[{ required: true, message: '请选择后端IP' }]}>
                <Select placeholder="请选择">
                    {ipAddresses.map(ip => {
                        if (!ip.ip_address) return null
                        return <Select.Option key={ip.ip_address} value={ip.ip_address}>{ip.ip_address}</Select.Option>
                    })}
                </Select>
            </Form.Item>
            <Form.Item label="后端端口" name="backend_port" rules={[{ required: true, message: '请输入端口' }]}>
                <InputNumber min={1} max={65535} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="ssl_enabled" valuePropName="checked">
                <div className="flex items-center gap-2">
                    <input type="checkbox" />
                    <span>启用SSL (HTTPS)</span>
                </div>
            </Form.Item>
            <Form.Item label="备注" name="description">
                <Input.TextArea />
            </Form.Item>
        </Form>
      </Modal>

      {/* 添加数据盘模态框 */}
      <Modal
        title="添加数据盘"
        open={hddModalVisible}
        onCancel={() => setHddModalVisible(false)}
        onOk={() => hddForm.submit()}
      >
        <Form form={hddForm} onFinish={handleAddHDD} layout="vertical">
            <Form.Item label="磁盘名称" name="hdd_name" rules={[{ required: true, message: '请输入磁盘名称' }]}>
                <Input placeholder="只能包含字母、数字和下划线" />
            </Form.Item>
            <Form.Item label="容量 (GB)" name="hdd_size" initialValue={10} rules={[{ required: true, message: '请输入容量' }]}>
                <InputNumber min={1} max={10240} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="类型" name="hdd_type" initialValue={0}>
                <Select>
                    <Select.Option value={0}>HDD</Select.Option>
                    <Select.Option value={1}>SSD</Select.Option>
                </Select>
            </Form.Item>
        </Form>
      </Modal>

      {/* 挂载数据盘确认模态框 */}
      <Modal
        title="挂载数据盘"
        open={mountHddModalVisible}
        onCancel={() => setMountHddModalVisible(false)}
        onOk={handleMountHDD}
        okText="确认挂载"
      >
        <p>确定要挂载数据盘 "<strong>{currentMountHdd?.hdd_path}</strong>" 吗？</p>
        <p className="text-gray-500 text-sm mt-2">挂载后需要在系统内进行配置才能使用。</p>
      </Modal>

      {/* 卸载数据盘确认模态框 */}
      <Modal
        title="卸载数据盘"
        open={unmountHddModalVisible}
        onCancel={() => setUnmountHddModalVisible(false)}
        onOk={handleUnmountHDD}
        okText="确认卸载"
        okType="danger"
      >
        <p>确定要卸载数据盘 "<strong>{currentUnmountHdd?.hdd_path}</strong>" 吗？</p>
        <p className="text-red-500 text-sm mt-2">请确保在系统内已卸载该磁盘，否则可能导致数据丢失。</p>
      </Modal>

      {/* 添加ISO挂载模态框 */}
      <Modal
        title="挂载ISO"
        open={isoModalVisible}
        onCancel={() => setIsoModalVisible(false)}
        onOk={() => isoForm.submit()}
      >
        <Form form={isoForm} onFinish={handleAddISO} layout="vertical">
            <Form.Item label="ISO镜像" name="iso_file" rules={[{ required: true, message: '请选择镜像' }]}>
                <Select placeholder="请选择">
                    {hostConfig?.images_maps && Object.entries(hostConfig.images_maps).map(([name, file]) => {
                         if (!file) return null
                         return <Select.Option key={name} value={file}>{name} ({file})</Select.Option>
                     })}
                    {/* Fallback if images_maps is not available directly, check api response */}
                </Select>
            </Form.Item>
            <Form.Item label="挂载名称" name="iso_name" rules={[{ required: true, message: '请输入名称' }]}>
                <Input />
            </Form.Item>
            <Form.Item label="备注" name="iso_hint">
                <Input />
            </Form.Item>
        </Form>
      </Modal>

      {/* 重装系统模态框 */}
      <Modal
        title="重装系统"
        open={reinstallModalVisible}
        onCancel={() => setReinstallModalVisible(false)}
        onOk={() => reinstallForm.submit()}
        okType="danger"
        okText="确认重装"
      >
        <Alert
            message="警告：重装系统将清除所有数据！"
            description="此操作不可逆，请确保已备份重要数据。"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
        />
        <Form form={reinstallForm} onFinish={handleReinstall} layout="vertical">
            <Form.Item
                label="操作系统"
                name="os_name"
                rules={[{ required: true, message: '请选择操作系统' }]}
            >
                <Select placeholder="请选择">
                    {hostConfig?.system_maps && Object.entries(hostConfig.system_maps).map(([name, val]) => {
                        const image = Array.isArray(val) ? val[0] : val
                        if (!image) return null
                        return <Select.Option key={name} value={image}>{name}</Select.Option>
                    })}
                </Select>
            </Form.Item>
            <Form.Item
                label="系统密码"
                name="password"
                rules={[{ required: true, message: '请输入新系统密码' }]}
            >
                <Input.Password />
            </Form.Item>
        </Form>
      </Modal>

      {/* 创建备份模态框 */}
      <Modal
        title="创建备份"
        open={backupModalVisible}
        onCancel={() => setBackupModalVisible(false)}
        onOk={() => backupForm.submit()}
      >
        <Form form={backupForm} onFinish={handleCreateBackup} layout="vertical">
            <Form.Item
                label="备份名称"
                name="backup_name"
                rules={[{ required: true, message: '请输入备份名称' }]}
            >
                <Input />
            </Form.Item>
        </Form>
      </Modal>

      {/* 添加用户模态框 */}
      <Modal
        title="添加用户"
        open={ownerModalVisible}
        onCancel={() => setOwnerModalVisible(false)}
        onOk={() => ownerForm.submit()}
      >
        <Form form={ownerForm} onFinish={handleAddOwner} layout="vertical">
            <Form.Item
                label="用户名"
                name="username"
                rules={[{ required: true, message: '请输入用户名' }]}
            >
                <Input />
            </Form.Item>
        </Form>
      </Modal>

      {/* 移交所有权模态框 */}
      <Modal
        title="移交所有权"
        open={transferOwnershipModalVisible}
        onCancel={() => setTransferOwnershipModalVisible(false)}
        onOk={handleTransferOwnership}
        okText="确认移交"
        okButtonProps={{ disabled: !transferOwnerConfirmChecked || !transferOwnerUsername }}
      >
        <div className="mb-4">
            <p>移交所有权将把当前虚拟机的所有权转让给另一个用户。</p>
        </div>
        <div className="mb-4">
            <label className="block mb-2 text-sm font-medium">新所有者用户名</label>
            <Input 
                value={transferOwnerUsername}
                onChange={(e) => setTransferOwnerUsername(e.target.value)}
                placeholder="请输入用户名"
            />
        </div>
        <div className="mb-4">
            <Space direction="vertical">
                <Checkbox 
                    checked={keepAccessChecked}
                    onChange={(e) => setKeepAccessChecked(e.target.checked)}
                >
                    保留我的访问权限 (作为普通协作者)
                </Checkbox>
                <Checkbox 
                    checked={transferOwnerConfirmChecked}
                    onChange={(e) => setTransferOwnerConfirmChecked(e.target.checked)}
                >
                    我确认移交所有权
                </Checkbox>
            </Space>
        </div>
      </Modal>

      {/* 移交数据盘模态框 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#1890ff' }}>
            <CloudSyncOutlined />
            <span>移交数据盘</span>
          </div>
        }
        open={transferHddModalVisible}
        onCancel={() => setTransferHddModalVisible(false)}
        onOk={handleTransferHDD}
        okText="确认移交"
        okButtonProps={{ disabled: !transferConfirmChecked }}
      >
        <div style={{ marginBottom: 24 }}>
           <p>确定要移交数据盘 "<strong>{currentTransferHdd?.hdd_path}</strong>" 吗？</p>
        </div>
        
        <div style={{ marginBottom: 16 }}>
           <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>目标虚拟机UUID *</label>
           <Input 
             placeholder="输入目标虚拟机UUID" 
             value={transferTargetUuid}
             onChange={(e) => setTransferTargetUuid(e.target.value)}
           />
           <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>数据盘将从当前虚拟机移交到目标虚拟机</div>
        </div>

        <Alert 
           message="目标机器不会自动挂载转移硬盘" 
           type="info" 
           showIcon 
           style={{ marginBottom: 16 }}
        />

        <div style={{ padding: 12, background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 4 }}>
           <Space>
             <input 
               type="checkbox" 
               id="transferConfirm" 
               checked={transferConfirmChecked}
               onChange={(e) => setTransferConfirmChecked(e.target.checked)}
             />
             <label htmlFor="transferConfirm" style={{ cursor: 'pointer', userSelect: 'none' }}>我同意关闭当前虚拟机执行操作</label>
           </Space>
        </div>
      </Modal>
    </div>
  )
}

export default VMDetail
