<?php

use app\common\logic\RunMap;
use app\common\model\HostModel;
use think\Db;

define('IDCSERVER_DEBUG', true);

// 调试日志输出函数
function idcserver_debug($message, $data = null) {
    if (!IDCSERVER_DEBUG) return;
    $log = '[LXD-DEBUG] ' . $message;
    if ($data !== null) {
        $log .= ' | Data: ' . json_encode($data, JSON_UNESCAPED_UNICODE);
    }
    error_log($log);
}

// 插件元数据信息
function idcserver_MetaData()
{
    return [
        'DisplayName' => '魔方财务-OpenIDCS对接模块',
        'APIVersion'  => '0.0.1',
        'HelpDoc'     => 'https://github.com/OpenIDCSTeam/OpenIDCS-Client',
    ];
}

// 产品配置选项定义
function idcserver_ConfigOptions()
{
    return [
        'cpus' => [
            'type'        => 'text',
            'name'        => 'CPU核心数',
            'description' => 'CPU核心数量',
            'default'     => '1',
            'key'         => 'cpus',
        ],
        'memory' => [
            'type'        => 'text',
            'name'        => '内存',
            'description' => '内存大小[单位：MB GB]',
            'default'     => '1024MB',
            'key'         => 'memory',
        ],
        'disk' => [
            'type'        => 'text',
            'name'        => '硬盘',
            'description' => '硬盘大小[单位：MB GB]',
            'default'     => '512MB',
            'key'         => 'disk',
        ],
        'image' => [
            'type'        => 'text',
            'name'        => '镜像',
            'description' => '系统镜像',
            'default'     => 'debian12',
            'key'         => 'image',
        ],
        'traffic_limit' => [
            'type'        => 'text',
            'name'        => '月流量限制',
            'description' => '单位：GB',
            'default'     => '100',
            'key'         => 'traffic_limit',
        ],
        'ingress' => [
            'type'        => 'text',
            'name'        => '入站带宽',
            'description' => '下载速度限制[单位：Mbit Gbit]',
            'default'     => '100Mbit',
            'key'         => 'ingress',
        ],
        'egress' => [
            'type'        => 'text',
            'name'        => '出站带宽',
            'description' => '上传速度限制[单位：Mbit Gbit]',
            'default'     => '100Mbit',
            'key'         => 'egress',
        ],
        'network_mode' => [
            'type'        => 'dropdown',
            'name'        => '网络模式',
            'description' => '选择容器网络运行模式',
            'default'     => 'mode1',
            'key'         => 'network_mode',
            'options'     => [
                'mode1' => '模式1：IPv4 NAT共享',
                'mode2' => '模式2：IPv6 NAT共享',
                'mode3' => '模式3：IPv4/IPv6 NAT共享',
                'mode4' => '模式4：IPv4 NAT共享 + IPv6独立',
                'mode5' => '模式5：IPv4独立',
                'mode6' => '模式6：IPv6独立',
                'mode7' => '模式7：IPv4独立 + IPv6独立',
            ],
        ],
        'nat_limit' => [
            'type'        => 'text',
            'name'        => 'NAT规则数量',
            'description' => '端口转发规则上限',
            'default'     => '5',
            'key'         => 'nat_limit',
        ],
        'cpu_allowance' => [
            'type'        => 'text',
            'name'        => 'CPU使用率限制',
            'description' => 'CPU占用百分比[0%-100%]',
            'default'     => '50%',
            'key'         => 'cpu_allowance',
        ],
        'disk_io_limit' => [
            'type'        => 'text',
            'name'        => '磁盘IO限速',
            'description' => '读写速度限制[单位：MB]',
            'default'     => '100MB',
            'key'         => 'disk_io_limit',
        ],
        'ipv4_limit' => [
            'type'        => 'text',
            'name'        => 'IPv4绑定数量',
            'description' => 'IPv4地址数量上限',
            'default'     => '1',
            'key'         => 'ipv4_limit',
        ],
        'ipv6_limit' => [
            'type'        => 'text',
            'name'        => 'IPv6绑定数量',
            'description' => 'IPv6地址数量上限',
            'default'     => '1',
            'key'         => 'ipv6_limit',
        ],
        'proxy_enabled' => [
            'type'        => 'dropdown',
            'name'        => 'Nginx反向代理功能',
            'description' => '反向代理开关',
            'default'     => 'false',
            'key'         => 'proxy_enabled',
            'options'     => ['false' => '禁用', 'true' => '启用'],
        ],
        'proxy_limit' => [
            'type'        => 'text',
            'name'        => '反向代理域名数量',
            'description' => '域名绑定数量上限',
            'default'     => '1',
            'key'         => 'proxy_limit',
        ],
        'host_name' => [
            'type'        => 'text',
            'name'        => 'OpenIDCS主机名称',
            'description' => 'OpenIDCS服务器中的主机标识',
            'default'     => 'default',
            'key'         => 'host_name',
        ],
        'allow_nesting' => [
            'type'        => 'dropdown',
            'name'        => '嵌套虚拟化',
            'description' => '支持Docker等虚拟化',
            'default'     => 'true',
            'key'         => 'allow_nesting',
            'options'     => ['true' => '启用', 'false' => '禁用'],
        ],
    ];
}

