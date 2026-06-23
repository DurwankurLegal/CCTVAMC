import { useEffect, useState } from "react";
import { Col, Row, Tag, Table, Typography, Alert } from "antd";
import {
  TeamOutlined, FileTextOutlined, ToolOutlined, DollarOutlined,
  AuditOutlined, CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";
import SmartCard from "../components/SmartCard";
import MetricProgressGauge from "../components/MetricProgressGauge";

const { Title, Text } = Typography;

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
  total_tickets: number;
  sla_breached_tickets: number;
  sla_compliance: number;
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
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [amcContracts, setAmcContracts] = useState<AMCRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [custRes, leadsRes, amcRes, invRes, ticketsRes] = await Promise.all([
          apiClient.get("/customers"),
          apiClient.get("/leads"),
          apiClient.get("/amc"),
          apiClient.get("/invoices"),
          apiClient.get("/service-tickets"),
        ]);

        const customers: Record<string, string> = {};
        custRes.data.forEach((c: any) => { customers[c.id] = c.name; });

        const leads = leadsRes.data;
        const amc = amcRes.data;
        const inv = invRes.data;
        const tickets = ticketsRes.data;

        const today = new Date();
        const paid = inv.filter((i: any) => i.status === "paid");
        const overdueDays = (i: any) => i.due_date ? Math.floor((today.getTime() - new Date(i.due_date).getTime()) / 86400000) : 0;
        const defaulted = inv.filter((i: any) => i.status === "overdue" && (i.notes?.includes("DEFAULTER") || overdueDays(i) > 45));
        const defaultedIds = new Set(defaulted.map((i: any) => i.id));
        const followup = inv.filter((i: any) => ["overdue", "partially_paid"].includes(i.status) && !defaultedIds.has(i.id));

        const slaBreached = tickets.filter((t: any) => t.sla_breached).length;
        const slaCompliance = tickets.length ? ((tickets.filter((t: any) => !t.sla_breached).length / tickets.length) * 100) : 100;

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
          total_tickets: tickets.length,
          sla_breached_tickets: slaBreached,
          sla_compliance: slaCompliance,
        });

        setInvoices(inv.map((i: any) => ({ ...i, customer_name: customers[i.customer_id] ?? "—" })));
        setAmcContracts(amc.map((a: any) => ({ ...a, customer_name: customers[a.customer_id] ?? "—" })));
      } catch (err) {
        console.error("Dashboard failed to load metrics", err);
      } finally {
        setLoading(false);
      }
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

  const renderOutstandingAlert = () => {
    if (!stats || stats.outstanding <= 0) return null;
    return (
      <Alert
        style={{
          marginTop: 8,
          background: "rgba(245, 158, 11, 0.1)",
          border: "1px solid rgba(245, 158, 11, 0.3)",
          borderRadius: "8px",
        }}
        type="warning"
        showIcon
        message={
          <span style={{ color: "#f59e0b", fontWeight: 500 }}>
            Outstanding receivables: ₹{stats.outstanding.toLocaleString("en-IN")} — {stats.followup_invoices} follow-up + {stats.defaulted_invoices} default accounts. Click cards below to track details.
          </span>
        }
      />
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Title level={4} style={{ margin: 0 }}>Operational Intelligence Command Center</Title>
        <span style={{ color: "#9ca3af", fontSize: "12px", background: "rgba(255,255,255,0.05)", padding: "4px 8px", borderRadius: "4px" }}>
          Metrics updated live
        </span>
      </div>

      {/* Row 1 — SLA Gauge & High-level Financial Overview */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <MetricProgressGauge
            title="SLA Compliance Rate"
            percent={stats?.sla_compliance ?? 100}
            status={stats && stats.sla_compliance < 90 ? (stats.sla_compliance < 75 ? "danger" : "warning") : "success"}
            subtext={
              <span>
                {stats?.total_tickets ?? 0} tickets · {stats?.sla_breached_tickets ?? 0} breached
                {stats && stats.sla_breached_tickets > 0 && <span className="pulsing-dot" style={{ marginLeft: "6px" }} />}
              </span>
            }
            onClick={() => navigate(`/tickets${stats?.sla_breached_tickets ? "?sla=breached" : ""}`)}
          />
        </Col>
        <Col xs={24} sm={12} md={8}>
          <SmartCard
            title="Revenue Collected"
            value={`₹${(stats?.total_revenue ?? 0).toLocaleString("en-IN")}`}
            prefix={<DollarOutlined />}
            status="success"
            onClick={() => navigate("/payments")}
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={12} md={8}>
          <SmartCard
            title="Outstanding Balance"
            value={`₹${(stats?.outstanding ?? 0).toLocaleString("en-IN")}`}
            prefix={<ExclamationCircleOutlined />}
            status="warning"
            onClick={() => navigate("/invoices?status=overdue")}
            loading={loading}
          />
        </Col>
      </Row>

      {/* Row 2 — Operational Metrics */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={8}>
          <SmartCard
            title="Active AMC Contracts"
            value={stats?.active_amc ?? 0}
            prefix={<FileTextOutlined />}
            suffix={
              stats?.pending_amc ? (
                <Tag color="gold" style={{ fontSize: "10px", margin: 0 }}>
                  {stats.pending_amc} Draft Contracts
                </Tag>
              ) : undefined
            }
            onClick={() => navigate("/amc?status=active")}
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <SmartCard
            title="Total Customers"
            value={stats?.total_customers ?? 0}
            prefix={<TeamOutlined />}
            onClick={() => navigate("/customers?status=active")}
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={24} lg={8}>
          <SmartCard
            title="Total Leads"
            value={stats?.total_leads ?? 0}
            prefix={<AuditOutlined />}
            suffix={
              stats?.converted_leads ? (
                <Text style={{ fontSize: "12px", color: "#10b981" }}>
                  ✓ {stats.converted_leads} converted to customers
                </Text>
              ) : undefined
            }
            onClick={() => navigate("/leads")}
            loading={loading}
          />
        </Col>
      </Row>

      {/* Row 3 — Invoices Health Check */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <SmartCard
            title="Paid Invoices"
            value={stats?.paid_invoices ?? 0}
            prefix={<CheckCircleOutlined />}
            status="success"
            onClick={() => navigate("/invoices?status=paid")}
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={8}>
          <SmartCard
            title="Needs Follow-up"
            value={stats?.followup_invoices ?? 0}
            prefix={<ExclamationCircleOutlined />}
            status="warning"
            onClick={() => navigate("/invoices?status=overdue")}
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={8}>
          <SmartCard
            title="Defaulter Accounts"
            value={stats?.defaulted_invoices ?? 0}
            prefix={<CloseCircleOutlined />}
            status="danger"
            onClick={() => navigate("/invoices?status=overdue&defaulter=true")}
            loading={loading}
          />
        </Col>
      </Row>

      {renderOutstandingAlert()}

      {/* AMC Contracts Table */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px" }}>
        <Title level={5} style={{ margin: 0 }}>Recent AMC Contracts</Title>
        <Table
          rowKey="contract_number"
          columns={amcCols}
          dataSource={amcContracts.slice(0, 5)}
          pagination={false}
          size="small"
          rowClassName={() => "interactive-table-row"}
          onRow={(record) => ({
            onClick: () => navigate(`/amc?contract_number=${record.contract_number}`),
          })}
        />
      </div>

      {/* Invoices Table */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <Title level={5} style={{ margin: 0 }}>Recent Invoices Status</Title>
        <Table
          rowKey="id"
          columns={invoiceCols}
          dataSource={invoices.slice(0, 5)}
          pagination={false}
          size="small"
          rowClassName={() => "interactive-table-row"}
          onRow={(record) => ({
            onClick: () => navigate(`/invoices?status=${record.status}`),
          })}
        />
      </div>
    </div>
  );
}
