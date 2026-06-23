import { useEffect, useState } from "react";
import { Row, Col, Card, Statistic, Typography, Spin, message, Button } from "antd";
import { ToolOutlined, SafetyCertificateOutlined, PlusOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import portalClient from "../../api/portalClient";

const { Title } = Typography;

interface Dash { open_tickets: number; total_tickets: number; active_amc_contracts: number }

export default function PortalDashboardPage() {
  const navigate = useNavigate();
  const [d, setD] = useState<Dash | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await portalClient.get("/dashboard");
        setD(data);
      } catch (e: any) {
        message.error(e?.response?.data?.detail || "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Spin style={{ display: "block", margin: "80px auto" }} />;
  if (!d) return null;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Welcome back</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/portal/tickets?new=1")}>
          Raise Service Request
        </Button>
      </div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}><Card><Statistic title="Open Tickets" value={d.open_tickets} prefix={<ToolOutlined />} valueStyle={{ color: "#fa8c16" }} /></Card></Col>
        <Col xs={24} sm={8}><Card><Statistic title="Total Tickets" value={d.total_tickets} prefix={<ToolOutlined />} /></Card></Col>
        <Col xs={24} sm={8}><Card><Statistic title="Active AMC" value={d.active_amc_contracts} prefix={<SafetyCertificateOutlined />} valueStyle={{ color: "#52c41a" }} /></Card></Col>
      </Row>
    </div>
  );
}
