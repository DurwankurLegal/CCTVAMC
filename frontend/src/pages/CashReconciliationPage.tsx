import React, { useState, useEffect } from "react";
import { Table, Button, Space, Tag, Modal, Form, Input, Select, DatePicker, Card, Row, Col, Typography, message, Tabs } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined, FilterOutlined } from "@ant-design/icons";
import apiClient, { apiErrorMessage } from "../api/client";
import dayjs from "dayjs";

const { Text, Title } = Typography;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

export const CashReconciliationPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState("pending");
  const [collections, setCollections] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Filters
  const [employees, setEmployees] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [filterEmployee, setFilterEmployee] = useState<string | undefined>(undefined);
  const [filterCompany, setFilterCompany] = useState<string | undefined>(undefined);

  // Review Modal State
  const [reviewRecord, setReviewRecord] = useState<any | null>(null);
  const [actionType, setActionType] = useState<"APPROVED" | "REJECTED">("APPROVED");
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [reviewForm] = Form.useForm();
  const [reviewSaving, setReviewSaving] = useState(false);

  // Receipt Preview State
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const loadFilterOptions = async () => {
    try {
      const [empRes, compRes] = await Promise.all([
        apiClient.get("/users"),
        apiClient.get("/companies")
      ]);
      setEmployees(empRes.data.filter((u: any) => u.role === "technician" || u.role === "admin" || u.role === "manager"));
      setCompanies(compRes.data);
    } catch (err: any) {
      console.error("Failed to load filter options", err);
    }
  };

  const loadCollections = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get("/cash-collections", {
        params: {
          employee_id: filterEmployee,
          company_id: filterCompany,
          status: activeTab === "pending" ? "pending" : undefined
        }
      });
      // In history tab, filter out pending entries
      if (activeTab === "history") {
        setCollections(data.filter((c: any) => c.status !== "pending"));
      } else {
        setCollections(data);
      }
    } catch (err: any) {
      message.error(apiErrorMessage(err, "Failed to load cash collections"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFilterOptions();
  }, []);

  useEffect(() => {
    loadCollections();
  }, [activeTab, filterEmployee, filterCompany]);

  const openReviewModal = (record: any, type: "APPROVED" | "REJECTED") => {
    setReviewRecord(record);
    setActionType(type);
    reviewForm.resetFields();
    reviewForm.setFieldsValue({ notes: "" });
    setIsReviewOpen(true);
  };

  const handleReviewSubmit = async (values: any) => {
    setReviewSaving(true);
    try {
      await apiClient.post(`/cash-collections/${reviewRecord.id}/action`, {
        action: actionType,
        notes: values.notes
      });
      message.success(`Collection successfully ${actionType === "APPROVED" ? "approved" : "rejected"}`);
      setIsReviewOpen(false);
      loadCollections();
    } catch (err: any) {
      message.error(apiErrorMessage(err, "Reconciliation action failed"));
    } finally {
      setReviewSaving(false);
    }
  };

  const columns = [
    {
      title: "Collected Date",
      dataIndex: "collected_at",
      key: "collected_at",
      render: (val: string) => dayjs(val).format("YYYY-MM-DD HH:mm")
    },
    {
      title: "Employee (Technician)",
      dataIndex: "employee_id",
      key: "employee",
      render: (val: string) => {
        const emp = employees.find((u) => u.id === val);
        return emp ? emp.full_name : <Text type="secondary">System User</Text>;
      }
    },
    {
      title: "Customer Name",
      dataIndex: "customer_name",
      key: "customer_name"
    },
    {
      title: "Company",
      dataIndex: "company_id",
      key: "company",
      render: (val: string) => {
        const comp = companies.find((c) => c.id === val);
        return comp ? comp.name : "-";
      }
    },
    {
      title: "Amount Collected",
      dataIndex: "amount",
      key: "amount",
      render: (val: number) => (
        <span style={{ fontWeight: "bold", color: "#10b981" }}>
          INR {val.toFixed(2)}
        </span>
      )
    },
    {
      title: "Receipt Photo",
      dataIndex: "receipt_photo_url",
      key: "receipt_photo",
      render: (val: string | null) => (
        val ? (
          <Button type="link" size="small" onClick={() => setPreviewUrl(val)}>View Receipt</Button>
        ) : (
          <Text type="secondary" style={{ fontSize: 11 }}>No Attachment</Text>
        )
      )
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (val: string) => {
        const color = val === "pending" ? "orange" : val === "received" ? "green" : "red";
        return <Tag color={color}>{val.toUpperCase()}</Tag>;
      }
    },
    {
      title: "Remarks",
      dataIndex: "remarks",
      key: "remarks",
      render: (text: string) => text || <Text type="secondary">-</Text>
    },
    ...(activeTab === "pending"
      ? [
          {
            title: "Reconcile Action",
            key: "actions",
            render: (_: any, record: any) => (
              <Space>
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  size="small"
                  onClick={() => openReviewModal(record, "APPROVED")}
                  style={{ backgroundColor: "#2e7d32", borderColor: "#2e7d32" }}
                >
                  Confirm Received
                </Button>
                <Button
                  danger
                  icon={<CloseCircleOutlined />}
                  size="small"
                  onClick={() => openReviewModal(record, "REJECTED")}
                >
                  Reject
                </Button>
              </Space>
            )
          }
        ]
      : [
          {
            title: "Audited details",
            key: "audit",
            render: (_: any, record: any) => {
              const latestLog = record.logs?.[record.logs.length - 1];
              return latestLog ? (
                <div style={{ fontSize: 11 }}>
                  <div>By: {latestLog.action_by ? (employees.find(e => e.id === latestLog.action_by)?.full_name || "Admin") : "Admin"}</div>
                  {latestLog.notes && <div style={{ color: "#777", fontStyle: "italic" }}>"{latestLog.notes}"</div>}
                </div>
              ) : "-";
            }
          }
        ])
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <Title level={3} style={{ margin: 0 }}>Employee Cash Reconciliation</Title>
      </div>

      <Card className="glass-card" style={{ marginBottom: 20 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Text type="secondary" style={{ display: "block", marginBottom: 6 }}><FilterOutlined /> Filter by Company</Text>
            <Select
              allowClear
              style={{ width: "100%" }}
              placeholder="All Companies"
              value={filterCompany}
              onChange={setFilterCompany}
              options={companies.map((c) => ({ label: c.name, value: c.id }))}
            />
          </Col>
          <Col span={6}>
            <Text type="secondary" style={{ display: "block", marginBottom: 6 }}><FilterOutlined /> Filter by Staff</Text>
            <Select
              allowClear
              style={{ width: "100%" }}
              placeholder="All Technicians"
              value={filterEmployee}
              onChange={setFilterEmployee}
              options={employees.map((e) => ({ label: e.full_name, value: e.id }))}
            />
          </Col>
        </Row>
      </Card>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "pending",
            label: `Pending Verification (${collections.length})`,
            children: (
              <Card className="glass-card">
                <Table rowKey="id" loading={loading} columns={columns} dataSource={collections} />
              </Card>
            )
          },
          {
            key: "history",
            label: "Reconciliation History",
            children: (
              <Card className="glass-card">
                <Table rowKey="id" loading={loading} columns={columns} dataSource={collections} />
              </Card>
            )
          }
        ]}
      />

      {/* Review Rejection/Approval notes Modal */}
      <Modal
        title={actionType === "APPROVED" ? "Approve Cash Receipt Handover" : "Reject Cash Receipt Handover"}
        open={isReviewOpen}
        onCancel={() => setIsReviewOpen(false)}
        onOk={() => reviewForm.submit()}
        confirmLoading={reviewSaving}
        destroyOnClose
      >
        <Form form={reviewForm} layout="vertical" onFinish={handleReviewSubmit} style={{ marginTop: 15 }}>
          <Text style={{ display: "block", marginBottom: 15 }}>
            {actionType === "APPROVED"
              ? "Confirming this registers the cash collection into the accounting ledger. The record will move to technician handover logs."
              : "Rejecting returns the record back to the technician's mobile workspace app for adjustment."}
          </Text>
          <Form.Item name="notes" label="Audit Remarks / Notes" rules={[{ required: actionType === "REJECTED", message: "Rejection remarks are mandatory" }]}>
            <TextArea rows={3} placeholder={actionType === "APPROVED" ? "e.g. Verified and collected physically" : "e.g. Invalid receipt photo uploaded, please upload again"} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Receipt Preview Modal */}
      <Modal
        title="Payment Receipt Attachment"
        open={!!previewUrl}
        footer={null}
        onCancel={() => setPreviewUrl(null)}
        width={600}
      >
        {previewUrl && (
          <img src={previewUrl} alt="Receipt Attachment" style={{ width: "100%", maxHeight: "500px", objectFit: "contain", borderRadius: 4 }} />
        )}
      </Modal>
    </div>
  );
};
