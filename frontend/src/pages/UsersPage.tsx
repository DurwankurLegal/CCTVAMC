import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message, Switch, Tooltip,
} from "antd";
import { PlusOutlined, EditOutlined, SafetyOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title, Text } = Typography;
const { Option } = Select;

const ROLES = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "coordinator", label: "Service Coordinator" },
  { value: "accounts", label: "Accounts" },
  { value: "technician", label: "Technician" },
  { value: "viewer", label: "Viewer" },
];
const roleColor: Record<string, string> = {
  admin: "red", manager: "volcano", coordinator: "blue", accounts: "green",
  technician: "geekblue", viewer: "default",
};

interface UserRow {
  id: string; email: string; full_name: string; phone?: string; role: string; is_active: boolean;
}
interface RoleInfo { key: string; permissions: string[] }

export default function UsersPage() {
  const [rows, setRows] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [roleInfo, setRoleInfo] = useState<Record<string, string[]>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get("/users", { params: { limit: 200 } });
      setRows(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    apiClient.get("/users/roles")
      .then(({ data }) => setRoleInfo(Object.fromEntries(data.roles.map((r: RoleInfo) => [r.key, r.permissions]))))
      .catch(() => { /* role catalogue is advisory */ });
  }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ role: "viewer" }); setOpen(true); };
  const openEdit = (row: UserRow) => { setEditing(row); form.setFieldsValue(row); setOpen(true); };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        const { password, email, ...changes } = values;
        await apiClient.patch(`/users/${editing.id}`, changes);
        message.success("User updated");
      } else {
        await apiClient.post("/users", values);
        message.success("User created");
      }
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (row: UserRow, active: boolean) => {
    try {
      await apiClient.patch(`/users/${row.id}`, { is_active: active });
      message.success(active ? "User activated" : "User deactivated");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Update failed");
    }
  };

  const columns = [
    { title: "Name", dataIndex: "full_name", key: "full_name" },
    { title: "Email", dataIndex: "email", key: "email" },
    { title: "Phone", dataIndex: "phone", key: "phone", render: (v?: string) => v || "—" },
    {
      title: "Role", dataIndex: "role", key: "role",
      render: (v: string) => (
        <Tooltip title={roleInfo[v] ? `Can access: ${roleInfo[v].join(", ")}` : undefined}>
          <Tag color={roleColor[v] ?? "default"} icon={<SafetyOutlined />}>{v}</Tag>
        </Tooltip>
      ),
    },
    {
      title: "Active", dataIndex: "is_active", key: "is_active",
      render: (v: boolean, row: UserRow) => (
        <Switch checked={v} size="small" onChange={(checked) => toggleActive(row, checked)} />
      ),
    },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, row: UserRow) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Edit</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Users & Roles</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Add User</Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} />

      <Modal title={editing ? "Edit User" : "Add User"} open={open} onOk={handleSave}
        onCancel={() => setOpen(false)} confirmLoading={saving} okText={editing ? "Save" : "Create"}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="full_name" label="Full Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: "email" }]}>
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item name="phone" label="Phone"><Input /></Form.Item>
          {!editing && (
            <Form.Item name="password" label="Password" rules={[{ required: true, min: 8 }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="role" label="Role" rules={[{ required: true }]}>
            <Select onChange={() => undefined}>
              {ROLES.map(r => <Option key={r.value} value={r.value}>{r.label}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item shouldUpdate={(p, c) => p.role !== c.role} style={{ marginBottom: 0 }}>
            {({ getFieldValue }) => {
              const perms = roleInfo[getFieldValue("role")];
              return perms ? (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Grants: {perms.join(", ")}
                </Text>
              ) : null;
            }}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
