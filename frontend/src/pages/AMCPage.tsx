import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, InputNumber, Select, Tag, Typography, DatePicker, Space, message, Row, Col, Input, AutoComplete } from "antd";
import { PlusOutlined, EditOutlined, UserOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";
import apiClient from "../api/client";
import type { AppDispatch, RootState } from "../store";
import { fetchCustomers } from "../store/customerSlice";
import dayjs from "dayjs";

const { Title } = Typography;
const { Option } = Select;

interface AMCContract {
  id: string;
  contract_number: string;
  customer_id: string;
  status: string;
  start_date: string;
  end_date: string;
  annual_amount: number;
  payment_frequency: string | null;
  is_active: boolean;
}

const STATUSES = ["draft", "active", "expiring", "renewed", "terminated"];

import { useParsedSearchParams } from "../utils/navigation";

export default function AMCPage() {
  const dispatch = useDispatch<AppDispatch>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<AMCContract[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<AMCContract | null>(null);
  const [form] = Form.useForm();
  const customers = useSelector((s: RootState) => s.customers.items);

  const { status, contract_number } = useParsedSearchParams();

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get("/amc");
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    dispatch(fetchCustomers());
  }, []);

  useEffect(() => {
    const createParam = searchParams.get("create");
    const nameParam = searchParams.get("customer_name");
    if (createParam === "true" && nameParam) {
      setEditing(null);
      form.resetFields();
      form.setFieldsValue({ customer_name: nameParam });
      setOpen(true);
      
      const newParams = new URLSearchParams(searchParams);
      newParams.delete("create");
      newParams.delete("customer_name");
      setSearchParams(newParams);
    }
  }, [searchParams]);

  const filteredItems = items.filter(item => {
    if (status && item.status !== status) return false;
    if (contract_number && item.contract_number !== contract_number) return false;
    return true;
  });

  const openCreate = () => { setEditing(null); form.resetFields(); setOpen(true); };
  const openEdit = (row: AMCContract) => {
    setEditing(row);
    form.setFieldsValue({
      ...row,
      start_date: row.start_date ? dayjs(row.start_date) : null,
      end_date: row.end_date ? dayjs(row.end_date) : null,
    });
    setOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        // Update accepts a subset; dates optional
        await apiClient.patch(`/amc/${editing.id}`, {
          status: values.status,
          end_date: values.end_date?.format("YYYY-MM-DD"),
          annual_amount: values.annual_amount,
          payment_frequency: values.payment_frequency,
          preventive_visits_per_year: values.preventive_visits_per_year,
        });
        message.success("Contract updated");
      } else {
        const customerName = values.customer_name.trim();
        let targetCustomerId = "";

        // Find existing customer (case-insensitive)
        const matchedCustomer = customers.find(
          (c: any) => c.name.toLowerCase() === customerName.toLowerCase()
        );

        if (matchedCustomer) {
          targetCustomerId = matchedCustomer.id;
        } else {
          // Create new customer
          const newCustRes = await apiClient.post("/customers", {
            name: customerName,
            category: "commercial",
            status: "active"
          });
          targetCustomerId = newCustRes.data.id;
          
          // Refresh customer store list
          dispatch(fetchCustomers());
        }

        await apiClient.post("/amc", {
          customer_id: targetCustomerId,
          start_date: values.start_date.format("YYYY-MM-DD"),
          end_date: values.end_date.format("YYYY-MM-DD"),
          annual_amount: values.annual_amount,
          payment_frequency: values.payment_frequency,
          preventive_visits_per_year: values.preventive_visits_per_year,
        });
        message.success("Contract created");
      }
      form.resetFields();
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const activate = async (row: AMCContract) => {
    try {
      await apiClient.post(`/amc/${row.id}/activate`);
      message.success("Contract activated; PM schedule generated");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Activate failed");
    }
  };

  const statusColor: Record<string, string> = {
    active: "green", expiring: "gold", terminated: "red", renewed: "cyan", draft: "blue",
  };

  const columns = [
    { title: "Contract #", dataIndex: "contract_number", key: "contract_number" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v}</Tag> },
    { title: "Start", dataIndex: "start_date", key: "start_date" },
    { title: "End", dataIndex: "end_date", key: "end_date" },
    { title: "Annual Amount (₹)", dataIndex: "annual_amount", key: "annual_amount", render: (v: number) => Number(v).toLocaleString("en-IN") },
    { title: "Frequency", dataIndex: "payment_frequency", key: "payment_frequency", render: (v: string) => v || "—" },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, row: AMCContract) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>Edit</Button>
          {row.status === "draft" && <Button size="small" type="link" onClick={() => activate(row)}>Activate</Button>}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>AMC Contracts</Title>
      </div>

      <Button
        type="primary"
        shape="circle"
        icon={<PlusOutlined />}
        onClick={openCreate}
        size="large"
        style={{
          position: "fixed",
          bottom: 32,
          right: 32,
          width: 56,
          height: 56,
          zIndex: 1000,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "22px"
        }}
        title="New Contract"
      />

      <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} />

      <Modal centered
        title={
          <div style={{ fontSize: "18px", fontWeight: 600, color: "#111827", paddingBottom: "12px", borderBottom: "1px solid #f3f4f6" }}>
            {editing ? "Edit Contract" : "New Contract"}
          </div>
        }
        open={open}
        onOk={handleSave}
        onCancel={() => setOpen(false)}
        confirmLoading={saving}
        width={600}
        okText={editing ? "Save" : "Create"}
        okButtonProps={{ size: "large", style: { borderRadius: "6px" } }}
        cancelButtonProps={{ size: "large", style: { borderRadius: "6px" } }}
        style={{ top: 80 }}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 20 }}>
          <Row gutter={16}>
            {!editing && (
              <Col span={24}>
                <Form.Item
                  name="customer_name"
                  label="Customer Name"
                  rules={[{ required: true, message: "Please enter customer name" }]}
                >
                  <AutoComplete
                    options={customers.map((c: any) => ({ value: c.name }))}
                    placeholder="e.g. Green Valley CHS"
                    filterOption={(inputValue, option) =>
                      option!.value.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
                    }
                  >
                    <Input prefix={<UserOutlined style={{ color: "#8c8c8c" }} />} />
                  </AutoComplete>
                </Form.Item>
              </Col>
            )}
            
            {editing && (
              <Col span={24}>
                <Form.Item name="status" label="Status" rules={[{ required: true }]}>
                  <Select placeholder="Select status">
                    {STATUSES.map(s => <Option key={s} value={s}>{s}</Option>)}
                  </Select>
                </Form.Item>
              </Col>
            )}
          </Row>

          <Row gutter={16}>
            {!editing && (
              <Col span={12}>
                <Form.Item name="start_date" label="Start Date" rules={[{ required: true }]}>
                  <DatePicker style={{ width: "100%" }} placeholder="Select start date" />
                </Form.Item>
              </Col>
            )}
            <Col span={editing ? 24 : 12}>
              <Form.Item name="end_date" label="End Date" rules={[{ required: !editing }]}>
                <DatePicker style={{ width: "100%" }} placeholder="Select end date" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="annual_amount" label="Annual Amount (₹)" rules={[{ required: !editing }]}>
                <InputNumber<number>
                  style={{ width: "100%" }}
                  min={0}
                  placeholder="e.g. 24,000"
                  addonBefore="₹"
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
                  parser={(value) => value ? parseFloat(value.replace(/\$\s?|(,*)/g, "")) || 0 : 0}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="payment_frequency" label="Payment Frequency">
                <Select allowClear placeholder="Select frequency">
                  <Option value="monthly">Monthly</Option>
                  <Option value="quarterly">Quarterly</Option>
                  <Option value="annual">Annual</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="preventive_visits_per_year" label="Preventive Visits / Year">
                <InputNumber style={{ width: "100%" }} min={0} placeholder="e.g. 4" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}
