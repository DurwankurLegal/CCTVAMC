import { useEffect, useState, useCallback } from "react";
import {
  Card, Descriptions, Tag, Button, Space, Typography, message, Progress, Table,
  Modal, Form, DatePicker, Row, Col, Spin, Result, Switch, List, Alert,
} from "antd";
import { ArrowLeftOutlined, KeyOutlined, UserOutlined } from "@ant-design/icons";
import { useParams, useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import apiClient from "../../api/client";

const { Title, Text } = Typography;

const statusColor: Record<string, string> = {
  trial: "blue", active: "green", suspended: "orange", cancelled: "red",
};

interface Tenant {
  id: string; name: string; slug: string; plan: string; status: string;
  gstin?: string; invoice_prefix?: string;
}
interface UsageEntry { used: number; limit: number; unlimited: boolean }
interface Usage { plan: string; users: UsageEntry; technicians: UsageEntry; sites: UsageEntry }
interface SubInvoice { id: string; invoice_number: string; plan: string; amount: number; status: string }
interface TenantUser {
  id: string; email: string; full_name: string; role: string;
  is_active: boolean; must_change_password: boolean; created_at: string | null;
}

function UsageBar({ label, entry }: { label: string; entry?: UsageEntry }) {
  if (!entry) return null;
  const pct = entry.unlimited ? 0 : Math.min(100, Math.round((entry.used / Math.max(entry.limit, 1)) * 100));
  return (
    <Col span={8}>
      <div style={{ marginBottom: 4 }}>{label}: <b>{entry.used}</b>{entry.unlimited ? " (unlimited)" : ` / ${entry.limit}`}</div>
      <Progress percent={entry.unlimited ? 100 : pct} showInfo={!entry.unlimited}
        status={pct >= 100 ? "exception" : "active"}
        strokeColor={entry.unlimited ? "#52c41a" : undefined} />
    </Col>
  );
}

export default function TenantDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [invoices, setInvoices] = useState<SubInvoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const [activeModules, setActiveModules] = useState<string[]>([]);
  const [updatingModules, setUpdatingModules] = useState(false);

  // Users & password reset state
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<TenantUser | null>(null);
  const [resetting, setResetting] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, u, inv, mods] = await Promise.all([
        apiClient.get(`/tenants/${id}`),
        apiClient.get(`/tenants/${id}/usage`),
        apiClient.get(`/tenants/${id}/subscription-invoices`),
        apiClient.get(`/tenants/${id}/modules`),
      ]);
      setTenant(t.data);
      setUsage(u.data);
      setInvoices(inv.data);
      setActiveModules(mods.data.modules || []);
    } catch (e: any) {
      if (e?.response?.status === 404) setNotFound(true);
      else message.error(e?.response?.data?.detail || "Failed to load tenant");
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const res = await apiClient.get(`/tenants/${id}/users`);
      setUsers(res.data || []);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load users");
    } finally {
      setUsersLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!loading) loadUsers(); }, [loading, loadUsers]);

  const handleToggleModule = async (code: string) => {
    let newModules = [...activeModules];
    if (newModules.includes(code)) {
      newModules = newModules.filter(m => m !== code);
    } else {
      newModules.push(code);
    }
    setUpdatingModules(true);
    try {
      await apiClient.post(`/tenants/${id}/modules`, { module_codes: newModules });
      setActiveModules(newModules);
      message.success("Tenant modules updated successfully");
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to update modules");
    } finally {
      setUpdatingModules(false);
    }
  };

  const changeStatus = async (action: "suspend" | "activate" | "cancel") => {
    try {
      await apiClient.post(`/tenants/${id}/${action}`);
      message.success(`Tenant ${action}d`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Action failed");
    }
  };

  const generateInvoice = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post(`/tenants/${id}/subscription-invoices`, {
        period_start: values.period[0].format("YYYY-MM-DD"),
        period_end: values.period[1].format("YYYY-MM-DD"),
      });
      message.success("Subscription invoice generated");
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Generation failed");
    } finally {
      setSaving(false);
    }
  };

  const handleResetPassword = async () => {
    if (!resetTarget) return;
    setResetting(true);
    try {
      const res = await apiClient.post(`/tenants/${id}/users/${resetTarget.id}/reset-password`);
      setGeneratedPassword(res.data.temp_password);
      loadUsers();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Password reset failed");
    } finally {
      setResetting(false);
    }
  };

  const openResetModal = (user: TenantUser) => {
    setResetTarget(user);
    setGeneratedPassword(null);
    setResetModalOpen(true);
  };

  const closeResetModal = () => {
    setResetModalOpen(false);
    setResetTarget(null);
    setGeneratedPassword(null);
  };

  if (loading) return <Spin style={{ display: "block", margin: "80px auto" }} />;
  if (notFound) return <Result status="404" title="Tenant not found"
    extra={<Button onClick={() => navigate("/platform/tenants")}>Back to tenants</Button>} />;
  if (!tenant) return null;

  const invoiceColumns = [
    { title: "Invoice #", dataIndex: "invoice_number", key: "invoice_number" },
    { title: "Plan", dataIndex: "plan", key: "plan", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Amount (Rs.)", dataIndex: "amount", key: "amount",
      render: (v: number) => v.toLocaleString("en-IN", { minimumFractionDigits: 2 }) },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag>{v}</Tag> },
  ];

  const userColumns = [
    { title: "Name", dataIndex: "full_name", key: "full_name",
      render: (v: string) => <Space><UserOutlined />{v || "—"}</Space> },
    { title: "Email", dataIndex: "email", key: "email" },
    { title: "Role", dataIndex: "role", key: "role", render: (v: string) => <Tag>{v}</Tag> },
    {
      title: "Status", key: "status",
      render: (_: unknown, r: TenantUser) => (
        <Space>
          <Tag color={r.is_active ? "green" : "red"}>{r.is_active ? "Active" : "Inactive"}</Tag>
          {r.must_change_password && <Tag color="orange">Must Change Password</Tag>}
        </Space>
      ),
    },
    {
      title: "Created", dataIndex: "created_at", key: "created_at",
      render: (v: string | null) => v ? dayjs(v).format("DD MMM YYYY") : "—",
    },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, r: TenantUser) => (
        <Button icon={<KeyOutlined />} size="small" danger onClick={() => openResetModal(r)}>
          Reset Password
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/platform/tenants")}>Back</Button>
        <Title level={4} style={{ margin: 0 }}>{tenant.name}</Title>
        <Tag color={statusColor[tenant.status] ?? "default"}>{tenant.status}</Tag>
      </Space>

      <Card title="Profile & Billing" style={{ marginBottom: 16 }}
        extra={
          <Space>
            <Button disabled={tenant.status === "active"} onClick={() => changeStatus("activate")}>Activate</Button>
            <Button disabled={tenant.status === "suspended"} onClick={() => changeStatus("suspend")}>Suspend</Button>
            <Button danger disabled={tenant.status === "cancelled"} onClick={() => changeStatus("cancel")}>Cancel</Button>
          </Space>
        }>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Slug">{tenant.slug}</Descriptions.Item>
          <Descriptions.Item label="Plan"><Tag>{tenant.plan}</Tag></Descriptions.Item>
          <Descriptions.Item label="GSTIN">{tenant.gstin || "—"}</Descriptions.Item>
          <Descriptions.Item label="Invoice Prefix">{tenant.invoice_prefix || "—"}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Plan Usage" style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <UsageBar label="Users" entry={usage?.users} />
          <UsageBar label="Technicians" entry={usage?.technicians} />
          <UsageBar label="Sites" entry={usage?.sites} />
        </Row>
      </Card>

      <Card
        title="Users & Password Management"
        style={{ marginBottom: 16 }}
        loading={usersLoading}
        extra={<Button size="small" onClick={loadUsers}>Refresh</Button>}
      >
        <Table
          rowKey="id"
          columns={userColumns}
          dataSource={users}
          size="small"
          locale={{ emptyText: "No users found for this tenant" }}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Card title="Subscribed Business Modules" style={{ marginBottom: 16 }} loading={updatingModules}>
        <List
          itemLayout="horizontal"
          dataSource={[
            { code: "sales", name: "Sales Management", description: "Quotations, sales orders, customer invoicing, payments" },
            { code: "rental", name: "Rental Management", description: "Rental inventory, serial units, rental agreements and billings" },
            { code: "amc", name: "AMC Management", description: "Annual maintenance contracts, preventive schedules, service tickets, technician visits" },
            { code: "inventory", name: "Inventory Management", description: "Products parts list, stock tracking, vendor purchase orders" },
            { code: "assets", name: "Asset Tracking", description: "Physical hardware assets registry tracked at client sites" },
          ]}
          renderItem={item => (
            <List.Item actions={[
              <Switch checked={activeModules.includes(item.code)} onChange={() => handleToggleModule(item.code)} />,
            ]}>
              <List.Item.Meta title={item.name} description={item.description} />
            </List.Item>
          )}
        />
      </Card>

      <Card title="Subscription Invoices"
        extra={<Button type="primary" onClick={() => { form.resetFields(); setOpen(true); }}>Generate Invoice</Button>}>
        <Table rowKey="id" columns={invoiceColumns} dataSource={invoices} size="small"
          locale={{ emptyText: "No subscription invoices yet" }} pagination={false} />
      </Card>

      <Modal title="Generate Subscription Invoice" open={open} onOk={generateInvoice}
        onCancel={() => setOpen(false)} confirmLoading={saving} okText="Generate">
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}
          initialValues={{ period: [dayjs().startOf("month"), dayjs().endOf("month")] }}>
          <Form.Item name="period" label="Billing Period" rules={[{ required: true }]}>
            <DatePicker.RangePicker style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={generatedPassword ? "Password Reset Successful" : `Reset Password — ${resetTarget?.email}`}
        open={resetModalOpen}
        onCancel={closeResetModal}
        footer={
          generatedPassword
            ? [<Button key="close" type="primary" onClick={closeResetModal}>Close</Button>]
            : [
                <Button key="cancel" onClick={closeResetModal}>Cancel</Button>,
                <Button key="reset" type="primary" danger loading={resetting} icon={<KeyOutlined />} onClick={handleResetPassword}>
                  Reset Password
                </Button>,
              ]
        }
      >
        {generatedPassword ? (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Alert type="warning" showIcon message="Save this password now — it will NOT be shown again." />
            <div style={{
              background: "#f5f5f5", border: "1px solid #d9d9d9", borderRadius: 6,
              padding: "12px 16px", marginTop: 8, fontFamily: "monospace",
              fontSize: 18, letterSpacing: 2, textAlign: "center",
            }}>
              <Text copyable strong style={{ fontSize: 18 }}>{generatedPassword}</Text>
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              The user will be required to change this password on next login.
            </Text>
          </Space>
        ) : (
          <Alert
            type="warning"
            showIcon
            message={`This will reset the password for "${resetTarget?.email}". A temporary password will be generated. The user will be forced to change it on next login.`}
          />
        )}
      </Modal>
    </div>
  );
}
