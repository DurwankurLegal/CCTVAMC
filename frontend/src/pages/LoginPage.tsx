import { Form, Input, Button, Card, Typography, Alert, ConfigProvider, theme } from "antd";
import { LockOutlined, MailOutlined, ShopOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../store/authSlice";
import type { AppDispatch, RootState } from "../store";

const { Title } = Typography;

export default function LoginPage() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { loading, error } = useSelector((s: RootState) => s.auth);
  const onFinish = async (values: { email: string; password: string; tenant_slug?: string }) => {
    const payload = values.tenant_slug?.trim()
      ? values
      : { email: values.email, password: values.password };
    const result = await dispatch(login(payload));
    if (login.fulfilled.match(result)) {
      navigate("/dashboard");
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0b0f19" }}>
      <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
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
            <div style={{ width: 140, height: 140, margin: "0 auto 16px", overflow: "hidden", display: "flex", justifyContent: "center", alignItems: "center", borderRadius: 8 }}>
              <img src="/logo.png" alt="CCTV AMC Logo" style={{ width: "220%", height: "auto", marginTop: "-25%" }} />
            </div>
            <Title level={3} style={{ margin: 0, fontWeight: 600, color: "#fff" }}>Welcome Back</Title>
            <Typography.Text type="secondary" style={{ fontSize: 16, color: "rgba(255, 255, 255, 0.65)" }}>Login to manage your account</Typography.Text>
          </div>
          {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
          <Form layout="vertical" onFinish={onFinish} size="large">
            <Form.Item name="email" rules={[{ required: true, type: "email", message: "Enter a valid email" }]}>
              <Input prefix={<MailOutlined style={{color: "rgba(255,255,255,0.65)"}}/>} placeholder="Email" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#fff" }} />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: "Enter your password" }]}>
               <Input.Password prefix={<LockOutlined style={{color: "rgba(255,255,255,0.65)"}}/>} placeholder="Password" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#fff" }} />
            </Form.Item>
            <Form.Item
              name="tenant_slug"
              tooltip="Only needed if your email is registered with more than one company"
            >
                <Input prefix={<ShopOutlined style={{color: "rgba(255,255,255,0.65)"}}/>} placeholder="Company code (optional, e.g. durwankur)" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#fff" }} />
              </Form.Item>
            <Form.Item style={{ marginBottom: 16 }}>
              <Button type="primary" htmlType="submit" block loading={loading}>
                Sign In
              </Button>
            </Form.Item>
            <div style={{ textAlign: "center", marginTop: 16 }}>
              <Typography.Text style={{ color: "rgba(255, 255, 255, 0.65)" }}>
                Don't have an account? <Link to="/signup" style={{ color: "var(--primary-color)" }}>Sign up</Link>
              </Typography.Text>
            </div>
          </Form>
        </Card>
      </ConfigProvider>
    </div>
  );
}
