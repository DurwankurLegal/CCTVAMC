import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, DatePicker, Popconfirm, Card, ConfigProvider, theme
} from "antd";
import {
  FileDoneOutlined, PlusOutlined, PlayCircleOutlined,
  CheckOutlined, ArrowLeftOutlined, ThunderboltOutlined, EyeOutlined
} from "@ant-design/icons";
import dayjs from "dayjs";
import apiClient from "../api/client";

const { Title, Text } = Typography;
const { Option } = Select;

const inr = (v: number) => "₹" + (v ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 });

const statusColors: Record<string, string> = {
  booked: "blue",
  active: "green",
  returned: "purple",
  closed: "default",
  cancelled: "red",
};

interface Customer { id: string; name: string }
interface CustomerSite { id: string; customer_id: string; name: string }
interface Company { id: string; name: string }
interface Product { id: string; sku: string; name: string; rental_price?: number; gst_rate?: number }
interface RentalUnit { id: string; product_id: string; serial_number: string; status: string }

interface ContractLine {
  id: string;
  product_id: string;
  rental_unit_id?: string;
  quantity: number;
  unit_price: number;
  gst_rate: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  total_amount: number;
}

interface RentalContract {
  id: string;
  contract_number: string;
  customer_id: string;
  site_id?: string;
  company_id: string;
  status: string;
  start_date: string;
  end_date: string;
  billing_cycle: string;
  deposit_amount: number;
  deposit_status: string;
  subtotal: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  total_amount: number;
  notes?: string;
  lines: ContractLine[];
}

