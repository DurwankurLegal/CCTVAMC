import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, InputNumber, Select, Tag, Typography, DatePicker, Space, message } from "antd";
import { PlusOutlined, EditOutlined } from "@ant-design/icons";
import { useSelector } from "react-redux";
import apiClient from "../api/client";
import type { RootState } from "../store";
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

  useEffect(() => { load(); }, []);

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
        await apiClient.post("/amc", {
          ...values,
          start_date: values.start_date.format("YYYY-MM-DD"),
          end_date: values.end_date.format("YYYY-MM-DD"),
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
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>New Contract</Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} />

      <Modal
        title={editing ? "Edit AMC Contract" : "New AMC Contract"}
        open={open} onOk={handleSave} onCancel={() => setOpen(false)} confirmLoading={saving} width={560}
        okText={editing ? "Save" : "Create"}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {!editing && (
            <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="children" placeholder="Select customer">
                {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
              </Select>
            </Form.Item>
          )}
          {editing && (
            <Form.Item name="status" label="Status">
              <Select>{STATUSES.map(s => <Option key={s} value={s}>{s}</Option>)}</Select>
            </Form.Item>
          )}
          {!editing && (
            <Form.Item name="start_date" label="Start Date" rules={[{ required: true }]}>
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
          )}
          <Form.Item name="end_date" label="End Date" rules={[{ required: !editing }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="annual_amount" label="Annual Amount (₹)" rules={[{ required: !editing }]}>
            <InputNumber style={{ width: "100%" }} min={0} />
          </Form.Item>
          <Form.Item name="payment_frequency" label="Payment Frequency">
            <Select allowClear>
              <Option value="monthly">Monthly</Option>
              <Option value="quarterly">Quarterly</Option>
              <Option value="annual">Annual</Option>
            </Select>
          </Form.Item>
          <Form.Item name="preventive_visits_per_year" label="Preventive Visits / Year">
            <InputNumber style={{ width: "100%" }} min={0} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
