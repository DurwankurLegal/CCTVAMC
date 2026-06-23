import { useEffect, useState, useCallback } from "react";
import {
  Tabs, Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, Tooltip,
} from "antd";
import { PlusOutlined, EditOutlined, DollarOutlined, ReloadOutlined, MinusCircleOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title } = Typography;
const { Option } = Select;

const VENDOR_STATUS = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "blacklisted", label: "Blacklisted" },
];
const statusColor: Record<string, string> = { active: "green", inactive: "default", blacklisted: "red" };
const inr = (v: number) => "₹" + (v ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 });

interface Vendor { id: string; name: string; vendor_type?: string; status: string; phone?: string; outstanding_payable: number }
interface PO { id: string; po_number: string; vendor_id: string; status: string; total_amount: number }

function VendorsTab() {
  const [rows, setRows] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Vendor | null>(null);
  const [payOpen, setPayOpen] = useState<Vendor | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [payForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows((await apiClient.get("/vendors", { params: { limit: 200 } })).data); }
    catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load vendors"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ status: "active", vendor_type: "supplier" }); setOpen(true); };
  const openEdit = (r: Vendor) => { setEditing(r); form.setFieldsValue(r); setOpen(true); };

  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      if (editing) await apiClient.patch(`/vendors/${editing.id}`, v);
      else await apiClient.post("/vendors", v);
      message.success("Saved"); setOpen(false); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Save failed"); }
    finally { setSaving(false); }
  };

  const recordPayment = async () => {
    const v = await payForm.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/vendors/payments", { vendor_id: payOpen!.id, ...v });
      message.success("Payment recorded"); setPayOpen(null); payForm.resetFields(); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed"); }
    finally { setSaving(false); }
  };

  const columns = [
    { title: "Name", dataIndex: "name", key: "name" },
    { title: "Type", dataIndex: "vendor_type", key: "vendor_type", render: (v?: string) => v || "—" },
    { title: "Phone", dataIndex: "phone", key: "phone", render: (v?: string) => v || "—" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v}</Tag> },
    { title: "Payable", dataIndex: "outstanding_payable", key: "outstanding_payable", render: inr },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, r: Vendor) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>Edit</Button>
          <Tooltip title="Record a payment to this vendor">
            <Button size="small" icon={<DollarOutlined />} onClick={() => { payForm.resetFields(); setPayOpen(r); }}>Pay</Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Add Vendor</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} />

      <Modal title={editing ? "Edit Vendor" : "Add Vendor"} open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText={editing ? "Save" : "Create"}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="vendor_type" label="Type">
            <Select><Option value="supplier">Supplier</Option><Option value="service_partner">Service Partner</Option></Select>
          </Form.Item>
          <Form.Item name="status" label="Status"><Select>{VENDOR_STATUS.map(s => <Option key={s.value} value={s.value}>{s.label}</Option>)}</Select></Form.Item>
          <Form.Item name="phone" label="Phone"><Input /></Form.Item>
          <Form.Item name="email" label="Email"><Input type="email" /></Form.Item>
          <Form.Item name="gstin" label="GSTIN"><Input /></Form.Item>
          <Form.Item name="contact_person" label="Contact Person"><Input /></Form.Item>
          <Form.Item name="payment_terms" label="Payment Terms"><Input placeholder="e.g. Net 30" /></Form.Item>
        </Form>
      </Modal>

      <Modal title={`Record Payment — ${payOpen?.name ?? ""}`} open={!!payOpen} onOk={recordPayment} onCancel={() => setPayOpen(null)} confirmLoading={saving} okText="Record">
        <Form form={payForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="amount" label="Amount (₹)" rules={[{ required: true }]}><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="method" label="Method"><Select allowClear><Option value="neft">NEFT</Option><Option value="upi">UPI</Option><Option value="cheque">Cheque</Option><Option value="cash">Cash</Option></Select></Form.Item>
          <Form.Item name="reference" label="Reference"><Input /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

function PurchaseOrdersTab() {
  const [rows, setRows] = useState<PO[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pos, vs] = await Promise.all([
        apiClient.get("/vendors/purchase-orders"),
        apiClient.get("/vendors", { params: { limit: 200 } }),
      ]);
      setRows(pos.data); setVendors(vs.data);
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load POs"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openCreate = () => { form.resetFields(); form.setFieldsValue({ line_items: [{ description: "", qty: 1, unit_cost: 0 }] }); setOpen(true); };

  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/vendors/purchase-orders", v);
      message.success("Purchase order created"); setOpen(false); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed"); }
    finally { setSaving(false); }
  };

  const reorder = async () => {
    try {
      const { data } = await apiClient.post("/vendors/reorder");
      const n = data.created_pos?.length ?? 0;
      message.success(n ? `Created ${n} reorder PO(s)` : "No low-stock items to reorder");
      load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Reorder failed"); }
  };

  const vendorName = (id: string) => vendors.find(v => v.id === id)?.name || id.slice(0, 8);
  const columns = [
    { title: "PO #", dataIndex: "po_number", key: "po_number" },
    { title: "Vendor", dataIndex: "vendor_id", key: "vendor_id", render: vendorName },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Total", dataIndex: "total_amount", key: "total_amount", render: inr },
  ];

  return (
    <>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 12 }}>
        <Button icon={<ReloadOutlined />} onClick={reorder}>Reorder Low Stock</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Create PO</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No purchase orders" }} />

      <Modal title="Create Purchase Order" open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText="Create" width={640}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="vendor_id" label="Vendor" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children" placeholder="Select vendor">
              {vendors.map(v => <Option key={v.id} value={v.id}>{v.name}</Option>)}
            </Select>
          </Form.Item>
          <Form.List name="line_items">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <Space key={key} align="baseline" style={{ display: "flex", marginBottom: 8 }}>
                    <Form.Item {...rest} name={[name, "description"]} rules={[{ required: true, message: "desc" }]}><Input placeholder="Description" style={{ width: 240 }} /></Form.Item>
                    <Form.Item {...rest} name={[name, "qty"]} rules={[{ required: true }]}><InputNumber min={1} placeholder="Qty" /></Form.Item>
                    <Form.Item {...rest} name={[name, "unit_cost"]} rules={[{ required: true }]}><InputNumber min={0} placeholder="Unit ₹" /></Form.Item>
                    <MinusCircleOutlined onClick={() => remove(name)} />
                  </Space>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ description: "", qty: 1, unit_cost: 0 })}>Add line item</Button>
              </>
            )}
          </Form.List>
          <Form.Item name="notes" label="Notes" style={{ marginTop: 12 }}><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

export default function VendorsPage() {
  return (
    <div>
      <Title level={4}>Vendors & Procurement</Title>
      <Tabs items={[
        { key: "vendors", label: "Vendors", children: <VendorsTab /> },
        { key: "pos", label: "Purchase Orders", children: <PurchaseOrdersTab /> },
      ]} />
    </div>
  );
}
