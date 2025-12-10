<?php

use think\Db;

define('LXDAPISERVER_DEBUG', true);

function lxdapiserver_debug($message, $data = null)
{
    if (!LXDAPISERVER_DEBUG) return;
    $log = '[LXDAPISERVER-DEBUG] ' . $message;
    if ($data !== null) {
        $log .= ' | Data: ' . json_encode($data, JSON_UNESCAPED_UNICODE);
    }
    error_log($log);
}

function lxdapiserver_MetaData()
{
    return [
        'DisplayName' => '魔方财务-LXD对接插件 by xkatld',
        'APIVersion'  => 'v2.0.2',
        'HelpDoc'     => 'https://github.com/xkatld/lxdapi-web-server',
    ];
}

function lxdapiserver_ConfigOptions()
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
            'description' => '内存大小，单位：MB',
            'default'     => '512',
            'key'         => 'memory',
        ],
        'disk' => [
            'type'        => 'text',
            'name'        => '硬盘',
            'description' => '硬盘大小，单位：MB',
            'default'     => '1024',
            'key'         => 'disk',
        ],
        'image' => [
            'type'        => 'text',
            'name'        => '镜像',
            'description' => '系统镜像名称',
            'default'     => 'alpine320',
            'key'         => 'image',
        ],
        'ingress' => [
            'type'        => 'text',
            'name'        => '入站带宽',
            'description' => '下载速度限制，单位：Mbit',
            'default'     => '100',
            'key'         => 'ingress',
        ],
        'egress' => [
            'type'        => 'text',
            'name'        => '出站带宽',
            'description' => '上传速度限制，单位：Mbit',
            'default'     => '100',
            'key'         => 'egress',
        ],
        'traffic_limit' => [
            'type'        => 'text',
            'name'        => '月流量限制',
            'description' => '单位：GB',
            'default'     => '100',
            'key'         => 'traffic_limit',
        ],
        'ipv4_pool_limit' => [
            'type'        => 'text',
            'name'        => 'IPv4地址池限制',
            'description' => 'IPv4独立地址数量上限',
            'default'     => '0',
            'key'         => 'ipv4_pool_limit',
        ],
        'ipv4_mapping_limit' => [
            'type'        => 'text',
            'name'        => 'IPv4端口映射限制',
            'description' => 'IPv4端口转发规则上限',
            'default'     => '0',
            'key'         => 'ipv4_mapping_limit',
        ],
        'ipv6_pool_limit' => [
            'type'        => 'text',
            'name'        => 'IPv6地址池限制',
            'description' => 'IPv6独立地址数量上限',
            'default'     => '0',
            'key'         => 'ipv6_pool_limit',
        ],
        'ipv6_mapping_limit' => [
            'type'        => 'text',
            'name'        => 'IPv6端口映射限制',
            'description' => 'IPv6端口转发规则上限',
            'default'     => '0',
            'key'         => 'ipv6_mapping_limit',
        ],
        'reverse_proxy_limit' => [
            'type'        => 'text',
            'name'        => '反向代理限制',
            'description' => '反向代理域名数量上限',
            'default'     => '0',
            'key'         => 'reverse_proxy_limit',
        ],
        'cpu_allowance' => [
            'type'        => 'text',
            'name'        => 'CPU使用率限制',
            'description' => 'CPU占用百分比，单位：%',
            'default'     => '50',
            'key'         => 'cpu_allowance',
        ],
        'io_read' => [
            'type'        => 'text',
            'name'        => '磁盘读取限制',
            'description' => '单位：MB/s',
            'default'     => '100',
            'key'         => 'io_read',
        ],
        'io_write' => [
            'type'        => 'text',
            'name'        => '磁盘写入限制',
            'description' => '单位：MB/s',
            'default'     => '50',
            'key'         => 'io_write',
        ],
        'processes_limit' => [
            'type'        => 'text',
            'name'        => '最大进程数',
            'description' => '进程数量上限',
            'default'     => '512',
            'key'         => 'processes_limit',
        ],
        'allow_nesting' => [
            'type'        => 'dropdown',
            'name'        => '嵌套虚拟化',
            'description' => '支持Docker等虚拟化',
            'default'     => 'true',
            'key'         => 'allow_nesting',
            'options'     => ['true' => '启用', 'false' => '禁用'],
        ],
        'memory_swap' => [
            'type'        => 'dropdown',
            'name'        => 'Swap开关',
            'description' => '虚拟内存开关',
            'default'     => 'true',
            'key'         => 'memory_swap',
            'options'     => ['true' => '启用', 'false' => '禁用'],
        ],
        'privileged' => [
            'type'        => 'dropdown',
            'name'        => '特权模式',
            'description' => '特权容器开关',
            'default'     => 'false',
            'key'         => 'privileged',
            'options'     => ['true' => '启用', 'false' => '禁用'],
        ],
    ];
}

