import React, { useEffect, useState } from 'react';
import { Card, Typography, Table, Button, message, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import api from '@/utils/apis.ts';
import {ProxyConfig } from '@/types';

const { Title } = Typography;

interface UserProxy extends ProxyConfig {
  hostName: string;
  vmUuid: string;
}

const UserProxys: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [proxies, setProxies] = useState<UserProxy[]>([]);

  useEffect(() => {
    fetchProxies();
  }, []);

  const fetchProxies = async () => {
    setLoading(true);
    try {
      // 1. 获取所有主机
      const hostsRes = await api.getHosts();
      if (hostsRes.code !== 200 || !hostsRes.data) {
        throw new Error('获取主机列表失败');
      }
      const hosts = Object.keys(hostsRes.data);

      const allProxies: UserProxy[] = [];

      // 2. 遍历主机获取VMs
      for (const hostName of hosts) {
        try {
          const vmsRes = await api.getVMs(hostName);
          if (vmsRes.code === 200 && vmsRes.data) {
             const vms = Array.isArray(vmsRes.data) ? vmsRes.data : Object.values(vmsRes.data);
             
             // 3. 遍历VMs获取Proxies
             // 为了避免并发请求过多，这里可以分批或者限制并发
             await Promise.all(vms.map(async (vm: any) => {
                 const vmUuid = vm.config?.vm_uuid || vm.uuid;
                 // 只有当 web_num > 0 时才去请求 (虽然 web_num 可能是配额，不是已用数量，但如果有配额就有可能有配置)
                 // 更准确的是直接请求
                 try {
                    const proxyRes = await api.getProxyConfigs(hostName, vmUuid);
                    if (proxyRes.code === 200 && proxyRes.data) {
                        proxyRes.data.forEach((p: ProxyConfig) => {
                             allProxies.push({
                                 ...p,
                                 hostName,
                                 vmUuid
                             });
                         });
                     }
                 } catch (e) {
                     // 忽略错误
                 }
             }));
          }
        } catch (e) {
          console.error(`获取主机 ${hostName} 数据失败`, e);
        }
      }

      setProxies(allProxies);
    } catch (error) {
      console.error('获取反向代理失败', error);
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '主机',
      dataIndex: 'hostName',
      key: 'hostName',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '虚拟机',
      dataIndex: 'vmUuid',
      key: 'vmUuid',
    },
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
      render: (text: string) => (
        <a href={`http://${text}`} target="_blank" rel="noopener noreferrer">
          {text}
        </a>
      ),
    },
    {
        title: '后端端口',
        dataIndex: 'backend_port',
        key: 'backend_port',
    },
    {
      title: '类型',
      dataIndex: 'proxy_type',
      key: 'proxy_type',
      render: (text: string) => <Tag color={text === 'https' ? 'green' : 'orange'}>{text || 'http'}</Tag>,
    },
    {
        title: '状态',
        dataIndex: 'enabled',
        key: 'enabled',
        render: (enabled: boolean) => (
            <Tag color={enabled ? 'success' : 'error'}>
                {enabled ? '已启用' : '已禁用'}
            </Tag>
        )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>我的反向代理</Title>
        <Button icon={<ReloadOutlined />} onClick={fetchProxies} loading={loading}>
          刷新
        </Button>
      </div>

      <Card>
        <Table
          dataSource={proxies}
          columns={columns}
          rowKey={(record) => `${record.hostName}-${record.vmUuid}-${record.domain}`} // 假设 domain 是唯一的
          loading={loading}
          locale={{ emptyText: '暂无反向代理配置' }}
        />
      </Card>
    </div>
  );
};

export default UserProxys;
