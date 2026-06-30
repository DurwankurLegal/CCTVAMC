import { BrowserRouter, Routes, Route, Navigate, Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, Button, theme, ConfigProvider, Modal, Dropdown } from "antd";
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
  BgColorsOutlined,
  CheckCircleOutlined,
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
import apiClient from "./api/client";
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

  const handleLogout = () => {
    Modal.confirm({
      title: "Sign Out",
      content: "Are you sure you want to sign out of the system?",
      okText: "Sign Out",
      cancelText: "Cancel",
      okButtonProps: { danger: true },
      onOk: () => {
        dispatch(logout());
        navigate("/login");
      }
    });
  };

  const currentThemeKey = localStorage.getItem("theme_override") || (tenantConfig?.branding as any)?.theme_key || "dark_professional";

  const themeMenuItems = [
    { key: "light_professional", label: "Light Professional" },
    { key: "dark_professional", label: "Dark Professional" },
    { key: "blue_corporate", label: "Blue Corporate" },
    { key: "green_nature", label: "Green Nature" },
  ];

  const handleThemeChange = async (key: string) => {
    localStorage.setItem("theme_override", key);
    const hasWritePermission = user?.permissions?.includes("tenants:write") || user?.role === "admin" || user?.is_platform_admin;
    if (hasWritePermission && tenantConfig) {
      try {
        await apiClient.patch("/tenant-admin/settings", {
          branding: {
            ...tenantConfig.branding,
            theme_key: key
          }
        });
      } catch (err) {
        console.error("Failed to sync theme to backend settings", err);
      }
    }
    window.location.reload();
  };

  const itemsTheme = themeMenuItems.map(t => ({
    key: t.key,
    label: t.label,
    icon: currentThemeKey === t.key ? <CheckCircleOutlined style={{ color: "#52c41a" }} /> : null
  }));

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

  const themeKey = (tenantConfig?.branding as any)?.theme_key || "dark_professional";
  const isDark = themeKey === "dark_professional" || themeKey === "blue_corporate";

  return (
    <Layout style={{ minHeight: "100vh", background: token.colorBgLayout }}>
      <Sider 
        width={220} 
        collapsible 
        collapsed={collapsed} 
        onCollapse={(v) => setCollapsed(v)}
        style={{ 
          background: isDark ? token.colorBgContainer : "#f8fafc", 
          borderRight: `1px solid ${token.colorBorder}` 
        }}
      >
        <div style={{ 
          height: 64, 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "center", 
          color: token.colorTextHeading, 
          fontWeight: 700, 
          fontSize: collapsed ? 11 : 16, 
          borderBottom: `1px solid ${token.colorBorder}`,
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
          theme={isDark ? "dark" : "light"}
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={["crm", "sales", "rental", "amc", "inventory", "finance", "admin"]}
          items={items}
          onClick={({ key }) => navigate(key)}
          style={{ marginTop: 8, background: "transparent", borderRight: 0 }}
        />
        {isPlatformAdmin && !collapsed && (
          <div style={{ padding: 16 }}>
            <Button 
              block 
              type="dashed" 
              onClick={() => navigate(onPlatform ? "/dashboard" : "/platform")}
              style={{ color: token.colorText, borderColor: token.colorBorder }}
            >
              {onPlatform ? "Tenant App →" : "Platform Console →"}
            </Button>
          </div>
        )}
      </Sider>
      <Layout style={{ background: token.colorBgLayout }}>
        <Header style={{ 
          background: token.colorBgContainer, 
          padding: "0 24px", 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "flex-end", 
          borderBottom: `1px solid ${token.colorBorder}`
        }}>
          {isPlatformAdmin && (
            <Button
              icon={onPlatform ? <DashboardOutlined /> : <CloudServerOutlined />}
              type="text"
              onClick={() => navigate(onPlatform ? "/dashboard" : "/platform")}
              style={{ color: token.colorTextSecondary, marginRight: "auto", display: "flex", alignItems: "center", gap: "6px" }}
            >
              {onPlatform ? "← Back to Tenant App" : "Platform Console →"}
            </Button>
          )}
          {!onPlatform && <NotificationBell />}
          <span style={{ margin: "0 16px", color: token.colorTextSecondary }}>{user?.email}</span>
          <Button
            icon={<KeyOutlined />}
            type="text"
            onClick={() => setTwoFAOpen(true)}
            style={{ color: token.colorTextSecondary, marginRight: 8 }}
          >
            2FA Security
          </Button>
          {!onPlatform && (
            <Dropdown
              menu={{
                items: itemsTheme,
                onClick: ({ key }) => handleThemeChange(key)
              }}
              trigger={["click"]}
            >
              <Button
                icon={<BgColorsOutlined />}
                type="text"
                style={{ color: token.colorTextSecondary, marginRight: 8 }}
              >
                Theme
              </Button>
            </Dropdown>
          )}
          {!onPlatform && <HelpButton />}
          <Button
            icon={<LogoutOutlined />}
            type="text"
            onClick={handleLogout}
            style={{ color: token.colorTextSecondary }}
          >
            Sign Out
          </Button>
        </Header>
        <Content style={{ 
          margin: 24, 
          padding: 24, 
          background: token.colorBgContainer, 
          borderRadius: 12, 
          border: `1px solid ${token.colorBorder}`,
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

export const THEMES = {
  light_professional: {
    name: "Light Professional",
    algorithm: "light",
    token: {
      colorPrimary: "#0958d9",
      colorBgContainer: "#ffffff",
      colorBgLayout: "#f1f5f9",
      colorBorder: "#cbd5e1",
      colorText: "#0f172a",
      colorTextSecondary: "#475569",
      colorTextHeading: "#0f172a",
    }
  },
  dark_professional: {
    name: "Dark Professional",
    algorithm: "dark",
    token: {
      colorPrimary: "#6366f1",
      colorBgContainer: "#161c2d",
      colorBgLayout: "#0b0f19",
      colorBorder: "rgba(255, 255, 255, 0.08)",
      colorText: "#f3f4f6",
      colorTextSecondary: "#9ca3af",
      colorTextHeading: "#ffffff",
    }
  },
  blue_corporate: {
    name: "Blue Corporate",
    algorithm: "dark",
    token: {
      colorPrimary: "#096dd9",
      colorBgContainer: "#111d2c",
      colorBgLayout: "#001529",
      colorBorder: "#1f385c",
      colorText: "#e6f7ff",
      colorTextSecondary: "#69c0ff",
      colorTextHeading: "#ffffff",
    }
  },
  green_nature: {
    name: "Green Nature",
    algorithm: "light",
    token: {
      colorPrimary: "#135200",
      colorBgContainer: "#f6ffed",
      colorBgLayout: "#f4f9f4",
      colorBorder: "#b7eb8f",
      colorText: "#061d02",
      colorTextSecondary: "#2d5c28",
      colorTextHeading: "#061d02",
    }
  }
};

export default function App() {
  const dispatch = useDispatch<AppDispatch>();
  const tenantConfig = useSelector((s: RootState) => s.tenant.config);

  useEffect(() => {
    dispatch(fetchTenantConfig(window.location.host));
  }, [dispatch]);

  const localOverride = localStorage.getItem("theme_override");
  const themeKey = localOverride || (tenantConfig?.branding as any)?.theme_key || "dark_professional";
  const selectedTheme = THEMES[themeKey as keyof typeof THEMES] || THEMES.dark_professional;
  const primaryColor = tenantConfig?.branding?.primary_color || selectedTheme.token.colorPrimary;
  const isDark = selectedTheme.algorithm === "dark";

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: primaryColor,
          colorBgContainer: selectedTheme.token.colorBgContainer,
          colorBgLayout: selectedTheme.token.colorBgLayout,
          colorBorder: selectedTheme.token.colorBorder,
          colorText: selectedTheme.token.colorText,
          colorTextSecondary: selectedTheme.token.colorTextSecondary,
          colorTextHeading: selectedTheme.token.colorTextHeading,
        },
        components: {
          Table: {
            headerBg: isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.02)",
            headerColor: selectedTheme.token.colorTextHeading,
          }
        }
      }}
    >
      <style>{`
        :root {
          --dashboard-bg: ${selectedTheme.token.colorBgLayout};
          --glass-bg: ${isDark ? "rgba(22, 28, 45, 0.6)" : "rgba(255, 255, 255, 0.85)"};
          --glass-border: ${selectedTheme.token.colorBorder};
          --text-primary: ${selectedTheme.token.colorText};
          --text-secondary: ${selectedTheme.token.colorTextSecondary};
          --glass-shadow: ${isDark ? "0 8px 32px 0 rgba(0, 0, 0, 0.25)" : "0 8px 24px 0 rgba(148, 163, 184, 0.08), 0 1px 3px 0 rgba(148, 163, 184, 0.04)"};
        }
        body {
          background-color: var(--dashboard-bg) !important;
          color: var(--text-primary) !important;
          ${!isDark ? `background: radial-gradient(at 0% 0%, #ffffff 0, #f1f5f9 100%) !important;` : ""}
        }
        ${!isDark ? `
        .ant-layout-sider {
          background: #f8fafc !important;
          border-right: 1px solid #cbd5e1 !important;
        }
        .ant-menu {
          background: transparent !important;
        }
        .ant-menu-item {
          color: #334155 !important;
        }
        .ant-menu-submenu-title {
          color: #334155 !important;
        }
        .ant-menu-item-selected {
          background-color: rgba(9, 88, 217, 0.08) !important;
          color: ${selectedTheme.token.colorPrimary} !important;
          font-weight: 600;
        }
        .ant-menu-item-selected .ant-menu-item-icon {
          color: ${selectedTheme.token.colorPrimary} !important;
        }
        .ant-tag {
          border-radius: 6px !important;
          padding: 2px 8px !important;
          font-weight: 500 !important;
        }
        .ant-card-title {
          font-weight: 700 !important;
          letter-spacing: -0.3px;
        }
        ` : ""}
      `}</style>
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
