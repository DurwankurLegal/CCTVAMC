import { BrowserRouter, Routes, Route, Navigate, Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Button, theme } from "antd";
import {
  DashboardOutlined,
  TeamOutlined,
  FileTextOutlined,
  ToolOutlined,
  LogoutOutlined,
  AuditOutlined,
  DollarOutlined,
  ShoppingCartOutlined,
} from "@ant-design/icons";
import { useDispatch } from "react-redux";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import CustomersPage from "./pages/CustomersPage";
import AMCPage from "./pages/AMCPage";
import ServiceTicketsPage from "./pages/ServiceTicketsPage";
import LeadsPage from "./pages/LeadsPage";
import InvoicesPage from "./pages/InvoicesPage";
import PaymentsPage from "./pages/PaymentsPage";
import { logout } from "./store/authSlice";
import type { AppDispatch } from "./store";

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: "/dashboard",        icon: <DashboardOutlined />,    label: "Dashboard" },
  { key: "/customers",        icon: <TeamOutlined />,         label: "Customers" },
  { key: "/amc",              icon: <FileTextOutlined />,     label: "AMC Contracts" },
  { key: "/tickets",          icon: <ToolOutlined />,         label: "Service Tickets" },
  { key: "/leads",            icon: <AuditOutlined />,        label: "Leads" },
  { key: "/invoices",         icon: <ShoppingCartOutlined />, label: "Invoices" },
  { key: "/payments",         icon: <DollarOutlined />,       label: "Payments" },
];

function ComingSoon({ title }: { title: string }) {
  return (
    <div style={{ textAlign: "center", padding: "80px 0", color: "#999" }}>
      <h2>{title}</h2>
      <p>This section is coming soon.</p>
    </div>
  );
}

function ProtectedLayout() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const isLoggedIn = !!localStorage.getItem("access_token");

  if (!isLoggedIn) return <Navigate to="/login" replace />;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={220} theme="dark">
        <div style={{ height: 64, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 16, borderBottom: "1px solid #1d2b3a" }}>
          CCTV AMC
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ marginTop: 8 }}
        />
      </Sider>
      <Layout>
        <Header style={{ background: token.colorBgContainer, padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "flex-end", borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
          <Button
            icon={<LogoutOutlined />}
            type="text"
            onClick={() => { dispatch(logout()); navigate("/login"); }}
          >
            Sign Out
          </Button>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: token.colorBgContainer, borderRadius: token.borderRadius, minHeight: 360 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/amc" element={<AMCPage />} />
          <Route path="/tickets" element={<ServiceTicketsPage />} />
          <Route path="/leads" element={<LeadsPage />} />
          <Route path="/invoices" element={<InvoicesPage />} />
          <Route path="/payments" element={<PaymentsPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

