import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, Switch, Card, ConfigProvider, theme
} from "antd";
import { BarcodeOutlined, EditOutlined, PlusOutlined, ShoppingOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title, Text } = Typography;
const { Option } = Select;

const CATEGORIES = ["Camera", "DVR", "NVR", "Switch", "HDD", "Cable", "Accessory", "Other"];

interface InventoryItem {
  id: string;
  name: string;
}

interface Product {
  id: string;
  sku: string;
  name: string;
  brand?: string;
  model?: string;
  category?: string;
  hsn_code?: string;
  gst_rate?: number;
  sale_price?: number;
  rental_price?: number;
  is_serial_tracked: boolean;
  warranty_months: number;
  inventory_item_id?: string;
  is_sellable: boolean;
  is_rentable: boolean;
  is_active: boolean;
}

export default function ProductsPage() {
  const [rows, setRows] = useState<Product[]>([]);
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const prodRes = await apiClient.get("/products", { params: { limit: 200 } });
      setRows(prodRes.data);
      const invRes = await apiClient.get("/inventory", { params: { limit: 200 } });
      setInventoryItems(invRes.data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load products");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      is_serial_tracked: false,
      warranty_months: 0,
      is_sellable: true,
      is_rentable: false,
      gst_rate: 18.0,
    });
    setOpen(true);
  };

  const openEdit = (r: Product) => {
    setEditing(r);
    form.setFieldsValue(r);
    setOpen(true);
  };

  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await apiClient.patch(`/products/${editing.id}`, v);
      } else {
        await apiClient.post("/products", v);
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
    { title: "SKU", dataIndex: "sku", key: "sku" },
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "Category", dataIndex: "category", key: "category", render: (v?: string) => v || "—" },
    { title: "Brand", dataIndex: "brand", key: "brand", render: (v?: string) => v || "—" },
    {
      title: "Stock Link",
      dataIndex: "inventory_item_id",
      key: "inventory_item_id",
      render: (v?: string) => {
        const item = inventoryItems.find((i) => i.id === v);
        return item ? item.name : <Tag color="orange">Unlinked</Tag>;
      },
    },
    { title: "Sale Price", dataIndex: "sale_price", key: "sale_price", render: (v?: number) => v != null ? "₹" + v : "—" },
    { title: "Rental Price", dataIndex: "rental_price", key: "rental_price", render: (v?: number) => v != null ? "₹" + v + "/mo" : "—" },
    {
      title: "Capabilities",
      key: "capabilities",
      render: (_: unknown, r: Product) => (
        <Space>
          {r.is_sellable && <Tag color="blue">Sellable</Tag>}
          {r.is_rentable && <Tag color="purple">Rentable</Tag>}
          {r.is_serial_tracked && <Tag color="cyan">Serial-Tracked</Tag>}
        </Space>
      ),
    },
    { title: "Status", dataIndex: "is_active", key: "is_active", render: (v: boolean) => <Tag color={v ? "green" : "default"}>{v ? "active" : "inactive"}</Tag> },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, r: Product) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>Edit</Button>
      ),
    },
  ];

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorBgContainer: "#161c2d",
          colorBorder: "rgba(255, 255, 255, 0.08)",
          colorText: "#f3f4f6",
          colorTextSecondary: "#9ca3af",
          colorTextHeading: "#ffffff",
          colorPrimary: "#8b5cf6",
        },
        components: {
          Table: {
            headerBg: "rgba(255, 255, 255, 0.04)",
            headerColor: "#f3f4f6",
          }
        }
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 4 }}>
          <div>
            <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
              <BarcodeOutlined style={{ color: "#8b5cf6" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Product SKU Catalog
              </span>
            </Title>
            <Text style={{ color: "#9ca3af", fontSize: "13.5px" }}>
              Define equipment SKUs, configure pricing plans, serial number tracking settings, and map catalog items to warehouse inventory.
            </Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)", border: "none", color: "#fff" }}>Add Product</Button>
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
              <ShoppingOutlined style={{ color: "#8b5cf6", fontSize: 18 }} />
              <span style={{ color: "#f3f4f6", fontWeight: 700, fontSize: 15 }}>
                Master Products List
              </span>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 100 }} />
        </Card>

        <Modal title={editing ? "Edit Product" : "Add Product"} open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText={editing ? "Save" : "Create"} width={600}>
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="sku" label="SKU / Part Number" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="name" label="Product Name" rules={[{ required: true }]}><Input /></Form.Item>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
              <Form.Item name="brand" label="Brand"><Input /></Form.Item>
              <Form.Item name="model" label="Model"><Input /></Form.Item>
              <Form.Item name="category" label="Category">
                <Select>{CATEGORIES.map(c => <Option key={c} value={c.toLowerCase()}>{c}</Option>)}</Select>
              </Form.Item>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="hsn_code" label="HSN Code"><Input /></Form.Item>
              <Form.Item name="gst_rate" label="Default GST %" rules={[{ required: true }]}><InputNumber min={0} max={28} style={{ width: "100%" }} /></Form.Item>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="sale_price" label="Sale Price (₹)"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
              <Form.Item name="rental_price" label="Rental Price (₹ / month)"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="warranty_months" label="Warranty (Months)"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
              <Form.Item name="inventory_item_id" label="Link to Inventory Stock">
                <Select allowClear placeholder="Select stock item to link">
                  {inventoryItems.map(i => <Option key={i.id} value={i.id}>{i.name}</Option>)}
                </Select>
              </Form.Item>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "16px", background: "rgba(255, 255, 255, 0.02)", padding: "16px", borderRadius: "8px", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
              <Form.Item name="is_sellable" valuePropName="checked" label="Sellable" style={{ marginBottom: 0 }}><Switch /></Form.Item>
              <Form.Item name="is_rentable" valuePropName="checked" label="Rentable" style={{ marginBottom: 0 }}><Switch /></Form.Item>
              <Form.Item name="is_serial_tracked" valuePropName="checked" label="Serial-Tracked" style={{ marginBottom: 0 }}><Switch /></Form.Item>
              {editing && <Form.Item name="is_active" valuePropName="checked" label="Active" style={{ marginBottom: 0 }}><Switch /></Form.Item>}
            </div>
          </Form>
        </Modal>
      </div>
    </ConfigProvider>
  );
}
