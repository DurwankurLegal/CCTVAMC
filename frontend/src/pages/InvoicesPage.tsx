import { useEffect, useState } from "react";
import { Table, Tag, Typography, Button, Modal, Form, Input, Select, DatePicker, InputNumber, Space, message } from "antd";
import { PlusOutlined, EditOutlined } from "@ant-design/icons";
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
  draft: "default", issued: "blue", paid: "green",
  partially_paid: "orange", cancelled: "volcano", credit_note: "purple",
};
const STATUSES = ["draft", "issued", "paid", "partially_paid", "cancelled"];

import { useSearchParams } from "react-router-dom";

export default function InvoicesPage() {
  const [items, setItems] = useState<Invoice[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Invoice | null>(null);
  const [form] = Form.useForm();

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
    if (statusParam && item.status !== statusParam) return false;
    
    if (isDefaulter) {
      const isOverdue = item.status === "overdue";
      const hasDefaulterNote = item.notes?.includes("DEFAULTER");
      const isOverdue45 = overdueDays(item) > 45;
      if (!isOverdue || !(hasDefaulterNote || isOverdue45)) return false;
    }
    return true;
  });

  const custMap = Object.fromEntries(customers.map(c => [c.id, c.name]));

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
        // InvoiceUpdate accepts status / due_date / notes only.
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
    {
      title: "Actions", key: "actions",
      render: (_: any, row: Invoice) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Edit</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Invoices</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>New Invoice</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} scroll={{ x: true }} />

      <Modal
        title={editing ? `Edit ${editing.invoice_number}` : "New Invoice"}
        open={open} onOk={handleSave} onCancel={() => setOpen(false)} confirmLoading={saving} width={520}
        okText={editing ? "Save" : "Create"}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {editing ? (
            <Form.Item name="status" label="Status">
              <Select>{STATUSES.map(s => <Option key={s} value={s}>{s.replace("_", " ")}</Option>)}</Select>
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
    </div>
  );
}
