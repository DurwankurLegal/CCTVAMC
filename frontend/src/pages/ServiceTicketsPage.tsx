import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Typography, Space, message, Radio, Card } from "antd";
import { PlusOutlined, EditOutlined, AppstoreOutlined, UnorderedListOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { fetchTickets } from "../store/ticketSlice";
import apiClient from "../api/client";
import type { AppDispatch, RootState } from "../store";
import { useSearchParams } from "react-router-dom";

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

export default function ServiceTicketsPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { items, loading } = useSelector((s: RootState) => s.tickets);
  const customers = useSelector((s: RootState) => s.customers.items);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Ticket | null>(null);
  const [form] = Form.useForm();
  
  const [viewMode, setViewMode] = useState<"table" | "kanban">("table");

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

  const renderKanbanBoard = () => {
    const getTicketsByStatus = (status: string) => filteredItems.filter(t => t.status === status);
    
    return (
      <div style={{ display: "flex", gap: "16px", overflowX: "auto", paddingBottom: "16px", minHeight: "450px" }}>
        {STATUSES.map(status => {
          const columnTickets = getTicketsByStatus(status);
          return (
            <div 
              key={status} 
              className="glass-card" 
              style={{ 
                flex: "0 0 280px", 
                display: "flex", 
                flexDirection: "column", 
                gap: "12px", 
                padding: "16px",
                background: "rgba(22, 28, 45, 0.4)",
                border: "1px solid rgba(255, 255, 255, 0.05)"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, textTransform: "capitalize", color: "#f3f4f6", fontSize: "13px" }}>
                  {status.replace("_", " ")}
                </span>
                <Tag color="blue" style={{ margin: 0 }}>{columnTickets.length}</Tag>
              </div>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto", flex: 1 }}>
                {columnTickets.map(ticket => (
                  <Card
                    key={ticket.id}
                    size="small"
                    className="interactive-table-row"
                    styles={{
                      body: { padding: "12px" }
                    }}
                    style={{ 
                      background: "rgba(11, 15, 25, 0.6)", 
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      borderRadius: "8px",
                      cursor: "pointer"
                    }}
                    onClick={() => openEdit(ticket)}
                  >
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontWeight: 600, color: "#3b82f6", fontSize: "11px" }}>
                          {ticket.ticket_number}
                        </span>
                        <Tag color={priorityColor[ticket.priority]} style={{ fontSize: "10px", margin: 0 }}>
                          {ticket.priority}
                        </Tag>
                      </div>
                      <span style={{ color: "#f3f4f6", fontSize: "12px", lineHeight: "1.4" }}>
                        {ticket.complaint}
                      </span>
                      {ticket.sla_breached && (
                        <Tag color="red" style={{ alignSelf: "flex-start", fontSize: "9px", margin: 0, marginTop: 4 }}>
                          SLA Breached
                        </Tag>
                      )}
                    </div>
                  </Card>
                ))}
                {columnTickets.length === 0 && (
                  <div style={{ textAlign: "center", color: "#6b7280", padding: "32px 0", fontSize: "12px" }}>
                    No tickets
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
        <Space size={16}>
          <Title level={4} style={{ margin: 0 }}>Service Tickets</Title>
          <Radio.Group value={viewMode} onChange={e => setViewMode(e.target.value)} size="small">
            <Radio.Button value="table"><UnorderedListOutlined /> Table</Radio.Button>
            <Radio.Button value="kanban"><AppstoreOutlined /> Kanban</Radio.Button>
          </Radio.Group>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Raise Ticket</Button>
      </div>

      {viewMode === "table" ? (
        <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} />
      ) : (
        renderKanbanBoard()
      )}

      <Modal
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
