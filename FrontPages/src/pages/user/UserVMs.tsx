import React, { useEffect, useState } from 'react';
import { Card, Typography, Row, Col, Spin, Empty, Button, message, Tag, Space, Tooltip } from 'antd';
import { ReloadOutlined, DesktopOutlined, LinkOutlined, SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '@/services/api';
import { VM } from '@/types';
import { useUserStore } from '@/store/userStore';

const { Title } = Typography;

// 扩展 VM 接口以包含 hostName
interface UserVM extends VM {
  hostName: string;
}

const UserVMs: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useUserStore();
  const [loading, setLoading] = useState(false);
  const [vms, setVms] = useState<UserVM[]>([]);

  // 状态文字映射
  const statusMap: Record<string, { text: string; color: string; pulse?: boolean }> = {
    STOPPED: { text: '已停止', color: 'default' },
    STARTED: { text: '运行中', color: 'success', pulse: true },
    SUSPEND: { text: '已暂停', color: 'warning' },
    ON_STOP: { text: '停止中', color: 'processing' },
    ON_OPEN: { text: '启动中', color: 'processing' },
    CRASHED: { text: '已崩溃', color: 'error' },
    UNKNOWN: { text: '未知', color: 'default' },
  };

  useEffect(() => {
    fetchAllVMs();
  }, []);

  const fetchAllVMs = async () => {
    setLoading(true);
    try {
      // 1. 获取所有主机
      const hostsRes = await api.getHosts();
      if (hostsRes.code !== 200 || !hostsRes.data) {
        throw new Error('获取主机列表失败');
      }

      const hosts = Object.keys(hostsRes.data);
      const allVMs: UserVM[] = [];

      // 2. 并行获取所有主机的虚拟机
      await Promise.all(hosts.map(async (hostName) => {
        try {
          const vmsRes = await api.getVMs(hostName);
          if (vmsRes.code === 200 && vmsRes.data) {
            // 将对象转换为数组并添加 hostName
            if (Array.isArray(vmsRes.data)) {
               // 兼容性处理
            } else {
               Object.values(vmsRes.data).forEach((vm: any) => {
                 allVMs.push({ ...vm, hostName });
               });
            }
          }
        } catch (err) {
          console.error(`获取主机 ${hostName} 的虚拟机失败`, err);
        }
      }));

      setVms(allVMs);
    } catch (error) {
      console.error('获取虚拟机失败', error);
      message.error('获取虚拟机列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenVnc = async (hostName: string, uuid: string) => {
    try {
      const hide = message.loading('正在获取VNC控制台地址...', 0);
      const result = await api.getVMConsole(hostName, uuid);
      hide();
      if (result.code === 200 && result.data) {
        // @ts-ignore
        const url = result.data.console_url || result.data;
        window.open(url, `vnc_${uuid}`, 'width=1024,height=768');
      } else {
        message.error('无法获取VNC控制台地址');
      }
    } catch (error) {
      message.error('连接失败');
    }
  };

  const handlePowerAction = async (hostName: string, uuid: string, action: any) => {
    try {
      const hide = message.loading(`正在执行操作...`, 0);
      const result = await api.vmPower(hostName, uuid, action);
      hide();
      if (result.code === 200) {
        message.success(`操作成功`);
        setTimeout(fetchAllVMs, 2000);
      } else {
        message.error(result.msg || '操作失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const renderVMCard = (vm: UserVM) => {
    // @ts-ignore
    const config = vm.config || {};
    // @ts-ignore
    const statusList = vm.status || [];
    // @ts-ignore
    const firstStatus = statusList.length > 0 ? statusList[0] : { ac_status: 'UNKNOWN' };
    const powerStatus = firstStatus.ac_status || 'UNKNOWN';
    const statusInfo = statusMap[powerStatus] || statusMap.UNKNOWN;

    return (
      <Col xs={24} sm={12} lg={8} xl={6} key={`${vm.hostName}-${config.vm_uuid || vm.uuid}`}>
        <Card
          hoverable
          title={config.vm_uuid || vm.uuid}
          extra={<Tag color="blue">{vm.hostName}</Tag>}
          actions={[
            <Tooltip title="VNC控制台">
              <DesktopOutlined key="vnc" onClick={() => handleOpenVnc(vm.hostName, config.vm_uuid || vm.uuid)} />
            </Tooltip>,
            <Tooltip title="开机">
                <Button type="text" size="small" disabled={powerStatus === 'STARTED'} onClick={() => handlePowerAction(vm.hostName, config.vm_uuid || vm.uuid, 'start')}>
                    开机
                </Button>
            </Tooltip>,
            <Tooltip title="关机">
                <Button type="text" danger size="small" disabled={powerStatus === 'STOPPED'} onClick={() => handlePowerAction(vm.hostName, config.vm_uuid || vm.uuid, 'stop')}>
                    关机
                </Button>
            </Tooltip>,
            // 如果是管理员，或者点击详情，跳转到主机特定的管理页面
             <Tooltip title="详细管理">
              <SettingOutlined key="setting" onClick={() => navigate(`/hosts/${vm.hostName}/vms`)} />
            </Tooltip>
          ]}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
             <span>状态:</span>
             <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
          </div>
          <p>OS: {config.os_name || 'Unknown'}</p>
          <p>CPU: {config.cpu_num} 核</p>
          <p>内存: {config.mem_num} MB</p>
          <p>硬盘: {config.hdd_num} MB</p>
        </Card>
      </Col>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>{user?.is_admin ? '系统容器管理' : '我的容器'}</Title>
        <Space>
            {user?.is_admin && (
                <Button onClick={() => navigate('/hosts')}>
                    切换到主机视图
                </Button>
            )}
            <Button icon={<ReloadOutlined />} onClick={fetchAllVMs} loading={loading}>
            刷新
            </Button>
        </Space>
      </div>

      {loading && vms.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Spin size="large" />
        </div>
      ) : vms.length === 0 ? (
        <Empty description="暂无容器" />
      ) : (
        <Row gutter={[16, 16]}>
          {vms.map(vm => renderVMCard(vm))}
        </Row>
      )}
    </div>
  );
};

export default UserVMs;
