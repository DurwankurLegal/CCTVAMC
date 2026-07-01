import { useEffect, useState, useCallback } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Typography, message } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import portalClient from "../../api/portalClient";

const { Title } = Typography;
const { Option } = Select;

const statusColor: Record<string, string> = {
  open: "blue", assigned: "cyan", in_progress: "gold", pending_parts: "orange",
  resolved: "green", closed: "default",
};
const PRIORITIES = ["low", "medium", "high", "critical"];

interface Ticket { id: string; ticket_number: string; status: string; priority: string; complaint: string; created_at?: string }

export default function PortalTicketsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [sites, setSites] = useState<{ id: string; name: string }[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await portalClient.get("/tickets");
      setRows(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = useCallback(async () => {
    form.resetFields();
    form.setFieldsValue({ priority: "medium" });
    setOpen(true);
    try { setSites((await portalClient.get("/sites")).data); } catch { /* sites optional */ }
  }, [form]);

  // Support deep-link ?new=1 from the dashboard CTA.
  useEffect(() => {
    if (params.get("new") === "1") {
      openCreate();
      params.delete("new");
      setParams(params, { replace: true });
    }
  }, [params, setParams, openCreate]);

  const handleCreate = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await portalClient.post("/tickets", values);
      message.success("Service request raised");
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to raise request");
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { title: "Ticket #", dataIndex: "ticket_number", key: "ticket_number",
      render: (v: string, r: Ticket) => <a onClick={() => navigate(`/portal/tickets/${r.id}`)}>{v}</a> },
    { title: "Complaint", dataIndex: "complaint", key: "complaint", ellipsis: true },
    { title: "Priority", dataIndex: "priority", key: "priority", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v.replace("_", " ")}</Tag> },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Service Tickets</Title>
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
        title="Raise Request"
      />

      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading}
        locale={{ emptyText: "No service requests yet" }} />

      <Modal title="Raise Service Request" open={open} onOk={handleCreate} onCancel={() => setOpen(false)}
        confirmLoading={saving} okText="Submit">
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="complaint" label="Describe the issue" rules={[{ required: true, min: 5 }]}>
            <Input.TextArea rows={3} placeholder="e.g. Lobby camera 2 is offline since morning" />
          </Form.Item>
          <Form.Item name="priority" label="Priority" rules={[{ required: true }]}>
            <Select>{PRIORITIES.map(p => <Option key={p} value={p}>{p}</Option>)}</Select>
          </Form.Item>
          {sites.length > 0 && (
            <Form.Item name="site_id" label="Site (optional)">
              <Select allowClear placeholder="Select a site">
                {sites.map(s => <Option key={s.id} value={s.id}>{s.name}</Option>)}
              </Select>
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
