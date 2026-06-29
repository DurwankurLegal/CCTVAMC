import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, DatePicker, Popconfirm, Card, ConfigProvider, theme
} from "antd";
import {
  ShopOutlined, PlusOutlined, CheckOutlined, CloseOutlined,
  PlayCircleOutlined, FileTextOutlined, EyeOutlined
} from "@ant-design/icons";
import dayjs from "dayjs";
import apiClient from "../api/client";

const { Title, Text } = Typography;
const { Option } = Select;

const inr = (v: number) => "₹" + (v ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 });

const statusColors: Record<string, string> = {
  draft: "default",
  confirmed: "blue",
  fulfilled: "green",
  cancelled: "red",
};

const STATES = [
  { code: "27", name: "Maharashtra" },
  { code: "29", name: "Karnataka" },
  { code: "33", name: "Tamil Nadu" },
  { code: "07", name: "Delhi" },
  { code: "19", name: "West Bengal" },
  { code: "09", name: "Uttar Pradesh" },
];

interface Customer { id: string; name: string }
interface Product { id: string; sku: string; name: string; sale_price?: number; is_serial_tracked: boolean }
interface OrderItem {
  product_id?: string;
  name: string;
  sku?: string;
  quantity: number;
  unit_price: number;
  gst_rate: number;
  amount: number;
  serials?: string[];
}
interface SalesOrder {
  id: string;
  order_number: string;
  customer_id: string;
  status: string;
  order_date: string;
  delivery_date?: string;
  line_items: OrderItem[];
  subtotal: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  total_amount: number;
  supply_state_code?: string;
  fulfilled_at?: string;
  invoice_id?: string;
  notes?: string;
}

