import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Typography, DatePicker } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import apiClient from "../api/client";
import dayjs from "dayjs";

const { Title } = Typography;
const { Option } = Select;

interface Lead {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  source: string;
  status: string;
  notes: string | null;
  follow_up_date: string | null;
  converted_customer_id: string | null;
}

const statusColor: Record<string, string> = {
  new: "blue", contacted: "cyan", qualified: "purple",
  converted: "green", lost: "red",
};

export default function LeadsPage() {
  const [items, setItems] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try { const { data } = await apiClient.get("/leads"); setItems(data); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleAdd = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/leads", {
        ...values,
        follow_up_date: values.follow_up_date?.format("YYYY-MM-DD") ?? null,
      });
      form.resetFields();
      setOpen(false);
      load();
    } finally { setSaving(false); }
  };

  const columns = [
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "Phone", dataIndex: "phone", key: "phone", render: (v: string) => v || "—" },
    { title: "Email", dataIndex: "email", key: "email", render: (v: string) => v || "—" },
    { title: "Source", dataIndex: "source", key: "source", render: (v: string) => <Tag>{v}</Tag> },
    {
      title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v}</Tag>,
    },
    {
      title: "Follow-up Date", dataIndex: "follow_up_date", key: "fud",
      render: (v: string) => v ? dayjs(v).format("DD MMM YYYY") : "—",
    },
    { title: "Notes", dataIndex: "notes", key: "notes", ellipsis: true, render: (v: string) => v || "—" },
    {
      title: "Converted", dataIndex: "converted_customer_id", key: "conv",
      render: (v: string) => v ? <Tag color="green">Yes</Tag> : <Tag>No</Tag>,
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Leads</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Add Lead</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />
      <Modal title="Add Lead" open={open} onOk={handleAdd} onCancel={() => setOpen(false)} confirmLoading={saving}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="phone" label="Phone"><Input /></Form.Item>
          <Form.Item name="email" label="Email"><Input type="email" /></Form.Item>
          <Form.Item name="source" label="Source" initialValue="referral">
            <Select>
              <Option value="referral">Referral</Option>
              <Option value="website">Website</Option>
              <Option value="walk_in">Walk-in</Option>
              <Option value="cold_call">Cold Call</Option>
              <Option value="exhibition">Exhibition</Option>
              <Option value="other">Other</Option>
            </Select>
          </Form.Item>
          <Form.Item name="follow_up_date" label="Follow-up Date">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="notes" label="Notes"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
