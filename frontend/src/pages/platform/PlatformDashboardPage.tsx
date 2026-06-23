import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Typography, Spin, message, Tag, Space } from "antd";
import { ShopOutlined, CheckCircleOutlined, PauseCircleOutlined, StopOutlined } from "@ant-design/icons";
import apiClient from "../../api/client";

const { Title } = Typography;

interface Metrics {
  total_tenants: number;
  active: number;
  suspended: number;
  trial: number;
  cancelled: number;
  by_plan: Record<string, number>;
}

export default function PlatformDashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await apiClient.get("/tenants/platform/metrics");
        setMetrics(data);
      } catch (e: any) {
        message.error(e?.response?.data?.detail || "Failed to load metrics");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Spin style={{ display: "block", margin: "80px auto" }} />;
  if (!metrics) return null;

  return (
    <div>
      <Title level={4}>Platform Overview</Title>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}><Card><Statistic title="Total Tenants" value={metrics.total_tenants} prefix={<ShopOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="Active" value={metrics.active} valueStyle={{ color: "#52c41a" }} prefix={<CheckCircleOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="Suspended" value={metrics.suspended} valueStyle={{ color: "#faad14" }} prefix={<PauseCircleOutlined />} /></Card></Col>
        <Col span={6}><Card><Statistic title="Cancelled" value={metrics.cancelled} valueStyle={{ color: "#ff4d4f" }} prefix={<StopOutlined />} /></Card></Col>
      </Row>

      <Card title="Plan Distribution">
        <Space size="large" wrap>
          {Object.entries(metrics.by_plan).length === 0 && <span style={{ color: "#999" }}>No tenants yet</span>}
          {Object.entries(metrics.by_plan).map(([plan, count]) => (
            <Statistic key={plan} title={<Tag>{plan}</Tag>} value={count} />
          ))}
        </Space>
      </Card>
    </div>
  );
}
