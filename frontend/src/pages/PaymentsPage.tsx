import { useEffect, useState } from "react";
import { Table, Tag, Typography, Button, Modal, Form, Select, DatePicker, InputNumber, Input } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import apiClient from "../api/client";
import dayjs from "dayjs";

const { Title } = Typography;
const { Option } = Select;

interface Payment {
  id: string;
  invoice_id: string;
  customer_id: string;
  amount: number;
  payment_date: string;
  mode: string;
  reference_number: string | null;
  notes: string | null;
}

interface Customer { id: string; name: string; }
interface Invoice { id: string; invoice_number: string; customer_id: string; total_amount: number; }

const modeColor: Record<string, string> = { cash: "gold", neft: "blue", upi: "purple", cheque: "cyan", rtgs: "geekblue" };

export default function PaymentsPage() {
  const [items, setItems] = useState<Payment[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [filteredInvoices, setFilteredInvoices] = useState<Invoice[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const [payRes, custRes, invRes] = await Promise.all([
        apiClient.get("/payments"), apiClient.get("/customers"), apiClient.get("/invoices"),
      ]);
      setItems(payRes.data);
      setCustomers(custRes.data);
      setInvoices(invRes.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const custMap = Object.fromEntries(customers.map(c => [c.id, c.name]));
  const invMap = Object.fromEntries(invoices.map(i => [i.id, i.invoice_number]));

  const handleAdd = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/payments", {
        ...values,
        payment_date: values.payment_date.format("YYYY-MM-DD"),
      });
      form.resetFields();
      setOpen(false);
      load();
    } finally { setSaving(false); }
  };

  const onCustomerChange = (custId: string) => {
    setFilteredInvoices(invoices.filter(i => i.customer_id === custId));
    form.setFieldValue("invoice_id", undefined);
  };

  const columns = [
    { title: "Customer", dataIndex: "customer_id", key: "cust", render: (v: string) => custMap[v] ?? "—" },
    { title: "Invoice #", dataIndex: "invoice_id", key: "inv", render: (v: string) => invMap[v] ?? "—" },
    { title: "Amount (₹)", dataIndex: "amount", key: "amt", render: (v: number) => Number(v).toLocaleString("en-IN") },
    { title: "Date", dataIndex: "payment_date", key: "date", render: (v: string) => dayjs(v).format("DD MMM YYYY") },
    { title: "Mode", dataIndex: "mode", key: "mode", render: (v: string) => <Tag color={modeColor[v] ?? "default"}>{v.toUpperCase()}</Tag> },
    { title: "Reference", dataIndex: "reference_number", key: "ref", render: (v: string) => v || "—" },
    { title: "Notes", dataIndex: "notes", key: "notes", ellipsis: true, render: (v: string) => v || "—" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Payments</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Record Payment</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />

      <Modal title="Record Payment" open={open} onOk={handleAdd} onCancel={() => { setOpen(false); setFilteredInvoices([]); }} confirmLoading={saving}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children" placeholder="Select customer" onChange={onCustomerChange}>
              {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="invoice_id" label="Invoice" rules={[{ required: true }]}>
            <Select placeholder="Select invoice" disabled={filteredInvoices.length === 0}>
              {filteredInvoices.map(i => <Option key={i.id} value={i.id}>{i.invoice_number} — ₹{Number(i.total_amount).toLocaleString("en-IN")}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="Amount (₹)" rules={[{ required: true }]}>
            <InputNumber style={{ width: "100%" }} min={0} precision={2} />
          </Form.Item>
          <Form.Item name="payment_date" label="Payment Date" rules={[{ required: true }]} initialValue={dayjs()}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="mode" label="Payment Mode" initialValue="upi">
            <Select>
              <Option value="cash">Cash</Option>
              <Option value="upi">UPI</Option>
              <Option value="neft">NEFT</Option>
              <Option value="rtgs">RTGS</Option>
              <Option value="cheque">Cheque</Option>
            </Select>
          </Form.Item>
          <Form.Item name="reference_number" label="Reference Number">
            <Input placeholder="UTR / Cheque no." />
          </Form.Item>
          <Form.Item name="notes" label="Notes"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