// 测试API连接
function idcserver_TestLink($params)
{
    idcserver_debug('开始测试API连接', $params);

    $data = [
        'url'  => '/api/system/statis',
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');


    if ($res === null) {
        return [
            'status' => 200,
            'data'   => [
                'server_status' => 0,
                'msg'           => "连接失败: 无法连接到服务器"
            ]
        ];
    } elseif (isset($res['error'])) {
        return [
            'status' => 200,
            'data'   => [
                'server_status' => 0,
                'msg'           => "连接失败: " . $res['error']
            ]
        ];
    } elseif (isset($res['code']) && $res['code'] == 200) {
        return [
            'status' => 200,
            'data'   => [
                'server_status' => 1,
                'msg'           => "连接成功"
            ]
        ];
    } elseif (isset($res['lxd_version'])) {
        return [
            'status' => 200,
            'data'   => [
                'server_status' => 1,
                'msg'           => "连接成功"
            ]
        ];
    } elseif (isset($res['code'])) {
        return [
            'status' => 200,
            'data'   => [
                'server_status' => 0,
                'msg'           => "连接失败: " . ($res['msg'] ?? '服务器返回错误')
            ]
        ];
    } else {
        return [
            'status' => 200,
            'data'   => [
                'server_status' => 0,
                'msg'           => "连接失败: 响应格式异常"
            ]
        ];
    }
}

// 客户区页面定义
function idcserver_ClientArea($params)
{
    $pages = [
        'info'     => ['name' => '产品信息'],
    ];
    
    $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
    
    if (in_array($network_mode, ['mode1', 'mode2', 'mode3', 'mode4'])) {
        $pages['nat_acl'] = ['name' => 'NAT转发'];
    }
    
    if (in_array($network_mode, ['mode5', 'mode7'])) {
        $pages['ipv4_acl'] = ['name' => 'IPv4绑定'];
    }
    
    if (in_array($network_mode, ['mode4', 'mode6', 'mode7'])) {
        $pages['ipv6_acl'] = ['name' => 'IPv6绑定'];
    }
    
    $proxy_enabled = ($params['configoptions']['proxy_enabled'] ?? 'false') === 'true';
    if ($proxy_enabled) {
        $pages['proxy_acl'] = ['name' => '反向代理'];
    }
    
    return $pages;
}

// 客户区输出处理
function idcserver_ClientAreaOutput($params, $key)
{
    idcserver_debug('ClientAreaOutput调用', ['key' => $key, 'action' => $_GET['action'] ?? null]);

    if (isset($_GET['action'])) {
        $action = $_GET['action'];
        idcserver_debug('处理API请求', ['action' => $action, 'domain' => $params['domain'] ?? null]);

        if (empty($params['domain'])) {
            header('Content-Type: application/json');
            echo json_encode(['code' => 400, 'msg' => '容器域名未设置']);
            exit;
        }

        if ($action === 'natcheck') {
            header('Content-Type: application/json');
            echo json_encode(idcserver_natcheck($params));
            exit;
        }

        if ($action === 'proxycheck') {
            header('Content-Type: application/json');
            echo json_encode(idcserver_proxycheck($params));
            exit;
        }

        $apiEndpoints = [
            'getinfo'    => '/api/status',
            'getstats'   => '/api/info',
            'gettraffic' => '/api/traffic',
            'getinfoall' => '/api/info',
            'natlist'    => '/api/natlist',
            'ipv4list'   => '/api/ipv4/list',
            'ipv6list'   => '/api/ipv6/list',
            'proxylist'  => '/api/proxy/list',
        ];

        $apiEndpoint = $apiEndpoints[$action] ?? '';

        if (!$apiEndpoint) {
            header('Content-Type: application/json');
            echo json_encode(['code' => 400, 'msg' => '不支持的操作: ' . $action]);
            exit;
        }

        $requestData = [
            'url'  => $apiEndpoint . '?hostname=' . $params['domain'],
            'type' => 'application/x-www-form-urlencoded',
            'data' => [],
        ];


        $res = idcserver_Curl($params, $requestData, 'GET');


        if ($res === null) {
            $res = ['code' => 500, 'msg' => '连接服务器失败'];
        } elseif (!is_array($res)) {
            $res = ['code' => 500, 'msg' => '服务器返回了无效的响应格式'];
        } else {
            $res = idcserver_TransformAPIResponse($action, $res);
        }

        header('Content-Type: application/json');
        header('Cache-Control: no-cache, no-store, must-revalidate');
        header('Pragma: no-cache');
        header('Expires: 0');
        echo json_encode($res);
        exit;
    }

    if ($key == 'info') {
        return [
            'template' => 'templates/info.html',
            'vars'     => [],
        ];
    }

    if ($key == 'nat_acl') {
        $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
        $nat_enabled = in_array($network_mode, ['mode1', 'mode2', 'mode3', 'mode4']);
        
        // 使用正确的API端点获取NAT列表
        $hs_name = $params['configoptions']['host_name'] ?? 'default';
        $vm_uuid = $params['domain'];
        
        $requestData = [
            'url'  => '/api/client/natget/' . $hs_name . '/' . $vm_uuid . '?_t=' . time(),
            'type' => 'application/x-www-form-urlencoded',
            'data' => [],
        ];
        $res = idcserver_Curl($params, $requestData, 'GET');

        $nat_limit = intval($params['configoptions']['nat_limit'] ?? 5);
        $current_count = idcserver_getNATRuleCount($params);

        return [
            'template' => 'templates/nat.html',
            'vars'     => [
                'list' => $res['data'] ?? [],
                'msg'  => $res['msg'] ?? '',
                'nat_limit' => $nat_limit,
                'current_count' => $current_count,
                'remaining_count' => max(0, $nat_limit - $current_count),
                'udp_enabled' => false, // UDP已禁用
                'nat_enabled' => $nat_enabled,
            ],
        ];
    }

    if ($key == 'ipv4_acl') {
        $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
        $ipv4_enabled = in_array($network_mode, ['mode5', 'mode7']);
        
        // 使用正确的API端点获取IPv4列表
        $hs_name = $params['configoptions']['host_name'] ?? 'default';
        $vm_uuid = $params['domain'];
        
        $requestData = [
            'url'  => '/api/client/ipaddr/detail/' . $hs_name . '/' . $vm_uuid . '?_t=' . time(),
            'type' => 'application/x-www-form-urlencoded',
            'data' => [],
        ];
        $res = idcserver_Curl($params, $requestData, 'GET');

        $ipv4_limit = intval($params['configoptions']['ipv4_limit'] ?? 1);
        $current_count = idcserver_getIPv4BindingCount($params);

        return [
            'template' => 'templates/ipv4.html',
            'vars'     => [
                'list' => $res['data'] ?? [],
                'msg'  => $res['msg'] ?? '',
                'ipv4_limit' => $ipv4_limit,
                'current_count' => $current_count,
                'remaining_count' => max(0, $ipv4_limit - $current_count),
                'container_name' => $params['domain'],
                'ipv4_enabled' => $ipv4_enabled,
                'ipv4_allow_delete' => true, // 默认允许删除
            ],
        ];
    }

    if ($key == 'ipv6_acl') {
        $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
        $ipv6_enabled = in_array($network_mode, ['mode4', 'mode6', 'mode7']);
        
        // 使用正确的API端点获取IPv6列表
        $hs_name = $params['configoptions']['host_name'] ?? 'default';
        $vm_uuid = $params['domain'];
        
        $requestData = [
            'url'  => '/api/client/ipaddr/detail/' . $hs_name . '/' . $vm_uuid . '?_t=' . time(),
            'type' => 'application/x-www-form-urlencoded',
            'data' => [],
        ];
        $res = idcserver_Curl($params, $requestData, 'GET');

        $ipv6_limit = intval($params['configoptions']['ipv6_limit'] ?? 1);
        $current_count = idcserver_getIPv6BindingCount($params);

        return [
            'template' => 'templates/ipv6.html',
            'vars'     => [
                'list' => $res['data'] ?? [],
                'msg'  => $res['msg'] ?? '',
                'ipv6_limit' => $ipv6_limit,
                'current_count' => $current_count,
                'remaining_count' => max(0, $ipv6_limit - $current_count),
                'container_name' => $params['domain'],
                'ipv6_enabled' => $ipv6_enabled,
                'ipv6_allow_delete' => true, // 默认允许删除
            ],
        ];
    }
    
    if ($key == 'proxy_acl') {
        $proxy_enabled = ($params['configoptions']['proxy_enabled'] ?? 'false') === 'true';
        
        // 使用正确的API端点获取反向代理列表
        $hs_name = $params['configoptions']['host_name'] ?? 'default';
        $vm_uuid = $params['domain'];
        
        $requestData = [
            'url'  => '/api/client/proxys/detail/' . $hs_name . '/' . $vm_uuid . '?_t=' . time(),
            'type' => 'application/x-www-form-urlencoded',
            'data' => [],
        ];
        
        $res = idcserver_Curl($params, $requestData, 'GET');
        
        $proxy_limit = intval($params['configoptions']['proxy_limit'] ?? 1);
        $current_count = is_array($res['data']) ? count($res['data']) : 0;
        
        return [
            'template' => 'templates/proxy.html',
            'vars'     => [
                'list' => $res['data'] ?? [],
                'msg'  => $res['msg'] ?? '',
                'proxy_limit' => $proxy_limit,
                'current_count' => $current_count,
                'remaining_count' => max(0, $proxy_limit - $current_count),
                'container_name' => $params['domain'],
                'proxy_enabled' => $proxy_enabled,
            ],
        ];
    }
}

function idcserver_getContainerIPs($params, $hostname) {
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $hostname;
    $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
    $server_ipv4 = $params['server_ip'];
    $server_ipv6 = $params['server_ipv6'] ?? '';
    
    $dedicatedip = '';
    $assignedips = '';
    
    // 尝试从虚拟机配置中获取IP地址（对齐Python的API端点）
    try {
        $data = [
            'url'  => '/api/client/detail/' . $hs_name . '/' . $vm_uuid,
            'type' => 'application/x-www-form-urlencoded',
            'data' => [],
        ];
        $res = idcserver_Curl($params, $data, 'GET');
        
        if (isset($res['code']) && $res['code'] == 200 && isset($res['data']['config'])) {
            $vm_config = $res['data']['config'];
            
            // 从nic_all中获取IP地址（对齐Python的NCConfig结构）
            if (isset($vm_config['nic_all']) && is_array($vm_config['nic_all'])) {
                $ipv4_addresses = [];
                $ipv6_addresses = [];
                
                foreach ($vm_config['nic_all'] as $nic_name => $nic_config) {
                    if (isset($nic_config['ip4_addr']) && !empty($nic_config['ip4_addr'])) {
                        $ipv4_addresses[] = $nic_config['ip4_addr'];
                    }
                    if (isset($nic_config['ip6_addr']) && !empty($nic_config['ip6_addr'])) {
                        $ipv6_addresses[] = $nic_config['ip6_addr'];
                    }
                }
            }
        }
    } catch (Exception $e) {
        idcserver_debug('获取虚拟机IP失败', ['error' => $e->getMessage()]);
    }
    
    switch ($network_mode) {
        case 'mode1':
            $dedicatedip = $server_ipv4;
            $assignedips = '';
            break;
        case 'mode2':
            $dedicatedip = $server_ipv6;
            $assignedips = '';
            break;
        case 'mode3':
            $dedicatedip = $server_ipv4;
            $assignedips = $server_ipv6;
            break;
        case 'mode4':
            $dedicatedip = $server_ipv4;
            $ipv6_list = idcserver_getIndependentIPv6List($params);
            $assignedips = !empty($ipv6_list) ? $ipv6_list[0] : '';
            break;
        case 'mode5':
            $ipv4_list = idcserver_getIndependentIPv4List($params);
            $dedicatedip = !empty($ipv4_list) ? $ipv4_list[0] : '';
            $assignedips = '';
            break;
        case 'mode6':
            $ipv6_list = idcserver_getIndependentIPv6List($params);
            $dedicatedip = !empty($ipv6_list) ? $ipv6_list[0] : '';
            $assignedips = '';
            break;
        case 'mode7':
            $ipv4_list = idcserver_getIndependentIPv4List($params);
            $ipv6_list = idcserver_getIndependentIPv6List($params);
            $dedicatedip = !empty($ipv4_list) ? $ipv4_list[0] : '';
            $assignedips = !empty($ipv6_list) ? $ipv6_list[0] : '';
            break;
    }
    
    return [
        'dedicatedip' => $dedicatedip,
        'assignedips' => $assignedips,
    ];
}

function idcserver_getIndependentIPv4List($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/ipaddr/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200 && isset($res['data']) && is_array($res['data'])) {
        $ipv4_addresses = [];
        foreach ($res['data'] as $item) {
            if (isset($item['public_ipv4'])) {
                $ipv4_addresses[] = $item['public_ipv4'];
            }
        }
        return $ipv4_addresses;
    }

    return [];
}

