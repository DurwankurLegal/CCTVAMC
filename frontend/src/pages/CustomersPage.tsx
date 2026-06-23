import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message } from "antd";
import { PlusOutlined, EditOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { fetchCustomers, createCustomer, updateCustomer } from "../store/customerSlice";
import type { AppDispatch, RootState } from "../store";

const { Title } = Typography;
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

export default function CustomersPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { items, loading } = useSelector((s: RootState) => s.customers);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => { dispatch(fetchCustomers()); }, [dispatch]);

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
      message.error(e?.message || "Save failed");
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
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Customers</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Add Customer</Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />

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
          <Form.Item name="email" label="Email"><Input type="email" /></Form.Item>
          <Form.Item name="address" label="Address"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="contact_person_name" label="Contact Person"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
