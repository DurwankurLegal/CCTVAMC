import { useState } from "react";
import { Form, Input, Button, Card, Typography, Alert } from "antd";
import { LockOutlined, MailOutlined, ShopOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import portalClient from "../../api/portalClient";

const { Title } = Typography;

export default function PortalLoginPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onFinish = async (values: { email: string; password: string; tenant_slug: string }) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await portalClient.post("/login", values);
      localStorage.setItem("portal_token", data.access_token);
      localStorage.setItem("portal_refresh", data.refresh_token);
      const me = await portalClient.get("/me");
      localStorage.setItem("portal_user", JSON.stringify(me.data));
      navigate("/portal");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f0f2f5", padding: 16 }}>
      <Card style={{ width: 420, maxWidth: "100%", boxShadow: "0 4px 24px rgba(0,0,0,0.1)" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Title level={3} style={{ margin: 0 }}>Customer Portal</Title>
          <Typography.Text type="secondary">Track your service requests & AMC</Typography.Text>
        </div>
        {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={onFinish} size="large">
          <Form.Item name="tenant_slug" rules={[{ required: true, message: "Enter your provider code" }]}>
            <Input prefix={<ShopOutlined />} placeholder="Service provider code (e.g. durwankur)" />
          </Form.Item>
          <Form.Item name="email" rules={[{ required: true, type: "email", message: "Enter a valid email" }]}>
            <Input prefix={<MailOutlined />} placeholder="Email" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "Enter your password" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Password" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>Sign In</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
