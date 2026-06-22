import { useEffect, useState } from "react";
import { Table, Tag, Typography, Button, Modal, Form, Input, Select, DatePicker, InputNumber } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import apiClient from "../api/client";
import dayjs from "dayjs";

const { Title } = Typography;
const { Option } = Select;

interface Invoice {
  id: string;
  invoice_number: string;
  customer_id: string;
  status: string;
  invoice_date: string;
  due_date: string | null;
  total_amount: number;
  amount_paid: number;
  notes: string | null;
}

interface Customer { id: string; name: string; }

const statusColor: Record<string, string> = {
  draft: "default", sent: "blue", paid: "green",
  partially_paid: "orange", overdue: "red", cancelled: "volcano",
};

export default function InvoicesPage() {
  const [items, setItems] = useState<Invoice[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [invRes, custRes] = await Promise.all([apiClient.get("/invoices"), apiClient.get("/customers")]);
      setItems(invRes.data);
      setCustomers(custRes.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const custMap = Object.fromEntries(customers.map(c => [c.id, c.name]));

  const handleAdd = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/invoices", {
        ...values,
        invoice_date: values.invoice_date.format("YYYY-MM-DD"),
        due_date: values.due_date?.format("YYYY-MM-DD") ?? null,
        line_items: [{ description: values.description, quantity: 1, unit_price: values.amount, amount: values.amount }],
      });
      form.resetFields();
      setOpen(false);
      load();
    } finally { setSaving(false); }
  };

  const columns = [
    { title: "Invoice #", dataIndex: "invoice_number", key: "inv" },
    { title: "Customer", dataIndex: "customer_id", key: "cust", render: (v: string) => custMap[v] ?? "—" },
    {
      title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v.replace("_", " ")}</Tag>,
    },
    { title: "Invoice Date", dataIndex: "invoice_date", key: "idate", render: (v: string) => dayjs(v).format("DD MMM YYYY") },
    { title: "Due Date", dataIndex: "due_date", key: "ddate", render: (v: string) => v ? dayjs(v).format("DD MMM YYYY") : "—" },
    { title: "Total (₹)", dataIndex: "total_amount", key: "total", render: (v: number) => Number(v).toLocaleString("en-IN") },
    { title: "Paid (₹)", dataIndex: "amount_paid", key: "paid", render: (v: number) => Number(v).toLocaleString("en-IN") },
    {
      title: "Balance (₹)", key: "bal",
      render: (_: any, r: Invoice) => {
        const bal = Number(r.total_amount) - Number(r.amount_paid);
        return <span style={{ color: bal > 0 ? "#f5222d" : "#52c41a" }}>{bal.toLocaleString("en-IN")}</span>;
      },
    },
    { title: "Notes", dataIndex: "notes", key: "notes", ellipsis: true, render: (v: string) => v || "—" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Invoices</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>New Invoice</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} scroll={{ x: true }} />

      <Modal title="New Invoice" open={open} onOk={handleAdd} onCancel={() => setOpen(false)} confirmLoading={saving} width={520}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children" placeholder="Select customer">
              {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="invoice_date" label="Invoice Date" rules={[{ required: true }]} initialValue={dayjs()}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="due_date" label="Due Date">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="description" label="Description" rules={[{ required: true }]}>
            <Input placeholder="e.g. AMC Q2 charges" />
          </Form.Item>
          <Form.Item name="amount" label="Amount (₹)" rules={[{ required: true }]}>
            <InputNumber style={{ width: "100%" }} min={0} precision={2} />
          </Form.Item>
          <Form.Item name="notes" label="Notes"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
