import React, { useState, useEffect } from "react";
import { Table, Button, Space, Tag, Modal, Form, Input, Select, DatePicker, Card, Row, Col, Typography, message, Tabs, InputNumber, Upload } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined, FilterOutlined, PlusOutlined, EditOutlined, UploadOutlined } from "@ant-design/icons";
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

  // Create/Edit Modal State
  const [isCreateEditOpen, setIsCreateEditOpen] = useState(false);
  const [createEditRecord, setCreateEditRecord] = useState<any | null>(null);
  const [createEditSaving, setCreateEditSaving] = useState(false);
  const [fileList, setFileList] = useState<any[]>([]);
  const [createEditForm] = Form.useForm();

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

  const openCreateModal = () => {
    setCreateEditRecord(null);
    createEditForm.resetFields();
    setFileList([]);
    setIsCreateEditOpen(true);
  };

  const openEditModal = (record: any) => {
    setCreateEditRecord(record);
    createEditForm.resetFields();
    setFileList([]);
    createEditForm.setFieldsValue({
      employee_id: record.employee_id,
      company_id: record.company_id,
      customer_name: record.customer_name,
      amount: record.amount,
      collected_at: dayjs(record.collected_at),
      remarks: record.remarks,
      service_ticket_id: record.service_ticket_id || undefined,
      invoice_id: record.invoice_id || undefined,
    });
    setIsCreateEditOpen(true);
  };

  const handleCreateEditSubmit = async (values: any) => {
    setCreateEditSaving(true);
    try {
      const payload = {
        ...values,
        collected_at: values.collected_at.toISOString(),
      };
      
      let collectionId: string;
      if (createEditRecord) {
        const { data } = await apiClient.put(`/cash-collections/${createEditRecord.id}`, payload);
        collectionId = data.id;
        message.success("Cash collection updated successfully");
      } else {
        const { data } = await apiClient.post("/cash-collections", payload);
        collectionId = data.id;
        message.success("Cash collection created successfully");
      }

      if (fileList.length > 0) {
        const formData = new FormData();
        formData.append("file", fileList[0]);
        await apiClient.post(`/cash-collections/${collectionId}/media`, formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });
      }

      setIsCreateEditOpen(false);
      loadCollections();
    } catch (err: any) {
      message.error(apiErrorMessage(err, "Failed to save cash collection"));
    } finally {
      setCreateEditSaving(false);
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
                <Button
                  type="link"
                  icon={<EditOutlined />}
                  size="small"
                  onClick={() => openEditModal(record)}
                >
                  Edit
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
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          Add Record
        </Button>
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

      {/* Create / Edit Modal */}
      <Modal
        title={createEditRecord ? "Edit Cash Collection Record" : "Add Cash Collection Record"}
        open={isCreateEditOpen}
        onCancel={() => setIsCreateEditOpen(false)}
        onOk={() => createEditForm.submit()}
        confirmLoading={createEditSaving}
        destroyOnClose
      >
        <Form form={createEditForm} layout="vertical" onFinish={handleCreateEditSubmit} style={{ marginTop: 15 }}>
          <Form.Item name="employee_id" label="Employee (Technician)" rules={[{ required: true, message: "Please select employee" }]}>
            <Select placeholder="Select staff member" options={employees.map(e => ({ label: e.full_name, value: e.id }))} />
          </Form.Item>

          <Form.Item name="company_id" label="Operating Company" rules={[{ required: true, message: "Please select operating company" }]}>
            <Select placeholder="Select company" options={companies.map(c => ({ label: c.name, value: c.id }))} />
          </Form.Item>

          <Form.Item name="customer_name" label="Customer Name" rules={[{ required: true, message: "Please enter customer name" }]}>
            <Input placeholder="e.g. Green Valley Estates" />
          </Form.Item>

          <Form.Item name="amount" label="Amount Collected (INR)" rules={[{ required: true, message: "Please enter amount" }]}>
            <InputNumber min={0.01} precision={2} style={{ width: "100%" }} placeholder="0.00" />
          </Form.Item>

          <Form.Item name="collected_at" label="Collected Date & Time" rules={[{ required: true, message: "Please select date and time" }]}>
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="service_ticket_id" label="Service Ticket ID (Optional)">
            <Input placeholder="Copy/paste UUID if linked to a ticket" />
          </Form.Item>

          <Form.Item name="invoice_id" label="Invoice ID (Optional)">
            <Input placeholder="Copy/paste UUID if linked to an invoice" />
          </Form.Item>

          <Form.Item name="remarks" label="Remarks">
            <TextArea rows={2} placeholder="e.g. Collected via cheque / cash handover details" />
          </Form.Item>

          <Form.Item label="Receipt Attachment Photo (Optional)">
            <Upload
              fileList={fileList}
              beforeUpload={(file) => {
                setFileList([file]);
                return false;
              }}
              onRemove={() => setFileList([])}
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>Select Image File</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
