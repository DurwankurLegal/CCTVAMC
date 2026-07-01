import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Typography, Space, message } from "antd";
import { PlusOutlined, EditOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { fetchTickets } from "../store/ticketSlice";
import apiClient from "../api/client";
import type { AppDispatch, RootState } from "../store";

const { Title } = Typography;
const { Option } = Select;

interface Ticket {
  id: string;
  ticket_number: string;
  customer_id: string;
  status: string;
  priority: string;
  complaint: string;
  resolution_notes?: string | null;
  sla_breached: boolean;
}

const STATUSES = ["open", "assigned", "in_progress", "pending_parts", "resolved", "closed"];
const PRIORITIES = ["low", "medium", "high", "critical"];

import { useSearchParams } from "react-router-dom";

export default function ServiceTicketsPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { items, loading } = useSelector((s: RootState) => s.tickets);
  const customers = useSelector((s: RootState) => s.customers.items);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Ticket | null>(null);
  const [form] = Form.useForm();

  const [searchParams] = useSearchParams();
  const statusParam = searchParams.get("status");
  const priorityParam = searchParams.get("priority");
  const slaParam = searchParams.get("sla");

  useEffect(() => { dispatch(fetchTickets()); }, [dispatch]);

  const filteredItems = items.filter(item => {
    if (statusParam && item.status !== statusParam) return false;
    if (priorityParam && item.priority !== priorityParam) return false;
    if (slaParam) {
      const isBreached = slaParam === "breached";
      if (item.sla_breached !== isBreached) return false;
    }
    return true;
  });

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ priority: "medium" }); setOpen(true); };
  const openEdit = (row: Ticket) => { setEditing(row); form.setFieldsValue(row); setOpen(true); };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await apiClient.patch(`/service-tickets/${editing.id}`, {
          status: values.status, priority: values.priority, resolution_notes: values.resolution_notes,
        });
        message.success("Ticket updated");
      } else {
        await apiClient.post("/service-tickets", values);
        message.success("Ticket raised");
      }
      form.resetFields();
      setOpen(false);
      dispatch(fetchTickets());
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const priorityColor: Record<string, string> = { low: "blue", medium: "orange", high: "red", critical: "purple" };
  const statusColor: Record<string, string> = {
    open: "blue", assigned: "cyan", in_progress: "orange", pending_parts: "gold", resolved: "green", closed: "default",
  };

  const columns = [
    { title: "Ticket #", dataIndex: "ticket_number", key: "ticket_number" },
    {
      title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v.replace("_", " ")}</Tag>,
    },
    {
      title: "Priority", dataIndex: "priority", key: "priority",
      render: (v: string) => <Tag color={priorityColor[v] ?? "default"}>{v}</Tag>,
    },
    { title: "Complaint", dataIndex: "complaint", key: "complaint", ellipsis: true },
    {
      title: "SLA", dataIndex: "sla_breached", key: "sla_breached",
      render: (v: boolean) => v ? <Tag color="red">Breached</Tag> : <Tag color="green">OK</Tag>,
    },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, row: Ticket) => (
        <Space><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Edit</Button></Space>
      ),
    },
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
        title="Raise Ticket"
      />

      <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} />

      <Modal centered
        title={editing ? `Edit ${editing.ticket_number}` : "Raise Service Ticket"}
        open={open} onOk={handleSave} onCancel={() => setOpen(false)} confirmLoading={saving}
        okText={editing ? "Save" : "Create"}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {!editing && (
            <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="children" placeholder="Select customer">
                {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
              </Select>
            </Form.Item>
          )}
          {editing && (
            <Form.Item name="status" label="Status">
              <Select>{STATUSES.map(s => <Option key={s} value={s}>{s.replace("_", " ")}</Option>)}</Select>
            </Form.Item>
          )}
          <Form.Item name="priority" label="Priority">
            <Select>{PRIORITIES.map(p => <Option key={p} value={p}>{p}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="complaint" label="Complaint / Description" rules={[{ required: !editing }]}>
            <Input.TextArea rows={3} disabled={!!editing} />
          </Form.Item>
          {editing && (
            <Form.Item name="resolution_notes" label="Resolution Notes">
              <Input.TextArea rows={3} />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
