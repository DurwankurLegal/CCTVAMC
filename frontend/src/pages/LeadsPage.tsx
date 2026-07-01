import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Typography, DatePicker, Space, message, Card, ConfigProvider, theme } from "antd";
import { PlusOutlined, EditOutlined, UsergroupAddOutlined } from "@ant-design/icons";
import apiClient from "../api/client";
import dayjs from "dayjs";

const { Title, Text } = Typography;
const { Option } = Select;

interface Lead {
  id: string;
  name: string;
  company_name: string | null;
  phone: string | null;
  email: string | null;
  category: string | null;
  interest_type: string | null;
  source: string;
  status: string;
  notes: string | null;
  follow_up_date: string | null;
  converted_customer_id: string | null;
}

const statusColor: Record<string, string> = {
  new: "blue", contacted: "cyan", quoted: "purple", converted: "green", lost: "red",
};
const SOURCES = ["referral", "walk_in", "social_media", "website", "cold_call", "other"];
const STATUSES = ["new", "contacted", "quoted", "converted", "lost"];
const CATEGORIES = [
  { value: "chs", label: "CHS" },
  { value: "commercial", label: "Commercial" },
  { value: "single_shop", label: "Single Shop" },
  { value: "consumer", label: "Consumer" },
  { value: "office", label: "Office" },
  { value: "home", label: "Home" }
];
const INTERESTS = [
  { value: "new_installation", label: "New Installation" }, { value: "amc", label: "AMC" }, { value: "upgrade", label: "Upgrade" },
];

export default function LeadsPage() {
  const [items, setItems] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Lead | null>(null);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try { const { data } = await apiClient.get("/leads"); setItems(data); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ source: "referral" }); setOpen(true); };
  const openEdit = (row: Lead) => {
    setEditing(row);
    form.setFieldsValue({ ...row, follow_up_date: row.follow_up_date ? dayjs(row.follow_up_date) : null });
    setOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    const payload = { ...values, follow_up_date: values.follow_up_date?.format("YYYY-MM-DD") ?? null };
    try {
      if (editing) {
        await apiClient.patch(`/leads/${editing.id}`, payload);
        message.success("Lead updated");
      } else {
        await apiClient.post("/leads", payload);
        message.success("Lead created");
      }
      form.resetFields();
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  const convert = async (row: Lead) => {
    try {
      await apiClient.post(`/leads/${row.id}/convert`);
      message.success("Lead converted to customer");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Convert failed");
    }
  };

  const columns = [
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "Company", dataIndex: "company_name", key: "company_name", render: (v: string) => v || "—" },
    { title: "Phone", dataIndex: "phone", key: "phone", render: (v: string) => v || "—" },
    { title: "Category", dataIndex: "category", key: "category", render: (v: string) => v ? <Tag>{v}</Tag> : "—" },
    { title: "Source", dataIndex: "source", key: "source", render: (v: string) => <Tag>{v}</Tag> },
    {
      title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v}</Tag>,
    },
    {
      title: "Follow-up", dataIndex: "follow_up_date", key: "fud",
      render: (v: string) => v ? dayjs(v).format("DD MMM YYYY") : "—",
    },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, row: Lead) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Edit</Button>
          {!row.converted_customer_id && row.status !== "converted" &&
            <Button size="small" type="link" onClick={() => convert(row)}>Convert</Button>}
        </Space>
      ),
    },
  ];

  return (
    <ConfigProvider theme={{}}>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 4 }}>
          <div>
            <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
              <UsergroupAddOutlined style={{ color: "#f59e0b" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Leads &amp; Pipeline Hub
              </span>
            </Title>
            <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
              Track prospective customer leads, follow-up timelines, and sales conversion flows.
            </Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)", border: "none", color: "#fff" }}>Add Lead</Button>
        </div>

        <Card
          id="leads-panel"
          className="glass-card"
          styles={{
            header: {
              background: "linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(245, 158, 11, 0.02) 100%)",
              borderBottom: "1px solid rgba(245, 158, 11, 0.15)",
              borderRadius: "12px 12px 0 0"
            },
            body: { padding: 0 }
          }}
          title={
            <Space>
              <UsergroupAddOutlined style={{ color: "#f59e0b", fontSize: 18 }} />
              <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
                Lead Directory
              </span>
              <Tag color="warning" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(245, 158, 11, 0.12)", border: "1px solid rgba(245, 158, 11, 0.2)" }}>
                LEADS &amp; PIPELINE
              </Tag>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />
        </Card>

        <Modal
          title={editing ? "Edit Lead" : "Add Lead"}
          open={open} onOk={handleSave} onCancel={() => setOpen(false)} confirmLoading={saving}
          okText={editing ? "Save" : "Create"}
        >
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="company_name" label="Company Name"><Input /></Form.Item>
            <Form.Item name="phone" label="Phone"><Input /></Form.Item>
            <Form.Item name="email" label="Email" rules={[{ type: "email", message: "Enter a valid email address" }]}><Input /></Form.Item>
            <Form.Item name="category" label="Category">
              <Select allowClear>{CATEGORIES.map(c => <Option key={c.value} value={c.value}>{c.label}</Option>)}</Select>
            </Form.Item>
            <Form.Item name="interest_type" label="Interest">
              <Select allowClear>{INTERESTS.map(c => <Option key={c.value} value={c.value}>{c.label}</Option>)}</Select>
            </Form.Item>
            <Form.Item name="source" label="Source">
              <Select>{SOURCES.map(s => <Option key={s} value={s}>{s.replace("_", " ")}</Option>)}</Select>
            </Form.Item>
            {editing && (
              <Form.Item name="status" label="Status">
                <Select>{STATUSES.map(s => <Option key={s} value={s}>{s}</Option>)}</Select>
              </Form.Item>
            )}
            <Form.Item name="follow_up_date" label="Follow-up Date">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="notes" label="Notes"><Input.TextArea rows={2} /></Form.Item>
          </Form>
        </Modal>
      </div>
    </ConfigProvider>
  );
}
