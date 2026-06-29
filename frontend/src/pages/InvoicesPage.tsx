import { useEffect, useState } from "react";
import { Table, Tag, Typography, Button, Modal, Form, Input, Select, DatePicker, InputNumber, Space, message, Row, Col, ConfigProvider, theme, Card } from "antd";
import { PlusOutlined, EditOutlined, DollarOutlined, CheckCircleOutlined, ExclamationCircleOutlined, FileOutlined } from "@ant-design/icons";
import apiClient from "../api/client";
import dayjs from "dayjs";
import { useSearchParams } from "react-router-dom";
import SmartCard from "../components/SmartCard";
import DocumentModal from "../components/DocumentModal";

const { Title, Text } = Typography;
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
  draft: "default", issued: "blue", paid: "green",
  partially_paid: "orange", cancelled: "volcano", credit_note: "purple",
  overdue: "red",
};
const STATUSES = ["draft", "issued", "paid", "partially_paid", "cancelled"];

export default function InvoicesPage() {
  const [items, setItems] = useState<Invoice[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Invoice | null>(null);
  const [form] = Form.useForm();

  // Document modal state
  const [docsOpen, setDocsOpen] = useState(false);
  const [selectedInvoiceForDocs, setSelectedInvoiceForDocs] = useState<Invoice | null>(null);

  const [searchParams] = useSearchParams();
  const statusParam = searchParams.get("status");
  const isDefaulter = searchParams.get("defaulter") === "true";

  const load = async () => {
    setLoading(true);
    try {
      const [invRes, custRes] = await Promise.all([apiClient.get("/invoices"), apiClient.get("/customers")]);
      setItems(invRes.data);
      setCustomers(custRes.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const today = new Date();
  const overdueDays = (i: Invoice) => i.due_date ? Math.floor((today.getTime() - new Date(i.due_date).getTime()) / 86400000) : 0;

  const filteredItems = items.filter(item => {
    const isOverdue = ["issued", "partially_paid"].includes(item.status) && overdueDays(item) > 0;
    
    if (statusParam) {
      if (statusParam === "overdue") {
        if (!isOverdue) return false;
      } else if (item.status !== statusParam) {
        return false;
      }
    }
    
    if (isDefaulter) {
      const hasDefaulterNote = item.notes?.includes("DEFAULTER");
      const isOverdue45 = overdueDays(item) > 45;
      if (!isOverdue || !(hasDefaulterNote || isOverdue45)) return false;
    }
    return true;
  });

  const custMap = Object.fromEntries(customers.map(c => [c.id, c.name]));

  // Calculate totals
  const totalBilled = filteredItems.reduce((acc, curr) => acc + Number(curr.total_amount), 0);
  const totalCollected = filteredItems.reduce((acc, curr) => acc + Number(curr.amount_paid), 0);
  const totalOutstanding = filteredItems
    .filter(i => ["issued", "partially_paid"].includes(i.status))
    .reduce((acc, curr) => acc + (Number(curr.total_amount) - Number(curr.amount_paid)), 0);
  const overdueInvoices = filteredItems.filter(item => 
    ["issued", "partially_paid"].includes(item.status) && overdueDays(item) > 0
  ).length;

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ invoice_date: dayjs() }); setOpen(true); };
  const openEdit = (row: Invoice) => {
    setEditing(row);
    form.setFieldsValue({ status: row.status, due_date: row.due_date ? dayjs(row.due_date) : null, notes: row.notes });
    setOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await apiClient.patch(`/invoices/${editing.id}`, {
          status: values.status,
          due_date: values.due_date?.format("YYYY-MM-DD") ?? null,
          notes: values.notes,
        });
        message.success("Invoice updated");
      } else {
        await apiClient.post("/invoices", {
          ...values,
          invoice_date: values.invoice_date.format("YYYY-MM-DD"),
          due_date: values.due_date?.format("YYYY-MM-DD") ?? null,
          line_items: [{ description: values.description, quantity: 1, unit_price: values.amount, amount: values.amount }],
        });
        message.success("Invoice created");
      }
      form.resetFields();
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  const columns = [
    { title: "Invoice #", dataIndex: "invoice_number", key: "inv", render: (v: string) => <span style={{ fontWeight: 600, color: "#3b82f6" }}>{v}</span> },
    { title: "Customer", dataIndex: "customer_id", key: "cust", render: (v: string) => custMap[v] ?? "—" },
    {
      title: "Status", dataIndex: "status", key: "status",
      render: (v: string, record: Invoice) => {
        let displayStatus = v;
        const isOverdue = ["issued", "partially_paid"].includes(record.status) && 
          record.due_date && (new Date(record.due_date).getTime() < new Date().setHours(0,0,0,0));
        if (isOverdue) displayStatus = "overdue";
        return <Tag color={statusColor[displayStatus] ?? "default"}>{displayStatus.replace("_", " ").toUpperCase()}</Tag>;
      }
    },
    { title: "Invoice Date", dataIndex: "invoice_date", key: "idate", render: (v: string) => dayjs(v).format("DD MMM YYYY") },
    { title: "Due Date", dataIndex: "due_date", key: "ddate", render: (v: string) => v ? dayjs(v).format("DD MMM YYYY") : "—" },
    { title: "Total (₹)", dataIndex: "total_amount", key: "total", align: "right" as const, render: (v: number) => <span style={{ fontWeight: 600 }}>{Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span> },
    { title: "Paid (₹)", dataIndex: "amount_paid", key: "paid", align: "right" as const, render: (v: number) => <span style={{ color: "#10b981", fontWeight: 600 }}>{Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span> },
    {
      title: "Balance (₹)", key: "bal",
      align: "right" as const,
      render: (_: any, r: Invoice) => {
        const bal = Number(r.total_amount) - Number(r.amount_paid);
        return <span style={{ color: bal > 0 ? "#f59e0b" : "#10b981", fontWeight: 600 }}>{bal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>;
      },
    },
    { title: "Notes", dataIndex: "notes", key: "notes", ellipsis: true, render: (v: string) => v || "—" },
    {
      title: "Actions", key: "actions",
      render: (_: any, row: Invoice) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Edit</Button>
          <Button
            size="small"
            icon={<FileOutlined />}
            onClick={() => {
              setSelectedInvoiceForDocs(row);
              setDocsOpen(true);
            }}
          >
            Docs
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <ConfigProvider theme={{}}>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Header Block */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 4 }}>
          <div>
            <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
              <DollarOutlined style={{ color: "#3b82f6" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Invoices Ledger
              </span>
            </Title>
            <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
              Track customer billing records, outstanding balances, and invoice ageings.
            </Text>
          </div>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={openCreate}
            style={{
              background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
              border: "none",
              color: "#fff"
            }}
          >
            New Invoice
          </Button>
        </div>

        {/* KPI Cards Row */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <SmartCard
              title="Total Invoiced"
              value={`₹${totalBilled.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
              prefix={<DollarOutlined />}
              status="info"
              loading={loading}
            />
          </Col>
          <Col xs={24} sm={8}>
            <SmartCard
              title="Total Collected"
              value={`₹${totalCollected.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
              prefix={<CheckCircleOutlined />}
              status="success"
              loading={loading}
            />
          </Col>
          <Col xs={24} sm={8}>
            <SmartCard
              title="Outstanding Receivables"
              value={`₹${totalOutstanding.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
              prefix={<ExclamationCircleOutlined />}
              status="warning"
              suffix={overdueInvoices ? <Tag color="red" style={{ margin: 0, marginLeft: 8 }}>{overdueInvoices} OVERDUE</Tag> : undefined}
              loading={loading}
            />
          </Col>
        </Row>

        {/* Table inside glass Card */}
        <Card
          id="invoices-ledger-panel"
          className="glass-card"
          styles={{
            header: {
              background: "linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0.02) 100%)",
              borderBottom: "1px solid rgba(59, 130, 246, 0.15)",
              borderRadius: "12px 12px 0 0"
            },
            body: { padding: 0 }
          }}
          title={
            <Space>
              <DollarOutlined style={{ color: "#3b82f6", fontSize: 18 }} />
              <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
                Invoices Ledger Records
              </span>
              <Tag color="blue" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(59, 130, 246, 0.12)", border: "1px solid rgba(59, 130, 246, 0.2)" }}>
                BILLING &amp; RECEIVABLES
              </Tag>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} scroll={{ x: true }} />
        </Card>

        {/* Modal Form */}
        <Modal
          title={editing ? `Edit ${editing.invoice_number}` : "New Invoice"}
          open={open} onOk={handleSave} onCancel={() => setOpen(false)} confirmLoading={saving} width={520}
          okText={editing ? "Save" : "Create"}
        >
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            {editing ? (
              <Form.Item name="status" label="Status">
                <Select>{STATUSES.map(s => <Option key={s} value={s}>{s.replace("_", " ").toUpperCase()}</Option>)}</Select>
              </Form.Item>
            ) : (
              <>
                <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
                  <Select showSearch optionFilterProp="children" placeholder="Select customer">
                    {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
                  </Select>
                </Form.Item>
                <Form.Item name="invoice_date" label="Invoice Date" rules={[{ required: true }]} initialValue={dayjs()}>
                  <DatePicker style={{ width: "100%" }} />
                </Form.Item>
              </>
            )}
            <Form.Item name="due_date" label="Due Date">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            {!editing && (
              <>
                <Form.Item name="description" label="Description" rules={[{ required: true }]}>
                  <Input placeholder="e.g. AMC Q2 charges" />
                </Form.Item>
                <Form.Item name="amount" label="Amount (₹)" rules={[{ required: true }]}>
                  <InputNumber style={{ width: "100%" }} min={0} precision={2} />
                </Form.Item>
              </>
            )}
            <Form.Item name="notes" label="Notes"><Input.TextArea rows={2} /></Form.Item>
          </Form>
        </Modal>

        <DocumentModal
          open={docsOpen}
          entityType="invoice"
          entityId={selectedInvoiceForDocs?.id || null}
          entityName={selectedInvoiceForDocs?.invoice_number || ""}
          onClose={() => setDocsOpen(false)}
        />
      </div>
    </ConfigProvider>
  );
}