function lxdapiserver_ParseMemory($str)
{
    $str = trim($str);
    if (empty($str)) return 0;
    
    if (stripos($str, 'GB') !== false) {
        return intval($str) * 1024;
    } elseif (stripos($str, 'MB') !== false) {
        return intval($str);
    } else {
        return intval($str);
    }
}

function lxdapiserver_ParseBandwidth($str)
{
    $str = trim($str);
    if (empty($str)) return 0;
    
    if (stripos($str, 'Gbit') !== false) {
        return intval($str) * 1000;
    } elseif (stripos($str, 'Mbit') !== false) {
        return intval($str);
    } else {
        return intval($str);
    }
}

function lxdapiserver_ApiRequest($params, $endpoint, $data = [], $method = 'POST')
{
    $curl = curl_init();
    
    $protocol = 'https';
    $url = $protocol . '://' . $params['server_ip'] . ':' . $params['port'] . $endpoint;
    
    lxdapiserver_debug('API请求', [
        'url' => $url,
        'method' => $method
    ]);
    
    $curlOptions = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_ENCODING       => '',
        CURLOPT_MAXREDIRS      => 10,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_HTTP_VERSION   => CURL_HTTP_VERSION_1_1,
        CURLOPT_CUSTOMREQUEST  => $method,
        CURLOPT_HTTPHEADER     => [
            'X-API-Hash: ' . $params['accesshash'],
            'Content-Type: application/json',
        ],
    ];
    
    $curlOptions[CURLOPT_SSL_VERIFYPEER] = false;
    $curlOptions[CURLOPT_SSL_VERIFYHOST] = false;
    $curlOptions[CURLOPT_SSLVERSION] = CURL_SSLVERSION_TLSv1_2;
    
    if ($method === 'POST' || $method === 'PUT') {
        if (!empty($data)) {
            $curlOptions[CURLOPT_POSTFIELDS] = json_encode($data);
        }
    }
    
    curl_setopt_array($curl, $curlOptions);
    
    $response = curl_exec($curl);
    $errno = curl_errno($curl);
    $httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
    $curlError = curl_error($curl);
    
    curl_close($curl);
    
    lxdapiserver_debug('API响应', [
        'http_code' => $httpCode,
        'response_length' => strlen($response),
        'curl_errno' => $errno
    ]);
    
    if ($errno) {
        lxdapiserver_debug('CURL错误', [
            'errno' => $errno,
            'error' => $curlError
        ]);
        return null;
    }
    
    $decoded = json_decode($response, true);
    return $decoded;
}

function lxdapiserver_TestLink($params)
{
    lxdapiserver_debug('测试API连接', $params);
    
    $res = lxdapiserver_ApiRequest($params, '/api/system/containers', [], 'GET');
    
    lxdapiserver_debug('TestLink API响应', $res);
    
    if ($res === null) {
        return [
            'status' => 200,
            'data'   => [
                'server_status' => 0,
                'msg'           => '连接失败: 无法连接到服务器'
            ]
        ];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return [
            'status' => 200,
            'data'   => [
                'server_status' => 1,
                'msg'           => '连接成功'
            ]
        ];
    }
    
    return [
        'status' => 200,
        'data'   => [
            'server_status' => 0,
            'msg'           => '连接失败: ' . ($res['msg'] ?? '未知错误')
        ]
    ];
}