export default function SalesOrdersPage() {
  const [rows, setRows] = useState<SalesOrder[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [viewing, setViewing] = useState<SalesOrder | null>(null);
  
  // Fulfilment state
  const [fulfilling, setFulfilling] = useState<SalesOrder | null>(null);
  const [fulfilForm] = Form.useForm();
  
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const ordersRes = await apiClient.get("/sales-orders", { params: { limit: 200 } });
      setRows(ordersRes.data);
      const custRes = await apiClient.get("/customers", { params: { limit: 200 } });
      setCustomers(custRes.data);
      const prodRes = await apiClient.get("/products", { params: { limit: 200 } });
      setProducts(prodRes.data.filter((p: any) => p.is_sellable && p.is_active));
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load sales orders");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const getCustomerName = (id: string) => {
    return customers.find(c => c.id === id)?.name || id.slice(0, 8);
  };

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      order_date: dayjs(),
      supply_state_code: "27",
      line_items: [{ product_id: undefined, quantity: 1, unit_price: 0 }]
    });
    setOpen(true);
  };

  const handleProductChange = (index: number, val: string) => {
    const prod = products.find(p => p.id === val);
    if (prod) {
      const items = form.getFieldValue("line_items");
      items[index] = {
        ...items[index],
        unit_price: prod.sale_price || 0,
      };
      form.setFieldsValue({ line_items: items });
    }
  };

  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/sales-orders", {
        customer_id: v.customer_id,
        order_date: v.order_date.format("YYYY-MM-DD"),
        delivery_date: v.delivery_date ? v.delivery_date.format("YYYY-MM-DD") : null,
        supply_state_code: v.supply_state_code,
        notes: v.notes,
        line_items: v.line_items.map((li: any) => ({
          product_id: li.product_id,
          quantity: li.quantity,
          unit_price: li.unit_price,
        }))
      });
      message.success("Sales order created");
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to create sales order");
    } finally {
      setSaving(false);
    }
  };

  const handleConfirm = async (orderId: string) => {
    try {
      await apiClient.post(`/sales-orders/${orderId}/confirm`);
      message.success("Order confirmed");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Confirmation failed");
    }
  };

  const handleCancel = async (orderId: string) => {
    try {
      await apiClient.post(`/sales-orders/${orderId}/cancel`);
      message.success("Order cancelled");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Cancellation failed");
    }
  };

  const openFulfilModal = (order: SalesOrder) => {
    fulfilForm.resetFields();
    const initialLineItems = order.line_items.map(li => {
      const prod = products.find(p => p.id === li.product_id);
      return {
        product_id: li.product_id,
        name: li.name,
        quantity: li.quantity,
        is_serial_tracked: prod?.is_serial_tracked ?? false,
        serials: Array(li.quantity).fill(""),
      };
    });
    fulfilForm.setFieldsValue({ line_items: initialLineItems });
    setFulfilling(order);
  };

  const saveFulfil = async () => {
    const v = await fulfilForm.validateFields();
    setSaving(true);
    try {
      // Map back serials into the order line items
      const payloadLineItems = fulfilling!.line_items.map((li, idx) => {
        const inputItem = v.line_items[idx];
        return {
          ...li,
          serials: inputItem.is_serial_tracked ? inputItem.serials.filter((s: string) => s.trim() !== "") : [],
        };
      });
      await apiClient.post(`/sales-orders/${fulfilling!.id}/fulfil`, { line_items: payloadLineItems });
      message.success("Order fulfilled and assets registered!");
      setFulfilling(null);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Fulfilment failed");
    } finally {
      setSaving(false);
    }
  };

  const generateInvoice = async (orderId: string) => {
    try {
      const res = await apiClient.post(`/sales-orders/${orderId}/invoice`);
      message.success(`Invoice generated: ${res.data.invoice_number}`);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to generate invoice");
    }
  };

  const columns = [
    { title: "Order #", dataIndex: "order_number", key: "order_number" },
    { title: "Customer", dataIndex: "customer_id", key: "customer_id", render: getCustomerName },
    { title: "Date", dataIndex: "order_date", key: "order_date" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColors[v] ?? "default"}>{v.toUpperCase()}</Tag> },
    { title: "Total Amount", dataIndex: "total_amount", key: "total_amount", render: inr },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, r: SalesOrder) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => setViewing(r)}>View</Button>
          
          {r.status === "draft" && (
            <>
              <Button size="small" type="primary" ghost icon={<CheckOutlined />} onClick={() => handleConfirm(r.id)}>Confirm</Button>
              <Popconfirm title="Cancel this order?" onConfirm={() => handleCancel(r.id)}>
                <Button size="small" danger icon={<CloseOutlined />}>Cancel</Button>
              </Popconfirm>
            </>
          )}

          {r.status === "confirmed" && (
            <>
              <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => openFulfilModal(r)}>Fulfil</Button>
              <Popconfirm title="Cancel this order?" onConfirm={() => handleCancel(r.id)}>
                <Button size="small" danger icon={<CloseOutlined />}>Cancel</Button>
              </Popconfirm>
            </>
          )}

          {["confirmed", "fulfilled"].includes(r.status) && !r.invoice_id && (
            <Button size="small" icon={<FileTextOutlined />} onClick={() => generateInvoice(r.id)}>Generate Invoice</Button>
          )}

          {r.invoice_id && (
            <Tag color="purple">Billed</Tag>
          )}
        </Space>
      ),
    },
  ];

  return (
    <ConfigProvider theme={{}}>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 4 }}>
          <div>
            <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
              <ShopOutlined style={{ color: "#8b5cf6" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Sales Order Management
              </span>
            </Title>
            <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
              Log physical sales transactions, check catalog availability, allocate device serial numbers, and generate tax invoices.
            </Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)", border: "none", color: "#fff" }}>New Sales Order</Button>
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
              <ShopOutlined style={{ color: "#8b5cf6", fontSize: 18 }} />
              <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
                Orders Ledger
              </span>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 100 }} />
        </Card>

        {/* Modal: Create Sales Order */}
        <Modal title="Create Sales Order" open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText="Create" width={750}>
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px" }}>
              <Form.Item name="customer_id" label="Customer" rules={[{ required: true, message: "Required" }]}>
                <Select showSearch optionFilterProp="children" placeholder="Select customer">
                  {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
                </Select>
              </Form.Item>
              <Form.Item name="supply_state_code" label="Place of Supply State" rules={[{ required: true }]}>
                <Select>
                  {STATES.map(s => <Option key={s.code} value={s.code}>{s.code} - {s.name}</Option>)}
                </Select>
              </Form.Item>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="order_date" label="Order Date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
              <Form.Item name="delivery_date" label="Expected Delivery Date"><DatePicker style={{ width: "100%" }} /></Form.Item>
            </div>

            <Title level={5} style={{ margin: "16px 0 8px 0" }}>Order Line Items</Title>
            <Form.List name="line_items">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name: n, ...rest }, index) => (
                    <div key={key} style={{ display: "grid", gridTemplateColumns: "3fr 1fr 1.5fr auto", gap: "12px", alignItems: "end", marginBottom: "8px" }}>
                      <Form.Item {...rest} name={[n, "product_id"]} label={index === 0 ? "Select Product Catalog SKU" : ""} rules={[{ required: true, message: "Required" }]}>
                        <Select placeholder="SKU/Product" onChange={(v) => handleProductChange(index, v)}>
                          {products.map(p => <Option key={p.id} value={p.id}>{p.name} ({p.sku})</Option>)}
                        </Select>
                      </Form.Item>
                      <Form.Item {...rest} name={[n, "quantity"]} label={index === 0 ? "Qty" : ""} rules={[{ required: true, message: "Required" }]}>
                        <InputNumber min={1} style={{ width: "100%" }} />
                      </Form.Item>
                      <Form.Item {...rest} name={[n, "unit_price"]} label={index === 0 ? "Price (₹)" : ""} rules={[{ required: true, message: "Required" }]}>
                        <InputNumber min={0} style={{ width: "100%" }} />
                      </Form.Item>
                      {fields.length > 1 && (
                        <Button type="text" danger onClick={() => remove(n)} style={{ marginBottom: "5px" }}>Remove</Button>
                      )}
                    </div>
                  ))}
                  <Button type="dashed" onClick={() => add({ product_id: undefined, quantity: 1, unit_price: 0 })} block icon={<PlusOutlined />} style={{ marginTop: "8px" }}>
                    Add Product Line
                  </Button>
                </>
              )}
            </Form.List>

            <Form.Item name="notes" label="Order Comments / Notes" style={{ marginTop: 16 }}><Input.TextArea rows={2} /></Form.Item>
          </Form>
        </Modal>

        {/* Modal: View Details */}
        <Modal title={`Sales Order Detail - ${viewing?.order_number ?? ""}`} open={!!viewing} onCancel={() => setViewing(null)} footer={null} width={650}>
          {viewing && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div><strong>Customer:</strong> {getCustomerName(viewing.customer_id)}</div>
                <div><strong>Order Date:</strong> {viewing.order_date}</div>
                <div><strong>Status:</strong> <Tag color={statusColors[viewing.status]}>{viewing.status.toUpperCase()}</Tag></div>
                <div><strong>Expected Delivery:</strong> {viewing.delivery_date || "—"}</div>
                <div><strong>Supply State:</strong> {STATES.find(s => s.code === viewing.supply_state_code)?.name || viewing.supply_state_code || "—"}</div>
                <div><strong>Fulfilled At:</strong> {viewing.fulfilled_at || "—"}</div>
              </div>

              <Card size="small" title="GST Calculation Summary" style={{ background: "rgba(255,255,255,0.01)" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span>Subtotal:</span><span>{inr(viewing.subtotal)}</span></div>
                  {viewing.cgst_amount > 0 && <div style={{ display: "flex", justifyContent: "space-between" }}><span>CGST:</span><span>{inr(viewing.cgst_amount)}</span></div>}
                  {viewing.sgst_amount > 0 && <div style={{ display: "flex", justifyContent: "space-between" }}><span>SGST:</span><span>{inr(viewing.sgst_amount)}</span></div>}
                  {viewing.igst_amount > 0 && <div style={{ display: "flex", justifyContent: "space-between" }}><span>IGST:</span><span>{inr(viewing.igst_amount)}</span></div>}
                  <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px dashed rgba(255,255,255,0.1)", paddingTop: "6px", fontWeight: "bold" }}>
                    <span>Grand Total:</span><span>{inr(viewing.total_amount)}</span>
                  </div>
                </div>
              </Card>

              <Title level={5}>Items Ordered</Title>
              <Table
                rowKey="sku"
                dataSource={viewing.line_items}
                pagination={false}
                size="small"
                columns={[
                  { title: "SKU / Item", dataIndex: "sku", key: "sku", render: (v, r) => v ? `${r.name} (${v})` : r.name },
                  { title: "Qty", dataIndex: "quantity", key: "quantity" },
                  { title: "Rate", dataIndex: "unit_price", key: "unit_price", render: (v) => "₹" + v },
                  { title: "GST%", dataIndex: "gst_rate", key: "gst_rate", render: (v) => v + "%" },
                  { title: "Amount", dataIndex: "amount", key: "amount", render: (v) => "₹" + v },
                ]}
              />
              {viewing.notes && <div><strong>Comments:</strong> <p style={{ whiteSpace: "pre-wrap" }}>{viewing.notes}</p></div>}
            </div>
          )}
        </Modal>

        {/* Modal: Fulfil / Register Serials */}
        <Modal title={`Fulfil Order - ${fulfilling?.order_number ?? ""}`} open={!!fulfilling} onOk={saveFulfil} onCancel={() => setFulfilling(null)} confirmLoading={saving} width={650}>
          <Form form={fulfilForm} layout="vertical" style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ display: "block", marginBottom: "16px" }}>
              Please register serial numbers for serial-tracked products to complete shipment. This automatically logs assets to the customer's site.
            </Text>
            <Form.List name="line_items">
              {(fields) => (
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  {fields.map(({ key, name: n, ...rest }) => {
                    const itemData = fulfilForm.getFieldValue(["line_items", n]);
                    return (
                      <div key={key} style={{ padding: "12px", background: "rgba(255,255,255,0.02)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                          <strong>{itemData.name}</strong>
                          <Tag>Qty: {itemData.quantity}</Tag>
                        </div>
                        {itemData.is_serial_tracked ? (
                          <Form.List name={[n, "serials"]}>
                            {(serialFields) => (
                              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                                {serialFields.map((sf, sIdx) => (
                                  <Form.Item
                                    {...sf}
                                    key={sf.key}
                                    label={`Serial #${sIdx + 1}`}
                                    rules={[{ required: true, message: "Serial required" }]}
                                    style={{ marginBottom: 0 }}
                                  >
                                    <Input placeholder="Enter serial code" />
                                  </Form.Item>
                                ))}
                              </div>
                            )}
                          </Form.List>
                        ) : (
                          <Text type="secondary">Product is not serial-tracked. Stock will be deducted directly.</Text>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </Form.List>
          </Form>
        </Modal>
      </div>
    </ConfigProvider>
  );
}