function idcserver_getIndependentIPv6List($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/ipaddr/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200 && isset($res['data']) && is_array($res['data'])) {
        $ipv6_addresses = [];
        foreach ($res['data'] as $item) {
            if (isset($item['public_ipv6'])) {
                $ipv6_addresses[] = $item['public_ipv6'];
            }
        }
        return $ipv6_addresses;
    }

    return [];
}

// 允许客户端调用的函数列表
function idcserver_AllowFunction()
{
    return [
        'client' => ['natadd', 'natdel', 'natlist', 'natcheck', 'ipv4add', 'ipv4del', 'ipv4list', 'ipv6add', 'ipv6del', 'ipv6list', 'proxyadd', 'proxydel', 'proxylist', 'proxycheck'],
    ];
}

// 创建虚拟机
function idcserver_CreateAccount($params)
{
    idcserver_debug('开始创建虚拟机', ['domain' => $params['domain']]);

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain']; // 使用domain作为虚拟机UUID

    // 生成随机端口和密码
    $vc_port = rand(10000, 59999);
    $vc_pass = $params['password'] ?? randStr(16);

    // 解析内存和硬盘配置（支持MB/GB单位）
    $memory_str = $params['configoptions']['memory'] ?? '512MB';
    $disk_str = $params['configoptions']['disk'] ?? '8192MB';
    
    $mem_num = idcserver_parseSize($memory_str);
    $hdd_num = idcserver_parseSize($disk_str);
    
    // 解析带宽配置（支持Mbit/Gbit单位）
    $ingress_str = $params['configoptions']['ingress'] ?? '100Mbit';
    $egress_str = $params['configoptions']['egress'] ?? '100Mbit';
    
    $speed_d = idcserver_parseBandwidth($ingress_str);
    $speed_u = idcserver_parseBandwidth($egress_str);
    
    // 解析流量限制（GB转MB）
    $traffic_limit_gb = (int)($params['configoptions']['traffic_limit'] ?? 100);
    $flu_num = $traffic_limit_gb * 1024;
    
    // 解析CPU使用率限制
    $cpu_allowance_str = $params['configoptions']['cpu_allowance'] ?? '50%';
    $cpu_per = (int)str_replace('%', '', $cpu_allowance_str);

    // 构建虚拟机配置（完全对齐Python的VMConfig结构）
    $vm_config = [
        'vm_uuid' => $vm_uuid,
        'os_name' => $params['configoptions']['image'] ?? 'debian12',
        'os_pass' => $vc_pass,
        'vc_port' => $vc_port,
        'vc_pass' => $vc_pass,
        // 资源配置
        'cpu_num' => (int)($params['configoptions']['cpus'] ?? 1),
        'cpu_per' => $cpu_per,
        'gpu_num' => 0,
        'gpu_mem' => 0,
        'mem_num' => $mem_num,
        'hdd_num' => $hdd_num,
        // 网络配置
        'speed_u' => $speed_u,
        'speed_d' => $speed_d,
        'flu_num' => $flu_num,
        'nat_num' => (int)($params['configoptions']['nat_limit'] ?? 100),
        'web_num' => (int)($params['configoptions']['proxy_limit'] ?? 100),
        // 附加配置（空数组/列表）
        'nic_all' => [],
        'hdd_all' => [],
        'iso_all' => [],
        'nat_all' => [],
        'web_all' => [],
        'backups' => [],
        'own_all' => ['admin'],
    ];

    // 处理网卡配置
    $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
    $nic_configs = [];

    // 根据网络模式配置网卡（对齐Python的NCConfig结构）
    switch ($network_mode) {
        case 'mode1':
        case 'mode2':
        case 'mode3':
        case 'mode4':
            // NAT模式
            $nic_configs['eth0'] = [
                'nic_type' => 'nat',
                'mac_addr' => generateRandomMac(),
                'ip4_addr' => '',
                'ip6_addr' => '',
            ];
            break;
        case 'mode5':
        case 'mode6':
        case 'mode7':
            // 独立IP模式（bridge）
            $nic_configs['eth0'] = [
                'nic_type' => 'bridge',
                'mac_addr' => generateRandomMac(),
                'ip4_addr' => '',
                'ip6_addr' => '',
            ];
            break;
    }

    $vm_config['nic_all'] = $nic_configs;

    $data = [
        'url'  => '/api/client/create/' . $hs_name,
        'type' => 'application/json',
        'data' => $vm_config,
    ];

    idcserver_debug('发送创建请求', $data);
    $res = idcserver_JSONCurl($params, $data, 'POST');
    idcserver_debug('创建响应', $res);

    if (isset($res['code']) && $res['code'] == 200) {
        sleep(2);

        // 构建IP信息
        $ipInfo = idcserver_getContainerIPs($params, $params['domain']);
        $dedicatedip = $ipInfo['dedicatedip'];
        $assignedips = $ipInfo['assignedips'];

        $update = [
            'dedicatedip'  => $dedicatedip,
            'assignedips'  => $assignedips,
            'domainstatus' => 'Active',
            'username'     => 'root',
            'password'     => $vc_pass,
        ];

        // SSH端口使用VNC端口
        $update['port'] = $vc_port;

        try {
            Db::name('host')->where('id', $params['hostid'])->update($update);
            idcserver_debug('数据库更新成功', $update);
        } catch (\Exception $e) {
             return ['status' => 'error', 'msg' => ($res['msg'] ?? '创建成功，但同步数据到面板失败: ' . $e->getMessage())];
        }

        return ['status' => 'success', 'msg' => $res['msg'] ?? '虚拟机创建成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '创建失败'];
    }
}

// 生成随机MAC地址
function generateRandomMac() {
    $mac = '';
    for ($i = 0; $i < 6; $i++) {
        $mac .= sprintf('%02x', mt_rand(0, 255));
        if ($i < 5) $mac .= ':';
    }
    return $mac;
}

// 解析大小字符串（支持MB/GB单位）
function idcserver_parseSize($size_str) {
    $size_str = trim(strtoupper($size_str));
    if (preg_match('/(\d+)\s*(MB|GB)?/', $size_str, $matches)) {
        $value = (int)$matches[1];
        $unit = $matches[2] ?? 'MB';
        if ($unit === 'GB') {
            return $value * 1024; // 转换为MB
        }
        return $value;
    }
    return (int)$size_str; // 默认当作MB
}

// 解析带宽字符串（支持Mbit/Gbit单位）
function idcserver_parseBandwidth($bandwidth_str) {
    $bandwidth_str = trim(strtoupper($bandwidth_str));
    if (preg_match('/(\d+)\s*(MBIT|GBIT)?/', $bandwidth_str, $matches)) {
        $value = (int)$matches[1];
        $unit = $matches[2] ?? 'MBIT';
        if ($unit === 'GBIT') {
            return $value * 1000; // 转换为Mbit
        }
        return $value;
    }
    return (int)$bandwidth_str; // 默认当作Mbit
}

// 同步虚拟机信息
function idcserver_Sync($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];
    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200) {
        if (class_exists('think\Db') && isset($params['hostid'])) {
            try {
                $ipInfo = idcserver_getContainerIPs($params, $params['domain']);
                
                $update_data = [
                    'dedicatedip' => $ipInfo['dedicatedip'],
                    'assignedips' => $ipInfo['assignedips'],
                ];

                // 从虚拟机配置中获取VNC端口
                if (isset($res['data']['config']['vc_port']) && !empty($res['data']['config']['vc_port'])) {
                    $update_data['port'] = $res['data']['config']['vc_port'];
                }

                Db::name('host')->where('id', $params['hostid'])->update($update_data);
            } catch (Exception $e) {
                idcserver_debug('同步数据库失败', ['error' => $e->getMessage()]);
            }
        }
        return ['status' => 'success', 'msg' => $res['msg'] ?? '同步成功'];
    }

    return ['status' => 'error', 'msg' => $res['msg'] ?? '同步失败'];
}