function lxdapiserver_CreateAccount($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('创建容器', ['domain' => $containerName]);
    
    $configoptions = $params['configoptions'];
    
    $requestData = [
        'name' => $containerName,
        'image' => $configoptions['image'] ?? 'alpine320',
        'username' => 'user_' . $params['userid'],
        'password' => $params['password'],
        'cpu' => (int)($configoptions['cpus'] ?? 1),
        'memory' => (int)($configoptions['memory'] ?? 512),
        'disk' => (int)($configoptions['disk'] ?? 1024),
        'ingress' => (int)($configoptions['ingress'] ?? 100),
        'egress' => (int)($configoptions['egress'] ?? 100),
        'traffic_limit' => (int)($configoptions['traffic_limit'] ?? 100),
        'allow_nesting' => ($configoptions['allow_nesting'] ?? 'true') === 'true',
        'memory_swap' => ($configoptions['memory_swap'] ?? 'true') === 'true',
        'privileged' => ($configoptions['privileged'] ?? 'false') === 'true',
        'cpu_allowance' => (int)($configoptions['cpu_allowance'] ?? 50),
        'io_read' => (int)($configoptions['io_read'] ?? 100),
        'io_write' => (int)($configoptions['io_write'] ?? 50),
        'processes_limit' => (int)($configoptions['processes_limit'] ?? 512),
        'ipv4_pool_limit' => (int)($configoptions['ipv4_pool_limit'] ?? 0),
        'ipv4_mapping_limit' => (int)($configoptions['ipv4_mapping_limit'] ?? 0),
        'ipv6_pool_limit' => (int)($configoptions['ipv6_pool_limit'] ?? 0),
        'ipv6_mapping_limit' => (int)($configoptions['ipv6_mapping_limit'] ?? 0),
        'reverse_proxy_limit' => (int)($configoptions['reverse_proxy_limit'] ?? 0),
    ];
    
    lxdapiserver_debug('创建请求数据', $requestData);
    
    $res = lxdapiserver_ApiRequest($params, '/api/system/containers', $requestData, 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        try {
            $update = [
                'domainstatus' => 'Active',
                'username'     => 'root',
                'dedicatedip'  => $params['server_ip'],
            ];
            
            Db::name('host')->where('id', $params['hostid'])->update($update);
            lxdapiserver_debug('数据库更新成功', $update);
        } catch (\Exception $e) {
            return ['status' => 'error', 'msg' => '创建成功但同步数据失败: ' . $e->getMessage()];
        }
        
        return ['status' => 'success', 'msg' => $res['msg'] ?? '创建成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '创建失败'];
}

function lxdapiserver_TerminateAccount($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('删除容器', ['domain' => $containerName]);
    
    $endpoint = '/api/system/containers/' . urlencode($containerName);
    $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'DELETE');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '删除成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '删除失败'];
}

function lxdapiserver_On($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('启动容器', ['domain' => $containerName]);
    
    $endpoint = '/api/system/containers/' . urlencode($containerName) . '/action?action=start';
    $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '启动成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '启动失败'];
}

function lxdapiserver_Off($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('停止容器', ['domain' => $containerName]);
    
    $endpoint = '/api/system/containers/' . urlencode($containerName) . '/action?action=stop';
    $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '停止成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '停止失败'];
}

function lxdapiserver_Reboot($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('重启容器', ['domain' => $containerName]);
    
    $endpoint = '/api/system/containers/' . urlencode($containerName) . '/action?action=restart';
    $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '重启成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '重启失败'];
}

function lxdapiserver_SuspendAccount($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('暂停容器', ['domain' => $containerName]);
    
    $endpoint = '/api/system/containers/' . urlencode($containerName) . '/action?action=pause';
    $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '暂停成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '暂停失败'];
}

function lxdapiserver_UnsuspendAccount($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('恢复容器', ['domain' => $containerName]);
    
    $endpoint = '/api/system/containers/' . urlencode($containerName) . '/action?action=resume';
    $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '恢复成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '恢复失败'];
}

function lxdapiserver_Status($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('查询状态', ['domain' => $containerName]);
    
    $endpoint = '/api/system/containers/' . urlencode($containerName);
    $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'GET');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200 && isset($res['data']['status'])) {
        $containerStatus = $res['data']['status'];
        $result = ['status' => 'success'];
        
        switch (strtoupper($containerStatus)) {
            case 'RUNNING':
                $result['data']['status'] = 'on';
                $result['data']['des'] = '运行中';
                break;
            case 'STOPPED':
                $result['data']['status'] = 'off';
                $result['data']['des'] = '已停止';
                break;
            case 'FROZEN':
                $result['data']['status'] = 'suspend';
                $result['data']['des'] = '已暂停';
                break;
            default:
                $result['data']['status'] = 'unknown';
                $result['data']['des'] = '未知状态';
                break;
        }
        
        return $result;
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '查询失败'];
}

function lxdapiserver_Sync($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('同步容器信息', ['domain' => $containerName]);
    
    $endpoint = '/api/system/containers/' . urlencode($containerName);
    $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'GET');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        try {
            $update = [];
            
            if (isset($res['data']['status'])) {
                $containerStatus = strtoupper($res['data']['status']);
                if ($containerStatus === 'RUNNING') {
                    $update['domainstatus'] = 'Active';
                } elseif ($containerStatus === 'STOPPED') {
                    $update['domainstatus'] = 'Suspended';
                }
            }
            
            if (!empty($update)) {
                Db::name('host')->where('id', $params['hostid'])->update($update);
                lxdapiserver_debug('同步数据库成功', $update);
            }
            
            return ['status' => 'success', 'msg' => '同步成功'];
        } catch (\Exception $e) {
            return ['status' => 'error', 'msg' => '同步失败: ' . $e->getMessage()];
        }
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '同步失败'];
}

