import React, { useState, useEffect } from "react";
import { Table, Button, Space, Tag, Modal, Form, Input, Select, Switch, Card, Row, Col, Typography, Divider, message, Tabs } from "antd";
import { PlusOutlined, EditOutlined, BuildOutlined, CheckCircleOutlined } from "@ant-design/icons";
import apiClient, { apiErrorMessage } from "../api/client";

const { Title, Text } = Typography;
const { TextArea } = Input;

export const CompanySettingsTab: React.FC = () => {
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Company Modal State
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<any | null>(null);
  const [companyForm] = Form.useForm();
  const [companySaving, setCompanySaving] = useState(false);

  // Template Modal State
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [templateCompany, setTemplateCompany] = useState<any | null>(null);
  const [templateForm] = Form.useForm();
  const [templateSaving, setTemplateSaving] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState("TAX_INVOICE");

  const loadCompanies = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get("/companies");
      setCompanies(data);
    } catch (err: any) {
      message.error(apiErrorMessage(err, "Failed to load companies"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCompanies();
  }, []);

  const openAddCompany = () => {
    setEditingCompany(null);
    companyForm.resetFields();
    companyForm.setFieldsValue({
      gst_status: "NON_GST",
      is_default: false,
      is_active: true,
      contact_details: {},
      bank_details: {},
      authorized_signatory: {}
    });
    setIsCompanyModalOpen(true);
  };

  const openEditCompany = (company: any) => {
    setEditingCompany(company);
    companyForm.resetFields();
    companyForm.setFieldsValue(company);
    setIsCompanyModalOpen(true);
  };

  const handleSaveCompany = async (values: any) => {
    setCompanySaving(true);
    try {
      if (editingCompany) {
        await apiClient.put(`/companies/${editingCompany.id}`, values);
        message.success("Company updated successfully");
      } else {
        await apiClient.post("/companies", values);
        message.success("Company created successfully");
      }
      setIsCompanyModalOpen(false);
      loadCompanies();
    } catch (err: any) {
      message.error(apiErrorMessage(err, "Failed to save company"));
    } finally {
      setCompanySaving(false);
    }
  };

  // Templates Management
  const openTemplates = async (company: any) => {
    setTemplateCompany(company);
    setSelectedDocType("TAX_INVOICE");
    setIsTemplateModalOpen(true);
    loadTemplate(company.id, "TAX_INVOICE");
  };

  const loadTemplate = async (companyId: string, docType: string) => {
    templateForm.resetFields();
    try {
      const { data } = await apiClient.get("/company-templates", {
        params: { company_id: companyId }
      });
      const template = data.find((t: any) => t.document_type === docType);
      if (template) {
        templateForm.setFieldsValue(template);
      } else {
        templateForm.setFieldsValue({
          company_id: companyId,
          document_type: docType,
          template_html: "",
          header_html: "",
          footer_html: "",
          is_active: true
        });
      }
    } catch (err: any) {
      message.error(apiErrorMessage(err, "Failed to load template"));
    }
  };

  const handleSaveTemplate = async (values: any) => {
    setTemplateSaving(true);
    try {
      await apiClient.post("/company-templates", {
        ...values,
        company_id: templateCompany.id,
        document_type: selectedDocType
      });
      message.success("Template saved successfully");
      setIsTemplateModalOpen(false);
    } catch (err: any) {
      message.error(apiErrorMessage(err, "Failed to save template"));
    } finally {
      setTemplateSaving(false);
    }
  };

  const companyColumns = [
    {
      title: "Company Name",
      dataIndex: "name",
      key: "name",
      render: (text: string, record: any) => (
        <Space>
          <span style={{ fontWeight: "bold" }}>{text}</span>
          {record.is_default && <Tag color="blue">Default</Tag>}
          {!record.is_active && <Tag color="red">Inactive</Tag>}
        </Space>
      )
    },
    {
      title: "GST Status",
      dataIndex: "gst_status",
      key: "gst_status",
      render: (text: string, record: any) => (
        <Space>
          <Tag color={text === "GST" ? "green" : "orange"}>{text}</Tag>
          {record.gstin && <Text code>{record.gstin}</Text>}
        </Space>
      )
    },
    {
      title: "Email & Phone",
      key: "contact",
      render: (_: any, record: any) => (
        <div>
          <div>{record.contact_details?.email || "-"}</div>
          <div style={{ fontSize: 11, color: "#888" }}>{record.contact_details?.phone || "-"}</div>
        </div>
      )
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, record: any) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEditCompany(record)}>Edit</Button>
          <Button icon={<BuildOutlined />} type="dashed" size="small" onClick={() => openTemplates(record)}>Templates</Button>
        </Space>
      )
    }
  ];

  return (
    <Card
      className="glass-card"
      title="Tenant Operating Entities (Companies)"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={openAddCompany}>
          Add Company
        </Button>
      }
    >
      <Table rowKey="id" loading={loading} columns={companyColumns} dataSource={companies} pagination={false} />

      {/* Add/Edit Company Modal */}
      <Modal
        title={editingCompany ? "Edit Company details" : "Add New Operating Company"}
        open={isCompanyModalOpen}
        onCancel={() => setIsCompanyModalOpen(false)}
        onOk={() => companyForm.submit()}
        confirmLoading={companySaving}
        width={750}
        destroyOnClose
      >
        <Form form={companyForm} layout="vertical" onFinish={handleSaveCompany} style={{ marginTop: 15 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="Company Name" rules={[{ required: true }]}>
                <Input placeholder="e.g. Durwankur Enterprises" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="gst_status" label="GST Registration" rules={[{ required: true }]}>
                <Select
                  options={[
                    { label: "GST Registered", value: "GST" },
                    { label: "Non-GST Entity", value: "NON_GST" }
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="gstin" label="GSTIN">
                <Input placeholder="e.g. 27AAAAA1111A1Z1" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="address" label="Registered Address">
            <TextArea rows={2} placeholder="Office address for bill printing..." />
          </Form.Item>

          <Divider orientation="left" style={{ margin: "10px 0" }}>Contact Details</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={["contact_details", "email"]} label="Billing Email">
                <Input type="email" placeholder="billing@company.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={["contact_details", "phone"]} label="Phone Number">
                <Input placeholder="+91 99999 88888" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ margin: "10px 0" }}>Bank Details</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name={["bank_details", "bank_name"]} label="Bank Name">
                <Input placeholder="HDFC Bank" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={["bank_details", "beneficiary_name"]} label="Account Holder Name">
                <Input placeholder="Durwankur Enterprises" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={["bank_details", "account_number"]} label="Account Number">
                <Input placeholder="5010000213123" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={["bank_details", "ifsc_code"]} label="IFSC Code">
                <Input placeholder="HDFC0000123" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={["bank_details", "branch"]} label="Branch Location">
                <Input placeholder="Shivaji Nagar, Pune" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ margin: "10px 0" }}>Authorized Signatory & Branding</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name={["authorized_signatory", "name"]} label="Signatory Name">
                <Input placeholder="Mr. Rajesh Patil" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={["authorized_signatory", "designation"]} label="Designation">
                <Input placeholder="Proprietor / Director" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={["authorized_signatory", "signature_url"]} label="Signature Image URL">
                <Input placeholder="https://cdn.com/signature.png" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item name="logo_url" label="Branded Logo URL">
                <Input placeholder="https://cdn.com/company_logo.png" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="is_default" label="Mark Default" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="is_active" label="Status Active" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Templates Editor Modal */}
      <Modal
        title={`Configure templates for: ${templateCompany?.name}`}
        open={isTemplateModalOpen}
        onCancel={() => setIsTemplateModalOpen(false)}
        onOk={() => templateForm.submit()}
        confirmLoading={templateSaving}
        width={850}
        destroyOnClose
      >
        <div style={{ marginBottom: 15, marginTop: 10 }}>
          <Space>
            <span>Document Type:</span>
            <Select
              style={{ width: 250 }}
              value={selectedDocType}
              onChange={(val) => {
                setSelectedDocType(val);
                loadTemplate(templateCompany.id, val);
              }}
              options={[
                { label: "Tax Invoice (GST)", value: "TAX_INVOICE" },
                { label: "Invoice (Non-GST)", value: "NON_GST_INVOICE" },
                { label: "Quotation (Standard Fallback)", value: "QUOTATION" },
                { label: "Quotation Template 1 (GST)", value: "QUOTATION_TEMPLATE1" },
                { label: "Quotation Template 2 (IOB Receipt)", value: "QUOTATION_TEMPLATE2" },
                { label: "Payment Receipt", value: "PAYMENT_RECEIPT" },
                { label: "AMC Service Report", value: "AMC_REPORT" }
              ]}
            />
          </Space>
        </div>

        <Form form={templateForm} layout="vertical" onFinish={handleSaveTemplate}>
          <Form.Item name="template_html" label="HTML Layout Code (Jinja2 format)" rules={[{ required: true }]}>
            <TextArea rows={12} style={{ fontFamily: "monospace", fontSize: 12 }} placeholder="Enter Jinja2 compatible HTML print layout..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="header_html" label="Custom Header HTML (Optional)">
                <TextArea rows={3} style={{ fontFamily: "monospace", fontSize: 11 }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="footer_html" label="Custom Footer HTML (Optional)">
                <TextArea rows={3} style={{ fontFamily: "monospace", fontSize: 11 }} />
              </Form.Item>
            </Col>
          </Row>

          <Card style={{ background: "rgba(255,255,255,0.01)", border: "1px dashed rgba(255,255,255,0.08)" }} size="small">
            <Text type="secondary" style={{ fontSize: 11 }}>
              <strong>Available Placeholder Variables:</strong><br/>
              <code>{"{{ company.name }}"}</code>, <code>{"{{ company.address }}"}</code>, <code>{"{{ company.gstin }}"}</code>, 
              <code>{"{{ company.bank.bank_name }}"}</code>, <code>{"{{ company.bank.account_number }}"}</code>, 
              <code>{"{{ doc.invoice_number }}"}</code>, <code>{"{{ doc.invoice_date }}"}</code>, <code>{"{{ customer.name }}"}</code>, 
              <code>{"{{ items }}"}</code> (loop array for lines)
            </Text>
          </Card>
        </Form>
      </Modal>
    </Card>
  );
};