// 删除虚拟机
function idcserver_TerminateAccount($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/delete/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];
    $res = idcserver_Curl($params, $data, 'DELETE');

    return isset($res['code']) && $res['code'] == 200
        ? ['status' => 'success', 'msg' => $res['msg'] ?? '删除成功']
        : ['status' => 'error', 'msg' => $res['msg'] ?? '删除失败'];
}

// 启动虚拟机（对齐Python的API端点）
function idcserver_On($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/powers/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => ['action' => 'S_START'], // 对齐Python的VMPowers操作
    ];
    $res = idcserver_JSONCurl($params, $data, 'POST');

    return isset($res['code']) && $res['code'] == 200
        ? ['status' => 'success', 'msg' => $res['msg'] ?? '开机成功']
        : ['status' => 'error', 'msg' => $res['msg'] ?? '开机失败'];
}

// 关闭虚拟机（对齐Python的API端点）
function idcserver_Off($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/powers/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => ['action' => 'H_CLOSE'], // 对齐Python的VMPowers操作
    ];
    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '关机成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '关机失败'];
    }
}

// 暂停虚拟机（对齐Python的API端点）
function idcserver_SuspendAccount($params)
{
    idcserver_debug('开始暂停虚拟机', ['domain' => $params['domain']]);

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/powers/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => ['action' => 'S_PAUSE'], // 对齐Python的VMPowers操作
    ];
    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '虚拟机暂停成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '虚拟机暂停失败'];
    }
}

// 恢复虚拟机（对齐Python的API端点）
function idcserver_UnsuspendAccount($params)
{
    idcserver_debug('开始解除暂停虚拟机', ['domain' => $params['domain']]);

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/powers/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => ['action' => 'S_START'], // 恢复就是启动
    ];
    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '虚拟机恢复成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '虚拟机恢复失败'];
    }
}

// 重启虚拟机（对齐Python的API端点）
function idcserver_Reboot($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/powers/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => ['action' => 'S_RESET'], // 对齐Python的VMPowers操作
    ];
    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '重启成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '重启失败'];
    }
}

// 获取容器NAT规则数量（对齐Python的API端点）
function idcserver_getNATRuleCount($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/natget/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200 && isset($res['data']) && is_array($res['data'])) {
        $rules = $res['data'];
        
        $counted = [];
        
        foreach ($rules as $rule) {
            $external_port = $rule['external_port'] ?? $rule['dport'] ?? '';
            $internal_port = $rule['internal_port'] ?? $rule['sport'] ?? '';
            $external_port_end = $rule['external_port_end'] ?? $rule['dport_end'] ?? 0;
            $internal_port_end = $rule['internal_port_end'] ?? $rule['sport_end'] ?? 0;
            $protocol = strtolower($rule['protocol'] ?? $rule['dtype'] ?? '');
            
            $key = $external_port . '_' . $internal_port . '_' . $external_port_end . '_' . $internal_port_end;
            
            if (!isset($counted[$key])) {
                $counted[$key] = [
                    'external_port' => $external_port,
                    'external_port_end' => $external_port_end,
                    'protocols' => []
                ];
            }
            
            $counted[$key]['protocols'][] = $protocol;
        }
        
        $totalCount = 0;
        foreach ($counted as $item) {
            if ($item['external_port_end'] > 0) {
                $portCount = $item['external_port_end'] - $item['external_port'] + 1;
                $totalCount += $portCount;
            } else {
                $totalCount += 1;
            }
        }
        
        return $totalCount;
    }

    return 0;
}

