import {useState, useEffect} from 'react'
import {Outlet, useNavigate, useLocation} from 'react-router-dom'
import {Layout, Menu, Avatar, Dropdown, Badge, Button, theme} from 'antd'
import {
    DashboardOutlined,
    CloudServerOutlined,
    UserOutlined,
    SettingOutlined,
    FileTextOutlined,
    BellOutlined,
    LogoutOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    GlobalOutlined,
    SwapOutlined,
    TranslationOutlined,
} from '@ant-design/icons'
import {useUserStore} from '@/store/userStore'
import { changeLanguage, getAvailableLanguages, getCurrentLanguage } from '@/utils/i18n'
import type {MenuProps} from 'antd'

const {Header, Sider, Content} = Layout

/**
 * 主布局组件
 * 包含侧边栏、顶部导航和内容区域
 */
function MainLayout() {
    const navigate = useNavigate()
    const location = useLocation()
    const {user, logout} = useUserStore()
    const [collapsed, setCollapsed] = useState(false) // 侧边栏折叠状态
    const [notifications, setNotifications] = useState(0) // 通知数量
    const [currentLang, setCurrentLang] = useState('zh-cn')
    const [languages, setLanguages] = useState<any[]>([])

    useEffect(() => {
        // 初始化语言状态
        setCurrentLang(getCurrentLanguage())
        setLanguages(getAvailableLanguages())

        // 监听语言变更事件
        const handleLangChange = (e: any) => {
            setCurrentLang(e.detail.language)
        }
        window.addEventListener('languageChanged', handleLangChange)
        
        // 轮询检查语言列表是否加载完成
        const interval = setInterval(() => {
            const langs = getAvailableLanguages()
            if (langs.length > 0 && languages.length === 0) {
                setLanguages(langs)
                setCurrentLang(getCurrentLanguage())
            }
        }, 1000)
        
        return () => {
            window.removeEventListener('languageChanged', handleLangChange)
            clearInterval(interval)
        }
    }, [languages.length])

    const {
        token: {colorBgContainer},
    } = theme.useToken()

    // 语言菜单项
    const languageMenuItems: MenuProps['items'] = languages.map(lang => ({
        key: lang.code,
        label: lang.native || lang.name,
        icon: lang.code === currentLang ? <SwapOutlined /> : null,
        onClick: () => changeLanguage(lang.code)
    }))

    // 用户界面菜单项
    const userMenuItems: MenuProps['items'] = [
        {
            key: '/user/dashboard',
            icon: <DashboardOutlined/>,
            label: '资源概览',
        },
        {
            key: '/user/vms',
            icon: <CloudServerOutlined/>,
            label: '容器管理',
        },
        {
            key: '/user/proxys',
            icon: <GlobalOutlined/>,
            label: '反向代理',
        },
        {
            key: '/user/nat',
            icon: <SwapOutlined/>,
            label: '端口转发',
        },
        {
            key: '/profile',
            icon: <UserOutlined/>,
            label: '个人资料',
        },
    ]

    // 系统界面菜单项（仅管理员可见）
    const adminMenuItems: MenuProps['items'] = [
        {
            key: '/dashboard',
            icon: <DashboardOutlined/>,
            label: '系统概览',
        },
        {
            key: '/hosts',
            icon: <CloudServerOutlined/>,
            label: '主机管理',
        },
        {
            key: '/vms',
            icon: <CloudServerOutlined/>,
            label: '容器管理',
        },
        {
            key: '/web-proxys',
            icon: <GlobalOutlined/>,
            label: '反向代理',
        },
        {
            key: '/nat-rules',
            icon: <SwapOutlined/>,
            label: '端口转发',
        },
        {
            key: '/users',
            icon: <UserOutlined/>,
            label: '用户管理',
        },
        {
            key: '/logs',
            icon: <FileTextOutlined/>,
            label: '日志查看',
        },
        {
            key: '/settings',
            icon: <SettingOutlined/>,
            label: '系统设置',
        },
    ]

    // 根据用户角色选择菜单
    const menuItems: MenuProps['items'] = user?.is_admin 
        ? [
            {
                key: 'user-interface',
                label: '用户界面',
                type: 'group',
                children: userMenuItems,
            },
            {
                key: 'system-interface',
                label: '系统界面',
                type: 'group',
                children: adminMenuItems,
            },
        ]
        : userMenuItems

    // 下拉菜单项
    const dropdownMenuItems: MenuProps['items'] = [
        {
            key: 'profile',
            icon: <UserOutlined/>,
            label: '个人资料',
            onClick: () => navigate('/profile'),
        },
        {
            key: 'settings',
            icon: <SettingOutlined/>,
            label: '设置',
            onClick: () => navigate('/settings'),
        },
        {
            type: 'divider',
        },
        {
            key: 'logout',
            icon: <LogoutOutlined/>,
            label: '退出登录',
            onClick: () => {
                logout()
                navigate('/login')
            },
        },
    ]

    // 菜单点击处理
    const handleMenuClick: MenuProps['onClick'] = ({key}) => {
        navigate(key)
    }

    return (
        <Layout style={{minHeight: '100vh'}}>
            {/* 侧边栏 */}
            <Sider trigger={null} collapsible collapsed={collapsed}>
                {/* Logo区域 */}
                <div
                    style={{
                        height: 64,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        fontSize: collapsed ? 16 : 20,
                        fontWeight: 'bold',
                    }}
                >
                    {collapsed ? 'OI' : 'OpenIDCS'}
                </div>

                {/* 菜单 */}
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    items={menuItems}
                    onClick={handleMenuClick}
                />
            </Sider>

            <Layout>
                {/* 顶部导航 */}
                <Header
                    style={{
                        padding: '0 16px',
                        background: colorBgContainer,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                    }}
                >
                    {/* 折叠按钮 */}
                    <Button
                        type="text"
                        icon={collapsed ? <MenuUnfoldOutlined/> : <MenuFoldOutlined/>}
                        onClick={() => setCollapsed(!collapsed)}
                        style={{fontSize: 16, width: 64, height: 64}}
                    />

                    {/* 右侧操作区 */}
                    <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
                        {/* 语言切换 */}
                        <Dropdown menu={{items: languageMenuItems}} placement="bottomRight">
                            <Button 
                                type="text" 
                                icon={<TranslationOutlined style={{fontSize: 18}} />}
                            />
                        </Dropdown>

                        {/* 通知 */}
                        <Badge count={notifications}>
                            <Button
                                type="text"
                                icon={<BellOutlined style={{fontSize: 18}}/>}
                                onClick={() => setNotifications(0)}
                            />
                        </Badge>

                        {/* 用户信息 */}
                        <Dropdown menu={{items: dropdownMenuItems}} placement="bottomRight">
                            <div style={{display: 'flex', alignItems: 'center', cursor: 'pointer'}}>
                                <Avatar icon={<UserOutlined/>}/>
                                <span style={{marginLeft: 8}}>{user?.username || '用户'}</span>
                            </div>
                        </Dropdown>
                    </div>
                </Header>

                {/* 内容区域 */}
                <Content
                    style={{
                        margin: '16px',
                        padding: 24,
                        minHeight: 280,
                        background: colorBgContainer,
                        borderRadius: 8,
                        overflow: 'auto',
                    }}
                >
                    <Outlet/>
                </Content>
            </Layout>
        </Layout>
    )
}

export default MainLayout
