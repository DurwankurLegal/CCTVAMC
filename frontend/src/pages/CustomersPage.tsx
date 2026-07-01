import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message, Tooltip } from "antd";
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

import { useParsedSearchParams } from "../utils/navigation";
import { useNavigate } from "react-router-dom";

export default function CustomersPage() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { items, loading } = useSelector((s: RootState) => s.customers);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  
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
        message.success("Customer created; redirecting to create contract...");
        setTimeout(() => {
          navigate(`/amc?create=true&customer_name=${encodeURIComponent(values.name)}`);
        }, 800);
      }
      form.resetFields();
      setOpen(false);
    } catch (e: any) {
      if (e?.errorFields) return; // inline field errors already shown
      message.error(typeof e === "string" ? e : e?.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "Category", dataIndex: "category", key: "category", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Mobile number", dataIndex: "phone", key: "phone", render: (v: string) => v || "—" },
    { title: "Email", dataIndex: "email", key: "email", render: (v: string) => v || "—" },
    {
      title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v ?? "active"}</Tag>,
    },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, row: Row) => (
        <Space size="small">
          <Tooltip title="Edit Customer">
            <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openEdit(row)} />
          </Tooltip>
          <Tooltip title="Create AMC Contract">
            <Button
              size="small"
              type="text"
              icon={<PlusOutlined />}
              onClick={() => navigate(`/amc?create=true&customer_name=${encodeURIComponent(row.name)}`)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Customers</Title>
      </div>

      <Button
        type="primary"
        shape="circle"
        icon={<PlusOutlined />}
        onClick={openCreate}
        size="large"
        style={{
          position: "fixed",
          bottom: 32,
          right: 32,
          width: 56,
          height: 56,
          zIndex: 1000,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "22px"
        }}
        title="Add Customer"
      />

      <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} />

      <Modal centered
        title={
          <div style={{ fontSize: "18px", fontWeight: 600, color: "#111827", paddingBottom: "12px", borderBottom: "1px solid #f3f4f6" }}>
            {editing ? "Edit Customer" : "Add New Customer"}
          </div>
        }
        open={open}
        onOk={handleSave}
        onCancel={() => setOpen(false)}
        confirmLoading={saving}
        className="scrolling-modal"
        okText={editing ? "Save" : "Create"}
        okButtonProps={{ size: "large", style: { borderRadius: "6px" } }}
        cancelButtonProps={{ size: "large", style: { borderRadius: "6px" } }}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 20 }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="Category" rules={[{ required: true }]}>
            <Select disabled={!!editing}>
              {CATEGORIES.map(c => <Option key={c.value} value={c.value}>{c.label}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="status" label="Status" rules={[{ required: true, message: "Please select status" }]}>
            <Select>{STATUSES.map(s => <Option key={s.value} value={s.value}>{s.label}</Option>)}</Select>
          </Form.Item>
          <Form.Item 
            name="phone" 
            label="Mobile number" 
            rules={[
              { required: true, message: "Please enter mobile number" },
              { pattern: /^\d{10}$/, message: "Please enter exactly 10 digits" }
            ]}
          >
            <Input 
              placeholder="10 digits accepted" 
              maxLength={10} 
              onKeyPress={(e) => { if (!/[0-9]/.test(e.key)) e.preventDefault(); }} 
            />
          </Form.Item>
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: "Please enter email address" },
              { type: "email", message: "Enter a valid email address" },
              { pattern: /^[a-zA-Z0-9@.]+$/, message: "Special characters are not allowed (only @ and .)" }
            ]}
          >
            <Input 
              type="email" 
              onKeyPress={(e) => {
                if (!/^[a-zA-Z0-9@.]+$/.test(e.key)) {
                  e.preventDefault();
                }
              }}
            />
          </Form.Item>
          <Form.Item name="address" label="Address"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item 
            name="contact_person_name" 
            label="Contact Person"
            rules={[
              { required: true, message: "Please enter contact person name" },
              { pattern: /^[A-Za-z\s]+$/, message: "Only alphabets and spaces are allowed" }
            ]}
          >
            <Input 
              onKeyPress={(e) => {
                if (!/^[A-Za-z\s]+$/.test(e.key)) {
                  e.preventDefault();
                }
              }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
