import { useEffect, useState, useCallback } from "react";
import {
  Tabs, Card, Form, Input, Button, Table, Tag, Space, Typography, message,
  ConfigProvider, theme, ColorPicker, Progress, Descriptions, Spin, List, Collapse,
  Switch, Tooltip, Modal, Alert, Select, Row, Col, Divider
} from "antd";
import {
  SettingOutlined, UserOutlined, FileTextOutlined, AppstoreOutlined,
  MailOutlined, SafetyCertificateOutlined, TeamOutlined, GlobalOutlined,
  EditOutlined, PlusOutlined, SafetyOutlined, BgColorsOutlined,
  SolutionOutlined, CreditCardOutlined, BuildOutlined, BankOutlined
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";
import type { RootState } from "../store";
import apiClient from "../api/client";
import { CompanySettingsTab } from "./CompanySettingsTab";
import { RichTextEditor } from "../components/RichTextEditor";
import { BrandedFileUpload } from "../components/BrandedFileUpload";
import { THEMES as THEMES_CONFIG } from "../App";

const { Title, Text } = Typography;
const { Option } = Select;

const ROLES = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "coordinator", label: "Service Coordinator" },
  { value: "accounts", label: "Accounts" },
  { value: "technician", label: "Technician" },
  { value: "viewer", label: "Viewer" },
];
const roleColor: Record<string, string> = {
  admin: "red", manager: "volcano", coordinator: "blue", accounts: "green",
  technician: "geekblue", viewer: "default",
};

const PLAN_CAPACITIES = {
  starter: { max_users: 5, max_sites: 25, max_technicians: 3 },
  growth: { max_users: 25, max_sites: 200, max_technicians: 15 },
  enterprise: { max_users: "Unlimited", max_sites: "Unlimited", max_technicians: "Unlimited" }
};

interface User {
  id: string; full_name: string; email: string; role: string; is_active: boolean;
}

interface Invoice {
  id: string; invoice_number: string; plan: string; amount: number; status: string;
}