// 添加NAT端口转发（对齐Python的API端点和PortData结构）
function idcserver_natadd($params)
{
    $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
    if (!in_array($network_mode, ['mode1', 'mode2', 'mode3', 'mode4'])) {
        return ['status' => 'error', 'msg' => 'NAT端口转发功能未启用，请联系管理员配置正确的网络模式。'];
    }
    
    parse_str(file_get_contents("php://input"), $post);

    $lan_port = intval($post['sport'] ?? 0); // 内网端口
    $wan_port = intval($post['dport'] ?? 0); // 外网端口
    $description = trim($post['description'] ?? '');
    $protocol = 'tcp'; // 默认仅支持TCP

    $nat_limit = intval($params['configoptions']['nat_limit'] ?? 5);
    $current_count = idcserver_getNATRuleCount($params);
    
    if ($lan_port <= 0 || $lan_port > 65535) {
        return ['status' => 'error', 'msg' => '内网端口超过范围'];
    }
    
    if ($current_count >= $nat_limit) {
        return ['status' => 'error', 'msg' => "NAT规则数量已达到限制（{$nat_limit}条），无法添加更多规则"];
    }

    // 构建PortData结构（对齐Python）
    $port_data = [
        'lan_port' => $lan_port,
        'wan_port' => $wan_port,
        'lan_addr' => '', // 由后端自动填充
        'wan_addr' => '', // 由后端自动填充
        'protocol' => $protocol,
        'port_tips' => $description,
    ];

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/natadd/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => $port_data,
    ];

    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => "NAT转发添加成功（{$protocol}）"];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? 'NAT转发添加失败'];
    }
}

// 删除NAT端口转发（对齐Python的API端点）
function idcserver_natdel($params)
{
    parse_str(file_get_contents("php://input"), $post);

    $rule_index = intval($post['rule_index'] ?? -1);
    
    if ($rule_index < 0) {
        return ['status' => 'error', 'msg' => '缺少规则索引参数'];
    }

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/natdel/' . $hs_name . '/' . $vm_uuid . '/' . $rule_index,
        'type' => 'application/x-www-form-urlencoded',
        'data' => '',
    ];

    $res = idcserver_Curl($params, $data, 'DELETE');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? 'NAT转发删除成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? 'NAT转发删除失败'];
    }
}

// 查询虚拟机运行状态（对齐Python的API端点）
function idcserver_Status($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/status/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];
    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200) {
        $result = ['status' => 'success'];

        // Python后端返回的是HWStatus列表，取第一个状态
        $status_list = $res['data'] ?? [];
        if (!empty($status_list) && is_array($status_list)) {
            $hw_status = $status_list[0];
            $vmStatus = $hw_status['vm_status'] ?? '';
            
            switch (strtoupper($vmStatus)) {
                case 'RUNNING':
                case 'STARTED':
                    $result['data']['status'] = 'on';
                    $result['data']['des'] = '运行中';
                    break;
                case 'STOPPED':
                case 'SHUTDOWN':
                    $result['data']['status'] = 'off';
                    $result['data']['des'] = '已关机';
                    break;
                case 'FROZEN':
                case 'SUSPENDED':
                case 'PAUSED':
                    $result['data']['status'] = 'suspend';
                    $result['data']['des'] = '已暂停';
                    break;
                default:
                    $result['data']['status'] = 'unknown';
                    $result['data']['des'] = '未知状态';
                    break;
            }
        } else {
            $result['data']['status'] = 'unknown';
            $result['data']['des'] = '无法获取状态';
        }

        return $result;
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '获取状态失败'];
    }
}

// 重置容器密码
function idcserver_CrackPassword($params, $new_pass)
{
    $data = [
        'url'  => '/api/password',
        'type' => 'application/json',
        'data' => [
            'hostname' => $params['domain'],
            'password' => $new_pass,
        ],
    ];
    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        try {
            Db::name('host')->where('id', $params['hostid'])->update(['password' => $new_pass]);
        } catch (\Exception $e) {
            return ['status' => 'error', 'msg' => ($res['msg'] ?? $res['message'] ?? 'LXD容器密码重置成功，但同步新密码到面板数据库失败: ' . $e->getMessage())];
        }
        return ['status' => 'success', 'msg' => $res['msg'] ?? $res['message'] ?? '密码重置成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? $res['message'] ?? '密码重置失败'];
    }
}

// 重装容器操作系统
function idcserver_Reinstall($params)
{
    if (empty($params['configoption1'])) {
        return ['status' => 'error', 'msg' => '操作系统参数错误'];
    }

    $hs_name = $params['customfields']['host_name'] ?? '';
    $vm_uuid = $params['domain'];
    $reinstall_pass = $params['password'] ?? randStr(16);
    $os_name = $params['configoption1']; // 从产品配置中获取操作系统

    // 构建重装配置（使用VMConfig格式）
    $reinstall_config = [
        'os_name' => $os_name,
        'os_pass' => $reinstall_pass,
    ];

    $data = [
        'url'  => '/api/client/update/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => $reinstall_config,
    ];
    
    $res = idcserver_JSONCurl($params, $data, 'PUT');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? $res['message'] ?? '重装成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? $res['message'] ?? '重装失败'];
    }
}

// 发送JSON格式的cURL请求
function idcserver_JSONCurl($params, $data = [], $request = 'POST')
{
    $curl = curl_init();

    $protocol = 'https';
    $url = $protocol . '://' . $params['server_ip'] . ':' . $params['port'] . $data['url'];

    $curlOptions = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_ENCODING       => '',
        CURLOPT_MAXREDIRS      => 10,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_HTTP_VERSION   => CURL_HTTP_VERSION_1_1,
        CURLOPT_CUSTOMREQUEST  => $request,
        CURLOPT_POSTFIELDS     => json_encode($data['data']),
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . $params['accesshash'],
            'Content-Type: application/json',
        ],
    ];

    $curlOptions[CURLOPT_SSL_VERIFYPEER] = false;
    $curlOptions[CURLOPT_SSL_VERIFYHOST] = false;
    $curlOptions[CURLOPT_SSLVERSION] = CURL_SSLVERSION_TLSv1_2;

    curl_setopt_array($curl, $curlOptions);

    $response = curl_exec($curl);
    $errno    = curl_errno($curl);

    curl_close($curl);

    if ($errno) {
        return null;
    }

    return json_decode($response, true);
}

