import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Select, DatePicker, Tag, Space,
  Typography, message, Descriptions, Image, List, Empty, Input, Tooltip,
} from "antd";
import { PlusOutlined, EditOutlined, EyeOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import apiClient from "../api/client";

const { Title } = Typography;
const { Option } = Select;

const typeColor: Record<string, string> = { corrective: "volcano", preventive: "green" };
const fmt = (v?: string | null) => (v ? new Date(v).toLocaleString("en-IN") : "—");

interface Visit {
  id: string;
  ticket_id?: string | null;
  amc_contract_id?: string | null;
  technician_id: string;
  visit_type: string;
  checkin_at?: string | null;
  checkout_at?: string | null;
  checkin_lat?: number | null;
  checkin_lng?: number | null;
  checkout_lat?: number | null;
  checkout_lng?: number | null;
  work_performed?: string | null;
  parts_used: any[];
  photo_urls: any[];
  signature_url?: string | null;
  customer_feedback?: string | null;
  is_synced: boolean;
}

interface Technician { id: string; full_name: string; email: string; role: string; }
interface Ticket { id: string; ticket_number: string; }
interface AMCContract { id: string; contract_number: string; }

const statusTag = (v: Visit) => {
  if (v.checkout_at) return <Tag color="green">Completed</Tag>;
  if (v.checkin_at) return <Tag color="gold">In Progress</Tag>;
  return <Tag color="default">Scheduled</Tag>;
};

export default function EngineerVisitsPage() {
  const [rows, setRows] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(false);

  // Create / Edit modal state
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Visit | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  // View detail modal state
  const [detail, setDetail] = useState<Visit | null>(null);

  // Dropdown data
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [amcContracts, setAmcContracts] = useState<AMCContract[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows((await apiClient.get("/engineer-visits", { params: { limit: 200 } })).data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load visits");
    } finally {
      setLoading(false);
    }
  }, []);

  // Load dropdown reference data once
  const loadDropdowns = useCallback(async () => {
    try {
      const [techRes, ticketRes, amcRes] = await Promise.all([
        apiClient.get("/users", { params: { limit: 200 } }),
        apiClient.get("/service-tickets", { params: { limit: 200 } }),
        apiClient.get("/amc", { params: { limit: 200 } }),
      ]);
      setTechnicians(techRes.data.filter((u: Technician) => u.role === "technician"));
      setTickets(ticketRes.data);
      setAmcContracts(amcRes.data);
    } catch {
      // non-critical — dropdowns degrade gracefully
    }
  }, []);

  useEffect(() => { load(); loadDropdowns(); }, [load, loadDropdowns]);

  const techName = (id: string) =>
    technicians.find(t => t.id === id)?.full_name || id.slice(0, 8) + "…";

  // ── Create ──────────────────────────────────────────────────────────────
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ visit_type: "corrective" });
    setFormOpen(true);
  };

  // ── Edit ─────────────────────────────────────────────────────────────────
  const openEdit = (v: Visit) => {
    setEditing(v);
    form.setFieldsValue({
      visit_type: v.visit_type,
      technician_id: v.technician_id,
      ticket_id: v.ticket_id ?? undefined,
      amc_contract_id: v.amc_contract_id ?? undefined,
      work_performed: v.work_performed ?? "",
      customer_feedback: v.customer_feedback ?? "",
      checkin_at: v.checkin_at ? dayjs(v.checkin_at) : null,
      checkout_at: v.checkout_at ? dayjs(v.checkout_at) : null,
    });
    setFormOpen(true);
  };

  // ── Save (Create or Patch) ────────────────────────────────────────────────
  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const payload = {
        ...values,
        checkin_at: values.checkin_at ? values.checkin_at.toISOString() : undefined,
        checkout_at: values.checkout_at ? values.checkout_at.toISOString() : undefined,
      };

      if (editing) {
        await apiClient.patch(`/engineer-visits/${editing.id}`, payload);
        message.success("Visit updated");
      } else {
        await apiClient.post("/engineer-visits", payload);
        message.success("Visit scheduled");
      }
      setFormOpen(false);
      form.resetFields();
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  // ── Table columns ─────────────────────────────────────────────────────────
  const columns = [
    {
      title: "Type",
      dataIndex: "visit_type",
      key: "visit_type",
      render: (v: string) => <Tag color={typeColor[v] ?? "default"}>{v}</Tag>,
    },
    {
      title: "Technician",
      dataIndex: "technician_id",
      key: "technician_id",
      render: (id: string) => techName(id),
    },
    {
      title: "Ticket",
      dataIndex: "ticket_id",
      key: "ticket_id",
      render: (v?: string | null) => {
        if (!v) return "—";
        const t = tickets.find(tk => tk.id === v);
        return t ? t.ticket_number : v.slice(0, 8) + "…";
      },
    },
    {
      title: "Check-in",
      dataIndex: "checkin_at",
      key: "checkin_at",
      render: fmt,
    },
    {
      title: "Check-out",
      dataIndex: "checkout_at",
      key: "checkout_at",
      render: fmt,
    },
    {
      title: "Status",
      key: "status",
      render: (_: unknown, v: Visit) => statusTag(v),
    },
    {
      title: "Synced",
      dataIndex: "is_synced",
      key: "is_synced",
      render: (v: boolean) => <Tag color={v ? "green" : "orange"}>{v ? "synced" : "pending"}</Tag>,
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, v: Visit) => (
        <Space>
          <Tooltip title="View full details">
            <Button size="small" icon={<EyeOutlined />} onClick={() => setDetail(v)}>View</Button>
          </Tooltip>
          <Tooltip title="Edit visit">
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(v)}>Edit</Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Engineer Visits</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Schedule Visit
        </Button>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        locale={{ emptyText: "No engineer visits yet" }}
      />

      {/* ── Create / Edit modal ──────────────────────────────────────────── */}
      <Modal
        title={editing ? "Edit Visit" : "Schedule Visit"}
        open={formOpen}
        onOk={handleSave}
        onCancel={() => { setFormOpen(false); form.resetFields(); }}
        confirmLoading={saving}
        okText={editing ? "Save Changes" : "Schedule"}
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {/* Visit type */}
          <Form.Item name="visit_type" label="Visit Type" rules={[{ required: true }]}>
            <Select>
              <Option value="corrective">Corrective</Option>
              <Option value="preventive">Preventive (PM)</Option>
            </Select>
          </Form.Item>

          {/* Technician — not editable post-checkin via mobile, but admin can reassign */}
          <Form.Item name="technician_id" label="Assign Technician">
            <Select
              showSearch
              allowClear
              placeholder="Select technician (defaults to yourself)"
              optionFilterProp="children"
            >
              {technicians.map(t => (
                <Option key={t.id} value={t.id}>{t.full_name} ({t.email})</Option>
              ))}
            </Select>
          </Form.Item>

          {/* Linked ticket */}
          <Form.Item name="ticket_id" label="Linked Service Ticket">
            <Select showSearch allowClear placeholder="Select ticket (optional)" optionFilterProp="children">
              {tickets.map(t => (
                <Option key={t.id} value={t.id}>{t.ticket_number}</Option>
              ))}
            </Select>
          </Form.Item>

          {/* Linked AMC contract */}
          <Form.Item name="amc_contract_id" label="Linked AMC Contract">
            <Select showSearch allowClear placeholder="Select AMC contract (optional)" optionFilterProp="children">
              {amcContracts.map(c => (
                <Option key={c.id} value={c.id}>{c.contract_number}</Option>
              ))}
            </Select>
          </Form.Item>

          {/* Edit-only fields */}
          {editing && (
            <>
              <Form.Item name="work_performed" label="Work Performed">
                <Input.TextArea rows={3} placeholder="Describe work done on-site" />
              </Form.Item>
              <Form.Item name="customer_feedback" label="Customer Feedback">
                <Input.TextArea rows={2} placeholder="Customer remarks / rating" />
              </Form.Item>
              <Form.Item name="checkin_at" label="Check-in Time (Admin Override)">
                <DatePicker showTime style={{ width: "100%" }} format="YYYY-MM-DD HH:mm" />
              </Form.Item>
              <Form.Item name="checkout_at" label="Check-out Time (Admin Override)">
                <DatePicker showTime style={{ width: "100%" }} format="YYYY-MM-DD HH:mm" />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>

      {/* ── View detail modal ───────────────────────────────────────────── */}
      <Modal
        title="Visit Details"
        open={!!detail}
        footer={null}
        onCancel={() => setDetail(null)}
        width={680}
      >
        {detail && (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Type">
                <Tag color={typeColor[detail.visit_type] ?? "default"}>{detail.visit_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Technician">{techName(detail.technician_id)}</Descriptions.Item>
              <Descriptions.Item label="Status">{statusTag(detail)}</Descriptions.Item>
              <Descriptions.Item label="Check-in">{fmt(detail.checkin_at)}</Descriptions.Item>
              <Descriptions.Item label="Check-out">{fmt(detail.checkout_at)}</Descriptions.Item>
              <Descriptions.Item label="Check-in GPS">
                {detail.checkin_lat != null
                  ? `${detail.checkin_lat}, ${detail.checkin_lng}`
                  : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Check-out GPS">
                {detail.checkout_lat != null
                  ? `${detail.checkout_lat}, ${detail.checkout_lng}`
                  : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Work Performed">
                {detail.work_performed || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Customer Feedback">
                {detail.customer_feedback || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Synced">
                <Tag color={detail.is_synced ? "green" : "orange"}>
                  {detail.is_synced ? "synced" : "pending sync"}
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            <Title level={5}>Parts Used</Title>
            {detail.parts_used?.length ? (
              <List
                size="small"
                dataSource={detail.parts_used}
                renderItem={(p: any) => (
                  <List.Item>{p.description || p.item_id} × {p.quantity}</List.Item>
                )}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No parts used" />
            )}

            <Title level={5} style={{ marginTop: 16 }}>Photos</Title>
            {detail.photo_urls?.length ? (
              <Image.PreviewGroup>
                <Space wrap>
                  {detail.photo_urls.map((u: string, i: number) => (
                    <Image key={i} width={96} src={u} />
                  ))}
                </Space>
              </Image.PreviewGroup>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No photos" />
            )}

            {detail.signature_url && (
              <>
                <Title level={5} style={{ marginTop: 16 }}>Customer Signature</Title>
                <Image width={200} src={detail.signature_url} />
              </>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}
