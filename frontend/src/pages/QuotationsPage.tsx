import { useEffect, useState, useCallback } from "react";
import {
  Tabs, Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, DatePicker, Popconfirm,
} from "antd";
import { PlusOutlined, CheckOutlined, CloseOutlined, SwapOutlined, MinusCircleOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import apiClient from "../api/client";

const { Title } = Typography;
const { Option } = Select;

const inr = (v: number) => "₹" + (v ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 });
const qStatusColor: Record<string, string> = { draft: "default", sent: "blue", approved: "green", rejected: "red", expired: "orange" };

interface Customer { id: string; name: string }
interface Quotation { id: string; quotation_number: string; customer_id: string; status: string; total_amount: number }
interface SalesOrder { id: string; order_number: string; customer_id: string; status: string; total_amount: number; order_date: string }

function useCustomers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  useEffect(() => { apiClient.get("/customers", { params: { limit: 200 } }).then(({ data }) => setCustomers(data)).catch(() => undefined); }, []);
  const name = (id: string) => customers.find(c => c.id === id)?.name || id.slice(0, 8);
  return { customers, name };
}

function QuotationsTab() {
  const { customers, name } = useCustomers();
  const [rows, setRows] = useState<Quotation[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [convert, setConvert] = useState<Quotation | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [cForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows((await apiClient.get("/quotations", { params: { limit: 200 } })).data); }
    catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load quotations"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openCreate = () => { form.resetFields(); form.setFieldsValue({ line_items: [{ description: "", quantity: 1, unit_price: 0, gst_rate: 18 }] }); setOpen(true); };

  const save = async () => {
    const v = await form.validateFields();
    const line_items = (v.line_items || []).map((li: any) => ({
      ...li, amount: Number(li.quantity) * Number(li.unit_price),
    }));
    setSaving(true);
    try {
      await apiClient.post("/quotations", { customer_id: v.customer_id, line_items, terms: v.terms, notes: v.notes });
      message.success("Quotation created"); setOpen(false); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed"); }
    finally { setSaving(false); }
  };

  const act = async (q: Quotation, action: "approve" | "reject") => {
    try { await apiClient.post(`/quotations/${q.id}/${action}`); message.success(`Quotation ${action}d`); load(); }
    catch (e: any) { message.error(e?.response?.data?.detail || "Action failed"); }
  };

  const doConvert = async () => {
    const v = await cForm.validateFields();
    setSaving(true);
    try {
      await apiClient.post(`/quotations/${convert!.id}/convert-to-amc`, {
        start_date: v.range[0].format("YYYY-MM-DD"),
        end_date: v.range[1].format("YYYY-MM-DD"),
        preventive_visits_per_year: v.preventive_visits_per_year,
      });
      message.success("Converted to AMC contract"); setConvert(null); cForm.resetFields(); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Conversion failed"); }
    finally { setSaving(false); }
  };

  const columns = [
    { title: "Quote #", dataIndex: "quotation_number", key: "quotation_number" },
    { title: "Customer", dataIndex: "customer_id", key: "customer_id", render: name },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={qStatusColor[v] ?? "default"}>{v}</Tag> },
    { title: "Total", dataIndex: "total_amount", key: "total_amount", render: inr },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, q: Quotation) => (
        <Space>
          {["draft", "sent"].includes(q.status) && <>
            <Button size="small" type="primary" ghost icon={<CheckOutlined />} onClick={() => act(q, "approve")}>Approve</Button>
            <Popconfirm title="Reject this quotation?" onConfirm={() => act(q, "reject")}>
              <Button size="small" danger icon={<CloseOutlined />}>Reject</Button>
            </Popconfirm>
          </>}
          {q.status === "approved" && <Button size="small" icon={<SwapOutlined />} onClick={() => { cForm.resetFields(); cForm.setFieldsValue({ preventive_visits_per_year: 2, range: [dayjs(), dayjs().add(1, "year")] }); setConvert(q); }}>To AMC</Button>}
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>New Quotation</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} />

      <Modal title="New Quotation" open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText="Create" width={680}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children" placeholder="Select customer">
              {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
            </Select>
          </Form.Item>
          <Form.List name="line_items">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name: n, ...rest }) => (
                  <Space key={key} align="baseline" style={{ display: "flex", marginBottom: 8 }} wrap>
                    <Form.Item {...rest} name={[n, "description"]} rules={[{ required: true, message: "desc" }]}><Input placeholder="Description" style={{ width: 200 }} /></Form.Item>
                    <Form.Item {...rest} name={[n, "quantity"]} rules={[{ required: true }]}><InputNumber min={1} placeholder="Qty" /></Form.Item>
                    <Form.Item {...rest} name={[n, "unit_price"]} rules={[{ required: true }]}><InputNumber min={0} placeholder="Unit ₹" /></Form.Item>
                    <Form.Item {...rest} name={[n, "gst_rate"]} rules={[{ required: true }]}><InputNumber min={0} max={28} placeholder="GST%" /></Form.Item>
                    <MinusCircleOutlined onClick={() => remove(n)} />
                  </Space>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ description: "", quantity: 1, unit_price: 0, gst_rate: 18 })}>Add line item</Button>
              </>
            )}
          </Form.List>
          <Form.Item name="terms" label="Terms" style={{ marginTop: 12 }}><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal title={`Convert ${convert?.quotation_number ?? ""} to AMC`} open={!!convert} onOk={doConvert} onCancel={() => setConvert(null)} confirmLoading={saving} okText="Convert">
        <Form form={cForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="range" label="Contract Period" rules={[{ required: true }]}><DatePicker.RangePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="preventive_visits_per_year" label="Preventive Visits / Year" rules={[{ required: true }]}><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

function SalesOrdersTab() {
  const { customers, name } = useCustomers();
  const [rows, setRows] = useState<SalesOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows((await apiClient.get("/sales-orders", { params: { limit: 200 } })).data); }
    catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load sales orders"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openCreate = () => { form.resetFields(); form.setFieldsValue({ order_date: dayjs(), line_items: [{ description: "", quantity: 1, unit_price: 0 }] }); setOpen(true); };

  const save = async () => {
    const v = await form.validateFields();
    const line_items = (v.line_items || []).map((li: any) => ({ ...li, amount: Number(li.quantity) * Number(li.unit_price) }));
    setSaving(true);
    try {
      await apiClient.post("/sales-orders", {
        customer_id: v.customer_id, order_date: v.order_date.format("YYYY-MM-DD"),
        delivery_date: v.delivery_date ? v.delivery_date.format("YYYY-MM-DD") : null,
        line_items, notes: v.notes,
      });
      message.success("Sales order created"); setOpen(false); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed"); }
    finally { setSaving(false); }
  };

  const columns = [
    { title: "Order #", dataIndex: "order_number", key: "order_number" },
    { title: "Customer", dataIndex: "customer_id", key: "customer_id", render: name },
    { title: "Date", dataIndex: "order_date", key: "order_date" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Total", dataIndex: "total_amount", key: "total_amount", render: inr },
  ];

  return (
    <>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>New Sales Order</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No sales orders" }} />

      <Modal title="New Sales Order" open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText="Create" width={680}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children">{customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}</Select>
          </Form.Item>
          <Space>
            <Form.Item name="order_date" label="Order Date" rules={[{ required: true }]}><DatePicker /></Form.Item>
            <Form.Item name="delivery_date" label="Delivery Date"><DatePicker /></Form.Item>
          </Space>
          <Form.List name="line_items">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name: n, ...rest }) => (
                  <Space key={key} align="baseline" style={{ display: "flex", marginBottom: 8 }}>
                    <Form.Item {...rest} name={[n, "description"]} rules={[{ required: true, message: "desc" }]}><Input placeholder="Description" style={{ width: 240 }} /></Form.Item>
                    <Form.Item {...rest} name={[n, "quantity"]} rules={[{ required: true }]}><InputNumber min={1} placeholder="Qty" /></Form.Item>
                    <Form.Item {...rest} name={[n, "unit_price"]} rules={[{ required: true }]}><InputNumber min={0} placeholder="Unit ₹" /></Form.Item>
                    <MinusCircleOutlined onClick={() => remove(n)} />
                  </Space>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ description: "", quantity: 1, unit_price: 0 })}>Add line item</Button>
              </>
            )}
          </Form.List>
          <Form.Item name="notes" label="Notes" style={{ marginTop: 12 }}><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

export default function QuotationsPage() {
  return (
    <div>
      <Title level={4}>Quotations & Sales Orders</Title>
      <Tabs items={[
        { key: "quotations", label: "Quotations", children: <QuotationsTab /> },
        { key: "sales-orders", label: "Sales Orders", children: <SalesOrdersTab /> },
      ]} />
    </div>
  );
}
