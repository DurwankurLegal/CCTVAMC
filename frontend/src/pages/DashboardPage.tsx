import { useEffect, useState } from "react";
import { Col, Row, Tag, Typography, Alert, Card, Table } from "antd";
import {
  TeamOutlined, FileTextOutlined, ToolOutlined, DollarOutlined,
  AuditOutlined, CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { Chart } from "react-google-charts";
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
        // Mocking the exact data requested for the static layout demonstration
        const mockStats = {
          total_customers: 5,
          total_leads: 10,
          converted_leads: 5,
          active_amc: 4,
          pending_amc: 1,
          paid_invoices: 3,
          followup_invoices: 0,
          defaulted_invoices: 0,
          total_revenue: 42480,
          outstanding: 30680,
          total_tickets: 3,
          sla_breached_tickets: 0,
          sla_compliance: 100,
        };

        const mockAmcContracts = [
          { contract_number: "AMC-2026-0001", customer_name: "Green Valley CHS", status: "active", annual_amount: 24000, end_date: "2027-01-15" },
          { contract_number: "AMC-2026-0002", customer_name: "Sunrise Apartments", status: "draft", annual_amount: 18000, end_date: "2027-02-10" },
          { contract_number: "AMC-2026-0003", customer_name: "MegaMart Retail", status: "pending", annual_amount: 48000, end_date: "2027-03-01" },
          { contract_number: "AMC-2026-0004", customer_name: "TechPark Offices", status: "active", annual_amount: 60000, end_date: "2027-04-20" },
          { contract_number: "AMC-2026-0005", customer_name: "Corner Electronics", status: "expired", annual_amount: 12000, end_date: "2026-06-30" },
        ];

        setStats(mockStats as DashboardStats);
        setAmcContracts(mockAmcContracts);
        setInvoices([]); // Not requested for this specific view mock
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
            Outstanding receivables: ₹{(stats.outstanding).toLocaleString("en-IN")} — {stats.followup_invoices} Follow-up + {stats.defaulted_invoices} defaulter accounts. Click cards below to track details.
          </span>
        }
      />
    );
  };

  const pieData = stats ? [
    ["Metric", "Value"],
    ['SLA Compliance (%)', stats.sla_compliance],
    ['Revenue (₹)', stats.total_revenue],
    ['Outstanding (₹)', stats.outstanding],
    ['Active AMC', stats.active_amc],
    ['Total Customers', stats.total_customers],
    ['Total Leads', stats.total_leads],
    ['Paid Invoices', stats.paid_invoices],
    ['Needs Follow-up', stats.followup_invoices],
    ['Defaulter Accounts', stats.defaulted_invoices],
  ] : [];

  const pieOptions = {
    is3D: true,
    colors: ['#10b981', '#34d399', '#ef4444', '#f59e0b', '#3b82f6', '#6366f1', '#8b5cf6', '#fcd34d', '#b91c1c'],
    legend: { position: 'bottom', textStyle: { fontSize: 12 } },
    chartArea: { width: '100%', height: '80%' },
    backgroundColor: 'transparent',
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Title level={4} style={{ margin: 0 }}>Operational Intelligence Command Center</Title>
        <span style={{ color: "#9ca3af", fontSize: "12px", background: "rgba(255,255,255,0.05)", padding: "4px 8px", borderRadius: "4px" }}>
          Metrics updated live
        </span>
      </div>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Row 1 — SLA Gauge & High-level Financial Overview */}
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8} style={{ display: "flex", flexDirection: "column" }}>
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
            <Col xs={24} sm={12} md={8} style={{ display: "flex", flexDirection: "column" }}>
              <SmartCard
                title="Revenue Collected"
                value={`₹${(stats?.total_revenue ?? 0).toLocaleString("en-IN")}`}
                prefix={<DollarOutlined />}
                status="success"
                onClick={() => navigate("/payments")}
                loading={loading}
              />
            </Col>
            <Col xs={24} sm={12} md={8} style={{ display: "flex", flexDirection: "column" }}>
              <SmartCard
                title="Outstanding Balance"
                value={<span style={{ color: "#ef4444" }}>₹{(stats?.outstanding ?? 0).toLocaleString("en-IN")}</span>}
                prefix={<ExclamationCircleOutlined style={{ color: "#ef4444" }} />}
                status="danger"
                onClick={() => navigate("/invoices?status=overdue")}
                loading={loading}
              />
            </Col>
          </Row>

          {/* Row 2 — Operational Metrics */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={8} style={{ display: "flex", flexDirection: "column" }}>
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
            <Col xs={24} sm={12} lg={8} style={{ display: "flex", flexDirection: "column" }}>
              <SmartCard
                title="Total Customers"
                value={stats?.total_customers ?? 0}
                prefix={<TeamOutlined />}
                onClick={() => navigate("/customers?status=active")}
                loading={loading}
              />
            </Col>
            <Col xs={24} sm={24} lg={8} style={{ display: "flex", flexDirection: "column" }}>
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
            <Col xs={24} sm={8} style={{ display: "flex", flexDirection: "column" }}>
              <SmartCard
                title="Paid Invoices"
                value={stats?.paid_invoices ?? 0}
                prefix={<CheckCircleOutlined />}
                status="success"
                onClick={() => navigate("/invoices?status=paid")}
                loading={loading}
              />
            </Col>
            <Col xs={24} sm={8} style={{ display: "flex", flexDirection: "column" }}>
              <SmartCard
                title="Needs Follow-up"
                value={stats?.followup_invoices ?? 0}
                prefix={<ExclamationCircleOutlined />}
                status="warning"
                onClick={() => navigate("/invoices?status=overdue")}
                loading={loading}
              />
            </Col>
            <Col xs={24} sm={8} style={{ display: "flex", flexDirection: "column" }}>
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
        </Col>

        <Col xs={24} lg={8}>
          <Card 
            title="Entity Distribution" 
            style={{ height: "100%", border: "1px solid #e5e7eb", borderRadius: "12px" }}
            styles={{ body: { display: "flex", alignItems: "center", justifyContent: "center", height: "calc(100% - 58px)" } }}
          >
            <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {stats && (
                <Chart
                  chartType="PieChart"
                  data={pieData}
                  options={pieOptions}
                  width="100%"
                  height="400px"
                />
              )}
            </div>
          </Card>
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
