import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Tag, Table, Typography, Badge, Alert } from "antd";
import {
  TeamOutlined, FileTextOutlined, ToolOutlined, DollarOutlined,
  AuditOutlined, CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined,
} from "@ant-design/icons";
import apiClient from "../api/client";

const { Title } = Typography;

interface DashboardStats {
  total_customers: number;
  total_leads: number;
  converted_leads: number;
  active_amc: number;
  pending_amc: number;
  paid_invoices: number;
  followup_invoices: number;
  defaulted_invoices: number;
  total_revenue: number;
  outstanding: number;
}

interface InvoiceRow {
  id: string;
  invoice_number: string;
  customer_name: string;
  total_amount: number;
  amount_paid: number;
  status: string;
  due_date: string;
  notes: string | null;
}

interface AMCRow {
  contract_number: string;
  customer_name: string;
  status: string;
  annual_amount: number;
  end_date: string;
}

const statusTag = (status: string) => {
  const map: Record<string, [string, React.ReactNode]> = {
    paid:           ["green",  <CheckCircleOutlined />],
    overdue:        ["red",    <CloseCircleOutlined />],
    partially_paid: ["orange", <ExclamationCircleOutlined />],
    active:         ["green",  <CheckCircleOutlined />],
    draft:          ["gold",   <ExclamationCircleOutlined />],
  };
  const [color, icon] = map[status] ?? ["default", null];
  return <Tag color={color} icon={icon}>{status.replace("_", " ")}</Tag>;
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [amcContracts, setAmcContracts] = useState<AMCRow[]>([]);

  useEffect(() => {
    const load = async () => {
      const [custRes, leadsRes, amcRes, invRes] = await Promise.all([
        apiClient.get("/customers"),
        apiClient.get("/leads"),
        apiClient.get("/amc"),
        apiClient.get("/invoices"),
      ]);

      const customers: Record<string, string> = {};
      custRes.data.forEach((c: any) => { customers[c.id] = c.name; });

      const leads = leadsRes.data;
      const amc = amcRes.data;
      const inv = invRes.data;

      const today = new Date();
      const paid = inv.filter((i: any) => i.status === "paid");
      const overdueDays = (i: any) => i.due_date ? Math.floor((today.getTime() - new Date(i.due_date).getTime()) / 86400000) : 0;
      const defaulted = inv.filter((i: any) => i.status === "overdue" && (i.notes?.includes("DEFAULTER") || overdueDays(i) > 45));
      const defaultedIds = new Set(defaulted.map((i: any) => i.id));
      const followup = inv.filter((i: any) => ["overdue", "partially_paid"].includes(i.status) && !defaultedIds.has(i.id));

      setStats({
        total_customers: custRes.data.length,
        total_leads: leads.length,
        converted_leads: leads.filter((l: any) => l.status === "converted").length,
        active_amc: amc.filter((a: any) => a.status === "active").length,
        pending_amc: amc.filter((a: any) => a.status === "draft").length,
        paid_invoices: paid.length,
        followup_invoices: followup.length,
        defaulted_invoices: defaulted.length,
        total_revenue: paid.reduce((s: number, i: any) => s + Number(i.amount_paid), 0),
        outstanding: inv.filter((i: any) => i.status !== "paid").reduce((s: number, i: any) => s + (Number(i.total_amount) - Number(i.amount_paid)), 0),
      });

      setInvoices(inv.map((i: any) => ({ ...i, customer_name: customers[i.customer_id] ?? "—" })));
      setAmcContracts(amc.map((a: any) => ({ ...a, customer_name: customers[a.customer_id] ?? "—" })));
    };
    load();
  }, []);

  const invoiceCols = [
    { title: "Invoice #", dataIndex: "invoice_number", key: "inv" },
    { title: "Customer", dataIndex: "customer_name", key: "cust" },
    { title: "Amount (₹)", dataIndex: "total_amount", key: "amt", render: (v: number) => v.toLocaleString("en-IN") },
    { title: "Paid (₹)", dataIndex: "amount_paid", key: "paid", render: (v: number) => v.toLocaleString("en-IN") },
    { title: "Status", dataIndex: "status", key: "status", render: statusTag },
    { title: "Due", dataIndex: "due_date", key: "due" },
    { title: "Remarks", dataIndex: "notes", key: "notes", ellipsis: true, render: (v: string | null) => v || "—" },
  ];

  const amcCols = [
    { title: "Contract #", dataIndex: "contract_number", key: "cn" },
    { title: "Customer", dataIndex: "customer_name", key: "cust" },
    { title: "Status", dataIndex: "status", key: "status", render: statusTag },
    { title: "Annual AMC (₹)", dataIndex: "annual_amount", key: "amt", render: (v: number) => v.toLocaleString("en-IN") },
    { title: "Valid Till", dataIndex: "end_date", key: "end" },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 20 }}>Dashboard</Title>

      {/* Row 1 — Business overview */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="Total Customers" value={stats?.total_customers ?? 0} prefix={<TeamOutlined />} valueStyle={{ color: "#1677ff" }} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="Total Leads" value={stats?.total_leads ?? 0} prefix={<AuditOutlined />} suffix={<span style={{ fontSize: 13, color: "#52c41a" }}>  {stats?.converted_leads ?? 0} converted</span>} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="Active AMC Contracts" value={stats?.active_amc ?? 0} prefix={<FileTextOutlined />} valueStyle={{ color: "#52c41a" }} suffix={stats?.pending_amc ? <Badge count={`${stats.pending_amc} pending`} color="gold" style={{ fontSize: 11 }} /> : null} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="Revenue Collected (₹)" value={stats?.total_revenue ?? 0} prefix={<DollarOutlined />} precision={0} valueStyle={{ color: "#722ed1" }} formatter={(v) => Number(v).toLocaleString("en-IN")} /></Card>
        </Col>
      </Row>

      {/* Row 2 — Invoice health */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={8}>
          <Card style={{ borderLeft: "4px solid #52c41a" }}>
            <Statistic title="Paid On Time" value={stats?.paid_invoices ?? 0} prefix={<CheckCircleOutlined style={{ color: "#52c41a" }} />} valueStyle={{ color: "#52c41a" }} suffix="invoices" />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderLeft: "4px solid #fa8c16" }}>
            <Statistic title="Needs Follow-up" value={stats?.followup_invoices ?? 0} prefix={<ExclamationCircleOutlined style={{ color: "#fa8c16" }} />} valueStyle={{ color: "#fa8c16" }} suffix="invoices" />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderLeft: "4px solid #f5222d" }}>
            <Statistic title="In Default" value={stats?.defaulted_invoices ?? 0} prefix={<CloseCircleOutlined style={{ color: "#f5222d" }} />} valueStyle={{ color: "#f5222d" }} suffix="customer(s)" />
          </Card>
        </Col>
      </Row>

      {/* Outstanding alert */}
      {(stats?.outstanding ?? 0) > 0 && (
        <Alert
          style={{ marginTop: 16 }}
          type="warning"
          showIcon
          message={`Outstanding receivables: ₹${stats!.outstanding.toLocaleString("en-IN")} — ${stats!.followup_invoices} follow-up + ${stats!.defaulted_invoices} default`}
        />
      )}

      {/* AMC Contracts table */}
      <Title level={5} style={{ marginTop: 24, marginBottom: 8 }}>AMC Contracts</Title>
      <Table rowKey="contract_number" columns={amcCols} dataSource={amcContracts} pagination={false} size="small"
        rowClassName={(r: AMCRow) => r.status === "draft" ? "ant-table-row-warning" : ""} />

      {/* Invoices table */}
      <Title level={5} style={{ marginTop: 24, marginBottom: 8 }}>Invoice Status</Title>
      <Table rowKey="id" columns={invoiceCols} dataSource={invoices} pagination={false} size="small"
        rowClassName={(r: InvoiceRow) => r.notes?.includes("DEFAULTER") ? "ant-table-row-danger" : ""} />
    </div>
  );
}
