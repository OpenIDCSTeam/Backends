import React, { useEffect, useState } from 'react';
import { Card, Typography, Row, Col, Progress, Spin, message } from 'antd';
import { useUserStore } from '@/utils/data.ts';
import api from '@/utils/apis.ts';

const { Title } = Typography;

const UserPanels: React.FC = () => {
  const { user, setUser } = useUserStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchUserData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchUserData = async () => {
    setLoading(true);
    try {
      const res = await api.getCurrentUser();
      if (res.code === 200) {
        setUser(res.data || null);
      }
    } catch (error) {
      console.error('获取用户信息失败', error);
      message.error('获取用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  if (!user) return <Spin />;

  const formatStorage = (mb: number): string => {
    if (mb < 1024) return `${mb}MB`;
    const gb = mb / 1024;
    if (gb < 1024) return `${gb.toFixed(1)}GB`;
    const tb = gb / 1024;
    return `${tb.toFixed(1)}TB`;
  }

  const renderResourceCard = (title: string, used: number, quota: number, unit: string = '', isStorage: boolean = false) => {
    const percent = quota > 0 ? Math.min(Math.round((used / quota) * 100), 100) : 0;
    const status = percent > 90 ? 'exception' : percent > 70 ? 'active' : 'normal';
    
    // 如果配额非常大（比如99999），显示为无限制
    const isUnlimited = quota > 1000000;
    
    let usedDisplay = `${used}${unit}`;
    let quotaDisplay = isUnlimited ? '无限制' : `${quota}${unit}`;

    if (isStorage) {
        usedDisplay = formatStorage(used);
        quotaDisplay = isUnlimited ? '无限制' : formatStorage(quota);
    }
    
    return (
      <Col xs={24} sm={12} md={8} lg={6} style={{ marginBottom: 16 }}>
        <Card title={title} variant="borderless">
          <div style={{ textAlign: 'center' }}>
            <Progress type="dashboard" percent={isUnlimited ? 0 : percent} status={status} format={() => usedDisplay} />
            <div style={{ marginTop: 8 }}>
              总配额: {quotaDisplay}
            </div>
          </div>
        </Card>
      </Col>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>资源概览</Title>
      
      <Spin spinning={loading}>
        <Row gutter={16}>
          {renderResourceCard('CPU 核心', user.used_cpu || 0, user.quota_cpu || 0, '核')}
          {renderResourceCard('内存', user.used_ram || 0, user.quota_ram || 0, '', true)}
          {renderResourceCard('磁盘存储', user.used_ssd || 0, user.quota_ssd || 0, '', true)}
          {/* 如果有GPU配额，也显示 */}
          {(user.quota_gpu || 0) > 0 && renderResourceCard('GPU', user.used_gpu || 0, user.quota_gpu || 0, '卡')}
        </Row>

        <Title level={4} style={{ marginTop: 24 }}>网络资源</Title>
        <Row gutter={16}>
          {renderResourceCard('NAT 端口', user.used_nat_ports || 0, user.quota_nat_ports || 0, '个')}
          {renderResourceCard('Web 代理', user.used_web_proxy || 0, user.quota_web_proxy || 0, '个')}
          {renderResourceCard('上行带宽', user.used_bandwidth_up || 0, user.quota_bandwidth_up || 0, 'Mbps')}
          {renderResourceCard('下行带宽', user.used_bandwidth_down || 0, user.quota_bandwidth_down || 0, 'Mbps')}
        </Row>
      </Spin>
    </div>
  );
};

export default UserPanels;