export default function TenantSettingsPage() {
  const navigate = useNavigate();
  const currentUser = useSelector((s: RootState) => s.auth.user);

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tenant, setTenant] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);

  const [roleInfo, setRoleInfo] = useState<Record<string, string[]>>({});
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [userForm] = Form.useForm();
  const [savingUser, setSavingUser] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [settingsRes, usageRes, invoicesRes] = await Promise.all([
        apiClient.get("/tenant-admin/settings"),
        apiClient.get("/tenant-admin/usage"),
        apiClient.get("/tenant-admin/subscription-invoices")
      ]);
      setTenant(settingsRes.data);
      setUsage(usageRes.data);
      setInvoices(invoicesRes.data);
      const emailTemplates = settingsRes.data.email_templates || {};
      const settingsObj = settingsRes.data.settings || {};
      form.setFieldsValue({
        ...settingsRes.data,
        gstin: settingsRes.data.gstin || settingsObj.tax_information?.gst_number || "",
        registered_address: settingsRes.data.registered_address || "",
        billing_contact_name: settingsRes.data.billing_contact_name || "",
        billing_contact_email: settingsRes.data.billing_contact_email || "",
        custom_domain: settingsRes.data.custom_domain || "",
        custom_email_sender: settingsRes.data.custom_email_sender || "",
        primary_color: settingsRes.data.branding?.primary_color || "#1677ff",
        logo_url: settingsRes.data.branding?.logo_url || "",
        theme_key: settingsRes.data.branding?.theme_key || "dark_professional",
        // Address Details
        address_line1: settingsObj.company_address?.address_line1 || "",
        address_line2: settingsObj.company_address?.address_line2 || "",
        city: settingsObj.company_address?.city || "",
        state: settingsObj.company_address?.state || "",
        pin_code: settingsObj.company_address?.pin_code || "",
        country: settingsObj.company_address?.country || "",
        // Tax Information
        pan_number: settingsObj.tax_information?.pan_number || "",
        // Contact Information
        contact_person: settingsObj.contact_information?.contact_person || "",
        mobile_number: settingsObj.contact_information?.mobile_number || "",
        telephone_number: settingsObj.contact_information?.telephone_number || "",
        email_address: settingsObj.contact_information?.email_address || "",
        website: settingsObj.contact_information?.website || "",
        // Bank Details
        bank_name: settingsObj.bank_details?.bank_name || "",
        branch_name: settingsObj.bank_details?.branch_name || "",
        account_holder_name: settingsObj.bank_details?.account_holder_name || "",
        account_number: settingsObj.bank_details?.account_number || "",
        ifsc_code: settingsObj.bank_details?.ifsc_code || "",
        upi_id: settingsObj.bank_details?.upi_id || "",
        // Signatory Details
        signatory_name: settingsObj.authorized_signatory?.name || "",
        signatory_designation: settingsObj.authorized_signatory?.designation || "",
        signature_url: settingsObj.authorized_signatory?.signature_url || "",
        seal_url: settingsObj.authorized_signatory?.seal_url || "",
        // Default Customer
        default_customer_name: settingsObj.default_customer_info?.name || "",
        default_customer_address: settingsObj.default_customer_info?.address || "",
        default_customer_gstin: settingsObj.default_customer_info?.gstin || "",
        default_customer_contact_person: settingsObj.default_customer_info?.contact_person || "",
        default_customer_mobile: settingsObj.default_customer_info?.mobile_number || "",
        default_customer_email: settingsObj.default_customer_info?.email_address || "",
        // Quotation Settings
        default_terms: settingsObj.quotation_settings?.default_terms || "",
        // Email templates
        amc_expiry_subject: emailTemplates.amc_expiry?.subject || "Your AMC {{contract_number}} expires in {{days}} days",
        amc_expiry_body: emailTemplates.amc_expiry?.body || "Dear customer,\n\nYour AMC contract {{contract_number}} is due to expire on {{end_date}} ({{days}} days from now). Please contact us to renew and avoid any interruption in service.\n\nThank you.",
        payment_due_subject: emailTemplates.payment_due?.subject || "Invoice {{invoice_number}} — payment due",
        payment_due_body: emailTemplates.payment_due?.body || "Dear customer,\n\nInvoice {{invoice_number}} for an amount of {{amount_due}} is due on {{due_date}}. Kindly arrange the payment at your earliest convenience.\n\nThank you.",
        quote_sent_subject: emailTemplates.quote_sent?.subject || "Quotation {{quotation_number}}",
        quote_sent_body: emailTemplates.quote_sent?.body || "Please find your quotation {{quotation_number}} for {{total_amount}}. It is valid until {{valid_until}}."
      });
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load settings data");
    } finally {
      setLoading(false);
    }
  }, [form]);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const { data } = await apiClient.get("/users", { params: { limit: 200 } });
      setUsers(data);
    } catch (e: any) {
      message.error("Failed to load tenant users");
    } finally {
      setUsersLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    loadUsers();
  }, [loadData, loadUsers]);

  useEffect(() => {
    apiClient.get("/users/roles")
      .then(({ data }) => setRoleInfo(Object.fromEntries(data.roles.map((r: any) => [r.key, r.permissions]))))
      .catch(() => { /* catalog is advisory */ });
  }, []);

  const openAddUser = () => {
    setEditingUser(null);
    userForm.resetFields();
    userForm.setFieldsValue({ role: "viewer" });
    setUserModalOpen(true);
  };

  const openEditUser = (user: User) => {
    setEditingUser(user);
    userForm.setFieldsValue(user);
    setUserModalOpen(true);
  };

  const handleSaveUser = async () => {
    const values = await userForm.validateFields();
    setSavingUser(true);
    try {
      if (editingUser) {
        const { password, email, ...changes } = values;
        await apiClient.patch(`/users/${editingUser.id}`, changes);
        message.success("Staff profile updated");
      } else {
        await apiClient.post("/users", values);
        message.success("New staff onboarded");
      }
      setUserModalOpen(false);
      loadUsers();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to save user");
    } finally {
      setSavingUser(false);
    }
  };

  const toggleUserActive = async (user: User, active: boolean) => {
    try {
      await apiClient.patch(`/users/${user.id}`, { is_active: active });
      message.success(active ? "User activated" : "User deactivated");
      loadUsers();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Update failed");
    }
  };

  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      const payload = {
        name: values.name,
        gstin: values.gstin,
        registered_address: values.registered_address,
        invoice_prefix: values.invoice_prefix,
        billing_contact_name: values.billing_contact_name,
        billing_contact_email: values.billing_contact_email,
        custom_domain: values.custom_domain || null,
        custom_email_sender: values.custom_email_sender || null,
        branding: {
          primary_color: typeof values.primary_color === 'string' ? values.primary_color : values.primary_color.toHexString(),
          logo_url: values.logo_url || null,
          theme_key: values.theme_key || "dark_professional"
        },
        settings: {
          ...(tenant?.settings || {}),
          company_address: {
            address_line1: values.address_line1 || "",
            address_line2: values.address_line2 || "",
            city: values.city || "",
            state: values.state || "",
            pin_code: values.pin_code || "",
            country: values.country || ""
          },
          tax_information: {
            gst_number: values.gstin || "",
            pan_number: values.pan_number || ""
          },
          contact_information: {
            contact_person: values.contact_person || "",
            mobile_number: values.mobile_number || "",
            telephone_number: values.telephone_number || "",
            email_address: values.email_address || "",
            website: values.website || ""
          },
          bank_details: {
            bank_name: values.bank_name || "",
            branch_name: values.branch_name || "",
            account_holder_name: values.account_holder_name || "",
            account_number: values.account_number || "",
            ifsc_code: values.ifsc_code || "",
            upi_id: values.upi_id || ""
          },
          authorized_signatory: {
            name: values.signatory_name || "",
            designation: values.signatory_designation || "",
            signature_url: values.signature_url || "",
            seal_url: values.seal_url || ""
          },
          default_customer_info: {
            name: values.default_customer_name || "",
            address: values.default_customer_address || "",
            gstin: values.default_customer_gstin || "",
            contact_person: values.default_customer_contact_person || "",
            mobile_number: values.default_customer_mobile || "",
            email_address: values.default_customer_email || ""
          },
          quotation_settings: {
            default_terms: values.default_terms || ""
          }
        },
        email_templates: {
          amc_expiry: {
            subject: values.amc_expiry_subject || "",
            body: values.amc_expiry_body || ""
          },
          payment_due: {
            subject: values.payment_due_subject || "",
            body: values.payment_due_body || ""
          },
          quote_sent: {
            subject: values.quote_sent_subject || "",
            body: values.quote_sent_body || ""
          }
        }
      };
      await apiClient.patch("/tenant-admin/settings", payload);
      message.success("Tenant settings updated successfully");
      localStorage.removeItem("theme_override"); // Clear local override so global theme applies
      loadData();
      // Reload page to apply new branding dynamically
      setTimeout(() => {
        window.location.reload();
      }, 800);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const invoiceColumns = [
    { title: "Invoice Number", dataIndex: "invoice_number", key: "invoice_number" },
    { title: "Plan Plan", dataIndex: "plan", key: "plan", render: (v: string) => <Tag color="blue">{v.toUpperCase()}</Tag> },
    { title: "Amount", dataIndex: "amount", key: "amount", render: (v: number) => `₹${v.toLocaleString("en-IN")}` },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={v === "paid" ? "green" : "orange"}>{v}</Tag> }
  ];

  const userColumns = [
    { title: "Name", dataIndex: "full_name", key: "full_name" },
    { title: "Email", dataIndex: "email", key: "email" },
    { title: "Phone", dataIndex: "phone", key: "phone", render: (v?: string) => v || "—" },
    {
      title: "Role", dataIndex: "role", key: "role",
      render: (v: string) => (
        <Tooltip title={roleInfo[v] ? `Can access: ${roleInfo[v].join(", ")}` : undefined}>
          <Tag color={roleColor[v] ?? "default"} icon={<SafetyOutlined />}>{v.toUpperCase()}</Tag>
        </Tooltip>
      ),
    },
    {
      title: "Active", dataIndex: "is_active", key: "is_active",
      render: (v: boolean, row: User) => (
        <Switch checked={v} size="small" onChange={(checked) => toggleUserActive(row, checked)} />
      ),
    },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, row: User) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditUser(row)}>Edit</Button>
        </Space>
      ),
    },
  ];

  if (loading || !tenant) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 400 }}>
        <Spin size="large" tip="Loading settings..." />
      </div>
    );
  }

  const caps: any = PLAN_CAPACITIES[tenant.plan as keyof typeof PLAN_CAPACITIES] || {};

  return (
    <ConfigProvider theme={{}}>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Header */}
        <div>
          <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
            <SettingOutlined style={{ color: tenant?.branding?.primary_color || "#6366f1" }} />
            <span className="gradient-text" style={{ background: `linear-gradient(90deg, #a5b4fc 0%, ${tenant?.branding?.primary_color || "#6366f1"} 50%, #4338ca 100%)`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Tenant Settings &amp; Customization
            </span>
          </Title>
          <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
            Configure white-labeled branding parameters, update legal business profile, manage subscription tiers, and audit workspace quotas.
          </Text>
        </div>

        {currentUser?.is_platform_admin && (
          <Alert
            message="Platform Administration Mode"
            description={
              <span>
                Looking to register or onboard a new company? You can manage all companies and tenants in the{" "}
                <a onClick={() => navigate("/platform/tenants")} style={{ fontWeight: 600, textDecoration: "underline" }}>
                  Platform Tenants Console
                </a>.
              </span>
            }
            type="info"
            showIcon
          />
        )}

        <Form form={form} layout="vertical" onFinish={handleSave} preserve={true}>
          <Tabs
            defaultActiveKey="profile"
            items={[
              {
                key: "profile",
                label: (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <SolutionOutlined />
                    Company Profile &amp; Tax
                  </span>
                ),
                forceRender: true,
                children: (
                  <Card className="glass-card" title="Company Profile & Tax Details">
                    <Form.Item name="name" label="Company Registered Name" rules={[{ required: true }]}>
                      <Input placeholder="e.g. Acme Security Systems" />
                    </Form.Item>

                    <Title level={5} style={{ marginTop: 16 }}>Address Details</Title>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="address_line1" label="Address Line 1">
                          <Input placeholder="e.g. 101, Business Park" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="address_line2" label="Address Line 2">
                          <Input placeholder="e.g. M.G. Road" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={6}>
                        <Form.Item name="city" label="City">
                          <Input placeholder="e.g. Pune" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item name="state" label="State">
                          <Input placeholder="e.g. Maharashtra" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item name="pin_code" label="PIN Code">
                          <Input placeholder="e.g. 411001" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item name="country" label="Country">
                          <Input placeholder="e.g. India" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Title level={5} style={{ marginTop: 16 }}>Tax Information</Title>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="gstin" label="GSTIN (GST Number)">
                          <Input placeholder="e.g. 27AAAAA1111A1Z1" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="pan_number" label="PAN Number">
                          <Input placeholder="e.g. ABCDE1234F" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Title level={5} style={{ marginTop: 16 }}>Contact Information</Title>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="contact_person" label="Contact Person">
                          <Input placeholder="e.g. Rajesh Patil" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="mobile_number" label="Mobile Number">
                          <Input placeholder="e.g. +91 9999988888" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="telephone_number" label="Telephone Number">
                          <Input placeholder="e.g. 020-2567890" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="email_address" label="Email Address">
                          <Input type="email" placeholder="e.g. contact@acmesecurity.com" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="website" label="Website">
                          <Input placeholder="e.g. www.acmesecurity.com" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Divider style={{ borderColor: "rgba(255,255,255,0.08)" }} />
                    <Title level={5}>Billing Contact (Workspace Subscriptions)</Title>
                    <Space style={{ display: "flex", width: "100%" }} size="large">
                      <Form.Item name="billing_contact_name" label="Contact Name" style={{ width: 300 }}>
                        <Input />
                      </Form.Item>
                      <Form.Item name="billing_contact_email" label="Contact Email" style={{ width: 300 }} rules={[{ type: "email" }]}>
                        <Input type="email" />
                      </Form.Item>
                    </Space>

                    <Form.Item name="invoice_prefix" label="Invoice Prefix" style={{ width: 250 }} rules={[{ required: true }]}>
                      <Input placeholder="e.g. INV-2026" />
                    </Form.Item>

                    <Button type="primary" htmlType="submit" loading={saving}>Save Profile Changes</Button>
                  </Card>
                )
              },
              {
                key: "branding",
                label: (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <BgColorsOutlined />
                    Branding &amp; Theme
                  </span>
                ),
                forceRender: true,
                children: (
                  <Card className="glass-card" title="Branding & System Theme">
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="logo_url" label="Company Logo (PNG, JPG, JPEG, SVG < 2MB)">
                          <BrandedFileUpload label="Upload Logo" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="theme_key" label="Built-in System Theme">
                          <Select placeholder="Select theme" onChange={(val) => {
                            const baseTheme = THEMES_CONFIG[val as keyof typeof THEMES_CONFIG];
                            if (baseTheme) {
                              form.setFieldsValue({ primary_color: baseTheme.token.colorPrimary });
                            }
                          }}>
                            <Option value="light_professional">Light Professional</Option>
                            <Option value="dark_professional">Dark Professional</Option>
                            <Option value="blue_corporate">Blue Corporate</Option>
                            <Option value="green_nature">Green Nature</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="primary_color" label="Brand Primary Color Theme" getValueFromEvent={(color) => color.toHexString()}>
                          <ColorPicker showText />
                        </Form.Item>
                      </Col>
                    </Row>
                    <div style={{ marginTop: 24, marginBottom: 24, padding: 16, background: "rgba(255,255,255,0.02)", borderRadius: 8, border: "1px dashed rgba(255,255,255,0.08)" }}>
                      <Text style={{ color: "var(--text-secondary)", display: "block", marginBottom: 12 }}>Visual Theme Preview:</Text>
                      <Space>
                        <Button type="primary">Primary Brand Button</Button>
                        <Button>Secondary Button</Button>
                        <Tag color="success">Active Workspace Status</Tag>
                      </Space>
                    </div>
                    <Button type="primary" htmlType="submit" loading={saving}>Apply Brand &amp; Theme Settings</Button>
                  </Card>
                )
              },
              {
                key: "bank",
                label: (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <BankOutlined />
                    Bank &amp; Signatory
                  </span>
                ),
                forceRender: true,
                children: (
                  <Card className="glass-card" title="Banking & Authorized Signatory Details">
                    <Title level={5}>Bank details for Invoices / Quotations</Title>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="bank_name" label="Bank Name">
                          <Input placeholder="e.g. HDFC Bank" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="branch_name" label="Branch Name">
                          <Input placeholder="e.g. Shivaji Nagar, Pune" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="account_holder_name" label="Account Holder Name">
                          <Input placeholder="e.g. Acme Security Systems" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="account_number" label="Account Number">
                          <Input placeholder="e.g. 5010000123456" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="ifsc_code" label="IFSC Code">
                          <Input placeholder="e.g. HDFC0000123" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item name="upi_id" label="UPI ID (Optional)" style={{ width: 350 }}>
                      <Input placeholder="e.g. acme@okhdfcbank" />
                    </Form.Item>

                    <Divider style={{ borderColor: "var(--glass-border)" }} />
                    <Title level={5}>Authorized Signatory</Title>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="signatory_name" label="Signatory Name">
                          <Input placeholder="e.g. Mr. Rajesh Patil" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="signatory_designation" label="Designation">
                          <Input placeholder="e.g. Director / Proprietor" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="signature_url" label="Signature Upload (PNG, JPG, JPEG, SVG < 2MB)">
                          <BrandedFileUpload label="Upload Signature" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="seal_url" label="Company Seal Upload (Optional, PNG, JPG, JPEG, SVG < 2MB)">
                          <BrandedFileUpload label="Upload Company Seal" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Button type="primary" htmlType="submit" loading={saving} style={{ marginTop: 16 }}>Save Bank &amp; Signatory Changes</Button>
                  </Card>
                )
              },
              {
                key: "defaults",
                label: (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <FileTextOutlined />
                    Quotation &amp; Defaults
                  </span>
                ),
                forceRender: true,
                children: (
                  <Card className="glass-card" title="Quotation Terms &amp; Default pre-fills">
                    <Title level={5}>Default Customer Information (for templates)</Title>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="default_customer_name" label="Customer Name">
                          <Input placeholder="e.g. Green Valley Apartments" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="default_customer_gstin" label="Customer GSTIN">
                          <Input placeholder="e.g. 27BBBBB2222B2Z2" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item name="default_customer_address" label="Customer Address">
                      <Input.TextArea rows={2} placeholder="Customer site address..." />
                    </Form.Item>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="default_customer_contact_person" label="Contact Person">
                          <Input placeholder="e.g. Mr. Amit Shah" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="default_customer_mobile" label="Mobile Number">
                          <Input placeholder="e.g. +91 98888 77777" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="default_customer_email" label="Email Address">
                          <Input type="email" placeholder="e.g. manager@greenvalley.com" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Divider style={{ borderColor: "var(--glass-border)" }} />
                    <Title level={5}>Default Quotation Terms &amp; Conditions</Title>
                    <Form.Item name="default_terms" label="Terms and Conditions (WYSIWYG Rich Text Editor)">
                      <RichTextEditor minHeight={200} placeholder="Type the default terms &amp; conditions that will pre-fill every new quotation..." />
                    </Form.Item>

                    <Button type="primary" htmlType="submit" loading={saving} style={{ marginTop: 16 }}>Save Quotations &amp; Defaults</Button>
                  </Card>
                )
              },
              {
                key: "companies",
                label: (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <BuildOutlined />
                    Multi-Company &amp; Templates
                  </span>
                ),
                children: <CompanySettingsTab />
              },
              {
                key: "users",
                label: (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <TeamOutlined />
                    Staff Directory
                  </span>
                ),
                children: (
                  <Card
                    className="glass-card"
                    title="Workspace Users List"
                    extra={
                      <Button type="primary" icon={<PlusOutlined />} onClick={openAddUser}>
                        Add Staff
                      </Button>
                    }
                  >
                    <Table rowKey="id" columns={userColumns} dataSource={users} loading={usersLoading} />
                  </Card>
                )
              },
              {
                key: "subscription",
                label: (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <CreditCardOutlined />
                    Subscription &amp; Resource Limits
                  </span>
                ),
                children: (
                  <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                    <Card className="glass-card" title="Subscription Status">
                      <Descriptions bordered column={2} size="small">
                        <Descriptions.Item label="Active Plan">
                          <Tag color="purple" style={{ fontSize: 13, fontWeight: "bold" }}>
                            {tenant.plan.toUpperCase()} PLAN
                          </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="Plan Status">
                          <Tag color={tenant.status === "active" ? "green" : "orange"}>
                            {tenant.status.toUpperCase()}
                          </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="Trial Ends At">
                          {tenant.trial_ends_at ? new Date(tenant.trial_ends_at).toLocaleDateString() : "No trial (Active Paid Subscription)"}
                        </Descriptions.Item>
                        <Descriptions.Item label="Billing Period">
                          Monthly Subscription Invoice Billing
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>

                    <Card className="glass-card" title="Quota & Limits Tracking">
                      <div style={{ display: "flex", flexDirection: "column", gap: 24, padding: "12px 0" }}>
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                            <Text>Administrative Users ({usage?.users?.used} / {caps.max_users})</Text>
                            <Text type="secondary">{Math.round((usage?.users?.used / caps.max_users) * 100)}% Used</Text>
                          </div>
                          <Progress percent={Math.round((usage?.users?.used / caps.max_users) * 100)} strokeColor="#8b5cf6" />
                        </div>
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                            <Text>Field Technicians ({usage?.technicians?.used} / {caps.max_technicians})</Text>
                            <Text type="secondary">{Math.round((usage?.technicians?.used / caps.max_technicians) * 100)}% Used</Text>
                          </div>
                          <Progress percent={Math.round((usage?.technicians?.used / caps.max_technicians) * 100)} strokeColor="#3b82f6" />
                        </div>
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                            <Text>Client Sites ({usage?.sites?.used} / {caps.max_sites})</Text>
                            <Text type="secondary">{Math.round((usage?.sites?.used / caps.max_sites) * 100)}% Used</Text>
                          </div>
                          <Progress percent={Math.round((usage?.sites?.used / caps.max_sites) * 100)} strokeColor="#10b981" />
                        </div>
                      </div>
                    </Card>

                    <Card className="glass-card" title="Platform Invoices History">
                      <Table rowKey="id" columns={invoiceColumns} dataSource={invoices} pagination={false} />
                    </Card>
                  </div>
                )
              },
              {
                key: "domain",
                label: (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <GlobalOutlined />
                    Custom Domain &amp; Mail
                  </span>
                ),
                forceRender: true,
                children: (
                  <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                    <Card className="glass-card" title="Custom URL & Email Sender">
                      <Form.Item name="custom_domain" label="Custom Access Domain (CNAME)" extra="Point a CNAME record in your DNS provider to cctvamc.com. Leave empty to use system subdomain.">
                        <Input placeholder="e.g. portal.greenvalley.in" prefix={<GlobalOutlined />} />
                      </Form.Item>
                      <Form.Item name="custom_email_sender" label="Custom SMTP Email Sender Address" extra="Automated tickets, notifications, and invoices will show this email in the From header.">
                        <Input placeholder="e.g. alerts@greenvalley.in" prefix={<MailOutlined />} />
                      </Form.Item>
                      <Button type="primary" htmlType="submit" loading={saving}>Save Domain Settings</Button>
                    </Card>

                    <Card className="glass-card" title="Custom Email Templates">
                      <Typography.Paragraph style={{ color: "var(--text-secondary)" }}>
                        Customize notification email subjects and bodies. You can use placeholders like <code>{"{{contract_number}}"}</code>, <code>{"{{invoice_number}}"}</code>, etc.
                      </Typography.Paragraph>
                      <Collapse 
                        ghost
                        items={[
                          {
                            key: "amc_expiry",
                            label: <span style={{ color: "#fff", fontWeight: 500 }}>AMC Expiration Email Template</span>,
                            children: (
                              <Space direction="vertical" style={{ width: "100%" }}>
                                <Form.Item name="amc_expiry_subject" label="Email Subject">
                                  <Input />
                                </Form.Item>
                                <Form.Item name="amc_expiry_body" label="Email Body (Plain Text / Markdown)">
                                  <Input.TextArea rows={4} />
                                </Form.Item>
                              </Space>
                            )
                          },
                          {
                            key: "payment_due",
                            label: <span style={{ color: "#fff", fontWeight: 500 }}>Invoice Payment Due Email Template</span>,
                            children: (
                              <Space direction="vertical" style={{ width: "100%" }}>
                                <Form.Item name="payment_due_subject" label="Email Subject">
                                  <Input />
                                </Form.Item>
                                <Form.Item name="payment_due_body" label="Email Body (Plain Text / Markdown)">
                                  <Input.TextArea rows={4} />
                                </Form.Item>
                              </Space>
                            )
                          },
                          {
                            key: "quote_sent",
                            label: <span style={{ color: "#fff", fontWeight: 500 }}>Quotation Sent Email Template</span>,
                            children: (
                              <Space direction="vertical" style={{ width: "100%" }}>
                                <Form.Item name="quote_sent_subject" label="Email Subject">
                                  <Input />
                                </Form.Item>
                                <Form.Item name="quote_sent_body" label="Email Body (Plain Text / Markdown)">
                                  <Input.TextArea rows={4} />
                                </Form.Item>
                              </Space>
                            )
                          }
                        ]}
                      />
                      <Button type="primary" htmlType="submit" loading={saving} style={{ marginTop: 16 }}>Save Templates Changes</Button>
                    </Card>
                  </div>
                )
              }
            ]}
          />
        </Form>
      </div>

      <Modal 
        title={editingUser ? "Edit Staff User" : "Add Staff User"} 
        open={userModalOpen} 
        onOk={handleSaveUser}
        onCancel={() => setUserModalOpen(false)} 
        confirmLoading={savingUser} 
        okText={editingUser ? "Save" : "Create"}
      >
        <Form form={userForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="full_name" label="Full Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: "email" }]}>
            <Input disabled={!!editingUser} />
          </Form.Item>
          <Form.Item name="phone" label="Phone"><Input /></Form.Item>
          {!editingUser && (
            <Form.Item name="password" label="Password" rules={[{ required: true, min: 8 }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="role" label="Role" rules={[{ required: true }]}>
            <Select onChange={() => undefined}>
              {ROLES.map(r => <Option key={r.value} value={r.value}>{r.label}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item shouldUpdate={(p, c) => p.role !== c.role} style={{ marginBottom: 0 }}>
            {({ getFieldValue }) => {
              const perms = roleInfo[getFieldValue("role")];
              return perms ? (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Grants: {perms.join(", ")}
                </Text>
              ) : null;
            }}
          </Form.Item>
        </Form>
      </Modal>
    </ConfigProvider>
  );
}
