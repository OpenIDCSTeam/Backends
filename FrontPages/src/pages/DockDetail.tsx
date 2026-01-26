import {useEffect, useState, useMemo} from 'react'
import {useParams, useNavigate} from 'react-router-dom'
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
    Row,
    Col,
    Descriptions,
    Badge,
    Spin,
    Alert,
    Checkbox,
    Dropdown,
    MenuProps,
    Radio,
    Tooltip,
    Divider
} from 'antd'
import {
    HomeOutlined,
    ReloadOutlined,
    PoweroffOutlined,
    DeleteOutlined,
    DesktopOutlined,
    EyeOutlined,
    CopyOutlined,
    PlusOutlined,
    UsergroupAddOutlined,
    MoreOutlined,
    WindowsOutlined,
    AppleOutlined,
    CodeOutlined,
    CloudSyncOutlined,
    AreaChartOutlined,
    HddOutlined,
    GlobalOutlined,
    SafetyCertificateOutlined,
    PlayCircleOutlined,
    PauseCircleOutlined,
    EditOutlined,
    KeyOutlined,
    DownOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import api from '@/utils/apis.ts'

/**
 * 虚拟机详情数据接口
 */
interface DockDetail {
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
    gpu_mem?: number // 显存大小
    speed_up: number
    speed_down: number
    nat_num: number
    web_num: number
    flu_num: number // 流量限制
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
    config?: any
}

interface VMStatus {
    ac_status: string
    mem_total: number
    mem_usage: number
    hdd_total: number
    hdd_usage: number
    gpu_total: number
    gpu_usage: number
    cpu_usage: number
    network_u: number
    network_d: number
    network_rx?: number
    network_tx?: number
    flu_usage?: number
    on_update: number

    [key: string]: any
}



interface NATRule {
    id: number
    protocol: string
    public_port: number
    private_port: number
    internal_ip?: string
    description?: string
}

interface IPAddress {
    nic_name: string
    ip_address: string
    ip6_address?: string
    ip_type: string
    subnet_mask?: string
    gateway?: string
}

interface ProxyRule {
    id: number
    domain: string
    target_port: number
    ssl_enabled: boolean
    backend_ip?: string
    description?: string
}

interface HDDInfo {
    hdd_index?: number
    hdd_num: number
    hdd_path: string
    hdd_type?: number
}

interface ISOInfo {
    iso_index?: number
    iso_path?: string
    iso_name?: string
    iso_file?: string
    iso_hint?: string
    iso_key?: string
}

interface BackupInfo {
    backup_index?: number
    backup_name: string
    backup_path?: string
    created_time: string
    size?: string
}

interface OwnerInfo {
    username: string
    role: string
    is_admin?: boolean
    email?: string
}

interface HostConfig {
    system_maps: Record<string, [string, number]>
    images_maps?: Record<string, string>
    tab_lock?: string[]
}

function VMDetail() {
    const {hostName, uuid} = useParams<{ hostName: string; uuid: string }>()
    const navigate = useNavigate()

    // 状态管理
    const [vm, setVM] = useState<DockDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState('overview')
    const [showPassword, setShowPassword] = useState(false)
    const [showVncPassword, setShowVncPassword] = useState(false)
    const [natRules, setNatRules] = useState<NATRule[]>([])
    const [ipAddresses, setIpAddresses] = useState<IPAddress[]>([])
    const [proxyRules, setProxyRules] = useState<ProxyRule[]>([])
    const [timeRange, setTimeRange] = useState(30) // 默认30分钟
    const [chartView, setChartView] = useState<'performance' | 'resource' | 'network'>('performance') // 默认性能视图
    const [monitorData, setMonitorData] = useState<any>({
        cpu: [], memory: [], disk: [], gpu: [], netUp: [], netDown: [], traffic: [], nat: [], proxy: [], labels: []
    })
    const [hostConfig, setHostConfig] = useState<HostConfig | null>(null)

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
    const [mountHddModalVisible, setMountHddModalVisible] = useState(false)
    const [unmountHddModalVisible, setUnmountHddModalVisible] = useState(false)

    const [ipQuota, setIpQuota] = useState<any>(null)
    const [hdds, setHdds] = useState<HDDInfo[]>([])
    const [currentTransferHdd, setCurrentTransferHdd] = useState<HDDInfo | null>(null)
    const [currentMountHdd, setCurrentMountHdd] = useState<HDDInfo | null>(null)
    const [currentUnmountHdd, setCurrentUnmountHdd] = useState<HDDInfo | null>(null)
    const [transferTargetUuid, setTransferTargetUuid] = useState('')
    const [transferOwnerUsername, setTransferOwnerUsername] = useState('')
    const [transferOwnerConfirmChecked, setTransferOwnerConfirmChecked] = useState(false)
    const [keepAccessChecked, setKeepAccessChecked] = useState(false)

    const [saveConfirmModalVisible, setSaveConfirmModalVisible] = useState(false)
    const [saveConfirmChecked, setSaveConfirmChecked] = useState(false)
    const [pendingEditValues, setPendingEditValues] = useState<any>(null)

    // 通用确认动作状态
    const [actionConfirmModalVisible, setActionConfirmModalVisible] = useState(false)
    const [currentAction, setCurrentAction] = useState<{
        title: string;
        content: string;
        onConfirm: () => Promise<void>;
        requireShutdown?: boolean;
        confirmChecked?: boolean;
    } | null>(null)

    const [isos, setIsos] = useState<ISOInfo[]>([])
    const [backups, setBackups] = useState<BackupInfo[]>([])
    const [owners, setOwners] = useState<OwnerInfo[]>([])

    const [form] = Form.useForm()
    const [ipForm] = Form.useForm()
    const [proxyForm] = Form.useForm()
    const [hddForm] = Form.useForm()
    const [isoForm] = Form.useForm()
    const [ownerForm] = Form.useForm()
    const [reinstallForm] = Form.useForm()
    const [backupForm] = Form.useForm()
    const [editVmForm] = Form.useForm()

    const [editNicList, setEditNicList] = useState<any[]>([])

    // New Confirmation States
    const [isoMountConfirmChecked, setIsoMountConfirmChecked] = useState(false)
    const [unmountIsoConfirmVisible, setUnmountIsoConfirmVisible] = useState(false)
    const [currentUnmountIso, setCurrentUnmountIso] = useState<string>('')
    const [unmountIsoConfirmChecked, setUnmountIsoConfirmChecked] = useState(false)

    const [unmountHddConfirmChecked, setUnmountHddConfirmChecked] = useState(false)
    const [mountHddConfirmChecked, setMountHddConfirmChecked] = useState(false)
    const [transferHddConfirmChecked, setTransferHddConfirmChecked] = useState(false)

    const [backupCreateConfirmChecked, setBackupCreateConfirmChecked] = useState(false)
    const [restoreConfirmChecked1, setRestoreConfirmChecked1] = useState(false)
    const [restoreConfirmChecked2, setRestoreConfirmChecked2] = useState(false)
    const [currentRestoreBackup, setCurrentRestoreBackup] = useState<string>('')
    const [restoreBackupModalVisible, setRestoreBackupModalVisible] = useState(false)

    const [reinstallConfirmChecked, setReinstallConfirmChecked] = useState(false)

    // Loading States
    const [isoActionLoading, setIsoActionLoading] = useState(false)
    const [hddActionLoading, setHddActionLoading] = useState(false)
    const [backupActionLoading, setBackupActionLoading] = useState(false)
    const [ownerActionLoading, setOwnerActionLoading] = useState(false)
    const [reinstallActionLoading, setReinstallActionLoading] = useState(false)
    // 截图状态
    const [vmScreenshot, setVmScreenshot] = useState<string>('')
    const [loadingScreenshot, setLoadingScreenshot] = useState<boolean>(false)
    
    // 当前虚拟机状态 - 用于避免使用未初始化的变量
    const [currentStatus, setCurrentStatus] = useState<VMStatus>({ ac_status: 'UNKNOWN', mem_total: 0, mem_usage: 0, hdd_total: 0, hdd_usage: 0, gpu_total: 0, gpu_usage: 0, cpu_usage: 0, network_u: 0, network_d: 0, on_update: 0 })

    // 计算所有可用的IP地址
    const availableIPs = useMemo(() => {
        if (!vm || !vm.config) return []
        const ipList: string[] = []

        // 优先从网卡配置获取确定的IP
        if (vm.config.nic_all) {
            Object.values(vm.config.nic_all).forEach((nic: any) => {
                if (nic.ip4_addr && nic.ip4_addr !== '-' && nic.ip4_addr !== '0.0.0.0') ipList.push(nic.ip4_addr)
                if (nic.ip6_addr && nic.ip6_addr !== '-' && nic.ip6_addr !== '::') ipList.push(nic.ip6_addr)
            })
        }

        // 补充ip_all
        if (vm.config.ip_all && Array.isArray(vm.config.ip_all)) {
            vm.config.ip_all.forEach((ip: any) => {
                if (ip.address) ipList.push(ip.address)
            })
        }

        return Array.from(new Set(ipList))
    }, [vm])

    // 获取OS图标
    const getOSIcon = (osName: string) => {
        const name = (osName || '').toLowerCase()
        const iconStyle = {fontSize: '24px', marginRight: '8px'}

        if (name.includes('windows')) return <WindowsOutlined style={{...iconStyle, color: '#1890ff'}}/>
        if (name.includes('macos')) return <AppleOutlined style={{...iconStyle, color: '#000000'}}/>
        if (name.includes('ubuntu')) return <span className="anticon" style={{...iconStyle, color: '#E95420'}}><i
            className="fab fa-ubuntu"></i><CodeOutlined/></span>
        if (name.includes('centos')) return <span className="anticon"
                                                  style={{...iconStyle, color: '#262577'}}><CodeOutlined/></span>
        if (name.includes('debian')) return <span className="anticon"
                                                  style={{...iconStyle, color: '#A81D33'}}><CodeOutlined/></span>
        if (name.includes('fedora')) return <span className="anticon"
                                                  style={{...iconStyle, color: '#294172'}}><CodeOutlined/></span>
        if (name.includes('linux')) return <span className="anticon"
                                                 style={{...iconStyle, color: '#333'}}><DesktopOutlined/></span>

        return <DesktopOutlined style={iconStyle}/>
    }

    // 获取操作系统显示名称
    const getOSDisplayName = (osName: string) => {
        if (!hostConfig || !hostConfig.system_maps) return osName;
        // system_maps Key is Display Name, Value is [filename, min_size] or filename
        for (const [displayName, val] of Object.entries(hostConfig.system_maps)) {
            const filename = Array.isArray(val) ? val[0] : val;
            if (filename === osName) {
                return displayName;
            }
        }
        return osName;
    }

    // 加载数据
    const loadHostInfo = async () => {
        if (!hostName) return
        try {
            const result = await api.getOSImages(hostName)
            if (result.code === 200) {
                const config = result.data as unknown as HostConfig
                setHostConfig(config)
            }
        } catch (error) {
            console.error(error)
        }
    }

    // 获取虚拟机截图
    const loadVMScreenshot = async () => {
        if (!hostName || !uuid || !vm) return
        
        const vmType = vm.config?.virt_type || '';
        if (vmType === 'OCInterface' || vmType === 'LxContainer') return;
        
        if (currentStatus.ac_status === 'STARTED') {
            setLoadingScreenshot(true);
            try {
                const response = await api.getVMScreenshot(hostName, uuid);
                if (response.data && response.data.screenshot) {
                    setVmScreenshot(`data:image/png;base64,${response.data.screenshot}`);
                }
            } catch (error) {
                console.error('获取截图失败:', error);
            } finally {
                setLoadingScreenshot(false);
            }
        }
    }

    const loadVMDetail = async (isPolling = false) => {
        if (!hostName || !uuid) return
        try {
            // 不显示全屏loading，只在首次加载显示
            if (!isPolling && !vm) setLoading(true)

            const [detailRes, statusRes] = await Promise.all([
                api.getVMDetail(hostName, uuid),
                api.getVMStatus(hostName, uuid)
            ])

            if (detailRes.data) {
                const vmData = detailRes.data as unknown as DockDetail
                if (statusRes.data) {
                    const statusData = Array.isArray(statusRes.data) ? statusRes.data : [statusRes.data]
                    vmData.status = statusData
                }

                // 修正IPv4显示
                if (!vmData.ipv4_address || vmData.ipv4_address === '-') {
                    if (vmData.config?.nic_all) {
                        const firstNic: any = Object.values(vmData.config.nic_all)[0]
                        if (firstNic) vmData.ipv4_address = firstNic.ip4_addr
                    }
                }

                setVM(vmData)
            }
        } catch (error) {
            if (!isPolling) message.error('加载虚拟机详情失败')
        } finally {
            if (!isPolling) setLoading(false)
        }
    }

    // 加载各种列表
    const loadNATRules = async () => {
        if (!hostName || !uuid) return
        try {
            const response = await api.getNATRules(hostName, uuid)
            if (response.data) setNatRules(Array.isArray(response.data) ? response.data as unknown as NATRule[] : [])
        } catch (error) {
            console.error(error)
        }
    }

    const loadIPAddresses = async () => {
        if (!hostName || !uuid) return
        try {
            const response = await api.getVMIPAddresses(hostName, uuid)
            if (response.data) setIpAddresses(Array.isArray(response.data) ? response.data as unknown as IPAddress[] : [])
            const userResponse = await api.getCurrentUser()
            if (userResponse.data) {
                const user = userResponse.data
                setIpQuota({
                    ip_num: user.quota_nat_ports || 0,
                    ip_used: 0,
                    user_data: user
                })
            }
        } catch (error) {
            console.error(error)
        }
    }

    const loadProxyRules = async () => {
        if (!hostName || !uuid) return
        try {
            const response = await api.getProxyConfigs(hostName, uuid)
            if (response.data) setProxyRules(Array.isArray(response.data) ? response.data as unknown as ProxyRule[] : [])
        } catch (error) {
            console.error(error)
        }
    }

    // 处理监控数据
    const processMonitorData = (statusList: any[], timeRangeMinutes: number) => {
        const data = {
            cpu: [],
            memory: [],
            disk: [],
            gpu: [],
            netUp: [],
            netDown: [],
            traffic: [],
            nat: [],
            proxy: [],
            labels: []
        } as any
        if (!statusList || statusList.length === 0) return data

        let latestTimestamp = 0
        statusList.forEach(status => {
            if (status.on_update && status.on_update > latestTimestamp) latestTimestamp = status.on_update
        })
        if (!latestTimestamp) latestTimestamp = Math.floor(Date.now() / 1000)

        const latestMinuteTimestamp = Math.floor(latestTimestamp / 60) * 60
        let sampleInterval = 1
        if (timeRangeMinutes > 60 && timeRangeMinutes <= 360) sampleInterval = 5
        else if (timeRangeMinutes > 360 && timeRangeMinutes <= 1440) sampleInterval = 10
        else if (timeRangeMinutes > 1440 && timeRangeMinutes <= 4320) sampleInterval = 30
        else if (timeRangeMinutes > 4320 && timeRangeMinutes <= 10080) sampleInterval = 60
        else if (timeRangeMinutes > 10080 && timeRangeMinutes <= 21600) sampleInterval = 120
        else if (timeRangeMinutes > 21600) sampleInterval = 240

        const totalPoints = Math.ceil(timeRangeMinutes / sampleInterval)
        const dataMap = new Map()
        statusList.forEach(status => {
            if (status.on_update) {
                const minuteTimestamp = Math.floor(status.on_update / 60) * 60
                dataMap.set(minuteTimestamp, status)
            }
        })

        for (let i = 0; i < totalPoints; i++) {
            const minuteOffset = (totalPoints - 1 - i) * sampleInterval
            const minuteTimestamp = latestMinuteTimestamp - minuteOffset * 60
            const status = dataMap.get(minuteTimestamp)

            const time = new Date(minuteTimestamp * 1000)
            const hours = String(time.getHours()).padStart(2, '0')
            const minutes = String(time.getMinutes()).padStart(2, '0')
            data.labels.push(`${hours}:${minutes}`)

            if (status) {
                data.cpu.push(status.cpu_usage || 0)
                data.memory.push(Number((status.mem_total > 0 ? (status.mem_usage / status.mem_total * 100) : 0).toFixed(2)))
                data.disk.push(Number((status.hdd_total > 0 ? (status.hdd_usage / status.hdd_total * 100) : 0).toFixed(2)))
                data.gpu.push(status.gpu_total || 0)
                data.netUp.push(status.network_u || 0)
                data.netDown.push(status.network_d || 0)
                data.traffic.push(status.flu_usage || 0)
                data.nat.push(status.nat_usage || 0)
                data.proxy.push(status.web_usage || 0)
            } else {
                data.cpu.push(0);
                data.memory.push(0);
                data.disk.push(0);
                data.gpu.push(0);
                data.netUp.push(0);
                data.netDown.push(0)
                data.traffic.push(0);
                data.nat.push(0);
                data.proxy.push(0)
            }
        }
        return data
    }

    const loadMonitorData = async () => {
        if (!hostName || !uuid) return
        try {
            const response = await api.getVMMonitorData(hostName, uuid, timeRange)
            if (response.data && Array.isArray(response.data)) {
                setMonitorData(processMonitorData(response.data, timeRange))
            }
        } catch (error) {
            console.error(error)
        }
    }

    const loadHDDs = async () => {
        if (!hostName || !uuid) return
        try {
            const response = await api.getVMHDDs(hostName, uuid)
            if (response.data) {
                const data = response.data as any
                const hddList = Object.entries(data.hdd_all || {}).map(([key, value]: [string, any]) => ({
                    hdd_path: key, ...value
                }))
                setHdds(hddList)
            }
        } catch (error) {
            console.error(error)
        }
    }

    const loadISOs = async () => {
        if (!hostName || !uuid) return
        try {
            const response = await api.getVMISOs(hostName, uuid)
            if (response.data) {
                const data = response.data as any
                const isoList = Object.entries(data.iso_all || {}).map(([key, value]: [string, any]) => ({
                    iso_key: key, ...value
                }))
                setIsos(isoList)
            }
        } catch (error) {
            console.error(error)
        }
    }

    const loadBackups = async () => {
        if (!hostName || !uuid) return
        try {
            const response = await api.getVMBackups(hostName, uuid)
            if (response.data) {
                const data = response.data as any
                // 处理不同的数据结构
                if (Array.isArray(data)) {
                    // 如果直接返回数组
                    setBackups(data)
                } else if (data.config && Array.isArray(data.config.backups)) {
                    // 旧的数据结构，包含config.backups
                    setBackups(data.config.backups)
                } else if (Array.isArray(data.backups)) {
                    // 新的数据结构，直接包含backups数组
                    setBackups(data.backups)
                } else {
                    // 其他情况，使用空数组
                    setBackups([])
                }
            } else {
                setBackups([])
            }
        } catch (error) {
            console.error('加载备份失败:', error)
            setBackups([])
        }
    }

    const loadOwners = async () => {
        if (!hostName || !uuid) return
        try {
            const response = await api.getVMOwners(hostName, uuid)
            if (response.data) {
                const data = response.data as any
                // 处理不同的数据结构
                if (Array.isArray(data)) {
                    // 如果直接返回数组
                    setOwners(data)
                } else if (data.owners && Array.isArray(data.owners)) {
                    // 如果返回的是包含owners数组的对象
                    setOwners(data.owners)
                } else {
                    // 其他情况，使用空数组
                    setOwners([])
                }
            } else {
                setOwners([])
            }
        } catch (error) {
            console.error('加载用户失败:', error)
            setOwners([])
        }
    }

    useEffect(() => {
        loadHostInfo();
        loadVMDetail();
        loadMonitorData()
        const interval = setInterval(() => {
            loadVMDetail(true);
            loadMonitorData()
            loadVMScreenshot()
        }, 10000)
        return () => clearInterval(interval)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [hostName, uuid])

    // 当虚拟机状态变为运行中时，获取截图
    useEffect(() => {
        if (currentStatus.ac_status === 'STARTED') {
            loadVMScreenshot();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentStatus.ac_status])

    // 更新当前状态
    useEffect(() => {
        if (vm && vm.status && vm.status.length > 0) {
            setCurrentStatus(vm.status[vm.status.length - 1])
        }
    }, [vm])

    useEffect(() => {
        // 无论切换到哪个标签页，都预加载所有数据，确保切换时数据已准备好
        loadNATRules()
        loadIPAddresses()
        loadProxyRules()
        loadHDDs()
        loadISOs()
        loadBackups()
        loadOwners()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    useEffect(() => {
        // 标签页切换时刷新对应数据
        if (activeTab === 'nat') loadNATRules()
        else if (activeTab === 'ip') loadIPAddresses()
        else if (activeTab === 'proxy') loadProxyRules()
        else if (activeTab === 'hdd') loadHDDs()
        else if (activeTab === 'iso') loadISOs()
        else if (activeTab === 'backup') loadBackups()
        else if (activeTab === 'owners') loadOwners()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab])

    useEffect(() => {
        loadMonitorData()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [timeRange])

    useEffect(() => {
        if (natModalVisible && ipAddresses.length === 0) loadIPAddresses()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [natModalVisible])

    // 通用确认弹窗逻辑
    const showConfirmAction = (title: string, content: string, onConfirm: () => Promise<void>, requireShutdown: boolean = false) => {
        setCurrentAction({title, content, onConfirm, requireShutdown, confirmChecked: false})
        setActionConfirmModalVisible(true)
    }

    const executeAction = async () => {
        if (!currentAction) return
        setActionConfirmModalVisible(false)
        const hide = message.loading('操作执行中，请稍候...', 0)
        try {
            await currentAction.onConfirm()
            hide()
            message.success('操作成功')
            setTimeout(loadVMDetail, 1500)
        } catch (error: any) {
            hide()
            message.error(error.message || '操作失败')
        }
    }

    // 操作处理函数
    const handlePowerAction = async (action: string) => {
        if (!hostName || !uuid) return
        const actionMap: any = {
            stop: '关机',
            hard_stop: '强制关机',
            hard_reset: '强制重启',
            reset: '重启',
            start: '启动',
            pause: '暂停',
            resume: '恢复'
        }
        const requireShutdown = ['stop', 'hard_stop', 'hard_reset'].includes(action)

        showConfirmAction(
            `${actionMap[action]}确认`,
            `确定要执行${actionMap[action]}操作吗？${requireShutdown ? '此操作可能导致数据丢失！' : ''}`,
            async () => {
                message.loading(`正在执行${actionMap[action]}操作...`, 0)
                await api.vmPower(hostName, uuid, action as any)
            },
            requireShutdown
        )
    }

    const handleDelete = () => {
        showConfirmAction('确认删除', '确定要删除这个虚拟机吗？此操作不可恢复！', async () => {
            await api.deleteVM(hostName!, uuid!)
            navigate(`/hosts/${hostName}/vms`)
        }, true)
    }

    const handleOpenVNC = async () => {
        if (!hostName || !uuid) return
        try {
            const hide = message.loading('正在获取控制台地址...', 0)
            const response = await api.getVMConsole(hostName, uuid)
            hide()

            const url = response.data?.console_url || (typeof response.data === 'string' ? response.data : null)
            if (url && url.startsWith('http')) {
                window.open(url, '_blank')
            } else {
                message.error('获取的控制台地址无效')
            }
        } catch (error) {
            message.error('打开控制台失败')
        }
    }

    const handleCopyPassword = (password: string, type: string) => {
        navigator.clipboard.writeText(password);
        message.success(`${type}密码已复制`)
    }

    const handleChangePassword = async (_values: any) => {
        showConfirmAction('修改密码确认', '确定要修改密码吗？虚拟机需要重启才能生效。', async () => {
            await api.changeVMPassword(hostName!, uuid!, {password: _values.new_password})
            setPasswordModalVisible(false)
        }, true)
    }

    const handleAddIPAddress = async (_values: any) => {
        const hide = message.loading('正在添加网卡...', 0)
        try {
            await api.addIPAddress(hostName!, uuid!, _values)
            hide()
            message.success('网卡添加成功')
            setIpModalVisible(false);
            ipForm.resetFields();
            loadIPAddresses()
        } catch (error) {
            hide()
            message.error('添加失败')
        }
    }

    const handleDeleteIPAddress = async (nicName: string) => {
        showConfirmAction('删除IP确认', '确定要删除这个IP地址吗？', async () => {
            await api.deleteIPAddress(hostName!, uuid!, nicName)
            loadIPAddresses()
        }, true)
    }

    const handleAddProxy = async (_values: any) => {
        try {
            await api.addProxyConfig(hostName!, uuid!, _values)
            message.success('反向代理添加成功')
            setProxyModalVisible(false);
            proxyForm.resetFields();
            loadProxyRules()
        } catch (error) {
            message.error('添加失败')
        }
    }

    const handleDeleteProxy = async (proxyId: number) => {
        showConfirmAction('删除代理确认', '确定要删除这个反向代理吗？', async () => {
            await api.deleteProxyConfig(hostName!, uuid!, proxyId)
            loadProxyRules()
        }, true)
    }

    const handleAddNATRule = async (_values: any) => {
        try {
            await api.addNATRule(hostName!, uuid!, _values)
            message.success('NAT规则添加成功')
            setNatModalVisible(false);
            form.resetFields();
            loadNATRules()
        } catch (error) {
            message.error('添加失败')
        }
    }

    const handleDeleteNAT = async (id: number) => {
        showConfirmAction('删除NAT规则', '确定要删除该规则吗？', async () => {
            await api.deleteNATRule(hostName!, uuid!, id)
            loadNATRules()
        }, true)
    }

    const handleAddHDD = async (_values: any) => {
        const regex = /^[a-zA-Z0-9_]+$/
        if (!regex.test(_values.hdd_name)) {
            message.error('磁盘名称只能包含数字、字母和下划线');
            return
        }
        setHddActionLoading(true)
        try {
            await api.addHDD(hostName!, uuid!, {
                hdd_size: _values.hdd_size * 1024,
                hdd_name: _values.hdd_name,
                hdd_type: _values.hdd_type
            })
            message.success('数据盘添加成功')
            setHddModalVisible(false);
            hddForm.resetFields();
            loadHDDs()
        } catch (error) {
            message.error('添加失败')
        } finally {
            setHddActionLoading(false)
        }
    }

    const handleMountHDD = async () => {
        if (!currentMountHdd) return
        setHddActionLoading(true)
        try {
            await api.post(`/api/client/hdd/mount/${hostName}/${uuid}`, {
                hdd_name: currentMountHdd.hdd_path,
                hdd_size: currentMountHdd.hdd_num,
                hdd_type: currentMountHdd.hdd_type
            })
            message.success('数据盘挂载成功')
            setMountHddModalVisible(false);
            loadHDDs()
        } catch (error) {
            message.error('挂载失败')
        } finally {
            setHddActionLoading(false)
        }
    }

    const handleUnmountHDD = async () => {
        if (!currentUnmountHdd) return
        setHddActionLoading(true)
        try {
            await api.post(`/api/client/hdd/unmount/${hostName}/${uuid}`, {hdd_name: currentUnmountHdd.hdd_path})
            message.success('数据盘卸载成功')
            setUnmountHddModalVisible(false);
            loadHDDs()
        } catch (error) {
            message.error('卸载失败')
        } finally {
            setHddActionLoading(false)
        }
    }

    const handleDeleteHDD = async (hddPath: string) => {
        showConfirmAction('删除数据盘确认', `确定要删除数据盘 "${hddPath}" 吗？此操作不可恢复！`, async () => {
            await api.delete(`/api/client/hdd/delete/${hostName}/${uuid}`, {data: {hdd_name: hddPath}})
            loadHDDs()
        }, true)
    }

    const handleOpenTransferHDD = (hdd: HDDInfo) => {
        setCurrentTransferHdd(hdd);
        setTransferTargetUuid('');
        setTransferHddConfirmChecked(false);
        setTransferHddModalVisible(true)
    }

    const handleTransferHDD = async () => {
        if (!currentTransferHdd) return
        setHddActionLoading(true)
        try {
            await api.post(`/api/client/hdd/transfer/${hostName}/${uuid}`, {
                hdd_name: currentTransferHdd.hdd_path,
                target_vm: transferTargetUuid
            })
            message.success('数据盘移交指令已发送')
            setTransferHddModalVisible(false);
            loadHDDs()
        } catch (error) {
            message.error('数据盘移交失败')
        } finally {
            setHddActionLoading(false)
        }
    }

    const handleAddISO = async (_values: any) => {
        setIsoActionLoading(true)
        try {
            await api.addISO(hostName!, uuid!, {
                iso_name: _values.iso_name,
                iso_file: _values.iso_file,
                iso_hint: _values.iso_hint
            })
            message.success('ISO挂载成功')
            setIsoModalVisible(false);
            isoForm.resetFields();
            loadISOs()
        } catch (error) {
            message.error('挂载失败')
        } finally {
            setIsoActionLoading(false)
        }
    }

    const handleDeleteISO = (isoName: string) => {
        setCurrentUnmountIso(isoName);
        setUnmountIsoConfirmChecked(false);
        setUnmountIsoConfirmVisible(true)
    }

    const executeUnmountISO = async () => {
        if (!currentUnmountIso) return
        setIsoActionLoading(true)
        try {
            await api.deleteISO(hostName!, uuid!, currentUnmountIso)
            message.success('ISO卸载成功')
            setUnmountIsoConfirmVisible(false);
            loadISOs()
        } catch (error) {
            message.error('卸载失败')
        } finally {
            setIsoActionLoading(false)
        }
    }

    const handleCreateBackup = async (_values: any) => {
        setBackupActionLoading(true)
        try {
            await api.createVMBackup(hostName!, uuid!, {vm_tips: _values.backup_name})
            message.success('备份创建指令已发送')
            setBackupModalVisible(false);
            backupForm.resetFields();
            loadBackups()
        } catch (error) {
            message.error('创建失败')
        } finally {
            setBackupActionLoading(false)
        }
    }

    const handleRestoreBackup = (backupName: string) => {
        setCurrentRestoreBackup(backupName);
        setRestoreConfirmChecked1(false);
        setRestoreConfirmChecked2(false);
        setRestoreBackupModalVisible(true)
    }

    const executeRestoreBackup = async () => {
        if (!currentRestoreBackup) return
        setBackupActionLoading(true)
        try {
            await api.restoreVMBackup(hostName!, uuid!, currentRestoreBackup)
            message.success('恢复指令已发送')
            setRestoreBackupModalVisible(false);
            setTimeout(() => window.location.reload(), 3000)
        } catch (error) {
            message.error('恢复失败')
        } finally {
            setBackupActionLoading(false)
        }
    }

    const handleDeleteBackup = async (backupName: string) => {
        showConfirmAction('删除备份确认', '确定要删除这个备份吗？此操作不可恢复！', async () => {
            await api.deleteVMBackup(hostName!, uuid!, backupName)
            loadBackups()
        }, true)
    }

    const handleAddOwner = async (_values: any) => {
        setOwnerActionLoading(true)
        try {
            await api.addVMOwner(hostName!, uuid!, {username: _values.username})
            message.success('用户添加成功')
            setOwnerModalVisible(false);
            ownerForm.resetFields();
            loadOwners()
        } catch (error) {
            message.error('添加失败')
        } finally {
            setOwnerActionLoading(false)
        }
    }

    const handleDeleteOwner = async (username: string) => {
        showConfirmAction('删除用户确认', `确定要移除用户 "${username}" 吗？`, async () => {
            await api.deleteVMOwner(hostName!, uuid!, username)
            loadOwners()
        }, false)
    }

    const handleTransferOwnership = async () => {
        if (!transferOwnerUsername) return
        setOwnerActionLoading(true)
        try {
            await api.post(`/api/client/owners/${hostName}/${uuid}/transfer`, {
                new_owner: transferOwnerUsername,
                keep_access: keepAccessChecked,
                confirm_transfer: transferOwnerConfirmChecked
            })
            message.success('所有权移交成功')
            setTransferOwnershipModalVisible(false);
            setTimeout(() => window.location.reload(), 1500)
        } catch (error) {
            message.error('移交失败')
        } finally {
            setOwnerActionLoading(false)
        }
    }

    const handleReinstall = async (values: any) => {
        setReinstallActionLoading(true)
        try {
            await api.reinstallVM(hostName!, uuid!, values)
            message.success('系统重装指令已发送')
            setReinstallModalVisible(false);
            reinstallForm.resetFields()
        } catch (error) {
            message.error('重装失败')
        } finally {
            setReinstallActionLoading(false)
        }
    }

    const handleUpdateVM = async (values: any) => {
        if (values.os_pass && !/^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/.test(values.os_pass)) {
            message.error('系统密码必须至少8位，且包含字母和数字');
            return
        }
        if (values.vc_pass && !/^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/.test(values.vc_pass)) {
            message.error('VNC密码必须至少8位，且包含字母和数字');
            return
        }
        setPendingEditValues(values);
        setSaveConfirmChecked(false);
        setSaveConfirmModalVisible(true)
    }

    const handleConfirmUpdateVM = async () => {
        if (!pendingEditValues) return
        const hide = message.loading('保存中...', 0)
        try {
            const nicAll: any = {}
            editNicList.forEach(nic => {
                if (nic.name) nicAll[nic.name] = {nic_type: nic.type, ip4_addr: nic.ip, ip6_addr: nic.ip6}
            })
            const updateData = {
                ...pendingEditValues,
                speed_u: pendingEditValues.speed_up,
                speed_d: pendingEditValues.speed_down,
                nic_all: nicAll
            }
            delete updateData.speed_up;
            delete updateData.speed_down
            await api.updateVM(hostName!, uuid!, updateData)
            hide()
            message.success('配置更新成功');
            setSaveConfirmModalVisible(false);
            setEditModalVisible(false);
            setPendingEditValues(null);
            setTimeout(() => window.location.reload(), 1500)
        } catch (error) {
            hide();
            message.error('配置更新失败')
        }
    }

    const addEditNic = () => {
        const newId = editNicList.length > 0 ? Math.max(...editNicList.map(n => n.id)) + 1 : 0
        setEditNicList([...editNicList, {id: newId, name: `ethernet${newId}`, type: 'nat', ip: '', ip6: ''}])
    }
    const removeEditNic = (id: number) => setEditNicList(editNicList.filter(n => n.id !== id))
    const updateEditNic = (id: number, field: string, value: any) => setEditNicList(editNicList.map(n => n.id === id ? {
        ...n,
        [field]: value
    } : n))

    const getStatusText = (status: string) => ({
        running: '运行中', started: '运行中',
        stopped: '已停止',
        paused: '已暂停', suspend: '已暂停',
        starting: '启动中',
        stopping: '关机中',
        restarting: '重启中',
        resuming: '恢复中',
        pausing: '暂停中',
        error: '错误',
        unknown: '未知'
    }[status.toLowerCase()] || status)

    const getChartOption = (title: string, data: number[], color: string, labels?: string[], unit: string = '%') => ({
        title: {text: title, left: 'center', textStyle: {fontSize: 12, fontWeight: 'normal', color: '#666'}},
        tooltip: {
            trigger: 'axis',
            formatter: (params: any[]) => `${params[0].axisValue}<br/>${params[0].marker}${params[0].seriesName}: ${params[0].value}${unit}`
        },
        grid: {left: '3%', right: '4%', bottom: '3%', top: '30px', containLabel: true},
        xAxis: {type: 'category', boundaryGap: false, data: labels},
        yAxis: {
            type: 'value',
            max: unit === '%' ? 100 : undefined,
            axisLabel: {formatter: `{value}${unit}`, fontSize: 10}
        },
        series: [{
            name: title,
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: data,
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 0,
                    y2: 1,
                    colorStops: [{offset: 0, color: color + '80'}, {offset: 1, color: color + '10'}]
                }
            },
            lineStyle: {color: color, width: 2},
            itemStyle: {color: color}
        }]
    })

    if (loading || !vm) return <div className="p-20 flex justify-center"><Spin size="large">
        <div style={{marginTop: 8}}>加载虚拟机详情...</div>
    </Spin></div>

    const config = vm.config || {}

    const actionMenu: MenuProps = {
        items: [
            {
                key: 'power', label: '电源操作', icon: <PoweroffOutlined/>, children: [
                    {
                        key: 'start',
                        label: '启动',
                        onClick: () => handlePowerAction('start'),
                        disabled: currentStatus.ac_status === 'STARTED'
                    },
                    {
                        key: 'stop',
                        label: '关机',
                        onClick: () => handlePowerAction('stop'),
                        disabled: currentStatus.ac_status !== 'STARTED'
                    },
                    {
                        key: 'pause',
                        label: '暂停',
                        onClick: () => handlePowerAction('pause'),
                        disabled: currentStatus.ac_status !== 'STARTED'
                    },
                    {
                        key: 'resume',
                        label: '恢复',
                        onClick: () => handlePowerAction('resume'),
                        disabled: currentStatus.ac_status !== 'SUSPEND'
                    },
                    {key: 'force_stop', label: '强制关机', onClick: () => handlePowerAction('hard_stop'), danger: true},
                    {
                        key: 'force_reset',
                        label: '强制重启',
                        onClick: () => handlePowerAction('hard_reset'),
                        danger: true
                    },
                ]
            },
            {key: 'delete', label: '删除实例', icon: <DeleteOutlined/>, danger: true, onClick: handleDelete}
        ]
    };

    const ResourceCard = ({title, icon, value, percent, color}: any) => (
        <div className="bg-gray-50 rounded-lg p-3 border border-gray-200 h-full flex flex-col justify-between">
            <div className="flex items-center gap-2 mb-[15px]">
                    {icon}
                    <span className="text-base text-gray-500">{title}</span>
                </div>
            <div>
                <div className="flex justify-between text-sm text-gray-500 mb-1">
                    <span className="font-medium text-gray-700">{value}</span>
                    <span>{percent}%</span>
                </div>
                <Progress percent={Math.min(percent, 100)} size="small" showInfo={false} strokeColor={color}/>
            </div>
        </div>
    )

    const formatMemory = (mb: number) => {
        if (mb < 1024) return mb + ' MB'
        if (mb < 1024 * 1024) return (mb / 1024).toFixed(2) + ' GB'
        return (mb / 1024 / 1024).toFixed(2) + ' TB'
    }

    const formatDisk = (mb: number) => {
        if (mb < 1024) return mb + ' MB'
        if (mb < 1024 * 1024) return (mb / 1024).toFixed(2) + ' GB'
        return (mb / 1024 / 1024).toFixed(2) + ' TB'
    }

    const getProgressBarColor = (percent: number) => {
        if (percent < 50) return '#10b981'
        if (percent < 70) return '#f59e0b'
        if (percent < 90) return '#f97316'
        return '#ef4444'
    }

    const overviewTab = (
        <Row gutter={24}>
            {/* 左侧面板：信息 + 配置 */}
            <Col span={16}>
                <div className="space-y-6">
                    {/* 机器信息区域 */}
                    <Card title="实例信息" size="small" variant="borderless" className="shadow-sm">
                        <Row gutter={24}>
                            <Col span={16}>
                                <Descriptions column={2} bordered size="small" styles={{
                                    label: {width: '100px', fontWeight: 500},
                                    content: {fontWeight: 500}
                                }}>
                                    <Descriptions.Item label="实例名称">{config.vm_uuid}</Descriptions.Item>
                                    <Descriptions.Item label="系统密码">
                                        <Space size="small">
                                            <span
                                                className="font-mono">{showPassword ? config.os_pass : '••••••••'}</span>
                                            <EyeOutlined className="cursor-pointer text-gray-400"
                                                         onClick={() => setShowPassword(!showPassword)}/>
                                            <CopyOutlined className="cursor-pointer text-gray-400"
                                                          onClick={() => handleCopyPassword(config.os_pass || '', '系统')}/>
                                        </Space>
                                    </Descriptions.Item>

                                    <Descriptions.Item label="实例状态"><Badge
                                        status={currentStatus.ac_status === 'STARTED' ? 'success' : 'error'}
                                        text={getStatusText(currentStatus.ac_status)}/></Descriptions.Item>
                                    <Descriptions.Item label="远程密码">
                                        <Space size="small">
                                            <span
                                                className="font-mono">{showVncPassword ? config.vc_pass : '••••••••'}</span>
                                            <EyeOutlined className="cursor-pointer text-gray-400"
                                                         onClick={() => setShowVncPassword(!showVncPassword)}/>
                                            <CopyOutlined className="cursor-pointer text-gray-400"
                                                          onClick={() => handleCopyPassword(config.vc_pass || '', 'VNC')}/>
                                        </Space>
                                    </Descriptions.Item>

                                    <Descriptions.Item label="主机名称">{hostName}</Descriptions.Item>
                                    <Descriptions.Item
                                        label="主机类型">{vm.config?.virt_type || 'Hyper-V'}</Descriptions.Item>
                                    <Descriptions.Item label="操作系统">
                                        <Space>
                                            {getOSIcon(config.os_name || '')}
                                            <span>{getOSDisplayName(config.os_name || '')}</span>
                                        </Space>
                                    </Descriptions.Item>
                                    <Descriptions.Item label="端口数量">{config.nat_num || 0} 个</Descriptions.Item>
                                    <Descriptions.Item
                                        label="IPv4地址">{vm.ipv4_address || '未分配'}</Descriptions.Item>
                                    <Descriptions.Item
                                        label="IPv6地址">{vm.ipv6_address || '未分配'}</Descriptions.Item>
                                    <Descriptions.Item label="上行带宽">{config.speed_u || 0} Mbps</Descriptions.Item>
                                    <Descriptions.Item label="下行带宽">{config.speed_d || 0} Mbps</Descriptions.Item>

                                    <Descriptions.Item
                                        label="所有者">{config.own_all?.[0] || 'admin'}</Descriptions.Item>
                                    <Descriptions.Item label="VNC端口">{config.vc_port || '未设置'}</Descriptions.Item>
                                </Descriptions>
                            </Col>
                            <Col span={8} className="flex flex-col justify-between">
                                <div className="bg-gray-100 rounded-lg flex items-center justify-center mb-4"
                                     style={{height: 170}}>
                                    {(() => {
                                        const vmType = vm.config?.virt_type || '';
                                        if (vmType === 'OCInterface' || vmType === 'LxContainer') {
                                            return (
                                                <div className="text-center">
                                                    <div className="text-lg text-gray-500 mb-2">容器类型虚拟机</div>
                                                    <div className="text-xs text-gray-400">截图功能不可用</div>
                                                </div>
                                            );
                                        } else if (currentStatus.ac_status === 'STARTED') {
                                            return (
                                                <div className="w-full h-full flex items-center justify-center relative">
                                                    <img 
                                                        src={vmScreenshot || ''} 
                                                        alt="虚拟机截图" 
                                                        className="max-w-full max-h-full object-contain"
                                                    />
                                                    <Spin spinning={loadingScreenshot} tip="获取截图中..." />
                                                </div>
                                            );
                                        } else {
                                            return (
                                                <div className="text-center">
                                                    <div className="text-4xl mb-2">{getOSIcon(config.os_name || '')}</div>
                                                    <div className="text-xs text-gray-400">虚拟机未运行，无法获取截图</div>
                                                </div>
                                            );
                                        }
                                    })()}
                                </div>
                                <div className="grid grid-cols-4 gap-2">
                                    <Tooltip title="启动"><Button size="small" icon={<PlayCircleOutlined/>}
                                                                  onClick={() => handlePowerAction('start')}
                                                                  disabled={currentStatus.ac_status === 'STARTED'}
                                                                  block><span className="hidden md:inline">启动</span></Button></Tooltip>
                                    <Tooltip title="关机"><Button size="small" icon={<PoweroffOutlined/>}
                                                                  onClick={() => handlePowerAction('stop')}
                                                                  disabled={currentStatus.ac_status !== 'STARTED'}
                                                                  block><span className="hidden md:inline">关机</span></Button></Tooltip>
                                    <Tooltip title="重启"><Button size="small" icon={<ReloadOutlined/>}
                                                                  onClick={() => handlePowerAction('reset')}
                                                                  block><span className="hidden md:inline">重启</span></Button></Tooltip>
                                    <Tooltip title="暂停"><Button size="small" icon={<PauseCircleOutlined/>}
                                                                  onClick={() => handlePowerAction('pause')}
                                                                  disabled={currentStatus.ac_status !== 'STARTED'}
                                                                  block><span className="hidden md:inline">暂停</span></Button></Tooltip>

                                    <Tooltip title="恢复"><Button size="small" icon={<PlayCircleOutlined/>}
                                                                  onClick={() => handlePowerAction('resume')}
                                                                  disabled={currentStatus.ac_status !== 'SUSPEND'}
                                                                  block><span className="hidden md:inline">恢复</span></Button></Tooltip>
                                    <Tooltip title="强制关机"><Button size="small" danger icon={<PoweroffOutlined/>}
                                                                      onClick={() => handlePowerAction('hard_stop')}
                                                                      block><span className="hidden md:inline">强关</span></Button></Tooltip>
                                    <Tooltip title="强制重启"><Button size="small" danger icon={<ReloadOutlined/>}
                                                                      onClick={() => handlePowerAction('hard_reset')}
                                                                      block><span className="hidden md:inline">重置</span></Button></Tooltip>
                                    <Tooltip title="编辑配置"><Button size="small" icon={<EditOutlined/>}
                                                                      onClick={() => setEditModalVisible(true)} block><span className="hidden md:inline">编辑</span></Button></Tooltip>

                                    <Tooltip title="重装系统"><Button size="small" danger icon={<CloudSyncOutlined/>}
                                                                      onClick={() => setReinstallModalVisible(true)}
                                                                      block><span className="hidden md:inline">重装</span></Button></Tooltip>
                                    <Tooltip title="删除"><Button size="small" danger icon={<DeleteOutlined/>}
                                                                  onClick={handleDelete} block><span className="hidden md:inline">删除</span></Button></Tooltip>
                                    <Tooltip title="VNC控制台"><Button size="small" type="primary"
                                                                       icon={<DesktopOutlined/>} onClick={handleOpenVNC}
                                                                       block><span className="hidden md:inline">VNC</span></Button></Tooltip>
                                    <Tooltip title="修改密码"><Button size="small" icon={<KeyOutlined/>}
                                                                      onClick={() => setPasswordModalVisible(true)}
                                                                      block><span className="hidden md:inline">改密</span></Button></Tooltip>
                                </div>
                            </Col>
                        </Row>
                    </Card>

                    {/* 实例配置区域 */}
                    <Card title="实例配置" size="small" variant="borderless" className="shadow-sm">
                        <Row gutter={[16, 16]}>
                            <Col span={8}>
                                <div className="space-y-4">
                                    <ResourceCard title="CPU" icon={<AreaChartOutlined className="text-blue-500"/>}
                                                  value={`${config.cpu_num || 0} 核`} subValue="利用率"
                                                  percent={currentStatus.cpu_usage || 0}
                                                  color={getProgressBarColor(currentStatus.cpu_usage || 0)}/>
                                    <ResourceCard title="RAM" icon={<DesktopOutlined className="text-green-500"/>}
                                                  value={`已用 ${formatMemory(currentStatus.mem_usage || 0)} / ${formatMemory(config.mem_num || 0)}`}
                                                  subValue="使用率"
                                                  percent={config.mem_num > 0 ? Math.round((currentStatus.mem_usage || 0) / config.mem_num * 100) : 0}
                                                  color={getProgressBarColor(config.mem_num > 0 ? Math.round((currentStatus.mem_usage || 0) / config.mem_num * 100) : 0)}/>
                                    <ResourceCard title="GPU" icon={<DesktopOutlined className="text-purple-500"/>}
                                                  value={`已用 ${formatMemory(currentStatus.gpu_total || 0)} / ${formatMemory(config.gpu_mem || 0)}`}
                                                  subValue="使用率"
                                                  percent={config.gpu_mem > 0 ? Math.round((currentStatus.gpu_total || 0) / config.gpu_mem * 100) : 0}
                                                  color={getProgressBarColor(config.gpu_mem > 0 ? Math.round((currentStatus.gpu_total || 0) / config.gpu_mem * 100) : 0)}/>
                                </div>
                            </Col>
                            <Col span={8}>
                                <div className="space-y-4">
                                    <ResourceCard title="硬盘" icon={<HddOutlined className="text-yellow-500"/>}
                                                  value={`已用 ${formatDisk(currentStatus.hdd_usage || 0)} / ${formatDisk(config.hdd_num || 0)}`}
                                                  subValue="使用率"
                                                  percent={config.hdd_num > 0 ? Math.round((currentStatus.hdd_usage || 0) / config.hdd_num * 100) : 0}
                                                  color={getProgressBarColor(config.hdd_num > 0 ? Math.round((currentStatus.hdd_usage || 0) / config.hdd_num * 100) : 0)}/>
                                    <ResourceCard title="流量" icon={<AreaChartOutlined className="text-red-500"/>}
                                                  value={`已用 ${formatDisk(currentStatus.flu_usage || 0)} / ${config.flu_num > 0 ? formatDisk(config.flu_num) : '∞'}`}
                                                  subValue="使用率"
                                                  percent={config.flu_num > 0 ? Math.round((currentStatus.flu_usage || 0) / config.flu_num * 100) : 0}
                                                  color={getProgressBarColor(config.flu_num > 0 ? Math.round((currentStatus.flu_usage || 0) / config.flu_num * 100) : 0)}/>
                                    <ResourceCard title="端口" icon={<GlobalOutlined className="text-indigo-500"/>}
                                                  value={`已用 ${config.nat_all ? Object.keys(config.nat_all).length : 0} / ${config.nat_num || 0} 个`}
                                                  subValue="使用率"
                                                  percent={config.nat_num > 0 ? Math.round((config.nat_all ? Object.keys(config.nat_all).length : 0) / config.nat_num * 100) : 0}
                                                  color={getProgressBarColor(config.nat_num > 0 ? Math.round((config.nat_all ? Object.keys(config.nat_all).length : 0) / config.nat_num * 100) : 0)}/>
                                </div>
                            </Col>
                            <Col span={8}>
                                <div className="space-y-4">
                                    <ResourceCard title="上行带宽" icon={<CloudSyncOutlined className="text-cyan-500"/>}
                                                  value={`已用 ${currentStatus.network_u || 0} / ${config.speed_u || 0} Mbps`}
                                                  subValue="使用率"
                                                  percent={config.speed_u > 0 ? Math.round((currentStatus.network_u || 0) / config.speed_u * 100) : 0}
                                                  color={getProgressBarColor(config.speed_u > 0 ? Math.round((currentStatus.network_u || 0) / config.speed_u * 100) : 0)}/>
                                    <ResourceCard title="下行带宽" icon={<CloudSyncOutlined className="text-cyan-600"/>}
                                                  value={`已用 ${currentStatus.network_d || 0} / ${config.speed_d || 0} Mbps`}
                                                  subValue="使用率"
                                                  percent={config.speed_d > 0 ? Math.round((currentStatus.network_d || 0) / config.speed_d * 100) : 0}
                                                  color={getProgressBarColor(config.speed_d > 0 ? Math.round((currentStatus.network_d || 0) / config.speed_d * 100) : 0)}/>
                                    <ResourceCard title="反向代理" icon={<GlobalOutlined className="text-pink-500"/>}
                                                  value={`已用 ${config.web_all ? Object.keys(config.web_all).length : 0} / ${config.web_num || 0} 个`}
                                                  subValue="使用率"
                                                  percent={config.web_num > 0 ? Math.round((config.web_all ? Object.keys(config.web_all).length : 0) / config.web_num * 100) : 0}
                                                  color={getProgressBarColor(config.web_num > 0 ? Math.round((config.web_all ? Object.keys(config.web_all).length : 0) / config.web_num * 100) : 0)}/>
                                </div>
                            </Col>
                        </Row>
                    </Card>
                </div>
            </Col>

            {/* 右侧面板：历史资源用量 */}
            <Col span={8}>
                <Card title="历史资源用量" size="small" variant="borderless" className="h-full shadow-sm"
                      extra={
                          <Radio.Group value={timeRange} onChange={e => setTimeRange(e.target.value)} size="small"
                                       optionType="button" buttonStyle="solid">
                              <Radio.Button value={30}>30分</Radio.Button>
                              <Radio.Button value={180}>3时</Radio.Button>
                              <Radio.Button value={360}>6时</Radio.Button>
                              <Radio.Button value={1440}>24时</Radio.Button>
                              <Radio.Button value={4320}>3天</Radio.Button>
                              <Radio.Button value={10080}>7天</Radio.Button>
                              <Radio.Button value={21600}>15天</Radio.Button>
                              <Radio.Button value={43200}>30天</Radio.Button>
                          </Radio.Group>
                      }
                >
                    <div className="mb-4 text-center">
                        <Radio.Group value={chartView} onChange={e => setChartView(e.target.value)} size="small">
                            <Radio.Button value="performance">性能</Radio.Button>
                            <Radio.Button value="resource">资源</Radio.Button>
                            <Radio.Button value="network">网络</Radio.Button>
                        </Radio.Group>
                    </div>

                    <div className="space-y-4 h-[calc(100%-40px)] flex flex-col">
                        {chartView === 'performance' && (
                            <>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('CPU使用率', monitorData.cpu, '#3b82f6', monitorData.labels)}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('RAM使用率', monitorData.memory, '#f59e0b', monitorData.labels)}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('GPU使用率', monitorData.gpu, '#8b5cf6', monitorData.labels, 'MB')}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                            </>
                        )}
                        {chartView === 'resource' && (
                            <>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('硬盘使用率', monitorData.disk, '#10b981', monitorData.labels)}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('流量使用率', monitorData.traffic, '#ef4444', monitorData.labels, 'GB')}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('端口使用数', monitorData.nat, '#6366f1', monitorData.labels, '个')}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                            </>
                        )}
                        {chartView === 'network' && (
                            <>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('上行带宽率', monitorData.netUp, '#06b6d4', monitorData.labels, 'Mbps')}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('下行带宽率', monitorData.netDown, '#0891b2', monitorData.labels, 'Mbps')}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                                <div className="bg-gray-50 rounded p-2 h-[33%] min-h-0 overflow-hidden">
                                    <ReactECharts
                                        option={getChartOption('反向代理数', monitorData.proxy, '#ec4899', monitorData.labels, '个')}
                                        style={{height: '100%', width: '100%', minHeight: '200px'}}/>
                                </div>
                            </>
                        )}
                    </div>
                </Card>
            </Col>
        </Row>
    );

    const tabItems = [
        {key: 'overview', label: '实例概览', children: overviewTab},
        {
            key: 'ip',
            label: '网卡管理',
            children: <Card title="IP地址管理" extra={<Button type="primary" icon={<PlusOutlined/>}
                                                              onClick={() => setIpModalVisible(true)}>添加IP地址</Button>}
                            variant="borderless"><Table rowKey={(r) => `${r.nic_name || 'nic'}-${r.ip_address || 'ip'}`}
                                                        dataSource={ipAddresses} columns={[{
                title: '网卡名称',
                dataIndex: 'nic_name'
            }, {title: 'IPv4地址', dataIndex: 'ip_address'}, {
                title: 'IPv6地址',
                dataIndex: 'ip6_address'
            }, {
                title: '操作',
                render: (_, r) => <Button danger size="small"
                                          onClick={() => handleDeleteIPAddress(r.nic_name)}>删除</Button>
            }]} pagination={false}/></Card>
        },
        {
            key: 'hdd',
            label: '数据磁盘',
            children: <Card title="数据盘管理" extra={<Button type="primary" icon={<PlusOutlined/>}
                                                              onClick={() => setHddModalVisible(true)}>添加数据盘</Button>}
                            variant="borderless"><Table rowKey={(r) => r.hdd_path || `hdd-${Math.random()}`}
                                                        dataSource={hdds} columns={[{
                title: '路径',
                dataIndex: 'hdd_path'
            }, {title: '大小(MB)', dataIndex: 'hdd_num'}, {
                title: '操作',
                render: (_, r) => <Space><Button size="small" onClick={() => {
                    setCurrentMountHdd(r);
                    setMountHddModalVisible(true)
                }}>挂载</Button><Button size="small" danger onClick={() => {
                    setCurrentUnmountHdd(r);
                    setUnmountHddModalVisible(true)
                }}>卸载</Button><Button danger size="small" onClick={() => {
                    handleOpenTransferHDD(r)
                }}>移交</Button><Button danger size="small"
                                        onClick={() => handleDeleteHDD(r.hdd_path)}>删除</Button></Space>
            }]} pagination={false}/></Card>
        },
        {
            key: 'iso',
            label: '光盘镜像',
            children: <Card title="ISO挂载" extra={<Button type="primary" icon={<PlusOutlined/>}
                                                           onClick={() => setIsoModalVisible(true)}>挂载ISO</Button>}
                            variant="borderless"><Table rowKey={(r) => r.iso_key || `iso-${Math.random()}`}
                                                        dataSource={isos} columns={[{
                title: '名称',
                dataIndex: 'iso_name'
            }, {title: '文件', dataIndex: 'iso_file'}, {
                title: '操作',
                render: (_, r) => <Button danger size="small" onClick={() => handleDeleteISO(r.iso_name!)}>卸载</Button>
            }]} pagination={false}/></Card>
        },
        {
            key: 'nat',
            label: '端口映射',
            children: <Card title="NAT端口转发规则"
                            extra={<Button type="primary" icon={<PlusOutlined/>} onClick={() => {
                                setNatModalVisible(true);
                                form.setFieldsValue({internal_ip: availableIPs[0]})
                            }}>添加规则</Button>} variant="borderless"><Table
                rowKey={(r) => r.id?.toString() || `nat-${Math.random()}`} dataSource={natRules}
                columns={[{title: '外网端口', dataIndex: 'public_port', width: 100}, {
                    title: '内网端口',
                    dataIndex: 'private_port',
                    width: 100
                }, {title: '内网地址', dataIndex: 'internal_ip', width: 140}, {
                    title: '备注',
                    dataIndex: 'description',
                    ellipsis: true
                }, {
                    title: '操作',
                    width: 80,
                    render: (_, r) => <Button danger size="small" onClick={() => handleDeleteNAT(r.id)}>删除</Button>
                }]} pagination={false}/></Card>
        },
        {
            key: 'proxy',
            label: '反向代理',
            children: <Card title="反向代理配置" extra={<Button type="primary" icon={<PlusOutlined/>} onClick={() => {
                setProxyModalVisible(true);
                proxyForm.setFieldsValue({backend_ip: availableIPs[0]})
            }}>添加代理</Button>} variant="borderless"><Table
                rowKey={(r) => r.id?.toString() || `proxy-${Math.random()}`} dataSource={proxyRules}
                columns={[{title: '域名', dataIndex: 'domain'}, {
                    title: '后端IP',
                    dataIndex: 'backend_ip'
                }, {title: '目标端口', dataIndex: 'target_port'}, {
                    title: '操作',
                    render: (_, r) => <Button danger size="small" onClick={() => handleDeleteProxy(r.id)}>删除</Button>
                }]} pagination={false}/></Card>
        },
        {
            key: 'backup',
            label: '备份管理',
            children: <Card title="备份管理" extra={<Button type="primary" icon={<PlusOutlined/>}
                                                            onClick={() => setBackupModalVisible(true)}>创建备份</Button>}
                            variant="borderless"><Table rowKey={(r) => r.backup_name || `backup-${Math.random()}`}
                                                        dataSource={backups} columns={[{
                title: '名称',
                dataIndex: 'backup_name'
            }, {title: '创建时间', dataIndex: 'created_time'}, {
                title: '操作',
                render: (_, r) => <Space><Button size="small"
                                                 onClick={() => handleRestoreBackup(r.backup_name)}>恢复</Button><Button
                    danger size="small" onClick={() => handleDeleteBackup(r.backup_name)}>删除</Button></Space>
            }]} pagination={false}/></Card>
        },
        {
            key: 'owners',
            label: '用户权限',
            children: <Card title="用户管理" extra={<Button type="primary" icon={<UsergroupAddOutlined/>}
                                                            onClick={() => setOwnerModalVisible(true)}>添加用户</Button>}
                            variant="borderless"><Table rowKey={(r) => r.username || `owner-${Math.random()}`}
                                                        dataSource={owners} columns={[{
                title: '用户名',
                dataIndex: 'username'
            }, {title: '角色', dataIndex: 'role'}, {
                title: '操作',
                render: (_, r) => <Button danger size="small"
                                          onClick={() => handleDeleteOwner(r.username)}>删除</Button>
            }]} pagination={false}/></Card>
        },
    ];

    const powerMenuProps: MenuProps = {
        items: [
            {key: 'start', label: '启动', icon: <PlayCircleOutlined/>, disabled: currentStatus.ac_status === 'STARTED'},
            {
                key: 'stop',
                label: '关机',
                icon: <PoweroffOutlined/>,
                disabled: currentStatus.ac_status !== 'STARTED',
                danger: true
            },
            {key: 'reset', label: '重启', icon: <ReloadOutlined/>, disabled: currentStatus.ac_status !== 'STARTED'},
            {key: 'hard_stop', label: '强制关机', icon: <PoweroffOutlined/>, danger: true},
            {key: 'hard_reset', label: '强制重启', icon: <ReloadOutlined/>, danger: true},
        ],
        onClick: (e) => handlePowerAction(e.key)
    }

    // 默认电源操作按钮
    const defaultPowerAction = currentStatus.ac_status === 'STARTED'
        ? {key: 'stop', label: '关机', icon: <PoweroffOutlined/>}
        : {key: 'start', label: '启动', icon: <PlayCircleOutlined/>}

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="bg-white border-b border-gray-200">
                <div className="px-6 py-2 border-b border-gray-100 bg-gray-50">
                    <Breadcrumb separator="/" items={[
                        {title: <HomeOutlined/>},
                        {title: 'VPS'},
                        {title: config.vm_uuid}
                    ]}/>
                </div>
                <div className="px-6 py-4">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-4">
                            <div
                                className="bg-gray-100 p-2 rounded text-2xl text-gray-600 flex items-center justify-center w-12 h-12">
                                {getOSIcon(config.os_name || '')}
                            </div>
                            <div>
                                <div className="flex items-center gap-3">
                                    <h1 className="text-xl font-bold text-gray-900 m-0">{config.vm_uuid}</h1>
                                    <Tag color="blue">{vm.config?.virt_type || 'Hyper-V'}</Tag>
                                    <Badge status={currentStatus.ac_status === 'STARTED' ? 'success' : 'error'}
                                           text={getStatusText(currentStatus.ac_status)}/>
                                    <span
                                        className="text-gray-500 text-sm border-l pl-3 ml-1">
                                        IPv4 : {vm.ipv4_address || '未分配'} <CopyOutlined className="cursor-pointer" onClick={() => handleCopyPassword(vm.ipv4_address || '', 'IPv4')}/>
                                        &nbsp;| IPv6 : {vm.ipv6_address || '未分配'} <CopyOutlined className="cursor-pointer" onClick={() => handleCopyPassword(vm.ipv6_address || '', 'IPv6')}/>
                                    </span>
                                </div>
                                <div className="flex gap-4 mt-2 text-sm text-gray-500">
                                    <span>主机名称: {hostName}</span>
                                    <span>主机类型: {vm.config?.virt_type || 'Hyper-V'}</span>
                                    <span>系统: {getOSDisplayName(config.os_name || '')}</span>
                                </div>
                            </div>
                        </div>
                        <Space>
                            <Button type="primary" className="bg-blue-600" onClick={handleOpenVNC}>一键远程</Button>
                            <Button onClick={() => setPasswordModalVisible(true)}>设置密码</Button>
                            <Dropdown menu={powerMenuProps}>
                                <Button icon={defaultPowerAction.icon}
                                        onClick={() => handlePowerAction(defaultPowerAction.key)}>
                                    {defaultPowerAction.label} <DownOutlined/>
                                </Button>
                            </Dropdown>

                            <Button onClick={() => setReinstallModalVisible(true)}>重装系统</Button>
                            <Button icon={<ReloadOutlined/>} onClick={() => loadVMDetail(false)}/>
                            <Dropdown menu={actionMenu}><Button icon={<MoreOutlined/>}/></Dropdown>
                        </Space>
                    </div>
                </div>
                <div className="px-6">
                    <Tabs activeKey={activeTab} onChange={setActiveTab}
                          items={tabItems.map(i => ({key: i.key, label: i.label}))} tabBarStyle={{marginBottom: 0}}/>
                </div>
            </div>
            <div className="p-6">
                {tabItems.find(i => i.key === activeTab)?.children}
            </div>

            <Modal title="编辑虚拟机配置" open={editModalVisible} onCancel={() => setEditModalVisible(false)}
                   onOk={() => editVmForm.submit()} width={700}>
                <Form form={editVmForm} onFinish={handleUpdateVM} layout="vertical">
                    <Form.Item name="vm_uuid" hidden><Input/></Form.Item>
                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item label="操作系统" name="os_name" initialValue={config.os_name}>
                                <Select>{hostConfig?.system_maps && Object.entries(hostConfig.system_maps).map(([name, val]) => {
                                    const image = Array.isArray(val) ? val[0] : val;
                                    return image ? <Select.Option key={name} value={image}>{name}</Select.Option> : null
                                })}</Select>
                            </Form.Item>
                        </Col>
                        <Col span={12}><Form.Item label="VNC端口" name="vc_port"
                                                  initialValue={config.vc_port}><InputNumber min={5900} max={65535}
                                                                                             style={{width: '100%'}}/></Form.Item></Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={12}><Form.Item label="系统密码" name="os_pass"
                                                  initialValue={config.os_pass}><Input.Password
                            placeholder="留空则不修改"/></Form.Item></Col>
                        <Col span={12}><Form.Item label="VNC密码" name="vc_pass"
                                                  initialValue={config.vc_pass}><Input.Password
                            placeholder="留空则不修改"/></Form.Item></Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={8}><Form.Item label="CPU核心" name="cpu_num"
                                                 initialValue={config.cpu_num}><InputNumber min={1} max={64}
                                                                                            style={{width: '100%'}}/></Form.Item></Col>
                        <Col span={8}><Form.Item label="内存(MB)" name="mem_num"
                                                 initialValue={config.mem_num}><InputNumber min={512} max={1048576}
                                                                                            style={{width: '100%'}}/></Form.Item></Col>
                        <Col span={8}><Form.Item label="硬盘(GB)" name="hdd_num"
                                                 initialValue={config.hdd_num}><InputNumber min={1} max={10240}
                                                                                            style={{width: '100%'}}/></Form.Item></Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={8}><Form.Item label="GPU数量" name="gpu_num"
                                                 initialValue={config.gpu_num || 0}><InputNumber min={0} max={8}
                                                                                                 style={{width: '100%'}}/></Form.Item></Col>
                        <Col span={8}><Form.Item label="上行带宽(Mbps)" name="speed_up"
                                                 initialValue={config.speed_up || 100}><InputNumber min={1} max={10000}
                                                                                                    style={{width: '100%'}}/></Form.Item></Col>
                        <Col span={8}><Form.Item label="下行带宽(Mbps)" name="speed_down"
                                                 initialValue={config.speed_down || 100}><InputNumber min={1}
                                                                                                      max={10000}
                                                                                                      style={{width: '100%'}}/></Form.Item></Col>
                    </Row>
                    <Row gutter={16}>
                        <Col span={8}><Form.Item label="NAT端口数" name="nat_num"
                                                 initialValue={config.nat_num || 0}><InputNumber min={0} max={100}
                                                                                                 style={{width: '100%'}}/></Form.Item></Col>
                        <Col span={8}><Form.Item label="Web代理数" name="web_num"
                                                 initialValue={config.web_num || 0}><InputNumber min={0} max={100}
                                                                                                 style={{width: '100%'}}/></Form.Item></Col>
                        <Col span={8}><Form.Item label="流量限制(GB)" name="flu_num" initialValue={config.flu_num || 0}><InputNumber
                            min={0} max={100000} style={{width: '100%'}}/></Form.Item></Col>
                    </Row>
                    <Divider orientation="left">
                        <div className="flex justify-between items-center w-full"><span>网卡配置</span><Button
                            type="dashed" size="small" onClick={addEditNic} icon={<PlusOutlined/>}>添加网卡</Button>
                        </div>
                    </Divider>
                    {editNicList.map((nic) => (
                        <div key={nic.id} className="mb-4 p-3 bg-gray-50 rounded border border-gray-200 relative">
                            <div className="absolute top-2 right-2"><Button type="text" danger size="small"
                                                                            icon={<DeleteOutlined/>}
                                                                            onClick={() => removeEditNic(nic.id)}/>
                            </div>
                            <Row gutter={8}>
                                <Col span={8}>
                                    <div className="mb-2"><span
                                        className="text-xs text-gray-500 block">网卡名称</span><Input value={nic.name}
                                                                                                      onChange={e => updateEditNic(nic.id, 'name', e.target.value)}
                                                                                                      size="small"/>
                                    </div>
                                </Col>
                                <Col span={8}>
                                    <div className="mb-2"><span
                                        className="text-xs text-gray-500 block">类型</span><Select value={nic.type}
                                                                                                   onChange={val => updateEditNic(nic.id, 'type', val)}
                                                                                                   size="small"
                                                                                                   style={{width: '100%'}}><Select.Option
                                        value="nat">NAT</Select.Option><Select.Option
                                        value="bridge">Bridge</Select.Option></Select></div>
                                </Col>
                                <Col span={8}>
                                    <div className="mb-2"><span
                                        className="text-xs text-gray-500 block">IPv4地址</span><Input value={nic.ip}
                                                                                                      onChange={e => updateEditNic(nic.id, 'ip', e.target.value)}
                                                                                                      placeholder="自动分配"
                                                                                                      size="small"/>
                                    </div>
                                </Col>
                                <Col span={24}>
                                    <div><span className="text-xs text-gray-500 block">IPv6地址 (可选)</span><Input
                                        value={nic.ip6} onChange={e => updateEditNic(nic.id, 'ip6', e.target.value)}
                                        placeholder="自动分配" size="small"/></div>
                                </Col>
                            </Row>
                        </div>
                    ))}
                </Form>
            </Modal>

            <Modal title="保存确认" open={saveConfirmModalVisible} onCancel={() => setSaveConfirmModalVisible(false)}
                   onOk={handleConfirmUpdateVM} okText="确认保存" okButtonProps={{disabled: !saveConfirmChecked}}
                   width={400}>
                <div className="mb-4"><p>确定要保存对虚拟机 "<strong>{uuid}</strong>" 的配置修改吗？</p></div>
                <div className="p-3 bg-gray-50 border border-gray-200 rounded flex items-center justify-center">
                    <Space><input type="checkbox" id="saveConfirmCheck" checked={saveConfirmChecked}
                                  onChange={(e) => setSaveConfirmChecked(e.target.checked)}
                                  className="w-4 h-4 text-blue-600"/><label htmlFor="saveConfirmCheck"
                                                                            className="cursor-pointer select-none text-sm text-gray-700">我已确认强制关闭虚拟机</label></Space>
                </div>
            </Modal>

            <Modal title={currentAction?.title} open={actionConfirmModalVisible}
                   onCancel={() => setActionConfirmModalVisible(false)} onOk={executeAction}
                   okButtonProps={{disabled: currentAction?.requireShutdown && !currentAction?.confirmChecked}}
                   width={400}>
                <div className="mb-4"><p>{currentAction?.content}</p></div>
                {currentAction?.requireShutdown && (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded flex items-center justify-center">
                        <Space><input type="checkbox" id="actionConfirmCheck" checked={currentAction.confirmChecked}
                                      onChange={(e) => setCurrentAction({
                                          ...currentAction,
                                          confirmChecked: e.target.checked
                                      })} className="w-4 h-4 text-blue-600"/><label htmlFor="actionConfirmCheck"
                                                                                    className="cursor-pointer select-none text-sm text-gray-700">我已确认强制关闭虚拟机</label></Space>
                    </div>
                )}
            </Modal>

            <Modal title="修改系统密码" open={passwordModalVisible} onCancel={() => setPasswordModalVisible(false)}
                   onOk={() => form.submit()}>
                <Form form={form} onFinish={handleChangePassword} layout="vertical">
                    <Form.Item label="新密码" name="new_password"
                               rules={[{required: true, message: '请输入新密码'}]}><Input.Password
                        autoComplete="new-password"/></Form.Item>
                    <Form.Item label="确认密码" name="confirm_password" dependencies={['new_password']} rules={[{
                        required: true,
                        message: '请确认密码'
                    }, ({getFieldValue}) => ({
                        validator(_, value) {
                            if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                            return Promise.reject(new Error('两次输入的密码不一致'))
                        }
                    })]}><Input.Password/></Form.Item>
                </Form>
            </Modal>

            <Modal title="添加NAT规则" open={natModalVisible} onCancel={() => setNatModalVisible(false)}
                   onOk={() => form.submit()}>
                <Form form={form} onFinish={handleAddNATRule} layout="vertical">
                    <Form.Item label="协议" name="protocol"
                               rules={[{required: true, message: '请选择协议'}]}><Select><Select.Option
                        value="tcp">TCP</Select.Option><Select.Option
                        value="udp">UDP</Select.Option></Select></Form.Item>
                    <Form.Item label="公网端口" name="public_port" initialValue={0}
                               help="留空或填0表示自动分配"><InputNumber min={0} max={65535}
                                                                         style={{width: '100%'}}/></Form.Item>
                    <Form.Item label="内网端口" name="private_port"
                               rules={[{required: true, message: '请输入内网端口'}]}><InputNumber min={1} max={65535}
                                                                                                  style={{width: '100%'}}/></Form.Item>
                    <Form.Item label="内网地址" name="internal_ip" initialValue={availableIPs[0]}><Select
                        placeholder="请选择IP地址">{availableIPs.map(ip => <Select.Option key={ip}
                                                                                          value={ip}>{ip}</Select.Option>)}</Select></Form.Item>
                    <Form.Item label="描述" name="description"><Input.TextArea rows={3}/></Form.Item>
                </Form>
            </Modal>

            <Modal title="添加IP地址" open={ipModalVisible} onCancel={() => setIpModalVisible(false)}
                   onOk={() => ipForm.submit()}>
                {ipQuota && (<div className="mb-4 p-3 bg-gray-50 rounded text-sm">
                    <div className="flex justify-between mb-1"><span>内网IP配额:</span><span
                        className="font-mono">{ipQuota.ip_used}/{ipQuota.ip_num}</span></div>
                    <div className="flex justify-between"><span>公网IP配额:</span><span
                        className="font-mono">{ipQuota.user_data?.used_pub_ips || 0}/{ipQuota.user_data?.quota_pub_ips || 0}</span>
                    </div>
                </div>)}
                <Form form={ipForm} onFinish={handleAddIPAddress} layout="vertical">
                    <Form.Item label="网卡类型" name="nic_type" initialValue="nat"><Select><Select.Option
                        value="nat">内网(NAT)</Select.Option><Select.Option
                        value="pub">公网(Public)</Select.Option></Select></Form.Item>
                    <Form.Item label="IPv4地址" name="ip4_addr"><Input placeholder="留空自动分配"/></Form.Item>
                    <Form.Item label="IPv6地址" name="ip6_addr"><Input placeholder="可选"/></Form.Item>
                    <Form.Item label="网关" name="nic_gate"><Input placeholder="可选"/></Form.Item>
                    <Form.Item label="子网掩码" name="nic_mask" initialValue="255.255.255.0"><Input/></Form.Item>
                </Form>
            </Modal>

            <Modal title="添加反向代理" open={proxyModalVisible} onCancel={() => setProxyModalVisible(false)}
                   onOk={() => proxyForm.submit()}>
                <Form form={proxyForm} onFinish={handleAddProxy} layout="vertical">
                    <Form.Item label="域名" name="domain" rules={[{required: true, message: '请输入域名'}]}
                               help="例如: www.example.com"><Input placeholder="example.com"/></Form.Item>
                    <Form.Item label="后端IP" name="backend_ip" initialValue={availableIPs[0]}
                               rules={[{required: true, message: '请选择后端IP'}]} help="选择要代理的内网IP地址"><Select
                        placeholder="请选择">{availableIPs.map(ip => <Select.Option key={ip}
                                                                                    value={ip}>{ip}</Select.Option>)}</Select></Form.Item>
                    <Form.Item label="后端端口" name="backend_port" rules={[{required: true, message: '请输入端口'}]}
                               help="后端服务运行的端口"><InputNumber min={1} max={65535}
                                                                      style={{width: '100%'}}/></Form.Item>
                    <Form.Item name="ssl_enabled" valuePropName="checked">
                        <div className="flex items-center gap-2"><input type="checkbox"/><span>启用SSL (HTTPS)</span>
                        </div>
                    </Form.Item>
                    <Form.Item label="备注" name="description"><Input.TextArea/></Form.Item>
                </Form>
            </Modal>

            <Modal title="添加数据盘" open={hddModalVisible} onCancel={() => setHddModalVisible(false)}
                   onOk={() => hddForm.submit()} confirmLoading={hddActionLoading}>
                <Form form={hddForm} onFinish={handleAddHDD} layout="vertical">
                    <Form.Item label="磁盘名称" name="hdd_name" rules={[{required: true, message: '请输入磁盘名称'}, {
                        pattern: /^[a-zA-Z0-9_]+$/,
                        message: '只能包含字母、数字和下划线'
                    }]} help="仅支持英文、数字和下划线"><Input placeholder="例如: data_disk_1"/></Form.Item>
                    <Form.Item label="容量 (GB)" name="hdd_size" initialValue={10}
                               rules={[{required: true, message: '请输入容量'}]} help="最小 1 GB"><InputNumber min={1}
                                                                                                               max={10240}
                                                                                                               style={{width: '100%'}}/></Form.Item>
                    <Form.Item label="类型" name="hdd_type" initialValue={0}><Select><Select.Option
                        value={0}>HDD</Select.Option><Select.Option value={1}>SSD</Select.Option></Select></Form.Item>
                </Form>
                <Alert message="注意：添加数据盘需要重启虚拟机才能生效。" type="warning" showIcon className="mt-4"/>
            </Modal>

            <Modal title="挂载数据盘" open={mountHddModalVisible} onCancel={() => setMountHddModalVisible(false)}
                   onOk={handleMountHDD} okText="确认挂载" okButtonProps={{disabled: !mountHddConfirmChecked}}
                   confirmLoading={hddActionLoading}>
                <p>确定要挂载数据盘 "<strong>{currentMountHdd?.hdd_path}</strong>" 吗？</p>
                <p className="text-gray-500 text-sm mt-2 mb-4">挂载后需要在系统内进行配置才能使用。</p>
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded flex items-center">
                    <Space><input type="checkbox" id="mountHddCheck" checked={mountHddConfirmChecked}
                                  onChange={(e) => setMountHddConfirmChecked(e.target.checked)}
                                  className="w-4 h-4 text-blue-600"/><label htmlFor="mountHddCheck"
                                                                            className="cursor-pointer select-none text-sm text-gray-700">我已同意强制关机此虚拟机</label></Space>
                </div>
            </Modal>

            <Modal title="卸载数据盘" open={unmountHddModalVisible} onCancel={() => setUnmountHddModalVisible(false)}
                   onOk={handleUnmountHDD} okText="确认卸载" okType="danger"
                   okButtonProps={{disabled: !unmountHddConfirmChecked}} confirmLoading={hddActionLoading}>
                <p>确定要卸载数据盘 "<strong>{currentUnmountHdd?.hdd_path}</strong>" 吗？</p>
                <p className="text-red-500 text-sm mt-2 mb-4">请确保在系统内已卸载该磁盘，否则可能导致数据丢失。</p>
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded flex items-center">
                    <Space><input type="checkbox" id="unmountHddCheck" checked={unmountHddConfirmChecked}
                                  onChange={(e) => setUnmountHddConfirmChecked(e.target.checked)}
                                  className="w-4 h-4 text-blue-600"/><label htmlFor="unmountHddCheck"
                                                                            className="cursor-pointer select-none text-sm text-gray-700">我已同意强制关机此虚拟机</label></Space>
                </div>
            </Modal>

            <Modal title="挂载ISO" open={isoModalVisible} onCancel={() => setIsoModalVisible(false)}
                   onOk={() => isoForm.submit()} okButtonProps={{disabled: !isoMountConfirmChecked}}
                   confirmLoading={isoActionLoading}>
                <Form form={isoForm} onFinish={handleAddISO} layout="vertical">
                    <Form.Item label="ISO镜像" name="iso_file" rules={[{required: true, message: '请选择镜像'}]}
                               help="从服务器可用的ISO镜像中选择"><Select
                        placeholder="请选择">{hostConfig?.images_maps && Object.entries(hostConfig.images_maps).map(([name, file]) => file ?
                        <Select.Option key={name}
                                       value={file}>{name} ({file})</Select.Option> : null)}</Select></Form.Item>
                    <Form.Item label="挂载名称" name="iso_name" rules={[{required: true, message: '请输入名称'}, {
                        pattern: /^[a-zA-Z0-9]+$/,
                        message: '只能包含英文字母和数字'
                    }]} help="仅支持英文和数字"><Input placeholder="例如: system_iso"/></Form.Item>
                    <Form.Item label="备注" name="iso_hint" help="可选，用于说明此ISO的用途"><Input
                        placeholder="例如: 系统安装盘"/></Form.Item>
                </Form>
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded flex items-center mt-4">
                    <Space><input type="checkbox" id="isoMountCheck" checked={isoMountConfirmChecked}
                                  onChange={(e) => setIsoMountConfirmChecked(e.target.checked)}
                                  className="w-4 h-4 text-purple-600"/><label htmlFor="isoMountCheck"
                                                                              className="cursor-pointer select-none text-sm text-gray-700">我已同意强制关机此虚拟机</label></Space>
                </div>
            </Modal>

            <Modal title="卸载ISO镜像" open={unmountIsoConfirmVisible}
                   onCancel={() => setUnmountIsoConfirmVisible(false)} onOk={executeUnmountISO} okText="确认卸载"
                   okType="danger" okButtonProps={{disabled: !unmountIsoConfirmChecked}}
                   confirmLoading={isoActionLoading}>
                <p>确定要卸载ISO镜像 "<strong>{currentUnmountIso}</strong>" 吗？</p>
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded flex items-center mt-4">
                    <Space><input type="checkbox" id="unmountIsoCheck" checked={unmountIsoConfirmChecked}
                                  onChange={(e) => setUnmountIsoConfirmChecked(e.target.checked)}
                                  className="w-4 h-4 text-orange-600"/><label htmlFor="unmountIsoCheck"
                                                                              className="cursor-pointer select-none text-sm text-gray-700">我已同意强制关机此虚拟机</label></Space>
                </div>
            </Modal>

            <Modal title="重装系统" open={reinstallModalVisible} onCancel={() => setReinstallModalVisible(false)}
                   onOk={() => reinstallForm.submit()} okType="danger" okText="确认重装"
                   okButtonProps={{disabled: !reinstallConfirmChecked}} confirmLoading={reinstallActionLoading}>
                <Alert message="警告：重装系统将清除所有数据！" description="此操作不可逆，请确保已备份重要数据。"
                       type="warning" showIcon style={{marginBottom: 16}}/>
                <Form form={reinstallForm} onFinish={handleReinstall} layout="vertical">
                    <Form.Item label="操作系统" name="os_name"
                               rules={[{required: true, message: '请选择操作系统'}]}><Select
                        placeholder="请选择">{hostConfig?.system_maps && Object.entries(hostConfig.system_maps).map(([name, val]) => {
                        const image = Array.isArray(val) ? val[0] : val;
                        return image ? <Select.Option key={name} value={image}>{name}</Select.Option> : null
                    })}</Select></Form.Item>
                    <Form.Item label="系统密码" name="password" rules={[{required: true, message: '请输入新系统密码'}]}><Input.Password/></Form.Item>
                </Form>
                <div className="p-3 bg-red-50 border border-red-200 rounded flex items-center mt-4">
                    <Space><input type="checkbox" id="reinstallCheck" checked={reinstallConfirmChecked}
                                  onChange={(e) => setReinstallConfirmChecked(e.target.checked)}
                                  className="w-4 h-4 text-red-600"/><label htmlFor="reinstallCheck"
                                                                           className="cursor-pointer select-none text-sm text-gray-700">我已备份数据，确认重装系统将清空系统盘数据</label></Space>
                </div>
            </Modal>

            <Modal title="创建备份" open={backupModalVisible} onCancel={() => setBackupModalVisible(false)}
                   onOk={() => backupForm.submit()} okButtonProps={{disabled: !backupCreateConfirmChecked}}
                   confirmLoading={backupActionLoading}>
                <Form form={backupForm} onFinish={handleCreateBackup} layout="vertical">
                    <Form.Item label="备份说明" name="backup_name" rules={[{required: true, message: '请输入备份说明'}]}
                               help="请输入备份的说明信息"><Input placeholder="例如: 系统更新前备份"/></Form.Item>
                </Form>
                <Alert message="备份可能需要数十分钟，取决于虚拟机硬盘大小，请耐心等待！" type="info" showIcon
                       className="mb-4 mt-2"/>
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded flex items-center">
                    <Space><input type="checkbox" id="backupCreateCheck" checked={backupCreateConfirmChecked}
                                  onChange={(e) => setBackupCreateConfirmChecked(e.target.checked)}
                                  className="w-4 h-4 text-purple-600"/><label htmlFor="backupCreateCheck"
                                                                              className="cursor-pointer select-none text-sm text-gray-700">我已确认停止当前虚拟机进行备份操作（未保存的数据将丢失）</label></Space>
                </div>
            </Modal>

            <Modal title="还原备份" open={restoreBackupModalVisible}
                   onCancel={() => setRestoreBackupModalVisible(false)} onOk={executeRestoreBackup} okText="确认还原"
                   okButtonProps={{disabled: !restoreConfirmChecked1 || !restoreConfirmChecked2}}
                   confirmLoading={backupActionLoading}>
                <p className="mb-4">为虚拟机 "<strong>{uuid}</strong>" 还原备份</p>
                <div className="mb-4 bg-blue-50 border border-blue-200 rounded p-3">
                    <p className="text-sm text-gray-700 mb-1">备份名称：<span
                        className="font-mono text-blue-700">{currentRestoreBackup}</span></p>
                </div>
                <div className="space-y-3 mb-6">
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded flex items-center">
                        <Space><input type="checkbox" id="restoreCheck1" checked={restoreConfirmChecked1}
                                      onChange={(e) => setRestoreConfirmChecked1(e.target.checked)}
                                      className="w-4 h-4 text-blue-600"/><label htmlFor="restoreCheck1"
                                                                                className="cursor-pointer select-none text-sm text-gray-700">我已确认停止当前虚拟机进行还原操作</label></Space>
                    </div>
                    <div className="p-3 bg-red-50 border border-red-200 rounded flex items-center">
                        <Space><input type="checkbox" id="restoreCheck2" checked={restoreConfirmChecked2}
                                      onChange={(e) => setRestoreConfirmChecked2(e.target.checked)}
                                      className="w-4 h-4 text-red-600"/><label htmlFor="restoreCheck2"
                                                                               className="cursor-pointer select-none text-sm text-gray-700">我已确认备份数据，将丢失系统盘数据</label></Space>
                    </div>
                </div>
            </Modal>

            <Modal title="添加用户" open={ownerModalVisible} onCancel={() => setOwnerModalVisible(false)}
                   onOk={() => ownerForm.submit()} confirmLoading={ownerActionLoading}>
                <Form form={ownerForm} onFinish={handleAddOwner} layout="vertical">
                    <Form.Item label="用户名" name="username" rules={[{required: true, message: '请输入用户名'}]}
                               help="添加后该用户将共享此虚拟机的访问权限，但不会占用该用户的资源配额"><Input
                        placeholder="请输入用户名"/></Form.Item>
                </Form>
                <div className="flex items-start space-x-2 mt-2 text-sm text-orange-600">
                    <SafetyCertificateOutlined className="mt-1"/>
                    <p>新的共享者必须拥有<strong>对应主机的访问权限</strong>才能看到该虚拟机</p>
                </div>
            </Modal>

            <Modal title="移交所有权" open={transferOwnershipModalVisible}
                   onCancel={() => setTransferOwnershipModalVisible(false)} onOk={handleTransferOwnership}
                   okText="确认移交" okButtonProps={{disabled: !transferOwnerConfirmChecked || !transferOwnerUsername}}
                   confirmLoading={ownerActionLoading}>
                <div className="mb-4"><p>移交所有权将把当前虚拟机的所有权转让给另一个用户。</p></div>
                <div className="mb-4"><label className="block mb-2 text-sm font-medium">新所有者用户名</label><Input
                    value={transferOwnerUsername} onChange={(e) => setTransferOwnerUsername(e.target.value)}
                    placeholder="请输入用户名"/>
                    <p className="text-xs text-gray-500 mt-1">移交后该用户将成为虚拟机的所有者，占用资源配额，您将不再占用此虚拟机资源配额</p>
                </div>
                <div className="mb-4"><Space direction="vertical">
                    <Checkbox checked={keepAccessChecked} onChange={(e) => setKeepAccessChecked(e.target.checked)}>保留我的访问权限
                        (作为普通协作者)</Checkbox>
                    <div className="ml-6 text-xs text-blue-600 mb-2">勾选将继续保留此虚拟机的访问权限，但不再是所有者
                    </div>
                    <Checkbox checked={transferOwnerConfirmChecked}
                              onChange={(e) => setTransferOwnerConfirmChecked(e.target.checked)}>我确认移交此虚拟机所有者权限</Checkbox>
                    <div className="ml-6 space-y-1">
                        <div
                            className="text-xs text-red-600 font-bold">此操作将立即执行且不可撤销，请谨慎确认所有者转移
                        </div>
                        <div className="text-xs text-orange-600">新的所有者必须拥有足够的可用资源配额才能完成移交</div>
                        <div className="text-xs text-orange-600">新的所有者必须拥有对应主机的访问权限才能完成移交</div>
                    </div>
                </Space></div>
            </Modal>

            <Modal title={<div style={{display: 'flex', alignItems: 'center', gap: 8, color: '#1890ff'}}>
                <CloudSyncOutlined/><span>移交数据盘</span></div>} open={transferHddModalVisible}
                   onCancel={() => setTransferHddModalVisible(false)} onOk={handleTransferHDD} okText="确认移交"
                   okButtonProps={{disabled: !transferHddConfirmChecked}} confirmLoading={hddActionLoading}>
                <div style={{marginBottom: 24}}><p>确定要移交数据盘 "<strong>{currentTransferHdd?.hdd_path}</strong>" 吗？
                </p></div>
                <div style={{marginBottom: 16}}><label style={{display: 'block', marginBottom: 8, fontWeight: 500}}>目标虚拟机UUID
                    *</label><Input placeholder="输入目标虚拟机UUID" value={transferTargetUuid}
                                    onChange={(e) => setTransferTargetUuid(e.target.value)}/>
                    <div style={{fontSize: 12, color: '#666', marginTop: 4}}>数据盘将从当前虚拟机移交到目标虚拟机</div>
                </div>
                <Alert message="目标机器不会自动挂载转移硬盘" type="info" showIcon style={{marginBottom: 16}}/>
                <div style={{padding: 12, background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 4}}>
                    <Space><input type="checkbox" id="transferConfirm" checked={transferHddConfirmChecked}
                                  onChange={(e) => setTransferHddConfirmChecked(e.target.checked)}/><label
                        htmlFor="transferConfirm"
                        style={{cursor: 'pointer', userSelect: 'none'}}>我同意关闭当前虚拟机执行操作</label></Space>
                </div>
            </Modal>
        </div>
    )
}

export default VMDetail
