import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, Segmented, Badge,
} from "antd";
import { PlusOutlined, EditOutlined, SwapOutlined, WarningOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title } = Typography;
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
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Inventory</Title>
        <Space>
          <Segmented value={view} onChange={(v) => setView(v as "all" | "low")}
            options={[{ label: "All Items", value: "all" }, { label: "Low Stock", value: "low" }]} />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Add Item</Button>
        </Space>
      </div>

      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading}
        locale={{ emptyText: view === "low" ? "No low-stock items 🎉" : "No items" }} />

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
  );
}
