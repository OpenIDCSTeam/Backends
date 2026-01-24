import { useEffect, useState } from 'react'
import { Select, Button, Modal, Card, Statistic } from 'antd'
import { 
  ReloadOutlined, 
  PlayCircleOutlined, 
  PauseCircleOutlined,
  DeleteOutlined,
  FileTextOutlined,
  AlertOutlined,
  InfoCircleOutlined,
  BugOutlined,
  EyeOutlined
} from '@ant-design/icons'
import api from '@/services/api'

/**
 * 日志数据接口
 */
interface Log {
  level: string // 日志级别
  message: string // 日志消息
  host: string // 主机名称
  timestamp: string // 时间戳
  actions: string // 操作类型
  success?: boolean // 是否成功
  results?: any // 操作结果
  execute?: string // 错误堆栈
  content?: string // 消息内容（备用字段）
}

/**
 * 主机信息接口
 */
interface HostInfo {
  [key: string]: any
}

/**
 * 日志查看页面
 */
function Logs() {
  // 状态管理
  const [logs, setLogs] = useState<Log[]>([]) // 所有日志
  const [filteredLogs, setFilteredLogs] = useState<Log[]>([]) // 过滤后的日志
  const [hosts, setHosts] = useState<string[]>([]) // 主机列表
  const [loading, setLoading] = useState(false) // 加载状态
  const [autoRefresh, setAutoRefresh] = useState(false) // 自动刷新状态
  const [filters, setFilters] = useState({
    host: '', // 主机筛选
    level: '', // 日志级别筛选
    limit: 100, // 显示条数
  })
  const [statistics, setStatistics] = useState({
    ERROR: 0,
    WARNING: 0,
    INFO: 0,
    DEBUG: 0,
  })

  /**
   * 加载主机列表
   */
  const loadHosts = async () => {
    try {
      const result = await api.getServerDetail()
      if (result && result.code === 200) {
        const hostNames = Object.keys(result.data || {})
        setHosts(hostNames)
      }
    } catch (error) {
      console.error('加载主机列表失败:', error)
    }
  }

  /**
   * 加载日志列表
   */
  const loadLogs = async () => {
    try {
      setLoading(true)
      const params: any = {
        limit: filters.limit,
      }
      if (filters.host) {
        params.hs_name = filters.host
      }
      
      const result = await api.getLoggerDetail(params)
      if (result && result.code === 200) {
        const logData = result.data || []
        setLogs(logData)
        filterLogs(logData, filters.level)
        updateStatistics(logData)
      }
    } catch (error) {
      console.error('加载日志失败:', error)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 过滤日志
   */
  const filterLogs = (logData: Log[], level: string) => {
    if (!level) {
      setFilteredLogs(logData)
    } else {
      setFilteredLogs(logData.filter(log => log.level === level))
    }
  }

  /**
   * 更新统计信息
   */
  const updateStatistics = (logData: Log[]) => {
    const stats = {
      ERROR: 0,
      WARNING: 0,
      INFO: 0,
      DEBUG: 0,
    }

    logData.forEach(log => {
      const level = (log.level || 'INFO').toUpperCase()
      if (level in stats) {
        stats[level as keyof typeof stats]++
      }
    })

    setStatistics(stats)
  }

  /**
   * 切换自动刷新
   */
  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh)
  }

  /**
   * 清空显示
   */
  const clearLogs = () => {
    setLogs([])
    setFilteredLogs([])
    setStatistics({
      ERROR: 0,
      WARNING: 0,
      INFO: 0,
      DEBUG: 0,
    })
  }

  /**
   * 显示操作详情
   */
  const showResults = (log: Log) => {
    Modal.info({
      title: '操作详情',
      width: 800,
      content: (
        <pre className="text-sm text-gray-700 bg-gray-50 p-3 rounded border border-gray-200 whitespace-pre-wrap max-h-96 overflow-y-auto">
          {JSON.stringify(log.results, null, 2)}
        </pre>
      ),
    })
  }

  /**
   * 显示错误堆栈
   */
  const showExecute = (log: Log) => {
    Modal.error({
      title: '错误堆栈',
      width: 800,
      content: (
        <pre className="text-sm text-red-700 bg-red-50 p-3 rounded border border-red-200 whitespace-pre-wrap font-mono max-h-96 overflow-y-auto">
          {log.execute}
        </pre>
      ),
    })
  }

  /**
   * 获取日志级别颜色
   */
  const getLevelColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'ERROR':
        return 'bg-red-500'
      case 'WARNING':
        return 'bg-yellow-500'
      case 'INFO':
        return 'bg-blue-500'
      case 'DEBUG':
        return 'bg-gray-500'
      default:
        return 'bg-gray-400'
    }
  }

  /**
   * 获取日志级别文本颜色
   */
  const getLevelTextColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'ERROR':
        return 'text-red-600'
      case 'WARNING':
        return 'text-yellow-600'
      case 'INFO':
        return 'text-blue-600'
      case 'DEBUG':
        return 'text-gray-600'
      default:
        return 'text-gray-600'
    }
  }

  // 初始化加载
  useEffect(() => {
    loadHosts()
    loadLogs()
  }, [])

  // 监听筛选条件变化
  useEffect(() => {
    loadLogs()
  }, [filters.host, filters.limit])

  // 监听日志级别筛选
  useEffect(() => {
    filterLogs(logs, filters.level)
  }, [filters.level])

  // 自动刷新
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    if (autoRefresh) {
      interval = setInterval(() => {
        loadLogs()
      }, 5000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh, filters])

  return (
    <div className="p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
          <FileTextOutlined className="text-blue-600" style={{ fontSize: '36px' }} />
          日志管理
        </h1>
        <p className="text-gray-600 mt-1">查看系统运行日志和事件记录</p>
      </div>

      {/* 过滤器 */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6 shadow-sm hover:shadow-md transition-shadow">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">主机筛选</label>
            <Select
              className="w-full"
              placeholder="全部主机"
              allowClear
              value={filters.host || undefined}
              onChange={(value) => setFilters({ ...filters, host: value || '' })}
            >
              {hosts.map(host => (
                <Select.Option key={host} value={host}>{host}</Select.Option>
              ))}
            </Select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">日志级别</label>
            <Select
              className="w-full"
              placeholder="全部级别"
              allowClear
              value={filters.level || undefined}
              onChange={(value) => setFilters({ ...filters, level: value || '' })}
            >
              <Select.Option value="ERROR">错误</Select.Option>
              <Select.Option value="WARNING">警告</Select.Option>
              <Select.Option value="INFO">信息</Select.Option>
              <Select.Option value="DEBUG">调试</Select.Option>
            </Select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">显示条数</label>
            <Select
              className="w-full"
              value={filters.limit}
              onChange={(value) => setFilters({ ...filters, limit: value })}
            >
              <Select.Option value={50}>50条</Select.Option>
              <Select.Option value={100}>100条</Select.Option>
              <Select.Option value={200}>200条</Select.Option>
              <Select.Option value={500}>500条</Select.Option>
            </Select>
          </div>
          <div className="flex items-end">
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={loadLogs}
              loading={loading}
              className="w-full"
            >
              刷新
            </Button>
          </div>
        </div>
      </div>

      {/* 日志列表 */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800 flex items-center gap-2">
            <FileTextOutlined className="text-blue-600" />
            日志记录
          </h2>
          <div className="flex items-center gap-2">
            <Button
              size="small"
              icon={autoRefresh ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={toggleAutoRefresh}
              className={autoRefresh ? 'bg-green-100 text-green-700 border-green-300' : ''}
            >
              {autoRefresh ? '停止刷新' : '自动刷新'}
            </Button>
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={clearLogs}
            >
              清空显示
            </Button>
          </div>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {loading && filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">
              <ReloadOutlined spin className="text-xl" />
              <span className="ml-2">加载日志中...</span>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">
              <FileTextOutlined className="text-xl" />
              <span className="ml-2">暂无日志记录</span>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredLogs.map((log, index) => {
                const level = log.level || 'INFO'
                const timestamp = log.timestamp || new Date().toISOString()
                const time = new Date(timestamp).toLocaleString('zh-CN')
                const message = log.message || log.content || '无消息内容'
                const host = log.host || '系统'
                const actions = log.actions || '未知操作'
                const success = log.success !== undefined ? (log.success ? '成功' : '失败') : '未知'
                const successColor = log.success === true ? 'text-green-600' : (log.success === false ? 'text-red-600' : 'text-gray-600')
                const hasResults = log.results && Object.keys(log.results).length > 0
                const hasExecute = log.execute && log.execute !== 'None' && log.execute.trim() !== ''

                return (
                  <div key={index} className="p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start gap-3">
                      <div className={`w-2 h-2 ${getLevelColor(level)} rounded-full mt-2 flex-shrink-0`}></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-semibold text-gray-600">{host}</span>
                            <span className={`text-xs ${getLevelTextColor(level)} font-medium uppercase`}>{level}</span>
                            <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded">{actions}</span>
                            <span className={`text-xs ${successColor} font-medium`}>{success}</span>
                            {hasResults && (
                              <Button
                                size="small"
                                type="link"
                                icon={<EyeOutlined />}
                                onClick={() => showResults(log)}
                                className="text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 px-2 py-0 h-6 border-0"
                              >
                                详情
                              </Button>
                            )}
                            {hasExecute && (
                              <Button
                                size="small"
                                type="link"
                                icon={<BugOutlined />}
                                onClick={() => showExecute(log)}
                                className="text-xs bg-orange-100 hover:bg-orange-200 text-orange-700 px-2 py-0 h-6 border-0"
                              >
                                堆栈
                              </Button>
                            )}
                          </div>
                          <span className="text-xs text-gray-500">{time}</span>
                        </div>
                        <p className="text-sm text-gray-800 break-words">{message}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* 统计信息 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
        <Card className="shadow-sm hover:shadow-md transition-shadow">
          <Statistic
            title="错误"
            value={statistics.ERROR}
            prefix={<AlertOutlined className="text-red-600" />}
            valueStyle={{ color: '#dc2626' }}
          />
        </Card>
        <Card className="shadow-sm hover:shadow-md transition-shadow">
          <Statistic
            title="警告"
            value={statistics.WARNING}
            prefix={<AlertOutlined className="text-yellow-600" />}
            valueStyle={{ color: '#ca8a04' }}
          />
        </Card>
        <Card className="shadow-sm hover:shadow-md transition-shadow">
          <Statistic
            title="信息"
            value={statistics.INFO}
            prefix={<InfoCircleOutlined className="text-blue-600" />}
            valueStyle={{ color: '#2563eb' }}
          />
        </Card>
        <Card className="shadow-sm hover:shadow-md transition-shadow">
          <Statistic
            title="调试"
            value={statistics.DEBUG}
            prefix={<BugOutlined className="text-gray-600" />}
            valueStyle={{ color: '#4b5563' }}
          />
        </Card>
      </div>
    </div>
  )
}

export default Logs
