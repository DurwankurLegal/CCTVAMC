import { BrowserRouter, Routes, Route, Navigate, Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Button, theme, ConfigProvider } from "antd";
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
  UsergroupAddOutlined,
  ShopOutlined,
  DatabaseOutlined,
  SolutionOutlined,
  BuildOutlined,
  CarOutlined,
  BarChartOutlined,
  BellOutlined,
  VideoCameraOutlined,
  BarcodeOutlined,
  AppstoreAddOutlined,
  FileDoneOutlined,
  KeyOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import NotificationBell from "./components/NotificationBell";
import { useEffect, useState, type ReactNode } from "react";
import { useDispatch, useSelector } from "react-redux";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import CustomersPage from "./pages/CustomersPage";
import AMCPage from "./pages/AMCPage";
import ServiceTicketsPage from "./pages/ServiceTicketsPage";
import LeadsPage from "./pages/LeadsPage";
import InvoicesPage from "./pages/InvoicesPage";
import PaymentsPage from "./pages/PaymentsPage";
import UsersPage from "./pages/UsersPage";
import VendorsPage from "./pages/VendorsPage";
import InventoryPage from "./pages/InventoryPage";
import QuotationsPage from "./pages/QuotationsPage";
import InstallationsPage from "./pages/InstallationsPage";
import EngineerVisitsPage from "./pages/EngineerVisitsPage";
import ReportsPage from "./pages/ReportsPage";
import NotificationsPage from "./pages/NotificationsPage";
import AssetsPage from "./pages/AssetsPage";
import PlatformDashboardPage from "./pages/platform/PlatformDashboardPage";
import TenantsPage from "./pages/platform/TenantsPage";
import TenantDetailPage from "./pages/platform/TenantDetailPage";
import PortalLoginPage from "./pages/portal/PortalLoginPage";
import PortalLayout from "./pages/portal/PortalLayout";
import PortalDashboardPage from "./pages/portal/PortalDashboardPage";
import PortalTicketsPage from "./pages/portal/PortalTicketsPage";
import PortalTicketDetailPage from "./pages/portal/PortalTicketDetailPage";
import PortalCoveragePage from "./pages/portal/PortalCoveragePage";
import PortalInvoicesPage from "./pages/portal/PortalInvoicesPage";
import ForceChangePassword from "./pages/ForceChangePassword";
import { logout, fetchMe } from "./store/authSlice";
import TwoFAModal from "./components/TwoFAModal";
import type { AppDispatch, RootState } from "./store";
import { filterTenantMenu, hasPerm } from "./utils/menu";
import { fetchTenantConfig } from "./store/tenantSlice";
import ModuleGuard from "./components/ModuleGuard";
import TenantSettingsPage from "./pages/TenantSettingsPage";
import { CashReconciliationPage } from "./pages/CashReconciliationPage";
import ProductsPage from "./pages/ProductsPage";
import SalesOrdersPage from "./pages/SalesOrdersPage";
import RentalUnitsPage from "./pages/RentalUnitsPage";
import RentalContractsPage from "./pages/RentalContractsPage";
import HelpCenter from "./pages/help/HelpCenter";
import HelpButton from "./components/HelpButton";

const { Header, Sider, Content } = Layout;

