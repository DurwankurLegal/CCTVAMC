import { useEffect, useState } from "react";
import { Table, Tag, Typography, Button, Modal, Form, Select, DatePicker, InputNumber, Input, Space, message, Tabs, Card, Row, Col, ConfigProvider, theme } from "antd";
import { PlusOutlined, EditOutlined, DownloadOutlined, DollarOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import apiClient from "../api/client";
import dayjs from "dayjs";

const { Title, Text } = Typography;
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
    { title: "Invoice #", dataIndex: "invoice_id", key: "inv", render: (v: string) => <span style={{ fontWeight: 600, color: "#3b82f6" }}>{invMap[v] ?? "—"}</span> },
    { title: "Amount (₹)", dataIndex: "amount", key: "amt", align: "right" as const, render: (v: number) => <span style={{ color: "#10b981", fontWeight: 600 }}>{Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span> },
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
      label: "Payments History",
      children: (
        <Card
          id="payments-history-panel"
          className="glass-card"
          styles={{
            header: {
              background: "linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.02) 100%)",
              borderBottom: "1px solid rgba(16, 185, 129, 0.15)",
              borderRadius: "12px 12px 0 0"
            },
            body: { padding: 0 }
          }}
          title={
            <Space>
              <CheckCircleOutlined style={{ color: "#10b981", fontSize: 18 }} />
              <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
                Payment Transactions History
              </span>
              <Tag color="green" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(16, 185, 129, 0.12)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                TRANSACTIONS LEDGER
              </Tag>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />
        </Card>
      ),
    },
    {
      key: "ageing",
      label: "Invoice Ageing Summary",
      children: (
        <Card
          id="invoice-ageing-panel"
          loading={loadingAgeing}
          data-testid="ageing"
          className="glass-card"
          styles={{
            header: {
              background: "linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(245, 158, 11, 0.02) 100%)",
              borderBottom: "1px solid rgba(245, 158, 11, 0.15)",
              borderRadius: "12px 12px 0 0"
            },
            body: { padding: "20px" }
          }}
          title={
            <Space>
              <ExclamationCircleOutlined style={{ color: "#f59e0b", fontSize: 18 }} />
              <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
                Outstanding Invoice Ageing Analysis
              </span>
              <Tag color="warning" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(245, 158, 11, 0.12)", border: "1px solid rgba(245, 158, 11, 0.2)" }}>
                AGEING BUCKETS
              </Tag>
            </Space>
          }
        >
          <Row gutter={[16, 16]}>
            {ageingData.map((d: any) => (
              <Col xs={24} sm={12} md={6} key={d.bucket}>
                <Card 
                  title={<span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{d.bucket.replace("_", " ").toUpperCase()}</span>} 
                  bordered={false} 
                  style={{ textAlign: "center", background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.04)" }}
                >
                  <Typography.Title level={3} style={{ margin: 0, color: "#f59e0b" }}>
                    ₹{Number(d.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </Typography.Title>
                  <Typography.Text style={{ color: "var(--text-secondary)" }}>{d.count} invoices</Typography.Text>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      ),
    },
  ];

  return (
    <ConfigProvider theme={{}}>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Header block */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 4 }}>
          <div>
            <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
              <CheckCircleOutlined style={{ color: "#10b981" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Payments Ledger
              </span>
            </Title>
            <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
              Record customer billing receipts and track historical payment distributions.
            </Text>
          </div>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={openCreate}
            style={{
              background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
              border: "none",
              color: "#fff"
            }}
          >
            Record Payment
          </Button>
        </div>

        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

        {/* Modal Form */}
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
    </ConfigProvider>
  );
}