function lxdapiserver_Reinstall($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('重装系统', ['domain' => $containerName, 'reinstall_os' => $params['reinstall_os'] ?? 'null']);
    
    if (empty($params['reinstall_os'])) {
        return ['status' => 'error', 'msg' => '操作系统参数错误'];
    }
    
    $requestData = [
        'image' => $params['reinstall_os'],
        'password' => $params['password'],
    ];
    
    $endpoint = '/api/system/containers/' . urlencode($containerName) . '/action?action=reinstall';
    $res = lxdapiserver_ApiRequest($params, $endpoint, $requestData, 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '重装成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '重装失败'];
}

function lxdapiserver_AdminButton($params)
{
    if (!empty($params['domain'])) {
        return [
            'Sync' => '同步状态',
            'TrafficReset' => '重置流量',
        ];
    }
    return [];
}

function lxdapiserver_TrafficReset($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('重置流量', ['domain' => $containerName]);
    
    $res = lxdapiserver_ApiRequest($params, '/api/system/traffic/reset?name=' . urlencode($containerName), [], 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        return ['status' => 'success', 'msg' => $res['msg'] ?? '流量重置成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '流量重置失败'];
}

function lxdapiserver_CrackPassword($params, $new_pass)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('重置密码', ['domain' => $containerName]);
    
    $requestData = [
        'password' => $new_pass
    ];
    
    $endpoint = '/api/system/containers/' . urlencode($containerName) . '/action?action=reset-password';
    $res = lxdapiserver_ApiRequest($params, $endpoint, $requestData, 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200) {
        try {
            Db::name('host')->where('id', $params['hostid'])->update(['password' => $new_pass]);
        } catch (\Exception $e) {
            return ['status' => 'error', 'msg' => '密码重置成功但同步数据失败: ' . $e->getMessage()];
        }
        return ['status' => 'success', 'msg' => $res['msg'] ?? '密码重置成功'];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? '密码重置失败'];
}

function lxdapiserver_vnc($params)
{
    $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
    lxdapiserver_debug('VNC控制台', ['domain' => $containerName]);
    
    $requestData = ['hostname' => $containerName];
    $res = lxdapiserver_ApiRequest($params, '/api/system/console/create-token', $requestData, 'POST');
    
    if ($res === null) {
        return ['status' => 'error', 'msg' => '请求失败'];
    }
    
    if (isset($res['code']) && $res['code'] == 200 && isset($res['data']['token'])) {
        $consoleUrl = 'https://' . $params['server_ip'] . ':' . $params['port'] . '/console?token=' . $res['data']['token'];
        
        return [
            'status' => 'success',
            'url' => $consoleUrl
        ];
    }
    
    return ['status' => 'error', 'msg' => $res['msg'] ?? 'VNC连接失败'];
}

function lxdapiserver_ClientArea($params)
{
    return [
        'info' => ['name' => '容器信息'],
    ];
}

function lxdapiserver_ClientAreaOutput($params, $key)
{
    lxdapiserver_debug('ClientAreaOutput调用', ['key' => $key]);
    
    if ($key == 'info') {
        $containerName = is_array($params['domain']) ? $params['domain'][0] : $params['domain'];
        
        $endpoint = '/api/system/containers/' . urlencode($containerName) . '/credential';
        $res = lxdapiserver_ApiRequest($params, $endpoint, [], 'GET');
        
        $jumpUrl = '';
        $iframeUrl = '';
        $accessCode = '';
        $errorMsg = '';
        
        if (isset($res['code']) && $res['code'] == 200 && isset($res['data'])) {
            $accessCode = $res['data']['access_code'] ?? '';
            $protocol = 'https';
            $baseUrl = $protocol . '://' . $params['server_ip'] . ':' . $params['port'];
            $jumpUrl = $baseUrl . '/container/dashboard?hash=' . $accessCode;
            $iframeUrl = $baseUrl . '/container/dashboard/base?hash=' . $accessCode;
        } else {
            $errorMsg = $res['msg'] ?? '获取访问码失败';
        }
        
        return [
            'template' => 'templates/info.html',
            'vars' => [
                'container_name' => $containerName,
                'server_ip' => $params['server_ip'],
                'server_port' => $params['port'],
                'jump_url' => $jumpUrl,
                'iframe_url' => $iframeUrl,
                'access_code' => $accessCode,
                'error_msg' => $errorMsg,
            ]
        ];
    }
    
    return '';
}