// 发送通用的cURL请求
function idcserver_Curl($params, $data = [], $request = 'POST')
{
    $curl = curl_init();

    $protocol = 'https';
    $url = $protocol . '://' . $params['server_ip'] . ':' . $params['port'] . $data['url'];

    idcserver_debug('发送请求', [
        'url' => $url,
        'method' => $request
    ]);

    $postFields = ($request === 'POST' || $request === 'PUT') ? ($data['data'] ?? null) : null;
    if ($request === 'GET' && !empty($data['data']) && is_array($data['data'])) {
        $url .= (strpos($url, '?') === false ? '?' : '&') . http_build_query($data['data']);
    } elseif ($request === 'GET' && !empty($data['data']) && is_string($data['data'])) {
         $url .= (strpos($url, '?') === false ? '?' : '&') . $data['data'];
    }

    $curlOptions = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_ENCODING       => '',
        CURLOPT_MAXREDIRS      => 10,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_HTTP_VERSION   => CURL_HTTP_VERSION_1_1,
        CURLOPT_CUSTOMREQUEST  => $request,
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . $params['accesshash'],
            'Content-Type: ' . ($data['type'] ?? 'application/x-www-form-urlencoded'),
        ],
    ];

    $curlOptions[CURLOPT_SSL_VERIFYPEER] = false;
    $curlOptions[CURLOPT_SSL_VERIFYHOST] = false;
    $curlOptions[CURLOPT_SSLVERSION] = CURL_SSLVERSION_TLSv1_2;

    curl_setopt_array($curl, $curlOptions);

    if ($postFields !== null) {
        curl_setopt($curl, CURLOPT_POSTFIELDS, $postFields);
    }

    $response = curl_exec($curl);
    $errno    = curl_errno($curl);
    $httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
    $curlError = curl_error($curl);

    curl_close($curl);

    idcserver_debug('请求响应', [
        'http_code' => $httpCode,
        'response_length' => strlen($response),
        'curl_errno' => $errno,
        'curl_error' => $curlError
    ]);

    if ($errno) {
        idcserver_debug('CURL错误', [
            'errno' => $errno,
            'error' => $curlError,
            'error_desc' => curl_strerror($errno)
        ]);
        return null;
    }

    $decoded = json_decode($response, true);
    idcserver_debug('解析响应', ['code' => $decoded['code'] ?? 'NO CODE']);
    return $decoded;
}

// 转换API响应以适配前端
function idcserver_TransformAPIResponse($action, $response)
{
    if (isset($response['error'])) {
        return [
            'code' => 400,
            'msg' => $response['error']
        ];
    }

    if (!isset($response['code']) || $response['code'] != 200) {
        return $response; 
    }

    switch ($action) {
        case 'getinfo':
            return $response;

        case 'getstats':
        case 'getinfoall':
            if (isset($response['data'])) {
                $data = $response['data'];

                $transformed = [
                    'code' => 200,
                    'msg' => '获取容器信息成功',
                    'data' => [
                        'hostname' => $data['hostname'] ?? '',
                        'status' => $data['status'] ?? '',
                        'ipv4' => $data['ipv4'] ?? '',
                        'ipv6' => $data['ipv6'] ?? '',
                        'type' => $data['type'] ?? '',
                        'created_at' => $data['created_at'] ?? '',
                        'cpus' => $data['config']['cpus'] ?? 1,
                        'memory' => $data['memory'] ?? 1024,
                        'disk' => $data['disk'] ?? 10240,
                        'config' => [
                            'cpus' => $data['config']['cpus'] ?? 1,
                            'memory' => $data['config']['memory'] ?? '1024 MB',
                            'disk' => $data['config']['disk'] ?? '10240 MB',
                            'traffic_limit' => $data['config']['traffic_limit'] ?? 0,
                        ],
                        'cpu_usage' => $data['cpu_usage'] ?? 0,
                        'memory_usage' => $data['memory_usage'] ?? '0 B',
                        'memory_usage_raw' => $data['memory_usage_raw'] ?? 0,
                        'disk_usage' => $data['disk_usage'] ?? '0 B',
                        'disk_usage_raw' => $data['disk_usage_raw'] ?? 0,
                        'traffic_usage' => $data['traffic_usage'] ?? '0 B',
                        'traffic_usage_raw' => $data['traffic_usage_raw'] ?? 0,
                        'cpu_percent' => $data['cpu_percent'] ?? 0,
                        'memory_percent' => $data['memory_percent'] ?? 0,
                        'disk_percent' => $data['disk_percent'] ?? 0,
                        'last_update' => date('Y-m-d H:i:s'),
                        'timestamp' => time(),
                    ]
                ];

                return $transformed;
            }
            break;

        case 'gettraffic':
            if (isset($response['data']['used'])) {
                return [
                    'code' => 200,
                    'msg' => '获取流量使用量成功',
                    'data' => [
                        'used' => $response['data']['used'],
                    ]
                ];
            }
            break;
        
        case 'ipv4list':
            if (isset($response['data']) && is_array($response['data'])) {
                return [
                    'code' => 200,
                    'msg' => $response['msg'] ?? 'IPv4列表获取成功',
                    'data' => [
                        'list' => $response['data'],
                        'limit' => 0,
                        'current' => count($response['data']),
                    ]
                ];
            }
            break;
        
        case 'ipv6list':
            if (isset($response['data']) && is_array($response['data'])) {
                return [
                    'code' => 200,
                    'msg' => $response['msg'] ?? 'IPv6列表获取成功',
                    'data' => [
                        'list' => $response['data'],
                        'limit' => 0,
                        'current' => count($response['data']),
                    ]
                ];
            }
            break;
        
        case 'natlist':
            if (isset($response['data']) && is_array($response['data'])) {
                return [
                    'code' => 200,
                    'msg' => $response['msg'] ?? 'NAT列表获取成功',
                    'data' => [
                        'list' => $response['data'],
                        'limit' => 0,
                        'current' => count($response['data']),
                    ]
                ];
            }
            break;
        
        case 'proxylist':
            if (isset($response['data']) && is_array($response['data'])) {
                return [
                    'code' => 200,
                    'msg' => $response['msg'] ?? 'Proxy列表获取成功',
                    'data' => [
                        'list' => $response['data'],
                        'limit' => 0,
                        'current' => count($response['data']),
                    ]
                ];
            }
            break;
    }

    return $response;
}

// 获取NAT规则列表（对齐Python的API端点）
function idcserver_natlist($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $requestData = [
        'url'  => '/api/client/natget/' . $hs_name . '/' . $vm_uuid . '?_t=' . time(),
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];
    $res = idcserver_Curl($params, $requestData, 'GET');
    if ($res === null) {
        return ['code' => 500, 'msg' => '连接API服务器失败', 'data' => []];
    }
    return $res;
}

