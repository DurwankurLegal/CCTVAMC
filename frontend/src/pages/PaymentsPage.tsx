import { useEffect, useState } from "react";
import { Table, Tag, Typography, Button, Modal, Form, Select, DatePicker, InputNumber, Input, Space, message, Tabs, Card, Row, Col } from "antd";
import { PlusOutlined, EditOutlined, DownloadOutlined } from "@ant-design/icons";
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

// Must match backend PaymentMode enum.
const MODES = ["cash", "cheque", "neft", "upi", "card", "other"];
const modeColor: Record<string, string> = {
  cash: "gold", neft: "blue", upi: "purple", cheque: "cyan", card: "geekblue", other: "default",
};

export default function PaymentsPage() {
  const [items, setItems] = useState<Payment[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Payment | null>(null);
  const [form] = Form.useForm();
  const [filteredInvoices, setFilteredInvoices] = useState<Invoice[]>([]);

  const [activeTab, setActiveTab] = useState("payments");
  const [ageingData, setAgeingData] = useState<any[]>([]);
  const [loadingAgeing, setLoadingAgeing] = useState(false);

  const loadAgeing = async () => {
    setLoadingAgeing(true);
    try {
      const { data } = await apiClient.get("/payments/ageing");
      setAgeingData(data);
    } catch (e: any) {
      message.error("Failed to load ageing report");
    } finally {
      setLoadingAgeing(false);
    }
  };

  useEffect(() => {
    if (activeTab === "ageing") {
      loadAgeing();
    }
  }, [activeTab]);

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

  const downloadReceipt = async (paymentId: string) => {
    try {
      const response = await apiClient.get(`/payments/${paymentId}/receipt`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `receipt-${paymentId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success("Receipt downloaded successfully");
    } catch (e: any) {
      message.error("Failed to download receipt");
    }
  };

  useEffect(() => { load(); }, []);

  const custMap = Object.fromEntries(customers.map(c => [c.id, c.name]));
  const invMap = Object.fromEntries(invoices.map(i => [i.id, i.invoice_number]));

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ payment_date: dayjs(), mode: "upi" }); setOpen(true); };
  const openEdit = (row: Payment) => {
    setEditing(row);
    form.setFieldsValue({
      amount: row.amount,
      payment_date: row.payment_date ? dayjs(row.payment_date) : null,
      mode: row.mode,
      reference_number: row.reference_number,
      notes: row.notes,
    });
    setOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await apiClient.patch(`/payments/${editing.id}`, {
          amount: values.amount,
          payment_date: values.payment_date?.format("YYYY-MM-DD"),
          mode: values.mode,
          reference_number: values.reference_number,
          notes: values.notes,
        });
        message.success("Payment updated");
      } else {
        await apiClient.post("/payments", { ...values, payment_date: values.payment_date.format("YYYY-MM-DD") });
        message.success("Payment recorded");
      }
      form.resetFields();
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
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
    {
      title: "Actions", key: "actions",
      render: (_: any, row: Payment) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Edit</Button>
          <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadReceipt(row.id)}>Receipt</Button>
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: "payments",
      label: "Payments",
      children: <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />,
    },
    {
      key: "ageing",
      label: "Ageing",
      children: (
        <Card loading={loadingAgeing} data-testid="ageing">
          <Row gutter={16}>
            {ageingData.map((d: any) => (
              <Col span={6} key={d.bucket}>
                <Card title={d.bucket.replace("_", " ").toUpperCase()} bordered={false} style={{ textAlign: "center", background: "#fafafa" }}>
                  <Typography.Title level={3} style={{ margin: 0 }}>
                    ₹{Number(d.amount).toLocaleString("en-IN")}
                  </Typography.Title>
                  <Typography.Text type="secondary">{d.count} invoices</Typography.Text>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Payments</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Record Payment</Button>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

      <Modal
        title={editing ? "Edit Payment" : "Record Payment"}
        open={open} onOk={handleSave} onCancel={() => { setOpen(false); setFilteredInvoices([]); }} confirmLoading={saving}
        okText={editing ? "Save" : "Record"}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {!editing && (
            <>
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
            </>
          )}
          <Form.Item name="amount" label="Amount (₹)" rules={[{ required: true }]}>
            <InputNumber style={{ width: "100%" }} min={0} precision={2} />
          </Form.Item>
          <Form.Item name="payment_date" label="Payment Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="mode" label="Payment Mode">
            <Select>{MODES.map(m => <Option key={m} value={m}>{m.toUpperCase()}</Option>)}</Select>
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
