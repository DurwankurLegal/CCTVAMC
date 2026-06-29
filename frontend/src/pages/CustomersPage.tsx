import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message, Card, ConfigProvider, theme } from "antd";
import { PlusOutlined, EditOutlined, FileOutlined, UserOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import DocumentModal from "../components/DocumentModal";
import { fetchCustomers, createCustomer, updateCustomer } from "../store/customerSlice";
import type { AppDispatch, RootState } from "../store";

const { Title, Text } = Typography;
const { Option } = Select;

const CATEGORIES = [
  { value: "chs", label: "Cooperative Housing Society" },
  { value: "commercial", label: "Commercial" },
  { value: "single_shop", label: "Single Shop" },
];
const STATUSES = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "amc_expired", label: "AMC Expired" },
  { value: "prospect", label: "Prospect" },
];
const statusColor: Record<string, string> = {
  active: "green", inactive: "red", amc_expired: "orange", prospect: "blue",
};

interface Row { id: string; name: string; category: string; status?: string; phone?: string; email?: string; }

import { useParsedSearchParams } from "../utils/navigation";

export default function CustomersPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { items, loading } = useSelector((s: RootState) => s.customers);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  // Document modal state
  const [docsOpen, setDocsOpen] = useState(false);
  const [selectedCustomerForDocs, setSelectedCustomerForDocs] = useState<Row | null>(null);
  
  const { status, category } = useParsedSearchParams();

  useEffect(() => { dispatch(fetchCustomers()); }, [dispatch]);

  const filteredItems = items.filter(item => {
    if (status && (item.status || "active") !== status) return false;
    if (category && item.category !== category) return false;
    return true;
  });

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ status: "active" }); setOpen(true); };
  const openEdit = (row: Row) => { setEditing(row); form.setFieldsValue(row); setOpen(true); };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await dispatch(updateCustomer({ id: editing.id, changes: values })).unwrap();
        message.success("Customer updated");
      } else {
        await dispatch(createCustomer({ ...values, is_active: true })).unwrap();
        message.success("Customer created");
      }
      form.resetFields();
      setOpen(false);
    } catch (e: any) {
      // Form validation errors are objects (errorFields); thrown thunk errors
      // arrive as a readable string via rejectWithValue.
      if (e?.errorFields) return; // inline field errors already shown
      message.error(typeof e === "string" ? e : e?.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "Category", dataIndex: "category", key: "category", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Phone", dataIndex: "phone", key: "phone", render: (v: string) => v || "—" },
    { title: "Email", dataIndex: "email", key: "email", render: (v: string) => v || "—" },
    {
      title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v ?? "active"}</Tag>,
    },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, row: Row) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Edit</Button>
          <Button
            size="small"
            icon={<FileOutlined />}
            onClick={() => {
              setSelectedCustomerForDocs(row);
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 4 }}>
          <div>
            <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
              <UserOutlined style={{ color: "#10b981" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #34d399 0%, #10b981 50%, #059669 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Customers Registry
              </span>
            </Title>
            <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
              Manage corporate housing societies, commercial entities, and retail shop customer records.
            </Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #10b981 0%, #059669 100%)", border: "none", color: "#fff" }}>Add Customer</Button>
        </div>

        <Card
          id="customers-ledger-panel"
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
              <UserOutlined style={{ color: "#10b981", fontSize: 18 }} />
              <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
                Customer Database
              </span>
              <Tag color="green" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(16, 185, 129, 0.12)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                CUSTOMER RECORDS
              </Tag>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} />
        </Card>

        <Modal
          title={editing ? "Edit Customer" : "Add Customer"}
          open={open} onOk={handleSave} onCancel={() => setOpen(false)} confirmLoading={saving}
          okText={editing ? "Save" : "Create"}
        >
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item name="name" label="Name" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="category" label="Category" rules={[{ required: true }]}>
              <Select disabled={!!editing}>
                {CATEGORIES.map(c => <Option key={c.value} value={c.value}>{c.label}</Option>)}
              </Select>
            </Form.Item>
            <Form.Item name="status" label="Status">
              <Select>{STATUSES.map(s => <Option key={s.value} value={s.value}>{s.label}</Option>)}</Select>
            </Form.Item>
            <Form.Item name="phone" label="Phone"><Input /></Form.Item>
            <Form.Item name="email" label="Email" rules={[{ type: "email", message: "Enter a valid email address" }]}>
              <Input type="email" />
            </Form.Item>
            <Form.Item name="address" label="Address"><Input.TextArea rows={2} /></Form.Item>
            <Form.Item name="contact_person_name" label="Contact Person"><Input /></Form.Item>
          </Form>
        </Modal>

        <DocumentModal
          open={docsOpen}
          entityType="customer"
          entityId={selectedCustomerForDocs?.id || null}
          entityName={selectedCustomerForDocs?.name || ""}
          onClose={() => setDocsOpen(false)}
        />
      </div>
    </ConfigProvider>
  );
}
