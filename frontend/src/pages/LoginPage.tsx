import { Form, Input, Button, Card, Typography, Alert } from "antd";
import { LockOutlined, MailOutlined, ShopOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { login } from "../store/authSlice";
import type { AppDispatch, RootState } from "../store";

const { Title } = Typography;

export default function LoginPage() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { loading, error } = useSelector((s: RootState) => s.auth);
  const tenantConfig = useSelector((s: RootState) => s.tenant.config);
  const isResolved = tenantConfig?.resolved === true;

  const onFinish = async (values: { email: string; password: string; tenant_slug?: string }) => {
    const payload = {
      email: values.email,
      password: values.password,
      tenant_slug: isResolved ? tenantConfig.slug : (values.tenant_slug?.trim() || undefined)
    };
    const result = await dispatch(login(payload));
    if (login.fulfilled.match(result)) {
      navigate("/dashboard");
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0b0f19" }}>
      <Card 
        style={{ 
          width: 400, 
          background: "rgba(22, 28, 45, 0.6)", 
          border: "1px solid var(--glass-border)", 
          borderRadius: 16,
          boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
          backdropFilter: "blur(8px)"
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          {isResolved && tenantConfig?.branding?.logo_url ? (
            <div style={{ marginBottom: 16 }}>
              <img 
                src={tenantConfig.branding.logo_url} 
                style={{ maxHeight: 60, maxWidth: 280, objectFit: "contain" }} 
                alt={tenantConfig.name} 
              />
            </div>
          ) : (
            <Title level={3} style={{ margin: 0, color: "#ffffff" }}>
              {isResolved ? tenantConfig.name : "CCTV AMC Platform"}
            </Title>
          )}
          <Typography.Text style={{ color: "var(--text-secondary)" }}>Sign in to your account</Typography.Text>
        </div>
        {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={onFinish} size="large">
          <Form.Item name="email" rules={[{ required: true, type: "email", message: "Enter a valid email" }]}>
            <Input prefix={<MailOutlined />} placeholder="Email" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)" }} />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "Enter your password" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Password" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)" }} />
          </Form.Item>
          {!isResolved && (
            <Form.Item
              name="tenant_slug"
              tooltip="Only needed if your email is registered with more than one company"
            >
              <Input prefix={<ShopOutlined />} placeholder="Company code (optional, e.g. durwankur)" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)" }} />
            </Form.Item>
          )}
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>
              Sign In
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
