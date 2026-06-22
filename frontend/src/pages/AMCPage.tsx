import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, InputNumber, Select, Tag, Typography, DatePicker } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useSelector } from "react-redux";
import apiClient from "../api/client";
import type { RootState } from "../store";
import dayjs from "dayjs";

const { Title } = Typography;
const { Option } = Select;

interface AMCContract {
  id: string;
  contract_number: string;
  customer_id: string;
  status: string;
  start_date: string;
  end_date: string;
  annual_amount: number;
  payment_frequency: string | null;
  is_active: boolean;
}

export default function AMCPage() {
  const [items, setItems] = useState<AMCContract[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const customers = useSelector((s: RootState) => s.customers.items);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get("/amc");
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleAdd = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/amc", {
        ...values,
        start_date: values.start_date.format("YYYY-MM-DD"),
        end_date: values.end_date.format("YYYY-MM-DD"),
      });
      form.resetFields();
      setOpen(false);
      load();
    } finally {
      setSaving(false);
    }
  };

  const statusColor: Record<string, string> = { active: "green", expired: "red", cancelled: "orange", draft: "blue" };

  const columns = [
    { title: "Contract #", dataIndex: "contract_number", key: "contract_number" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v}</Tag> },
    { title: "Start", dataIndex: "start_date", key: "start_date" },
    { title: "End", dataIndex: "end_date", key: "end_date" },
    { title: "Annual Amount (₹)", dataIndex: "annual_amount", key: "annual_amount", render: (v: number) => v.toLocaleString("en-IN") },
    { title: "Frequency", dataIndex: "payment_frequency", key: "payment_frequency", render: (v: string) => v || "—" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>AMC Contracts</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>New Contract</Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />

      <Modal title="New AMC Contract" open={open} onOk={handleAdd} onCancel={() => setOpen(false)} confirmLoading={saving} width={560}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children" placeholder="Select customer">
              {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="start_date" label="Start Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="end_date" label="End Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} disabledDate={d => d && d < (form.getFieldValue("start_date") || dayjs())} />
          </Form.Item>
          <Form.Item name="annual_amount" label="Annual Amount (₹)" rules={[{ required: true }]}>
            <InputNumber style={{ width: "100%" }} min={0} />
          </Form.Item>
          <Form.Item name="payment_frequency" label="Payment Frequency">
            <Select allowClear>
              <Option value="monthly">Monthly</Option>
              <Option value="quarterly">Quarterly</Option>
              <Option value="annual">Annual</Option>
            </Select>
          </Form.Item>
          <Form.Item name="preventive_visits_per_year" label="Preventive Visits / Year">
            <InputNumber style={{ width: "100%" }} min={0} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
