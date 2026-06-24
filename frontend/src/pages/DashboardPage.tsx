import { useEffect, useState } from "react";
import { Col, Row, Tag, Table, Typography, Alert, Card, Space } from "antd";
import {
  TeamOutlined, FileTextOutlined, DollarOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined,
  BarChartOutlined
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, Legend } from "recharts";
import apiClient from "../api/client";
import SmartCard from "../components/SmartCard";
import MetricProgressGauge from "../components/MetricProgressGauge";
import AIInsightsPanel from "../components/AIInsightsPanel";
import ActivityTimeline from "../components/ActivityTimeline";

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

// Sample metrics for collections & billing trends
const trendData = [
  { name: "Jan", billed: 120000, collected: 95000 },
  { name: "Feb", billed: 180000, collected: 140000 },
  { name: "Mar", billed: 150000, collected: 130000 },
  { name: "Apr", billed: 220000, collected: 190000 },
  { name: "May", billed: 280000, collected: 240000 },
  { name: "Jun", billed: 310000, collected: 275000 }
];

const statusTag = (status: string, record?: any) => {
  let displayStatus = status;
  if (record && record.due_date) {
    const today = new Date();
    const isOverdue = ["issued", "partially_paid"].includes(record.status) && 
      (new Date(record.due_date).getTime() < today.setHours(0,0,0,0));
    if (isOverdue) {
      displayStatus = "overdue";
    }
  }
  const map: Record<string, [string, React.ReactNode]> = {
    paid:           ["green",  <CheckCircleOutlined />],
    overdue:        ["red",    <CloseCircleOutlined />],
    partially_paid: ["orange", <ExclamationCircleOutlined />],
    active:         ["green",  <CheckCircleOutlined />],
    draft:          ["gold",   <ExclamationCircleOutlined />],
    issued:         ["blue",   <ExclamationCircleOutlined />],
  };
  const [color, icon] = map[displayStatus] ?? ["default", null];
  return <Tag color={color} icon={icon}>{displayStatus.replace("_", " ")}</Tag>;
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
        
        // Dynamic overdue check
        const isOverdue = (i: any) => ["issued", "partially_paid"].includes(i.status) && overdueDays(i) > 0;

        const defaulted = inv.filter((i: any) => isOverdue(i) && (i.notes?.includes("DEFAULTER") || overdueDays(i) > 45));
        const defaultedIds = new Set(defaulted.map((i: any) => i.id));
        const followup = inv.filter((i: any) => (isOverdue(i) || i.status === "partially_paid") && !defaultedIds.has(i.id));

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
          outstanding: inv.filter((i: any) => ["issued", "partially_paid"].includes(i.status)).reduce((s: number, i: any) => s + (Number(i.total_amount) - Number(i.amount_paid)), 0),
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
  ];

  const amcCols = [
    { title: "Contract #", dataIndex: "contract_number", key: "cn" },
    { title: "Customer", dataIndex: "customer_name", key: "cust" },
    { title: "Status", dataIndex: "status", key: "status", render: statusTag },
    { title: "Annual AMC (₹)", dataIndex: "annual_amount", key: "amt", render: (v: number) => v.toLocaleString("en-IN") },
    { title: "Valid Till", dataIndex: "end_date", key: "end" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Title level={4} style={{ margin: 0 }}>Operational Intelligence Command Center</Title>
        <span style={{ color: "#9ca3af", fontSize: "12px", background: "rgba(255,255,255,0.05)", padding: "4px 8px", borderRadius: "4px" }}>
          Metrics updated live
        </span>
      </div>

      {/* Row 1 — Executive Visual Insights (Gauges & Trends) */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
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
        <Col xs={24} lg={16}>
          <Card 
            className="glass-card"
            styles={{
              header: { borderBottom: "1px solid rgba(255, 255, 255, 0.05)", padding: "12px 24px" },
              body: { padding: "16px 20px" }
            }}
            title={
              <Space>
                <BarChartOutlined style={{ color: "#14b8a6", fontSize: 18 }} />
                <span style={{ color: "#f3f4f6", fontWeight: 700 }}>Financial Ledger Trends (₹)</span>
              </Space>
            }
          >
            <div style={{ width: "100%", height: 180 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorBilled" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorCollected" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="name" stroke="#9ca3af" fontSize={11} tickLine={false} />
                  <YAxis stroke="#9ca3af" fontSize={11} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#0b0f19", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
                  <Area type="monotone" dataKey="billed" name="Billed Amount" stroke="#6366f1" fillOpacity={1} fill="url(#colorBilled)" strokeWidth={2} />
                  <Area type="monotone" dataKey="collected" name="Collected Amount" stroke="#10b981" fillOpacity={1} fill="url(#colorCollected)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Row 2 — Smart Cards Matrix */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <SmartCard
            title="Total Revenue"
            value={`₹${(stats?.total_revenue ?? 0).toLocaleString("en-IN")}`}
            prefix={<DollarOutlined />}
            status="success"
            onClick={() => navigate("/payments")}
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <SmartCard
            title="Outstanding Balance"
            value={`₹${(stats?.outstanding ?? 0).toLocaleString("en-IN")}`}
            prefix={<ExclamationCircleOutlined />}
            status="warning"
            onClick={() => navigate("/invoices?status=overdue")}
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <SmartCard
            title="Active AMC Contracts"
            value={stats?.active_amc ?? 0}
            prefix={<FileTextOutlined />}
            onClick={() => navigate("/amc?status=active")}
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <SmartCard
            title="Total Customers"
            value={stats?.total_customers ?? 0}
            prefix={<TeamOutlined />}
            onClick={() => navigate("/customers?status=active")}
            loading={loading}
          />
        </Col>
      </Row>

      {/* Row 3 — AI Operations Deck & Timelines */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <AIInsightsPanel />
        </Col>
        <Col xs={24} lg={8}>
          <ActivityTimeline />
        </Col>
      </Row>

      {stats && stats.outstanding > 0 && (
        <Alert
          style={{
            background: "rgba(245, 158, 11, 0.1)",
            border: "1px solid rgba(245, 158, 11, 0.3)",
            borderRadius: "8px",
          }}
          type="warning"
          showIcon
          message={
            <span style={{ color: "#f59e0b", fontWeight: 500 }}>
              Overdue balances pending: ₹{stats.outstanding.toLocaleString("en-IN")} — Click Invoices Status tables below to manage followups.
            </span>
          }
        />
      )}

      {/* Tables Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
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
        </Col>
        <Col xs={24} lg={12}>
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
        </Col>
      </Row>
    </div>
  );
}
