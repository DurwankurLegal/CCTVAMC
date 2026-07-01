import { useEffect, useState, useCallback } from "react";
import {
  Tabs, Table, Button, Modal, Form, Input, Select, Tag, Typography, message,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title } = Typography;
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
        title="Add Template"
      />
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No templates" }} />

      <Modal centered title="Add Template" open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText="Create">
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
  return <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No notification logs" }} />;
}

export default function NotificationsPage() {
  return (
    <div>
      <Title level={4}>Notifications</Title>
      <Tabs items={[
        { key: "templates", label: "Templates", children: <TemplatesTab /> },
        { key: "logs", label: "Delivery Logs", children: <LogsTab /> },
      ]} />
    </div>
  );
}
