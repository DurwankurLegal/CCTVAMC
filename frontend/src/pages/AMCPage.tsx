import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, InputNumber, Select, Tag, Typography, DatePicker, Space, message, Input, Card, ConfigProvider, theme } from "antd";
import { PlusOutlined, EditOutlined, ClockCircleOutlined, FileOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import apiClient from "../api/client";
import { fetchCustomers } from "../store/customerSlice";
import type { AppDispatch, RootState } from "../store";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import DocumentModal from "../components/DocumentModal";

const { Title, Text } = Typography;
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
  const [items, setItems] = useState<AMCContract[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<AMCContract | null>(null);
  const [form] = Form.useForm();
  const customers = useSelector((s: RootState) => s.customers.items);

  const { status, contract_number } = useParsedSearchParams();

  // Document attachments state
  const [docsOpen, setDocsOpen] = useState(false);
  const [selectedAMCForDocs, setSelectedAMCForDocs] = useState<AMCContract | null>(null);

  // PM Schedule state
  const [pmScheduleOpen, setPmScheduleOpen] = useState(false);
  const [selectedAMCForPm, setSelectedAMCForPm] = useState<AMCContract | null>(null);
  const [pmSchedule, setPmSchedule] = useState<any[]>([]);
  const [pmSummary, setPmSummary] = useState<any>(null);
  const [loadingSchedule, setLoadingSchedule] = useState(false);

  // Reschedule / Skip Action state
  const [actionPmVisit, setActionPmVisit] = useState<any | null>(null);
  const [pmActionType, setPmActionType] = useState<"reschedule" | "skip" | null>(null);
  const [actionReason, setActionReason] = useState("");
  const [actionNewDate, setActionNewDate] = useState<Dayjs | null>(null);
  const [submittingAction, setSubmittingAction] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get("/amc");
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  const loadPmSchedule = async (amcId: string) => {
    setLoadingSchedule(true);
    try {
      const { data } = await apiClient.get(`/amc/${amcId}/pm-schedule`);
      setPmSchedule(data.visits || []);
      setPmSummary(data.summary || null);
    } catch {
      setPmSchedule([]);
      setPmSummary(null);
    } finally {
      setLoadingSchedule(false);
    }
  };

  const handlePmActionSubmit = async () => {
    if (!actionPmVisit || !pmActionType) return;
    if (pmActionType === "reschedule" && !actionNewDate) {
      message.warning("Please select a new date");
      return;
    }
    if (!actionReason.trim()) {
      message.warning("Please provide a reason");
      return;
    }

    setSubmittingAction(true);
    try {
      if (pmActionType === "reschedule") {
        await apiClient.post(`/amc/pm-schedule/${actionPmVisit.id}/reschedule`, {
          new_date: actionNewDate!.format("YYYY-MM-DD"),
          reason: actionReason.trim(),
        });
        message.success("PM visit rescheduled");
      } else {
        await apiClient.post(`/amc/pm-schedule/${actionPmVisit.id}/skip`, {
          reason: actionReason.trim(),
        });
        message.success("PM visit skipped");
      }
      setPmActionType(null);
      setActionPmVisit(null);
      if (selectedAMCForPm) {
        loadPmSchedule(selectedAMCForPm.id);
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Action failed");
    } finally {
      setSubmittingAction(false);
    }
  };

  useEffect(() => { load(); dispatch(fetchCustomers()); }, [dispatch]);

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
          {row.status !== "draft" && (
            <Button
              size="small"
              icon={<ClockCircleOutlined />}
              onClick={() => {
                setSelectedAMCForPm(row);
                loadPmSchedule(row.id);
                setPmScheduleOpen(true);
              }}
            >
              PM Schedule
            </Button>
          )}
          <Button
            size="small"
            icon={<FileOutlined />}
            onClick={() => {
              setSelectedAMCForDocs(row);
              setDocsOpen(true);
            }}
          >
            Docs
          </Button>
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
          colorPrimary: "#14b8a6",
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
              <SafetyCertificateOutlined style={{ color: "#14b8a6" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                AMC Contracts Hub
              </span>
            </Title>
            <Text style={{ color: "#9ca3af", fontSize: "13.5px" }}>
              Oversee annual maintenance contracts, generate schedules, track preventive visits, and manage attachments.
            </Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)", border: "none", color: "#fff" }}>New Contract</Button>
        </div>

        <Card
          id="amc-contracts-panel"
          className="glass-card"
          styles={{
            header: {
              background: "linear-gradient(135deg, rgba(20, 184, 166, 0.08) 0%, rgba(20, 184, 166, 0.02) 100%)",
              borderBottom: "1px solid rgba(20, 184, 166, 0.15)",
              borderRadius: "12px 12px 0 0"
            },
            body: { padding: 0 }
          }}
          title={
            <Space>
              <SafetyCertificateOutlined style={{ color: "#14b8a6", fontSize: 18 }} />
              <span style={{ color: "#f3f4f6", fontWeight: 700, fontSize: 15 }}>
                Active Maintenance Agreements
              </span>
              <Tag color="cyan" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(20, 184, 166, 0.12)", border: "1px solid rgba(20, 184, 166, 0.2)" }}>
                AMC CONTRACTS &amp; SLA
              </Tag>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} />
        </Card>

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

      <Modal
        title={`PM Schedule — ${selectedAMCForPm?.contract_number}`}
        open={pmScheduleOpen}
        onCancel={() => setPmScheduleOpen(false)}
        footer={null}
        width={750}
      >
        {pmSummary && (
          <div style={{ marginBottom: 16, display: "flex", gap: 12 }}>
            <Tag color="blue">Total: {pmSummary.total}</Tag>
            <Tag color="green">Completed: {pmSummary.completed}</Tag>
            <Tag color="red">Skipped: {pmSummary.skipped}</Tag>
            <Tag color="orange">Pending: {pmSummary.pending}</Tag>
          </div>
        )}
        <Table
          rowKey="id"
          loading={loadingSchedule}
          dataSource={pmSchedule}
          size="small"
          pagination={false}
          columns={[
            { title: "Seq #", dataIndex: "sequence_no", key: "seq" },
            { title: "Date", dataIndex: "scheduled_date", key: "date" },
            {
              title: "Status",
              dataIndex: "status",
              key: "status",
              render: (v: string) => {
                const map: Record<string, string> = {
                  planned: "default",
                  done: "green",
                  skipped: "red",
                  rescheduled: "orange",
                };
                return <Tag color={map[v] ?? "default"}>{v.toUpperCase()}</Tag>;
              },
            },
            { title: "Reason / Notes", dataIndex: "reason_code", key: "reason", render: (v: string) => v || "—" },
            {
              title: "Actions",
              key: "actions",
              render: (_: any, r: any) => {
                if (r.status === "planned" || r.status === "rescheduled") {
                  return (
                    <Space>
                      <Button
                        size="small"
                        onClick={() => {
                          setActionPmVisit(r);
                          setPmActionType("reschedule");
                          setActionReason("");
                          setActionNewDate(dayjs(r.scheduled_date));
                        }}
                      >
                        Reschedule
                      </Button>
                      <Button
                        size="small"
                        danger
                        onClick={() => {
                          setActionPmVisit(r);
                          setPmActionType("skip");
                          setActionReason("");
                        }}
                      >
                        Skip
                      </Button>
                    </Space>
                  );
                }
                return "—";
              },
            },
          ]}
        />
      </Modal>

      <Modal
        title={pmActionType === "reschedule" ? "Reschedule PM Visit" : "Skip PM Visit"}
        open={!!pmActionType}
        onOk={handlePmActionSubmit}
        onCancel={() => { setPmActionType(null); setActionPmVisit(null); }}
        confirmLoading={submittingAction}
      >
        <div style={{ marginTop: 16 }}>
          {pmActionType === "reschedule" && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4 }}>New Scheduled Date:</div>
              <DatePicker
                style={{ width: "100%" }}
                value={actionNewDate}
                onChange={(d) => setActionNewDate(d)}
                format="YYYY-MM-DD"
              />
            </div>
          )}
          <div>
            <div style={{ marginBottom: 4 }}>Reason:</div>
            <Input.TextArea
              rows={3}
              value={actionReason}
              onChange={(e) => setActionReason(e.target.value)}
              placeholder="Provide a reason..."
            />
          </div>
        </div>
      </Modal>

      <DocumentModal
        open={docsOpen}
        entityType="amc"
        entityId={selectedAMCForDocs?.id || null}
        entityName={selectedAMCForDocs?.contract_number || ""}
        onClose={() => setDocsOpen(false)}
      />
      </div>
    </ConfigProvider>
  );
}

