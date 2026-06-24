import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, Segmented, Badge, Card, ConfigProvider, theme
} from "antd";
import { PlusOutlined, EditOutlined, SwapOutlined, WarningOutlined, AppstoreOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title, Text } = Typography;
const { Option } = Select;

const MOVEMENTS = ["purchase", "sale", "consumption", "transfer", "adjustment", "return"];

interface Item {
  id: string; name: string; part_number?: string; unit?: string;
  reorder_level: number; current_stock: number; van_stock: number;
  unit_cost?: number; is_active: boolean;
}

export default function InventoryPage() {
  const [rows, setRows] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<"all" | "low">("all");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Item | null>(null);
  const [adjust, setAdjust] = useState<Item | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [adjForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = view === "low" ? "/inventory/low-stock" : "/inventory";
      setRows((await apiClient.get(url, { params: view === "low" ? {} : { limit: 200 } })).data);
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load inventory"); }
    finally { setLoading(false); }
  }, [view]);
  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ reorder_level: 0 }); setOpen(true); };
  const openEdit = (r: Item) => { setEditing(r); form.setFieldsValue(r); setOpen(true); };

  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      if (editing) await apiClient.patch(`/inventory/${editing.id}`, v);
      else await apiClient.post("/inventory", v);
      message.success("Saved"); setOpen(false); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Save failed"); }
    finally { setSaving(false); }
  };

  const doAdjust = async () => {
    const v = await adjForm.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/inventory/adjust", { item_id: adjust!.id, ...v });
      message.success("Stock adjusted"); setAdjust(null); adjForm.resetFields(); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Adjustment failed"); }
    finally { setSaving(false); }
  };

  const columns = [
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "Part #", dataIndex: "part_number", key: "part_number", render: (v?: string) => v || "—" },
    {
      title: "In Stock", dataIndex: "current_stock", key: "current_stock",
      render: (v: number, r: Item) =>
        v <= r.reorder_level
          ? <Badge status="warning" text={<span>{v} <WarningOutlined style={{ color: "#faad14" }} /></span>} />
          : <span>{v}</span>,
    },
    { title: "Van Stock", dataIndex: "van_stock", key: "van_stock" },
    { title: "Reorder At", dataIndex: "reorder_level", key: "reorder_level" },
    { title: "Unit Cost", dataIndex: "unit_cost", key: "unit_cost", render: (v?: number) => v != null ? "₹" + v : "—" },
    { title: "Status", dataIndex: "is_active", key: "is_active", render: (v: boolean) => <Tag color={v ? "green" : "default"}>{v ? "active" : "inactive"}</Tag> },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, r: Item) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>Edit</Button>
          <Button size="small" icon={<SwapOutlined />} onClick={() => { adjForm.resetFields(); adjForm.setFieldsValue({ movement_type: "adjustment" }); setAdjust(r); }}>Adjust</Button>
        </Space>
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
              <AppstoreOutlined style={{ color: "#8b5cf6" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Inventory Control Ledger
              </span>
            </Title>
            <Text style={{ color: "#9ca3af", fontSize: "13.5px" }}>
              Monitor parts stock levels, van allocations, reorder alerts, and register adjustments.
            </Text>
          </div>
          <Space>
            <Segmented value={view} onChange={(v) => setView(v as "all" | "low")}
              options={[{ label: "All Items", value: "all" }, { label: "Low Stock", value: "low" }]} />
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)", border: "none", color: "#fff" }}>Add Item</Button>
          </Space>
        </div>

        <Card
          id="inventory-ledger-panel"
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
              <AppstoreOutlined style={{ color: "#8b5cf6", fontSize: 18 }} />
              <span style={{ color: "#f3f4f6", fontWeight: 700, fontSize: 15 }}>
                Stock Items Catalogue
              </span>
              <Tag color="purple" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(139, 92, 246, 0.12)", border: "1px solid rgba(139, 92, 246, 0.2)" }}>
                PARTS &amp; WAREHOUSE
              </Tag>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={rows} loading={loading}
            locale={{ emptyText: view === "low" ? "No low-stock items 🎉" : "No items" }} />
        </Card>

        <Modal title={editing ? "Edit Item" : "Add Item"} open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText={editing ? "Save" : "Create"}>
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
            {!editing && <Form.Item name="part_number" label="Part Number"><Input /></Form.Item>}
            {!editing && <Form.Item name="unit" label="Unit"><Input placeholder="e.g. pcs, mtr" /></Form.Item>}
            {!editing && <Form.Item name="hsn_code" label="HSN Code"><Input /></Form.Item>}
            {!editing && <Form.Item name="gst_rate" label="GST %"><InputNumber min={0} max={28} style={{ width: "100%" }} /></Form.Item>}
            <Form.Item name="reorder_level" label="Reorder Level" rules={[{ required: true }]}><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
            <Form.Item name="unit_cost" label="Unit Cost (₹)"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
          </Form>
        </Modal>

        <Modal title={`Adjust Stock — ${adjust?.name ?? ""}`} open={!!adjust} onOk={doAdjust} onCancel={() => setAdjust(null)} confirmLoading={saving} okText="Apply">
          <Form form={adjForm} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item name="quantity" label="Quantity (+ in / − out)" rules={[{ required: true }]}>
              <InputNumber style={{ width: "100%" }} placeholder="e.g. 10 or -3" />
            </Form.Item>
            <Form.Item name="movement_type" label="Movement Type" rules={[{ required: true }]}>
              <Select>{MOVEMENTS.map(m => <Option key={m} value={m}>{m}</Option>)}</Select>
            </Form.Item>
            <Form.Item name="notes" label="Notes"><Input.TextArea rows={2} /></Form.Item>
          </Form>
        </Modal>
      </div>
    </ConfigProvider>
  );
}
