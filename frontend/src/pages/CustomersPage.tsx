import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Space, Typography } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { fetchCustomers, createCustomer } from "../store/customerSlice";
import type { AppDispatch, RootState } from "../store";

const { Title } = Typography;
const { Option } = Select;

export default function CustomersPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { items, loading } = useSelector((s: RootState) => s.customers);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => { dispatch(fetchCustomers()); }, [dispatch]);

  const handleAdd = async () => {
    const values = await form.validateFields();
    setSaving(true);
    await dispatch(createCustomer({ ...values, is_active: true }));
    setSaving(false);
    form.resetFields();
    setOpen(false);
  };

  const columns = [
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "Category", dataIndex: "category", key: "category", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Phone", dataIndex: "phone", key: "phone", render: (v: string) => v || "—" },
    { title: "Email", dataIndex: "email", key: "email", render: (v: string) => v || "—" },
    {
      title: "Status", dataIndex: "is_active", key: "is_active",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "Active" : "Inactive"}</Tag>,
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Customers</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Add Customer</Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />

      <Modal title="Add Customer" open={open} onOk={handleAdd} onCancel={() => setOpen(false)} confirmLoading={saving}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="Category" rules={[{ required: true }]}>
            <Select>
              <Option value="residential">Residential</Option>
              <Option value="commercial">Commercial</Option>
              <Option value="society">Society</Option>
              <Option value="government">Government</Option>
            </Select>
          </Form.Item>
          <Form.Item name="phone" label="Phone">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>
          <Form.Item name="address" label="Address">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="contact_person_name" label="Contact Person">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
