import { useEffect, useState, useCallback } from "react";
import {
  Tabs, Table, Button, Modal, Form, Input, Select, Tag, Typography, message, Card, ConfigProvider, theme, Space
} from "antd";
import { PlusOutlined, BellOutlined, MailOutlined, HistoryOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title, Text } = Typography;
const { Option } = Select;

const EVENTS = [
  "ticket_assigned", "ticket_updated", "sla_breach", "amc_expiry", "payment_due",
  "warranty_expiry", "installation_handover", "lead_followup", "quote_sent",
  "quote_approved", "quote_rejected", "low_stock", "purchase_order_created",
  "customer_ticket_created", "customer_ticket_comment", "visit_reminder",
];
const CHANNELS = ["in_app", "email", "sms"];
const statusColor: Record<string, string> = { sent: "green", pending: "blue", failed: "red", delivered: "green" };

interface Template { id: string; event_type: string; channel: string; subject?: string; body: string; is_active: boolean }
interface Log { id: string; event_type: string; channel: string; recipient: string; status: string; retry_count: number; created_at?: string }

function TemplatesTab() {
  const [rows, setRows] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows((await apiClient.get("/notifications/templates")).data); }
    catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load templates"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openCreate = () => { form.resetFields(); form.setFieldsValue({ channel: "in_app" }); setOpen(true); };
  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try { await apiClient.post("/notifications/templates", v); message.success("Template created"); setOpen(false); load(); }
    catch (e: any) { message.error(e?.response?.data?.detail || "Save failed"); }
    finally { setSaving(false); }
  };

  const columns = [
    { title: "Event", dataIndex: "event_type", key: "event_type", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Channel", dataIndex: "channel", key: "channel", render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: "Subject", dataIndex: "subject", key: "subject", render: (v?: string) => v || "—" },
    { title: "Body", dataIndex: "body", key: "body", ellipsis: true },
    { title: "Active", dataIndex: "is_active", key: "is_active", render: (v: boolean) => <Tag color={v ? "green" : "default"}>{v ? "yes" : "no"}</Tag> },
  ];

  return (
    <>
      <Card
        id="templates-panel"
        className="glass-card"
        styles={{
          header: {
            background: "linear-gradient(135deg, rgba(236, 72, 153, 0.08) 0%, rgba(236, 72, 153, 0.02) 100%)",
            borderBottom: "1px solid rgba(236, 72, 153, 0.15)",
            borderRadius: "12px 12px 0 0"
          },
          body: { padding: 0 }
        }}
        title={
          <Space>
            <MailOutlined style={{ color: "#ec4899", fontSize: 18 }} />
            <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
              Message Templates
            </span>
            <Tag color="pink" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(236, 72, 153, 0.12)", border: "1px solid rgba(236, 72, 153, 0.2)" }}>
              NOTIFICATION TEMPLATES
            </Tag>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #ec4899 0%, #db2777 100%)", border: "none", color: "#fff" }}>Add Template</Button>
        }
      >
        <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No templates" }} />
      </Card>

      <Modal title="Add Template" open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText="Create">
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="event_type" label="Event" rules={[{ required: true }]}>
            <Select showSearch>{EVENTS.map(e => <Option key={e} value={e}>{e}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="channel" label="Channel" rules={[{ required: true }]}>
            <Select>{CHANNELS.map(c => <Option key={c} value={c}>{c}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="subject" label="Subject"><Input /></Form.Item>
          <Form.Item name="body" label="Body" rules={[{ required: true }]} extra="Use {{placeholders}} like {{ticket_number}}, {{item}}, {{po_number}}.">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

function LogsTab() {
  const [rows, setRows] = useState<Log[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    apiClient.get("/notifications/logs", { params: { limit: 200 } })
      .then(({ data }) => setRows(data))
      .catch((e) => message.error(e?.response?.data?.detail || "Failed to load logs"))
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    { title: "Event", dataIndex: "event_type", key: "event_type", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Channel", dataIndex: "channel", key: "channel" },
    { title: "Recipient", dataIndex: "recipient", key: "recipient" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v}</Tag> },
    { title: "Retries", dataIndex: "retry_count", key: "retry_count" },
  ];
  return (
    <Card
      id="logs-panel"
      className="glass-card"
      styles={{
        header: {
          background: "linear-gradient(135deg, rgba(236, 72, 153, 0.08) 0%, rgba(236, 72, 153, 0.02) 100%)",
          borderBottom: "1px solid rgba(236, 72, 153, 0.15)",
          borderRadius: "12px 12px 0 0"
        },
        body: { padding: 0 }
      }}
      title={
        <Space>
          <HistoryOutlined style={{ color: "#ec4899", fontSize: 18 }} />
          <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
            Message Transmission Logs
          </span>
          <Tag color="pink" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(236, 72, 153, 0.12)", border: "1px solid rgba(236, 72, 153, 0.2)" }}>
            TRANSMISSION HISTORIC LOGS
          </Tag>
        </Space>
      }
    >
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No notification logs" }} />
    </Card>
  );
}

export default function NotificationsPage() {
  return (
    <ConfigProvider theme={{}}>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Header Block */}
        <div>
          <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
            <BellOutlined style={{ color: "#ec4899" }} />
            <span className="gradient-text" style={{ background: "linear-gradient(90deg, #f472b6 0%, #ec4899 50%, #db2777 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Alerts &amp; Notifications Hub
            </span>
          </Title>
          <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
            Configure automated system alerts, manage email &amp; SMS message templates, and track delivery reports.
          </Text>
        </div>

        <Tabs items={[
          { key: "templates", label: "Templates", children: <TemplatesTab /> },
          { key: "logs", label: "Delivery Logs", children: <LogsTab /> },
        ]} />
      </div>
    </ConfigProvider>
  );
}