function idcserver_natcheck($params)
{
    // 先尝试从URL查询参数获取
    $dport = intval($_GET['dport'] ?? 0);
    $dtype = strtolower(trim($_GET['dtype'] ?? ''));
    $hostname = trim($_GET['hostname'] ?? '');

    // 如果GET参数为空，尝试从POST获取
    if ($dport <= 0) {
        $dport = intval($_POST['dport'] ?? 0);
    }
    if (empty($dtype)) {
        $dtype = strtolower(trim($_POST['dtype'] ?? 'tcp'));
    }
    if (empty($hostname)) {
        $hostname = trim($_POST['hostname'] ?? '');
    }

    // 如果还是为空，尝试从原始POST数据解析
    if ($dport <= 0 || empty($hostname)) {
        $postRaw = file_get_contents("php://input");
        if (!empty($postRaw)) {
            parse_str($postRaw, $input);
            if ($dport <= 0) {
                $dport = intval($input['dport'] ?? 0);
            }
            if (empty($dtype)) {
                $dtype = strtolower(trim($input['dtype'] ?? 'tcp'));
            }
            if (empty($hostname)) {
                $hostname = trim($input['hostname'] ?? '');
            }
        }
    }

    // 如果hostname还是空，使用params中的domain
    if (empty($hostname)) {
        $hostname = trim($params['domain'] ?? '');
    }

    idcserver_debug('natcheck参数解析', [
        'dport' => $dport, 
        'dtype' => $dtype, 
        'hostname' => $hostname,
        'GET' => $_GET,
        'POST' => $_POST,
        'raw_input' => file_get_contents("php://input"),
        'params_domain' => $params['domain'] ?? 'null'
    ]);

    // 参数验证
    if ($dport <= 0) {
        return ['code' => 400, 'msg' => '缺少端口参数', 'data' => ['available' => false, 'reason' => '缺少端口参数']];
    }
    if (!in_array($dtype, ['tcp', 'udp'])) {
        return ['code' => 400, 'msg' => '协议类型错误', 'data' => ['available' => false, 'reason' => '协议类型错误']];
    }
    if ($dport < 10000 || $dport > 65535) {
        return ['code' => 400, 'msg' => '端口范围为10000-65535', 'data' => ['available' => false, 'reason' => '端口范围为10000-65535']];
    }
    if (empty($hostname)) {
        return ['code' => 400, 'msg' => '容器标识缺失', 'data' => ['available' => false, 'reason' => '容器标识缺失']];
    }

    // 使用GET请求调用后端API
    $queryParams = http_build_query([
        'hostname' => $hostname,
        'protocol' => $dtype,
        'port'     => $dport,
    ]);

    $requestData = [
        'url'  => '/api/nat/check?' . $queryParams,
        'type' => 'application/x-www-form-urlencoded',
        'data' => '',
    ];

    $res = idcserver_Curl($params, $requestData, 'GET');

    if ($res === null) {
        return ['code' => 500, 'msg' => '连接服务器失败', 'data' => ['available' => false, 'reason' => '连接服务器失败']];
    }

    if (!isset($res['code'])) {
        return ['code' => 500, 'msg' => '服务器返回无效数据', 'data' => ['available' => false, 'reason' => '服务器返回无效数据']];
    }

    return $res;
}

// 获取VNC控制台URL（对齐Python的API端点）
function idcserver_vnc($params) {
    idcserver_debug('VNC控制台请求', ['domain' => $params['domain']]);

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    // 检查虚拟机状态
    $statusData = [
        'url'  => '/api/client/status/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];
    $statusRes = idcserver_Curl($params, $statusData, 'GET');

    if (!isset($statusRes['code']) || $statusRes['code'] != 200) {
        return ['status' => 'error', 'msg' => $statusRes['msg'] ?? '无法获取虚拟机状态'];
    }

    // 检查虚拟机是否运行
    $status_list = $statusRes['data'] ?? [];
    if (!empty($status_list) && is_array($status_list)) {
        $hw_status = $status_list[0];
        $vmStatus = strtoupper($hw_status['vm_status'] ?? '');
        if (!in_array($vmStatus, ['RUNNING', 'STARTED'])) {
            return ['status' => 'error', 'msg' => '虚拟机未运行，无法连接控制台'];
        }
    } else {
        return ['status' => 'error', 'msg' => '无法获取虚拟机状态'];
    }

    // 获取VNC访问地址
    $remoteData = [
        'url'  => '/api/client/remote/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $remoteRes = idcserver_Curl($params, $remoteData, 'GET');

    if (!isset($remoteRes['code']) || $remoteRes['code'] != 200) {
        return ['status' => 'error', 'msg' => $remoteRes['msg'] ?? '生成控制台访问地址失败'];
    }

    $consoleUrl = $remoteRes['data']['url'] ?? '';
    if (empty($consoleUrl)) {
        return ['status' => 'error', 'msg' => '控制台访问地址为空'];
    }

    return [
        'status' => 'success',
        'url' => $consoleUrl,
        'msg' => '控制台连接已准备就绪'
    ];
}

// 后台自定义按钮定义
function idcserver_AdminButton($params)
{
    if (!empty($params['domain'])) {
        return [
            'TrafficReset' => '流量重置',
        ];
    }
    return [];
}

// 处理流量重置请求
function idcserver_TrafficReset($params)
{
    idcserver_debug('流量重置请求', ['domain' => $params['domain']]);

    if (empty($params['domain'])) {
        return ['status' => 'error', 'msg' => '容器域名参数缺失'];
    }

    $data = [
        'url'  => '/api/traffic/reset?hostname=' . urlencode($params['domain']),
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'POST');


    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '流量统计已重置'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '流量重置失败'];
    }
}

// 获取IPv6绑定数量（对齐Python的API端点）
function idcserver_getIPv6BindingCount($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/ipaddr/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200 && isset($res['data']) && is_array($res['data'])) {
        return count($res['data']);
    }

    return 0;
}

// 添加IPv4独立绑定（对齐Python的API端点）
function idcserver_ipv4add($params)
{
    $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
    if (!in_array($network_mode, ['mode5', 'mode7'])) {
        return ['status' => 'error', 'msg' => 'IPv4独立绑定功能未启用，请联系管理员配置为模式5（IPv4独立）或模式7（IPv4独立 + IPv6独立）。'];
    }
    
    parse_str(file_get_contents("php://input"), $post);

    $description = trim($post['description'] ?? '');

    $ipv4_limit = intval($params['configoptions']['ipv4_limit'] ?? 1);
    $current_count = idcserver_getIPv4BindingCount($params);
    
    if ($current_count >= $ipv4_limit) {
        return ['status' => 'error', 'msg' => "IPv4绑定数量已达到限制（{$ipv4_limit}个），无法添加更多绑定"];
    }

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    // 构建NCConfig结构（对齐Python）
    $nic_data = [
        'nic_type' => 'bridge',
        'mac_addr' => generateRandomMac(),
        'ip4_addr' => '', // 由后端自动分配
        'ip6_addr' => '',
        'nic_tips' => $description,
    ];

    $data = [
        'url'  => '/api/client/ipaddr/create/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => $nic_data,
    ];

    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? 'IPv4绑定添加成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? 'IPv4绑定添加失败'];
    }
}

// 删除IPv4独立绑定（对齐Python的API端点）
function idcserver_ipv4del($params)
{
    parse_str(file_get_contents("php://input"), $post);

    $nic_index = intval($post['nic_index'] ?? -1);

    if ($nic_index < 0) {
        return ['status' => 'error', 'msg' => '缺少网卡索引参数'];
    }

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/ipaddr/delete/' . $hs_name . '/' . $vm_uuid . '/' . $nic_index,
        'type' => 'application/x-www-form-urlencoded',
        'data' => '',
    ];

    $res = idcserver_Curl($params, $data, 'DELETE');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? 'IPv4绑定删除成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? 'IPv4绑定删除失败'];
    }
}