// `perm` gates menu visibility against the user's effective permissions from
// /auth/me. Items without a perm are always shown (e.g. Dashboard).
const tenantMenu = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
  {
    key: "crm",
    icon: <TeamOutlined />,
    label: "CRM (Core)",
    children: [
      { key: "/leads", label: "Leads", perm: "leads:read" },
      { key: "/customers", label: "Customers", perm: "customers:read" },
    ],
  },
  {
    key: "sales",
    icon: <ShoppingCartOutlined />,
    label: "Sales (Optional)",
    module: "sales",
    children: [
      { key: "/quotations", label: "Quotations", perm: "quotations:read" },
      { key: "/sales-orders", label: "Sales Orders", perm: "sales_orders:read" },
      { key: "/invoices", label: "Invoices", perm: "invoices:read" },
      { key: "/payments", label: "Payments", perm: "payments:read" },
    ],
  },
  {
    key: "rental",
    icon: <AppstoreAddOutlined />,
    label: "Rental (Optional)",
    module: "rental",
    children: [
      { key: "/products", label: "Product Catalog", perm: "products:read" },
      { key: "/rentals/units", label: "Rental Assets", perm: "rentals:read" },
      { key: "/rentals/contracts", label: "Rental Contracts", perm: "rentals:read" },
    ],
  },
  {
    key: "amc",
    icon: <FileTextOutlined />,
    label: "AMC (Optional)",
    module: "amc",
    children: [
      { key: "/amc", label: "AMC Contracts", perm: "amc:read" },
      { key: "/tickets", label: "Service Tickets", perm: "service_tickets:read" },
      { key: "/visits", label: "Engineer Visits", perm: "engineer_visits:read" },
      { key: "/installations", label: "Installations", perm: "installations:read" },
    ],
  },
  {
    key: "inventory",
    icon: <DatabaseOutlined />,
    label: "Inventory (Optional)",
    module: "inventory",
    children: [
      { key: "/inventory", label: "Inventory", perm: "inventory:read" },
      { key: "/assets", label: "Assets", perm: "assets:read", module: "assets" },
      { key: "/vendors", label: "Vendors", perm: "vendors:read" },
    ],
  },
  {
    key: "finance",
    icon: <DollarOutlined />,
    label: "Finance (Optional)",
    children: [
      { key: "/reconciliation", label: "Cash Collection", perm: "payments:read" },
    ],
  },
  { key: "/reports", icon: <BarChartOutlined />, label: "Reports (Core)", perm: "reports:read" },
  { key: "/notifications", icon: <BellOutlined />, label: "Notifications (Core)", perm: "notifications:write" },
  {
    key: "admin",
    icon: <SettingOutlined />,
    label: "Administration (Core)",
    children: [
      { key: "/users", label: "Users & Roles", perm: "users:write" },
      { key: "/settings", label: "Tenant Settings", perm: "tenants:write" },
    ],
  },
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
  const tenantConfig = useSelector((s: RootState) => s.tenant.config);
  const isLoggedIn = !!localStorage.getItem("access_token");
  
  const [collapsed, setCollapsed] = useState(false);
  const [twoFAOpen, setTwoFAOpen] = useState(false);

  // Refresh identity once if we have a token but no resolved user (e.g. after reload).
  useEffect(() => {
    if (isLoggedIn && !user) dispatch(fetchMe());
  }, [isLoggedIn, user, dispatch]);

  if (!isLoggedIn) return <Navigate to="/login" replace />;

  // A provisioned admin on a temp password must reset it before using the app.
  if (user?.must_change_password && location.pathname !== "/force-password-change") {
    return <Navigate to="/force-password-change" replace />;
  }

  const isPlatformAdmin = !!user?.is_platform_admin;
  const onPlatform = location.pathname.startsWith("/platform");
  const items = isPlatformAdmin && onPlatform ? platformMenu : filterTenantMenu(tenantMenu, user);

  return (
    <Layout style={{ minHeight: "100vh", background: "#0b0f19" }}>
      <Sider 
        width={220} 
        collapsible 
        collapsed={collapsed} 
        onCollapse={(v) => setCollapsed(v)}
        style={{ 
          background: "rgba(11, 15, 25, 0.9)", 
          borderRight: "1px solid rgba(255, 255, 255, 0.08)" 
        }}
      >
        <div style={{ 
          height: 64, 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "center", 
          color: "#fff", 
          fontWeight: 700, 
          fontSize: collapsed ? 11 : 16, 
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          transition: "font-size 0.2s"
        }}>
          {collapsed ? (
            onPlatform ? "PLAT" : "CCTV"
          ) : onPlatform ? (
            "Platform Admin"
          ) : tenantConfig?.branding?.logo_url ? (
            <img src={tenantConfig.branding.logo_url} style={{ maxHeight: 32, maxWidth: 180, objectFit: "contain" }} alt={tenantConfig.name} />
          ) : (
            tenantConfig?.name || "CCTV AMC"
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={["crm", "sales", "rental", "amc", "inventory", "finance", "admin"]}
          items={items}
          onClick={({ key }) => navigate(key)}
          style={{ marginTop: 8, background: "transparent" }}
        />
        {isPlatformAdmin && !collapsed && (
          <div style={{ padding: 16 }}>
            <Button block ghost onClick={() => navigate(onPlatform ? "/dashboard" : "/platform")}>
              {onPlatform ? "Tenant App →" : "Platform Console →"}
            </Button>
          </div>
        )}
      </Sider>
      <Layout style={{ background: "#0b0f19" }}>
        <Header style={{ 
          background: "rgba(22, 28, 45, 0.5)", 
          padding: "0 24px", 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "flex-end", 
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          backdropFilter: "blur(8px)"
        }}>
          {!onPlatform && <NotificationBell />}
          <span style={{ margin: "0 16px", color: "#9ca3af" }}>{user?.email}</span>
          <Button
            icon={<KeyOutlined />}
            type="text"
            onClick={() => setTwoFAOpen(true)}
            style={{ color: "#9ca3af", marginRight: 8 }}
          >
            2FA Security
          </Button>
          {!onPlatform && <HelpButton />}
          <Button
            icon={<LogoutOutlined />}
            type="text"
            onClick={() => { dispatch(logout()); navigate("/login"); }}
            style={{ color: "#9ca3af" }}
          >
            Sign Out
          </Button>
        </Header>
        <Content style={{ 
          margin: 24, 
          padding: 24, 
          background: "rgba(22, 28, 45, 0.3)", 
          borderRadius: 12, 
          border: "1px solid rgba(255, 255, 255, 0.05)",
          minHeight: 360 
        }}>
          <Outlet />
        </Content>
        <TwoFAModal
          open={twoFAOpen}
          totpEnabled={!!user?.totp_enabled}
          onClose={() => setTwoFAOpen(false)}
          onSuccess={() => dispatch(fetchMe())}
        />
      </Layout>
    </Layout>
  );
}

// Route-level RBAC guard: blocks direct-URL access to a page the user's role
// has no permission for (defense-in-depth alongside the backend's 403s).
function RequirePerm({ perm, children }: { perm: string; children: ReactNode }) {
  const user = useSelector((s: RootState) => s.auth.user);
  const isLoggedIn = !!localStorage.getItem("access_token");
  if (isLoggedIn && user === null) return null; // identity still resolving after reload
  if (!hasPerm(user, perm)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
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
  const dispatch = useDispatch<AppDispatch>();
  const tenantConfig = useSelector((s: RootState) => s.tenant.config);

  useEffect(() => {
    dispatch(fetchTenantConfig(window.location.host));
  }, [dispatch]);

  const primaryColor = tenantConfig?.branding?.primary_color || "#1677ff";

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: primaryColor,
          colorBgContainer: "#161c2d",
          colorBorder: "rgba(255, 255, 255, 0.08)",
          colorText: "#f3f4f6",
          colorTextSecondary: "#9ca3af",
          colorTextHeading: "#ffffff",
        }
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/force-password-change" element={<ForceChangePassword />} />

          {/* Customer self-service portal — separate identity/token from staff app */}
          <Route path="/portal/login" element={<PortalLoginPage />} />
          <Route path="/portal" element={<PortalLayout />}>
            <Route index element={<PortalDashboardPage />} />
            <Route path="tickets" element={<PortalTicketsPage />} />
            <Route path="tickets/:id" element={<PortalTicketDetailPage />} />
            <Route path="coverage" element={<PortalCoveragePage />} />
            <Route path="invoices" element={<PortalInvoicesPage />} />
          </Route>

          <Route element={<ProtectedLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/customers" element={<RequirePerm perm="customers:read"><CustomersPage /></RequirePerm>} />
            <Route path="/amc" element={<RequirePerm perm="amc:read"><ModuleGuard moduleCode="amc"><AMCPage /></ModuleGuard></RequirePerm>} />
            <Route path="/tickets" element={<RequirePerm perm="service_tickets:read"><ModuleGuard moduleCode="amc"><ServiceTicketsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/leads" element={<RequirePerm perm="leads:read"><LeadsPage /></RequirePerm>} />
            <Route path="/invoices" element={<RequirePerm perm="invoices:read"><InvoicesPage /></RequirePerm>} />
            <Route path="/payments" element={<RequirePerm perm="payments:read"><PaymentsPage /></RequirePerm>} />
            <Route path="/reconciliation" element={<RequirePerm perm="payments:read"><CashReconciliationPage /></RequirePerm>} />
            <Route path="/users" element={<RequirePerm perm="users:write"><UsersPage /></RequirePerm>} />
            <Route path="/vendors" element={<RequirePerm perm="vendors:read"><ModuleGuard moduleCode="inventory"><VendorsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/inventory" element={<RequirePerm perm="inventory:read"><ModuleGuard moduleCode="inventory"><InventoryPage /></ModuleGuard></RequirePerm>} />
            <Route path="/products" element={<RequirePerm perm="products:read"><ModuleGuard moduleCode="rental"><ProductsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/sales-orders" element={<RequirePerm perm="sales_orders:read"><ModuleGuard moduleCode="sales"><SalesOrdersPage /></ModuleGuard></RequirePerm>} />
            <Route path="/rentals/units" element={<RequirePerm perm="rentals:read"><ModuleGuard moduleCode="rental"><RentalUnitsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/rentals/contracts" element={<RequirePerm perm="rentals:read"><ModuleGuard moduleCode="rental"><RentalContractsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/quotations" element={<RequirePerm perm="quotations:read"><ModuleGuard moduleCode="sales"><QuotationsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/installations" element={<RequirePerm perm="installations:read"><ModuleGuard moduleCode="amc"><InstallationsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/visits" element={<RequirePerm perm="engineer_visits:read"><ModuleGuard moduleCode="amc"><EngineerVisitsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/assets" element={<RequirePerm perm="assets:read"><ModuleGuard moduleCode="assets"><AssetsPage /></ModuleGuard></RequirePerm>} />
            <Route path="/reports" element={<RequirePerm perm="reports:read"><ReportsPage /></RequirePerm>} />
            <Route path="/notifications" element={<RequirePerm perm="notifications:write"><NotificationsPage /></RequirePerm>} />
            <Route path="/settings" element={<RequirePerm perm="tenants:write"><TenantSettingsPage /></RequirePerm>} />
            <Route element={<PlatformGuard />}>
              <Route path="/platform" element={<PlatformDashboardPage />} />
              <Route path="/platform/tenants" element={<TenantsPage />} />
              <Route path="/platform/tenants/:id" element={<TenantDetailPage />} />
            </Route>
            <Route path="/help" element={<Navigate to="/help/introduction" replace />} />
            <Route path="/help/:articleSlug" element={<HelpCenter />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
