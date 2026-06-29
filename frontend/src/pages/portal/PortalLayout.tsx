import { Layout, Menu, Button, Grid, Modal } from "antd";
import {
  DashboardOutlined, ToolOutlined, SafetyCertificateOutlined,
  FileTextOutlined, LogoutOutlined,
} from "@ant-design/icons";
import { Outlet, Navigate, useNavigate, useLocation } from "react-router-dom";

const { Header, Content } = Layout;
const { useBreakpoint } = Grid;

const items = [
  { key: "/portal", icon: <DashboardOutlined />, label: "Dashboard" },
  { key: "/portal/tickets", icon: <ToolOutlined />, label: "Service Tickets" },
  { key: "/portal/coverage", icon: <SafetyCertificateOutlined />, label: "AMC & Assets" },
  { key: "/portal/invoices", icon: <FileTextOutlined />, label: "Invoices" },
];

export default function PortalLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const screens = useBreakpoint();
  const token = localStorage.getItem("portal_token");
  if (!token) return <Navigate to="/portal/login" replace />;

  const user = (() => {
    try { return JSON.parse(localStorage.getItem("portal_user") || "null"); } catch { return null; }
  })();

  const logout = () => {
    Modal.confirm({
      title: "Sign Out",
      content: "Are you sure you want to sign out of the Customer Portal?",
      okText: "Sign Out",
      cancelText: "Cancel",
      okButtonProps: { danger: true },
      onOk: () => {
        localStorage.removeItem("portal_token");
        localStorage.removeItem("portal_refresh");
        localStorage.removeItem("portal_user");
        navigate("/portal/login");
      }
    });
  };

  // Match the most specific menu key (so /portal/tickets/:id keeps Tickets active).
  const selected = [...items].map(i => i.key).filter(k => location.pathname.startsWith(k))
    .sort((a, b) => b.length - a.length)[0] || "/portal";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header style={{ display: "flex", alignItems: "center", padding: screens.xs ? "0 12px" : "0 24px", background: "#001529" }}>
        <div style={{ color: "#fff", fontWeight: 700, fontSize: 16, marginRight: 24, whiteSpace: "nowrap" }}>
          {screens.xs ? "Portal" : "Customer Portal"}
        </div>
        <Menu theme="dark" mode="horizontal" selectedKeys={[selected]} items={items}
          onClick={({ key }) => navigate(key)} style={{ flex: 1, minWidth: 0 }} />
        <span style={{ color: "rgba(255,255,255,0.65)", marginRight: 12 }}>
          {!screens.xs && (user?.customer_name || user?.email)}
        </span>
        <Button type="text" icon={<LogoutOutlined />} style={{ color: "#fff" }} onClick={logout}>
          {!screens.xs && "Sign Out"}
        </Button>
      </Header>
      <Content style={{ margin: screens.xs ? 12 : 24, padding: screens.xs ? 16 : 24, background: "#fff", borderRadius: 8 }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
