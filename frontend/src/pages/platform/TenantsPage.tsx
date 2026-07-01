import { useEffect, useState, useCallback } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message, Dropdown } from "antd";
import { PlusOutlined, MoreOutlined, ReloadOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import apiClient from "../../api/client";

const { Title } = Typography;
const { Option } = Select;

const PLANS = [
  { value: "starter", label: "Starter" },
  { value: "growth", label: "Growth" },
  { value: "enterprise", label: "Enterprise" },
];
const STATUSES = [
  { value: "trial", label: "Trial" },
  { value: "active", label: "Active" },
  { value: "suspended", label: "Suspended" },
  { value: "cancelled", label: "Cancelled" },
];
const statusColor: Record<string, string> = {
  trial: "blue", active: "green", suspended: "orange", cancelled: "red",
};

interface Tenant {
  id: string; name: string; slug: string; plan: string; status: string;
  gstin?: string; invoice_prefix?: string;
}

export default function TenantsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [planFilter, setPlanFilter] = useState<string | undefined>();
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (statusFilter) params.status = statusFilter;
      if (planFilter) params.plan = planFilter;
      if (search) params.search = search;
      const { data } = await apiClient.get("/tenants", { params });
      setRows(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, planFilter, search]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => { form.resetFields(); form.setFieldsValue({ plan: "starter" }); setOpen(true); };

  const handleCreate = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/tenants", values);
      message.success("Tenant created");
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Create failed");
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (id: string, action: "suspend" | "activate" | "cancel") => {
    try {
      await apiClient.post(`/tenants/${id}/${action}`);
      message.success(`Tenant ${action}d`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Action failed");
    }
  };

  const columns = [
    { title: "Name", dataIndex: "name", key: "name",
      render: (v: string, r: Tenant) => <a onClick={() => navigate(`/platform/tenants/${r.id}`)}>{v}</a> },
    { title: "Slug", dataIndex: "slug", key: "slug" },
    { title: "Plan", dataIndex: "plan", key: "plan", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v}</Tag> },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, r: Tenant) => (
        <Dropdown
          menu={{
            items: [
              { key: "view", label: "View details", onClick: () => navigate(`/platform/tenants/${r.id}`) },
              { type: "divider" as const },
              { key: "activate", label: "Activate", disabled: r.status === "active", onClick: () => changeStatus(r.id, "activate") },
              { key: "suspend", label: "Suspend", disabled: r.status === "suspended", onClick: () => changeStatus(r.id, "suspend") },
              { key: "cancel", label: "Cancel", danger: true, disabled: r.status === "cancelled", onClick: () => changeStatus(r.id, "cancel") },
            ],
          }}
        >
          <Button size="small" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Tenants</Title>
      </div>
      <Button
        type="primary"
        shape="circle"
        icon={<PlusOutlined />}
        onClick={openCreate}
        size="large"
        style={{
          position: "fixed",
          bottom: 40,
          right: 40,
          width: 56,
          height: 56,
          zIndex: 1000,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "22px"
        }}
        title="Onboard Tenant"
      />

      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search placeholder="Search name/slug" allowClear style={{ width: 220 }}
          onSearch={setSearch} />
        <Select placeholder="Status" allowClear style={{ width: 160 }} value={statusFilter}
          onChange={setStatusFilter}>
          {STATUSES.map(s => <Option key={s.value} value={s.value}>{s.label}</Option>)}
        </Select>
        <Select placeholder="Plan" allowClear style={{ width: 160 }} value={planFilter}
          onChange={setPlanFilter}>
          {PLANS.map(p => <Option key={p.value} value={p.value}>{p.label}</Option>)}
        </Select>
        <Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>
      </Space>

      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} />

      <Modal title="Onboard Tenant" open={open} onOk={handleCreate} onCancel={() => setOpen(false)}
        confirmLoading={saving} okText="Create">
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Company Name" rules={[{ required: true }]}>
            <Input placeholder="Acme Security Pvt. Ltd." />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[
            { required: true },
            { pattern: /^[a-z0-9-]+$/, message: "lowercase letters, numbers, hyphens only" },
          ]}>
            <Input placeholder="acme-security" />
          </Form.Item>
          <Form.Item name="plan" label="Plan" rules={[{ required: true }]}>
            <Select>{PLANS.map(p => <Option key={p.value} value={p.value}>{p.label}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="gstin" label="GSTIN"><Input /></Form.Item>
          <Form.Item name="invoice_prefix" label="Invoice Prefix"><Input placeholder="INV" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