// 获取IPv4绑定列表（对齐Python的API端点）
function idcserver_ipv4list($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/ipaddr/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded', 
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200) {
        $ipv4_limit = intval($params['configoptions']['ipv4_limit'] ?? 1);
        $current_count = count($res['data'] ?? []);
        
        return [
            'status' => 'success', 
            'data' => [
                'list' => $res['data'] ?? [],
                'limit' => $ipv4_limit,
                'current' => $current_count,
            ],
        ];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? 'IPv4绑定列表获取失败'];
    }
}

// 获取IPv4绑定数量（对齐Python的API端点）
function idcserver_getIPv4BindingCount($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/ipaddr/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200 && isset($res['data'])) {
        return count($res['data']);
    }

    return 0;
}

// 添加IPv6独立绑定（对齐Python的API端点）
function idcserver_ipv6add($params)
{
    $network_mode = $params['configoptions']['network_mode'] ?? 'mode1';
    if (!in_array($network_mode, ['mode4', 'mode6', 'mode7'])) {
        return ['status' => 'error', 'msg' => 'IPv6独立绑定功能未启用，请联系管理员配置为模式4、模式6或模式7。'];
    }
    
    parse_str(file_get_contents("php://input"), $post);

    $description = trim($post['description'] ?? '');

    $ipv6_limit = intval($params['configoptions']['ipv6_limit'] ?? 1);
    $current_count = idcserver_getIPv6BindingCount($params);
    
    if ($current_count >= $ipv6_limit) {
        return ['status' => 'error', 'msg' => "IPv6绑定数量已达到限制（{$ipv6_limit}个），无法添加更多绑定"];
    }

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    // 构建NCConfig结构（对齐Python）
    $nic_data = [
        'nic_type' => 'bridge',
        'mac_addr' => generateRandomMac(),
        'ip4_addr' => '',
        'ip6_addr' => '', // 由后端自动分配
        'nic_tips' => $description,
    ];

    $data = [
        'url'  => '/api/client/ipaddr/create/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => $nic_data,
    ];

    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? 'IPv6绑定添加成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? 'IPv6绑定添加失败'];
    }
}

// 删除IPv6独立绑定（对齐Python的API端点）
function idcserver_ipv6del($params)
{
    parse_str(file_get_contents("php://input"), $post);

    $nic_index = intval($post['nic_index'] ?? -1);

    if ($nic_index < 0) {
        return ['status' => 'error', 'msg' => '缺少网卡索引参数'];
    }

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/ipaddr/delete/' . $hs_name . '/' . $vm_uuid . '/' . $nic_index,
        'type' => 'application/x-www-form-urlencoded',
        'data' => '',
    ];

    $res = idcserver_Curl($params, $data, 'DELETE');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? 'IPv6绑定删除成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? 'IPv6绑定删除失败'];
    }
}

// 获取IPv6绑定列表（对齐Python的API端点）
function idcserver_ipv6list($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/ipaddr/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded', 
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'data' => $res['data'] ?? [], 'msg' => $res['msg'] ?? ''];
    } else {
        return ['status' => 'error', 'data' => [], 'msg' => $res['msg'] ?? '获取IPv6绑定列表失败'];
    }
}

// 添加反向代理（对齐Python的API端点和WebProxy结构）
function idcserver_proxyadd($params)
{
    $proxy_enabled = ($params['configoptions']['proxy_enabled'] ?? 'false') === 'true';
    if (!$proxy_enabled) {
        return ['status' => 'error', 'msg' => 'Nginx反向代理功能已禁用，请联系管理员启用此功能。'];
    }
    
    parse_str(file_get_contents("php://input"), $post);

    $domain = trim($post['domain'] ?? '');
    $lan_port = intval($post['container_port'] ?? 80);
    $description = trim($post['description'] ?? '');
    $is_https = ($post['ssl_enabled'] ?? 'false') === 'true';

    if (empty($domain)) {
        return ['status' => 'error', 'msg' => '请输入域名'];
    }

    // 验证域名格式
    if (!preg_match('/^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/', $domain)) {
        return ['status' => 'error', 'msg' => '域名格式无效'];
    }

    // 检查数量限制
    $proxy_limit = intval($params['configoptions']['proxy_limit'] ?? 1);
    $current_count = idcserver_getProxyCount($params);
    
    if ($current_count >= $proxy_limit) {
        return ['status' => 'error', 'msg' => "已达到反向代理数量上限（{$proxy_limit}个），无法继续添加"];
    }

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    // 构建WebProxy结构（对齐Python）
    $proxy_data = [
        'web_addr' => $domain,
        'lan_port' => $lan_port,
        'lan_addr' => '', // 由后端自动填充
        'wan_addr' => '', // 由后端自动填充
        'is_https' => $is_https,
        'web_tips' => $description,
    ];

    $data = [
        'url'  => '/api/client/proxys/create/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/json',
        'data' => $proxy_data,
    ];

    $res = idcserver_JSONCurl($params, $data, 'POST');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => '反向代理添加成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '添加反向代理失败'];
    }
}

// 删除反向代理（对齐Python的API端点）
function idcserver_proxydel($params)
{
    parse_str(file_get_contents("php://input"), $post);

    $proxy_index = intval($post['proxy_index'] ?? -1);

    if ($proxy_index < 0) {
        return ['status' => 'error', 'msg' => '缺少代理索引参数'];
    }

    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];

    $data = [
        'url'  => '/api/client/proxys/delete/' . $hs_name . '/' . $vm_uuid . '/' . $proxy_index,
        'type' => 'application/x-www-form-urlencoded',
        'data' => '',
    ];

    $res = idcserver_Curl($params, $data, 'DELETE');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => '反向代理删除成功'];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '删除反向代理失败'];
    }
}

// 获取反向代理列表（对齐Python的API端点）
function idcserver_proxylist($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/proxys/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'data' => $res['data'] ?? [], 'msg' => $res['msg'] ?? ''];
    } else {
        return ['status' => 'error', 'data' => [], 'msg' => $res['msg'] ?? '获取反向代理列表失败'];
    }
}

// 检查域名是否可用
function idcserver_proxycheck($params)
{
    parse_str(file_get_contents("php://input"), $post);
    
    $domain = trim($post['domain'] ?? '');
    
    if (empty($domain)) {
        return ['status' => 'error', 'msg' => '请输入域名'];
    }
    
    $data = [
        'url'  => '/api/proxy/check?domain=' . urlencode($domain),
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];
    
    $res = idcserver_Curl($params, $data, 'GET');
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'data' => $res['data'] ?? [], 'msg' => $res['msg'] ?? ''];
    } else {
        return ['status' => 'error', 'msg' => $res['msg'] ?? '检查域名失败'];
    }
}

// 获取反向代理数量（对齐Python的API端点）
function idcserver_getProxyCount($params)
{
    $hs_name = $params['configoptions']['host_name'] ?? 'default';
    $vm_uuid = $params['domain'];
    
    $data = [
        'url'  => '/api/client/proxys/detail/' . $hs_name . '/' . $vm_uuid,
        'type' => 'application/x-www-form-urlencoded',
        'data' => [],
    ];

    $res = idcserver_Curl($params, $data, 'GET');

    if (isset($res['code']) && $res['code'] == 200 && is_array($res['data'])) {
        return count($res['data']);
    }

    return 0;
}