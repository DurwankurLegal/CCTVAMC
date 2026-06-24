import { useEffect, useState, useCallback } from "react";
import {
  Tabs, Card, Form, Input, Button, Table, Tag, Space, Typography, message,
  ConfigProvider, theme, ColorPicker, Progress, Descriptions, Spin, List, Collapse
} from "antd";
import {
  SettingOutlined, UserOutlined, FileTextOutlined, AppstoreOutlined,
  MailOutlined, SafetyCertificateOutlined, TeamOutlined, GlobalOutlined
} from "@ant-design/icons";
import apiClient from "../api/client";

const { Title, Text } = Typography;

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
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tenant, setTenant] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);

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
      form.setFieldsValue({
        ...settingsRes.data,
        gstin: settingsRes.data.gstin || "",
        registered_address: settingsRes.data.registered_address || "",
        billing_contact_name: settingsRes.data.billing_contact_name || "",
        billing_contact_email: settingsRes.data.billing_contact_email || "",
        custom_domain: settingsRes.data.custom_domain || "",
        custom_email_sender: settingsRes.data.custom_email_sender || "",
        primary_color: settingsRes.data.branding?.primary_color || "#1677ff",
        logo_url: settingsRes.data.branding?.logo_url || "",
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
          logo_url: values.logo_url || null
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
    { title: "Role", dataIndex: "role", key: "role", render: (v: string) => <Tag color="geekblue">{v.toUpperCase()}</Tag> },
    { title: "Status", dataIndex: "is_active", key: "is_active", render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "Active" : "Inactive"}</Tag> }
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
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorBgContainer: "#161c2d",
          colorBorder: "rgba(255, 255, 255, 0.08)",
          colorText: "#f3f4f6",
          colorTextSecondary: "#9ca3af",
          colorTextHeading: "#ffffff",
          colorPrimary: tenant?.branding?.primary_color || "#6366f1",
        },
        components: {
          Table: {
            headerBg: "rgba(255, 255, 255, 0.04)",
            headerColor: "#f3f4f6",
          }
        }
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Header */}
        <div>
          <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
            <SettingOutlined style={{ color: tenant?.branding?.primary_color || "#6366f1" }} />
            <span className="gradient-text" style={{ background: `linear-gradient(90deg, #a5b4fc 0%, ${tenant?.branding?.primary_color || "#6366f1"} 50%, #4338ca 100%)`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Tenant Settings &amp; Customization
            </span>
          </Title>
          <Text style={{ color: "#9ca3af", fontSize: "13.5px" }}>
            Configure white-labeled branding parameters, update legal business profile, manage subscription tiers, and audit workspace quotas.
          </Text>
        </div>

        <Form form={form} layout="vertical" onFinish={handleSave} preserve={true}>
          <Tabs
            defaultActiveKey="profile"
            items={[
              {
                key: "profile",
                label: "Business Profile",
                forceRender: true,
                children: (
                  <Card className="glass-card" title="Company Business Profile">
                    <Form.Item name="name" label="Company Registered Name" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                    <Space style={{ display: "flex", width: "100%" }} size="large">
                      <Form.Item name="gstin" label="GSTIN" style={{ width: 250 }}>
                        <Input placeholder="e.g. 27AAAAA1111A1Z1" />
                      </Form.Item>
                      <Form.Item name="invoice_prefix" label="Invoice Prefix" style={{ width: 250 }} rules={[{ required: true }]}>
                        <Input placeholder="e.g. INV-2026" />
                      </Form.Item>
                    </Space>
                    <Form.Item name="registered_address" label="Registered Address">
                      <Input.TextArea rows={3} />
                    </Form.Item>
                    <Title level={5} style={{ marginTop: 24, marginBottom: 16 }}>Billing Contact</Title>
                    <Space style={{ display: "flex", width: "100%" }} size="large">
                      <Form.Item name="billing_contact_name" label="Contact Name" style={{ width: 300 }}>
                        <Input />
                      </Form.Item>
                      <Form.Item name="billing_contact_email" label="Contact Email" style={{ width: 300 }} rules={[{ type: "email" }]}>
                        <Input type="email" />
                      </Form.Item>
                    </Space>
                    <Button type="primary" htmlType="submit" loading={saving}>Save Profile Changes</Button>
                  </Card>
                )
              },
              {
                key: "branding",
                label: "Branding & Theme",
                forceRender: true,
                children: (
                  <Card className="glass-card" title="White-label Branding">
                    <Form.Item name="logo_url" label="Company Logo URL">
                      <Input placeholder="https://example.com/logo.png" />
                    </Form.Item>
                    <Form.Item name="primary_color" label="Brand Primary Color Theme" getValueFromEvent={(color) => color.toHexString()}>
                      <ColorPicker showText />
                    </Form.Item>
                    <div style={{ marginTop: 24, marginBottom: 24, padding: 16, background: "rgba(255,255,255,0.02)", borderRadius: 8, border: "1px dashed rgba(255,255,255,0.08)" }}>
                      <Text style={{ color: "#9ca3af", display: "block", marginBottom: 12 }}>Visual Theme Preview:</Text>
                      <Space>
                        <Button type="primary">Primary Brand Button</Button>
                        <Button>Secondary Button</Button>
                        <Tag color="success">Active Workspace Status</Tag>
                      </Space>
                    </div>
                    <Button type="primary" htmlType="submit" loading={saving}>Apply Brand Settings</Button>
                  </Card>
                )
              },
              {
                key: "users",
                label: "Staff Directory",
                children: (
                  <Card className="glass-card" title="Workspace Users List">
                    <Table rowKey="id" columns={userColumns} dataSource={users} loading={usersLoading} />
                  </Card>
                )
              },
              {
                key: "subscription",
                label: "Subscription & Resource Limits",
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
                label: "Custom Domain & Mail",
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
                      <Typography.Paragraph style={{ color: "#9ca3af" }}>
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
    </ConfigProvider>
  );
}
