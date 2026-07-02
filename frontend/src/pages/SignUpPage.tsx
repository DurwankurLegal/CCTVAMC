import { Form, Input, Button, Card, Typography, Alert, ConfigProvider, theme } from "antd";
import { LockOutlined, MailOutlined, ShopOutlined, UserOutlined, IdcardOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, Link } from "react-router-dom";
import { signup } from "../store/authSlice";
import type { AppDispatch, RootState } from "../store";

const { Title, Text } = Typography;

export default function SignUpPage() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { loading, error } = useSelector((s: RootState) => s.auth);

  const onFinish = async (values: { company_name: string; company_slug: string; full_name: string; email: string; password: string }) => {
    const result = await dispatch(signup(values));
    if (signup.fulfilled.match(result)) {
      navigate("/dashboard");
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0b0f19", padding: "40px 20px" }}>
      <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
        <Card 
          style={{ 
            width: 450, 
            background: "rgba(22, 28, 45, 0.6)", 
            border: "1px solid var(--glass-border)", 
            borderRadius: 16,
            boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
            backdropFilter: "blur(8px)"
          }}
        >
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <div style={{ width: 100, height: 100, margin: "0 auto 16px", overflow: "hidden", display: "flex", justifyContent: "center", alignItems: "center", borderRadius: 8 }}>
              <img src="/logo.png" alt="CCTV AMC Logo" style={{ width: "220%", height: "auto", marginTop: "-25%" }} />
            </div>
            <Title level={3} style={{ margin: 0, fontWeight: 600, color: "#fff" }}>Create an Account</Title>
            <Text type="secondary" style={{ fontSize: 16, color: "rgba(255, 255, 255, 0.65)" }}>Set up your company workspace</Text>
          </div>
          {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
          <Form layout="vertical" onFinish={onFinish} size="large">
            <Form.Item name="company_name" rules={[{ required: true, message: "Enter your company name" }]}>
              <Input prefix={<ShopOutlined style={{color: "rgba(255,255,255,0.65)"}}/>} placeholder="Company Name (e.g. Acme Corp)" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#fff" }} />
            </Form.Item>
            <Form.Item name="company_slug" rules={[{ required: true, message: "Enter a company code" }]} tooltip="A short, unique code for your company used during login (no spaces)">
              <Input prefix={<IdcardOutlined style={{color: "rgba(255,255,255,0.65)"}}/>} placeholder="Company Code (e.g. acme)" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#fff" }} />
            </Form.Item>
            <Form.Item name="full_name" rules={[{ required: true, message: "Enter your full name" }]}>
              <Input prefix={<UserOutlined style={{color: "rgba(255,255,255,0.65)"}}/>} placeholder="Your Full Name" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#fff" }} />
            </Form.Item>
            <Form.Item name="email" rules={[{ required: true, type: "email", message: "Enter a valid email" }]}>
              <Input prefix={<MailOutlined style={{color: "rgba(255,255,255,0.65)"}}/>} placeholder="Email Address" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#fff" }} />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: "Enter a password" }]}>
               <Input.Password prefix={<LockOutlined style={{color: "rgba(255,255,255,0.65)"}}/>} placeholder="Password" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)", color: "#fff" }} />
            </Form.Item>
            <Form.Item style={{ marginBottom: 16 }}>
              <Button type="primary" htmlType="submit" block loading={loading}>
                Sign Up
              </Button>
            </Form.Item>
            <div style={{ textAlign: "center", marginTop: 16 }}>
              <Text style={{ color: "rgba(255, 255, 255, 0.65)" }}>
                Already have an account? <Link to="/login" style={{ color: "var(--primary-color)" }}>Log in</Link>
              </Text>
            </div>
          </Form>
        </Card>
      </ConfigProvider>
    </div>
  );
}
