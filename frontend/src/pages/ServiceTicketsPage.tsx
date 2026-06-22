import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Typography } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { fetchTickets } from "../store/ticketSlice";
import apiClient from "../api/client";
import type { AppDispatch, RootState } from "../store";

const { Title } = Typography;
const { Option } = Select;

export default function ServiceTicketsPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { items, loading } = useSelector((s: RootState) => s.tickets);
  const customers = useSelector((s: RootState) => s.customers.items);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => { dispatch(fetchTickets()); }, [dispatch]);

  const handleAdd = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/service-tickets", values);
      form.resetFields();
      setOpen(false);
      dispatch(fetchTickets());
    } finally {
      setSaving(false);
    }
  };

  const priorityColor: Record<string, string> = { low: "blue", medium: "orange", high: "red", critical: "purple" };
  const statusColor: Record<string, string> = { open: "blue", in_progress: "orange", resolved: "green", closed: "default", cancelled: "red" };

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
    { title: "Raised", dataIndex: "created_at", key: "created_at", render: (v: string) => new Date(v).toLocaleDateString("en-IN") },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Service Tickets</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Raise Ticket</Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />

      <Modal title="Raise Service Ticket" open={open} onOk={handleAdd} onCancel={() => setOpen(false)} confirmLoading={saving}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children" placeholder="Select customer">
              {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="priority" label="Priority" initialValue="medium">
            <Select>
              <Option value="low">Low</Option>
              <Option value="medium">Medium</Option>
              <Option value="high">High</Option>
              <Option value="critical">Critical</Option>
            </Select>
          </Form.Item>
          <Form.Item name="complaint" label="Complaint / Description" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
