import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  InputNumber, DatePicker, Dropdown, Alert,
} from "antd";
import { PlusOutlined, MoreOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import apiClient from "../api/client";

const { Title } = Typography;
const { Option } = Select;

const STATUS_FLOW = ["survey_pending", "survey_done", "material_allocated", "in_progress", "completed", "handed_over"];
const statusColor: Record<string, string> = {
  survey_pending: "default", survey_done: "blue", material_allocated: "cyan",
  in_progress: "gold", completed: "green", handed_over: "purple",
};

interface Customer { id: string; name: string }
interface Installation {
  id: string; work_order_number: string; customer_id: string; status: string;
  target_completion_date?: string; recommended_camera_count?: number; amc_contract_id?: string;
}

export default function InstallationsPage() {
  const [rows, setRows] = useState<Installation[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [survey, setSurvey] = useState<Installation | null>(null);
  const [handover, setHandover] = useState<Installation | null>(null);
  const [otp, setOtp] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [sForm] = Form.useForm();
  const [hForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ins, cs] = await Promise.all([
        apiClient.get("/installations", { params: { limit: 200 } }),
        apiClient.get("/customers", { params: { limit: 200 } }),
      ]);
      setRows(ins.data); setCustomers(cs.data);
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load installations"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const cName = (id: string) => customers.find(c => c.id === id)?.name || id.slice(0, 8);

  const create = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      await apiClient.post("/installations", {
        customer_id: v.customer_id,
        target_completion_date: v.target_completion_date ? v.target_completion_date.format("YYYY-MM-DD") : null,
      });
      message.success("Work order created"); setCreateOpen(false); form.resetFields(); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed"); }
    finally { setSaving(false); }
  };

  const setStatus = async (r: Installation, status: string) => {
    try { await apiClient.patch(`/installations/${r.id}`, { status }); message.success("Status updated"); load(); }
    catch (e: any) { message.error(e?.response?.data?.detail || "Failed"); }
  };

  const recordSurvey = async () => {
    const v = await sForm.validateFields();
    setSaving(true);
    try {
      await apiClient.post(`/installations/${survey!.id}/survey`, {
        survey_date: v.survey_date ? v.survey_date.format("YYYY-MM-DD") : null,
        survey_notes: v.survey_notes, feasibility_notes: v.feasibility_notes,
        recommended_camera_count: v.recommended_camera_count,
      });
      message.success("Survey recorded"); setSurvey(null); sForm.resetFields(); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed"); }
    finally { setSaving(false); }
  };

  const requestOtp = async (r: Installation) => {
    try {
      const { data } = await apiClient.post(`/installations/${r.id}/handover-otp`);
      setOtp(data.otp);
      Modal.info({ title: "Handover OTP", content: `Share this OTP with the customer: ${data.otp}` });
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed"); }
  };

  const doHandover = async () => {
    const v = await hForm.validateFields();
    setSaving(true);
    try {
      await apiClient.post(`/installations/${handover!.id}/handover`, v);
      message.success("Handover complete — AMC created"); setHandover(null); hForm.resetFields(); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Handover failed"); }
    finally { setSaving(false); }
  };

  const columns = [
    { title: "Work Order", dataIndex: "work_order_number", key: "work_order_number" },
    { title: "Customer", dataIndex: "customer_id", key: "customer_id", render: cName },
    { title: "Cameras", dataIndex: "recommended_camera_count", key: "cameras", render: (v?: number) => v ?? "—" },
    { title: "Target", dataIndex: "target_completion_date", key: "target", render: (v?: string) => v || "—" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v.replace(/_/g, " ")}</Tag> },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, r: Installation) => {
        const items = [
          { key: "survey", label: "Record survey", onClick: () => { sForm.resetFields(); sForm.setFieldsValue({ survey_date: dayjs() }); setSurvey(r); } },
          ...STATUS_FLOW.filter(s => s !== r.status && s !== "handed_over").map(s => ({
            key: s, label: `Mark ${s.replace(/_/g, " ")}`, onClick: () => setStatus(r, s),
          })),
          { type: "divider" as const },
          { key: "otp", label: "Request handover OTP", disabled: r.status === "handed_over", onClick: () => requestOtp(r) },
          { key: "handover", label: "Complete handover", disabled: r.status === "handed_over", onClick: () => { hForm.resetFields(); hForm.setFieldsValue({ amc_months: 12, preventive_visits_per_year: 2, amc_annual_amount: 0 }); setHandover(r); } },
        ];
        return <Dropdown menu={{ items }}><Button size="small" icon={<MoreOutlined />} /></Dropdown>;
      },
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Installations</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setCreateOpen(true); }}>New Work Order</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No installation work orders" }} />

      <Modal title="New Installation Work Order" open={createOpen} onOk={create} onCancel={() => setCreateOpen(false)} confirmLoading={saving} okText="Create">
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="children">{customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="target_completion_date" label="Target Completion"><DatePicker style={{ width: "100%" }} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="Record Survey" open={!!survey} onOk={recordSurvey} onCancel={() => setSurvey(null)} confirmLoading={saving} okText="Save">
        <Form form={sForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="survey_date" label="Survey Date"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="recommended_camera_count" label="Recommended Cameras"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="survey_notes" label="Survey Notes"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="feasibility_notes" label="Feasibility Notes"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="Complete Handover" open={!!handover} onOk={doHandover} onCancel={() => setHandover(null)} confirmLoading={saving} okText="Complete">
        <Alert type="info" showIcon style={{ marginBottom: 16 }}
          message="Enter the OTP shared with the customer. An AMC contract is created on successful handover." />
        <Form form={hForm} layout="vertical">
          <Form.Item name="otp" label="Customer OTP" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="amc_annual_amount" label="AMC Annual Amount (₹)" rules={[{ required: true }]}><InputNumber min={0} style={{ width: "100%" }} /></Form.Item>
          <Space>
            <Form.Item name="amc_months" label="AMC Months" rules={[{ required: true }]}><InputNumber min={1} /></Form.Item>
            <Form.Item name="preventive_visits_per_year" label="PM Visits/Year" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