export default function RentalContractsPage() {
  const [rows, setRows] = useState<RentalContract[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [sites, setSites] = useState<CustomerSite[]>([]);
  const [filteredSites, setFilteredSites] = useState<CustomerSite[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [availableUnits, setAvailableUnits] = useState<RentalUnit[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [viewing, setViewing] = useState<RentalContract | null>(null);

  // Check-out / Check-in Modals
  const [checkoutModal, setCheckoutModal] = useState<RentalContract | null>(null);
  const [checkinModal, setCheckinModal] = useState<RentalContract | null>(null);
  const [billingModal, setBillingModal] = useState(false);

  const [form] = Form.useForm();
  const [checkoutForm] = Form.useForm();
  const [checkinForm] = Form.useForm();
  const [billingForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const contractsRes = await apiClient.get("/rentals/contracts", { params: { limit: 200 } });
      setRows(contractsRes.data);
      const custRes = await apiClient.get("/customers", { params: { limit: 200 } });
      setCustomers(custRes.data);
      const siteRes = await apiClient.get("/customers/sites", { params: { limit: 200 } });
      setSites(siteRes.data);
      const compRes = await apiClient.get("/companies", { params: { limit: 200 } });
      setCompanies(compRes.data);
      const prodRes = await apiClient.get("/products", { params: { limit: 200 } });
      setProducts(prodRes.data.filter((p: any) => p.is_rentable && p.is_active));
      const unitsRes = await apiClient.get("/rentals/units", { params: { limit: 200 } });
      setAvailableUnits(unitsRes.data.filter((u: any) => u.status === "available"));
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to load rental contracts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCustomerChange = (val: string) => {
    setFilteredSites(sites.filter(s => s.customer_id === val));
    form.setFieldsValue({ site_id: undefined });
  };

  const handleProductChange = (index: number, val: string) => {
    const prod = products.find(p => p.id === val);
    if (prod) {
      const items = form.getFieldValue("lines");
      items[index] = {
        ...items[index],
        unit_price: prod.rental_price || 0,
        gst_rate: prod.gst_rate || 18,
      };
      form.setFieldsValue({ lines: items });
    }
  };

  const getCustomerName = (id: string) => customers.find(c => c.id === id)?.name || id.slice(0, 8);
  const getSiteName = (id?: string) => id ? sites.find(s => s.id === id)?.name || id.slice(0, 8) : "—";
  const getCompanyName = (id: string) => companies.find(c => c.id === id)?.name || id.slice(0, 8);
  const getProductName = (id: string) => products.find(p => p.id === id)?.name || "Unknown SKU";

  const openCreate = () => {
    form.resetFields();
    setFilteredSites([]);
    form.setFieldsValue({
      start_date: dayjs(),
      end_date: dayjs().add(1, "year"),
      billing_cycle: "monthly",
      deposit_status: "pending",
      lines: [{ product_id: undefined, quantity: 1, unit_price: 0, gst_rate: 18 }]
    });
    setOpen(true);
  };

  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/rentals/contracts", {
        ...v,
        start_date: v.start_date.format("YYYY-MM-DD"),
        end_date: v.end_date.format("YYYY-MM-DD"),
        lines: v.lines.map((l: any) => ({
          product_id: l.product_id,
          quantity: l.quantity,
          unit_price: l.unit_price,
          gst_rate: l.gst_rate
        }))
      });
      message.success("Contract created successfully");
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Creation failed");
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (contractId: string) => {
    try {
      await apiClient.post(`/rentals/contracts/${contractId}/activate`);
      message.success("Contract activated");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Activation failed");
    }
  };

  const openCheckout = (contract: RentalContract) => {
    checkoutForm.resetFields();
    setCheckoutModal(contract);
  };

  const saveCheckout = async () => {
    const v = await checkoutForm.validateFields();
    setSaving(true);
    try {
      await apiClient.post(`/rentals/contracts/${checkoutModal!.id}/checkout`, v);
      message.success("Equipment checked out and assigned!");
      setCheckoutModal(null);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Check-out failed");
    } finally {
      setSaving(false);
    }
  };

  const openCheckin = (contract: RentalContract) => {
    checkinForm.resetFields();
    setCheckinModal(contract);
  };

  const saveCheckin = async () => {
    const v = await checkinForm.validateFields();
    setSaving(true);
    try {
      await apiClient.post(`/rentals/contracts/${checkinModal!.id}/checkin`, v);
      message.success("Equipment checked in!");
      setCheckinModal(null);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Check-in failed");
    } finally {
      setSaving(false);
    }
  };

  const runRecurringBilling = async () => {
    const v = await billingForm.validateFields();
    setSaving(true);
    try {
      const bDate = v.billing_date ? v.billing_date.format("YYYY-MM-DD") : null;
      const res = await apiClient.post("/rentals/contracts/generate-billing", null, {
        params: bDate ? { billing_date: bDate } : {}
      });
      message.success(`${res.data.message}. Invoices Created: ${res.data.invoices_generated}`);
      setBillingModal(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Billing generation failed");
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { title: "Contract #", dataIndex: "contract_number", key: "contract_number" },
    { title: "Customer", dataIndex: "customer_id", key: "customer_id", render: getCustomerName },
    { title: "Site", dataIndex: "site_id", key: "site_id", render: getSiteName },
    { title: "Start Date", dataIndex: "start_date", key: "start_date" },
    { title: "End Date", dataIndex: "end_date", key: "end_date" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColors[v] ?? "default"}>{v.toUpperCase()}</Tag> },
    { title: "Monthly Rate", dataIndex: "total_amount", key: "total_amount", render: inr },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, r: RentalContract) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => setViewing(r)}>View</Button>
          
          {r.status === "booked" && (
            <>
              <Button size="small" type="primary" ghost icon={<CheckOutlined />} onClick={() => handleActivate(r.id)}>Activate</Button>
              <Button size="small" icon={<PlayCircleOutlined />} onClick={() => openCheckout(r)}>Check-Out</Button>
            </>
          )}

          {r.status === "active" && (
            <>
              <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => openCheckin(r)}>Check-In</Button>
            </>
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
              <FileDoneOutlined style={{ color: "#8b5cf6" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Leasing &amp; Rental Contracts
              </span>
            </Title>
            <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
              Draft customer rental contracts, dispatch hardware assets to customer sites, and trigger monthly recurring lease invoices.
            </Text>
          </div>
          <Space>
            <Button icon={<ThunderboltOutlined />} onClick={() => { billingForm.resetFields(); billingForm.setFieldsValue({ billing_date: dayjs() }); setBillingModal(true); }} style={{ background: "rgba(139, 92, 246, 0.15)", border: "1px solid rgba(139, 92, 246, 0.3)", color: "#c084fc" }}>
              Run Monthly Billing
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)", border: "none", color: "#fff" }}>New Contract</Button>
          </Space>
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
              <FileDoneOutlined style={{ color: "#8b5cf6", fontSize: 18 }} />
              <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
                Active Rental Agreements
              </span>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} pagination={{ pageSize: 100 }} />
        </Card>

        {/* Modal: Create Contract */}
        <Modal title="New Rental Contract" open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText="Create" width={750}>
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="customer_id" label="Customer" rules={[{ required: true, message: "Required" }]}>
                <Select showSearch optionFilterProp="children" placeholder="Select customer" onChange={handleCustomerChange}>
                  {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
                </Select>
              </Form.Item>
              <Form.Item name="site_id" label="Customer Deployment Site">
                <Select placeholder="Select deployment site">
                  {filteredSites.map(s => <Option key={s.id} value={s.id}>{s.name}</Option>)}
                </Select>
              </Form.Item>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="company_id" label="Billing Company Entity" rules={[{ required: true, message: "Required" }]}>
                <Select placeholder="Select company">
                  {companies.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
                </Select>
              </Form.Item>
              <Form.Item name="billing_cycle" label="Billing Frequency" rules={[{ required: true }]}>
                <Select>
                  <Option value="monthly">Monthly</Option>
                  <Option value="weekly">Weekly</Option>
                  <Option value="daily">Daily</Option>
                </Select>
              </Form.Item>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="start_date" label="Lease Start Date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
              <Form.Item name="end_date" label="Lease Expiration Date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <Form.Item name="deposit_amount" label="Security Deposit (₹)"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
              <Form.Item name="deposit_status" label="Deposit Status" rules={[{ required: true }]}>
                <Select>
                  <Option value="pending">Pending</Option>
                  <Option value="paid">Paid</Option>
                  <Option value="refunded">Refunded</Option>
                </Select>
              </Form.Item>
            </div>

            <Title level={5} style={{ margin: "16px 0 8px 0" }}>Rental Equipment Lines</Title>
            <Form.List name="lines">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name: n, ...rest }, index) => (
                    <div key={key} style={{ display: "grid", gridTemplateColumns: "3fr 1fr 1.5fr 1fr auto", gap: "12px", alignItems: "end", marginBottom: "8px" }}>
                      <Form.Item {...rest} name={[n, "product_id"]} label={index === 0 ? "Lease Product" : ""} rules={[{ required: true, message: "Required" }]}>
                        <Select placeholder="Select product" onChange={(v) => handleProductChange(index, v)}>
                          {products.map(p => <Option key={p.id} value={p.id}>{p.name} ({p.sku})</Option>)}
                        </Select>
                      </Form.Item>
                      <Form.Item {...rest} name={[n, "quantity"]} label={index === 0 ? "Qty" : ""} rules={[{ required: true }]}>
                        <InputNumber min={1} style={{ width: "100%" }} />
                      </Form.Item>
                      <Form.Item {...rest} name={[n, "unit_price"]} label={index === 0 ? "Rent/Month" : ""} rules={[{ required: true }]}>
                        <InputNumber min={0} style={{ width: "100%" }} />
                      </Form.Item>
                      <Form.Item {...rest} name={[n, "gst_rate"]} label={index === 0 ? "GST%" : ""} rules={[{ required: true }]}>
                        <InputNumber min={0} max={28} style={{ width: "100%" }} />
                      </Form.Item>
                      {fields.length > 1 && (
                        <Button type="text" danger onClick={() => remove(n)} style={{ marginBottom: "5px" }}>Remove</Button>
                      )}
                    </div>
                  ))}
                  <Button type="dashed" onClick={() => add({ product_id: undefined, quantity: 1, unit_price: 0, gst_rate: 18 })} block icon={<PlusOutlined />} style={{ marginTop: "8px" }}>
                    Add Rental Item
                  </Button>
                </>
              )}
            </Form.List>

            <Form.Item name="notes" label="Special Terms / Notes" style={{ marginTop: 16 }}><Input.TextArea rows={2} /></Form.Item>
          </Form>
        </Modal>

        {/* Modal: View Details */}
        <Modal title={`Rental Contract Detail - ${viewing?.contract_number ?? ""}`} open={!!viewing} onCancel={() => setViewing(null)} footer={null} width={650}>
          {viewing && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div><strong>Customer:</strong> {getCustomerName(viewing.customer_id)}</div>
                <div><strong>Site:</strong> {getSiteName(viewing.site_id)}</div>
                <div><strong>Company:</strong> {getCompanyName(viewing.company_id)}</div>
                <div><strong>Status:</strong> <Tag color={statusColors[viewing.status]}>{viewing.status.toUpperCase()}</Tag></div>
                <div><strong>Start Date:</strong> {viewing.start_date}</div>
                <div><strong>End Date:</strong> {viewing.end_date}</div>
                <div><strong>Billing Cycle:</strong> {viewing.billing_cycle.toUpperCase()}</div>
                <div><strong>Security Deposit:</strong> {inr(viewing.deposit_amount)} ({viewing.deposit_status.toUpperCase()})</div>
              </div>

              <Card size="small" title="Estimated Recurring Monthly GST" style={{ background: "rgba(255,255,255,0.01)" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span>Subtotal:</span><span>{inr(viewing.subtotal)}</span></div>
                  {viewing.cgst_amount > 0 && <div style={{ display: "flex", justifyContent: "space-between" }}><span>CGST:</span><span>{inr(viewing.cgst_amount)}</span></div>}
                  {viewing.sgst_amount > 0 && <div style={{ display: "flex", justifyContent: "space-between" }}><span>SGST:</span><span>{inr(viewing.sgst_amount)}</span></div>}
                  {viewing.igst_amount > 0 && <div style={{ display: "flex", justifyContent: "space-between" }}><span>IGST:</span><span>{inr(viewing.igst_amount)}</span></div>}
                  <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px dashed rgba(255,255,255,0.1)", paddingTop: "6px", fontWeight: "bold" }}>
                    <span>Grand Monthly Total:</span><span>{inr(viewing.total_amount)}</span>
                  </div>
                </div>
              </Card>

              <Title level={5}>Contract Lines &amp; Allocated Units</Title>
              <Table
                rowKey="id"
                dataSource={viewing.lines}
                pagination={false}
                size="small"
                columns={[
                  { title: "Product / SKU", dataIndex: "product_id", key: "product_id", render: getProductName },
                  { title: "Qty", dataIndex: "quantity", key: "quantity" },
                  { title: "Rent Rate", dataIndex: "unit_price", key: "unit_price", render: (v) => "₹" + v },
                  { title: "Allocated Unit ID", dataIndex: "rental_unit_id", key: "rental_unit_id", render: (v) => v ? <Tag color="green">Allocated ({v.slice(0,8)})</Tag> : <Tag color="orange">Pending Allocation</Tag> }
                ]}
              />
              {viewing.notes && <div><strong>Terms / Notes:</strong> <p style={{ whiteSpace: "pre-wrap" }}>{viewing.notes}</p></div>}
            </div>
          )}
        </Modal>

        {/* Modal: Check-Out */}
        <Modal title={`Equipment Check-Out - ${checkoutModal?.contract_number ?? ""}`} open={!!checkoutModal} onOk={saveCheckout} onCancel={() => setCheckoutModal(null)} confirmLoading={saving} width={500}>
          <Form form={checkoutForm} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item name="rental_unit_id" label="Select Physical Unit (Available Serials)" rules={[{ required: true, message: "Required" }]}>
              <Select placeholder="Select a serial-tracked hardware item">
                {availableUnits
                  .filter(u => checkoutModal?.lines.some(l => l.product_id === u.product_id && !l.rental_unit_id))
                  .map(u => (
                    <Option key={u.id} value={u.id}>
                      {u.serial_number} — {getProductName(u.product_id)}
                    </Option>
                  ))
                }
              </Select>
            </Form.Item>
            <Form.Item name="condition" label="Check-Out Condition" rules={[{ required: true }]}>
              <Select>
                <Option value="new">NEW</Option>
                <Option value="good">GOOD</Option>
                <Option value="fair">FAIR</Option>
              </Select>
            </Form.Item>
            <Form.Item name="notes" label="Check-Out Notes"><Input.TextArea rows={2} /></Form.Item>
          </Form>
        </Modal>

        {/* Modal: Check-In */}
        <Modal title={`Equipment Check-In - ${checkinModal?.contract_number ?? ""}`} open={!!checkinModal} onOk={saveCheckin} onCancel={() => setCheckinModal(null)} confirmLoading={saving} width={500}>
          <Form form={checkinForm} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item name="rental_unit_id" label="Select Returning Unit" rules={[{ required: true, message: "Required" }]}>
              <Select placeholder="Select unit returning to inventory">
                {checkinModal?.lines
                  .filter(l => l.rental_unit_id !== null && l.rental_unit_id !== undefined)
                  .map(l => (
                    <Option key={l.rental_unit_id} value={l.rental_unit_id!}>
                      {getProductName(l.product_id)}
                    </Option>
                  ))
                }
              </Select>
            </Form.Item>
            <Form.Item name="condition" label="Returning Condition" rules={[{ required: true }]}>
              <Select>
                <Option value="good">GOOD</Option>
                <Option value="fair">FAIR</Option>
                <Option value="poor">POOR (Will set to maintenance)</Option>
              </Select>
            </Form.Item>
            <Form.Item name="notes" label="Check-In Notes"><Input.TextArea rows={2} /></Form.Item>
          </Form>
        </Modal>

        {/* Modal: Run recurring billing */}
        <Modal title="Run Monthly Recurring Billing" open={billingModal} onOk={runRecurringBilling} onCancel={() => setBillingModal(false)} confirmLoading={saving} width={450}>
          <Form form={billingForm} layout="vertical" style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ display: "block", marginBottom: "16px" }}>
              This will parse all active rental contracts and automatically generate monthly tax invoices for the selected billing target date.
            </Text>
            <Form.Item name="billing_date" label="Billing Run Target Date" rules={[{ required: true }]}>
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </ConfigProvider>
  );
}
