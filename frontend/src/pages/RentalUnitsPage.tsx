import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, DatePicker, Card, ConfigProvider, theme
} from "antd";
import { AppstoreAddOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import apiClient from "../api/client";

const { Title, Text } = Typography;
const { Option } = Select;

const statusColors: Record<string, string> = {
  available: "green",
  reserved: "blue",
  on_rent: "purple",
  maintenance: "orange",
  retired: "red",
};

interface Product {
  id: string;
  sku: string;
  name: string;
}

interface RentalUnit {
  id: string;
  product_id: string;
  serial_number: string;
  condition?: string;
  status: string;
  purchase_cost?: number;
  purchase_date?: string;
  notes?: string;
  is_active: boolean;
}

export default function RentalUnitsPage() {
  const [rows, setRows] = useState<RentalUnit[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<RentalUnit | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const unitsRes = await apiClient.get("/rentals/units", { params: { limit: 200 } });
      setRows(unitsRes.data);
      const prodRes = await apiClient.get("/products", { params: { limit: 200 } });
      setProducts(prodRes.data.filter((p: any) => p.is_rentable && p.is_active));
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load rental units");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const getProductName = (id: string) => {
    return products.find(p => p.id === id)?.name || "Unknown SKU";
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      status: "available",
      condition: "new",
      purchase_date: dayjs()
    });
    setOpen(true);
  };

  const openEdit = (r: RentalUnit) => {
    setEditing(r);
    form.setFieldsValue({
      ...r,
      purchase_date: r.purchase_date ? dayjs(r.purchase_date) : null
    });
    setOpen(true);
  };

  const save = async () => {
    const v = await form.validateFields();
    const payload = {
      ...v,
      purchase_date: v.purchase_date ? v.purchase_date.format("YYYY-MM-DD") : null
    };
    setSaving(true);
    try {
      if (editing) {
        await apiClient.patch(`/rentals/units/${editing.id}`, payload);
      } else {
        await apiClient.post("/rentals/units", payload);
      }
      message.success("Saved");
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { title: "Serial Number", dataIndex: "serial_number", key: "serial_number" },
    { title: "Product SKU", dataIndex: "product_id", key: "product_id", render: getProductName },
    { title: "Condition", dataIndex: "condition", key: "condition", render: (v?: string) => v ? v.toUpperCase() : "—" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColors[v] ?? "default"}>{v.toUpperCase()}</Tag> },
    { title: "Cost", dataIndex: "purchase_cost", key: "purchase_cost", render: (v?: number) => v != null ? "₹" + v : "—" },
    { title: "Purchase Date", dataIndex: "purchase_date", key: "purchase_date", render: (v?: string) => v || "—" },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, r: RentalUnit) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>Edit</Button>
      ),
    },
  ];

  return (
    <ConfigProvider theme={{}}>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 4 }}>
          <div>
            <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
              <AppstoreAddOutlined style={{ color: "#8b5cf6" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Rental Inventory Registry
              </span>
            </Title>
            <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
              Add individual physical hardware items allocated for leasing, log condition changes, and audit deployment states.
            </Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)", border: "none", color: "#fff" }}>Add Rental Unit</Button>
        </div>

        <Card
          className="glass-card"
          styles={{
            header: {
              background: "linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(139, 92, 246, 0.02) 100%)",
              borderBottom: "1px solid rgba(139, 92, 246, 0.15)",
              borderRadius: "12px 12px 0 0"
            },
            body: { padding: 0 }
          }}
          title={
            <Space>
              <AppstoreAddOutlined style={{ color: "#8b5cf6", fontSize: 18 }} />
              <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
                Physical Serialized Inventory
              </span>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 100 }} />
        </Card>

        <Modal title={editing ? "Edit Rental Unit" : "Add Rental Unit"} open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText={editing ? "Save" : "Create"} width={500}>
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            {!editing && (
              <Form.Item name="product_id" label="Linked Rental Product" rules={[{ required: true, message: "Required" }]}>
                <Select placeholder="Select product type">
                  {products.map(p => <Option key={p.id} value={p.id}>{p.name} ({p.sku})</Option>)}
                </Select>
              </Form.Item>
            )}
            <Form.Item name="serial_number" label="Serial Number" rules={[{ required: true, message: "Required" }]}><Input /></Form.Item>
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="condition" label="Physical Condition">
                <Select>
                  <Option value="new">NEW</Option>
                  <Option value="good">GOOD</Option>
                  <Option value="fair">FAIR</Option>
                  <Option value="poor">POOR</Option>
                </Select>
              </Form.Item>
              <Form.Item name="status" label="Registry Status" rules={[{ required: true }]}>
                <Select>
                  <Option value="available">AVAILABLE</Option>
                  <Option value="reserved">RESERVED</Option>
                  <Option value="on_rent">ON RENT</Option>
                  <Option value="maintenance">MAINTENANCE</Option>
                  <Option value="retired">RETIRED</Option>
                </Select>
              </Form.Item>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="purchase_cost" label="Purchase Cost (₹)"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
              <Form.Item name="purchase_date" label="Purchase Date"><DatePicker style={{ width: "100%" }} /></Form.Item>
            </div>

            <Form.Item name="notes" label="Log Notes"><Input.TextArea rows={2} /></Form.Item>
          </Form>
        </Modal>
      </div>
    </ConfigProvider>
  );
}
