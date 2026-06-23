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
  CloudServerOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import CustomersPage from "./pages/CustomersPage";
import AMCPage from "./pages/AMCPage";
import ServiceTicketsPage from "./pages/ServiceTicketsPage";
import LeadsPage from "./pages/LeadsPage";
import InvoicesPage from "./pages/InvoicesPage";
import PaymentsPage from "./pages/PaymentsPage";
import PlatformDashboardPage from "./pages/platform/PlatformDashboardPage";
import TenantsPage from "./pages/platform/TenantsPage";
import TenantDetailPage from "./pages/platform/TenantDetailPage";
import { logout, fetchMe } from "./store/authSlice";
import type { AppDispatch, RootState } from "./store";

const { Header, Sider, Content } = Layout;

const tenantMenu = [
  { key: "/dashboard",        icon: <DashboardOutlined />,    label: "Dashboard" },
  { key: "/customers",        icon: <TeamOutlined />,         label: "Customers" },
  { key: "/amc",              icon: <FileTextOutlined />,     label: "AMC Contracts" },
  { key: "/tickets",          icon: <ToolOutlined />,         label: "Service Tickets" },
  { key: "/leads",            icon: <AuditOutlined />,        label: "Leads" },
  { key: "/invoices",         icon: <ShoppingCartOutlined />, label: "Invoices" },
  { key: "/payments",         icon: <DollarOutlined />,       label: "Payments" },
];

const platformMenu = [
  { key: "/platform",         icon: <CloudServerOutlined />,  label: "Platform Overview" },
  { key: "/platform/tenants", icon: <ApartmentOutlined />,    label: "Tenants" },
];

function ProtectedLayout() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const user = useSelector((s: RootState) => s.auth.user);
  const isLoggedIn = !!localStorage.getItem("access_token");

  // Refresh identity once if we have a token but no resolved user (e.g. after reload).
  useEffect(() => {
    if (isLoggedIn && !user) dispatch(fetchMe());
  }, [isLoggedIn, user, dispatch]);

  if (!isLoggedIn) return <Navigate to="/login" replace />;

  const isPlatformAdmin = !!user?.is_platform_admin;
  const onPlatform = location.pathname.startsWith("/platform");
  const items = isPlatformAdmin && onPlatform ? platformMenu : tenantMenu;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={220} theme="dark">
        <div style={{ height: 64, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 16, borderBottom: "1px solid #1d2b3a" }}>
          {onPlatform ? "Platform Admin" : "CCTV AMC"}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={items}
          onClick={({ key }) => navigate(key)}
          style={{ marginTop: 8 }}
        />
        {isPlatformAdmin && (
          <div style={{ padding: 16 }}>
            <Button block ghost onClick={() => navigate(onPlatform ? "/dashboard" : "/platform")}>
              {onPlatform ? "Tenant App →" : "Platform Console →"}
            </Button>
          </div>
        )}
      </Sider>
      <Layout>
        <Header style={{ background: token.colorBgContainer, padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "flex-end", borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
          <span style={{ marginRight: 16, color: token.colorTextSecondary }}>{user?.email}</span>
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

function PlatformGuard() {
  const user = useSelector((s: RootState) => s.auth.user);
  const isLoggedIn = !!localStorage.getItem("access_token");
  // While identity is still resolving after a reload, don't bounce the user out.
  if (isLoggedIn && user === null) return null;
  if (!user?.is_platform_admin) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
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
          <Route element={<PlatformGuard />}>
            <Route path="/platform" element={<PlatformDashboardPage />} />
            <Route path="/platform/tenants" element={<TenantsPage />} />
            <Route path="/platform/tenants/:id" element={<TenantDetailPage />} />
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
