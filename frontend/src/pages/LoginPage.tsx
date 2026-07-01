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

  const onFinish = async (values: { email: string; password: string; tenant_slug?: string }) => {
    // Drop an empty tenant code so single-tenant emails still resolve by email.
    const payload = values.tenant_slug?.trim()
      ? values
      : { email: values.email, password: values.password };
    const result = await dispatch(login(payload));
    if (login.fulfilled.match(result)) {
      navigate("/dashboard");
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f0f2f5" }}>
      <Card style={{ width: 400, boxShadow: "0 4px 24px rgba(0,0,0,0.1)" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ width: 140, height: 140, margin: "0 auto 16px", overflow: "hidden", display: "flex", justifyContent: "center", alignItems: "center", borderRadius: 8 }}>
            <img src="/logo.png" alt="CCTV AMC Logo" style={{ width: "220%", height: "auto", marginTop: "-25%" }} />
          </div>
          <Title level={3} style={{ margin: 0, fontWeight: 600 }}>Welcome Back</Title>
          <Typography.Text type="secondary" style={{ fontSize: 16 }}>Login to manage your account</Typography.Text>
        </div>
        {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={onFinish} size="large">
          <Form.Item name="email" rules={[{ required: true, type: "email", message: "Enter a valid email" }]}>
            <Input prefix={<MailOutlined />} placeholder="Email" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "Enter your password" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Password" />
          </Form.Item>
          <Form.Item
            name="tenant_slug"
            tooltip="Only needed if your email is registered with more than one company"
          >
            <Input prefix={<ShopOutlined />} placeholder="Company code (optional, e.g. durwankur)" />
          </Form.Item>
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
