import { useEffect, useState } from "react";
import dayjs, { type Dayjs } from "dayjs";
import {
  Card, List, Button, Table, Typography, message, Space, Tag, Descriptions,
  Empty, Spin, Select, DatePicker, Row, Col, Statistic, Progress, Divider,
  Collapse, Badge, Tooltip,
} from "antd";
import {
  FileExcelOutlined, FilePdfOutlined, FileTextOutlined, PlayCircleOutlined,
  FileSearchOutlined, DownloadOutlined, SafetyCertificateOutlined,
  ToolOutlined, AuditOutlined, DollarOutlined, BarChartOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined,
} from "@ant-design/icons";
import apiClient from "../api/client";
import SmartCard from "../components/SmartCard";
import MetricProgressGauge from "../components/MetricProgressGauge";

const { Title, Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Panel } = Collapse;
const { Option } = Select;

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReportMeta { key: string; title: string; }

interface AMCOption {
  id: string;
  contract_number: string;
  customer_id: string;
  status: string;
  start_date: string;
  end_date: string;
  annual_amount: number;
}

interface KPIs {
  total_tickets: number;
  tickets_resolved: number;
  sla_met: number;
  sla_breached: number;
  sla_compliance_pct: number;
  total_visits: number;
  corrective_visits: number;
  preventive_visits: number;
  avg_visit_duration_hrs: number;
  pm_planned: number;
  pm_done: number;
  pm_skipped: number;
  pm_adherence_pct: number;
  total_billed: number;
  total_collected: number;
  outstanding_balance: number;
}

interface ConsolidatedReport {
  generated_at: string;
  report_period: { from_date: string; to_date: string };
  contract: Record<string, any>;
  customer: Record<string, any>;
  assets: any[];
  tickets: any[];
  visits: any[];
  pm_schedules: any[];
  invoices: any[];
  payments: any[];
  kpis: KPIs;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function downloadBlob(data: BlobPart, filename: string, mime: string) {
  const url = window.URL.createObjectURL(new Blob([data], { type: mime }));
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); window.URL.revokeObjectURL(url);
}

function fmtINR(v: number) {
  return "₹" + v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function slaColor(pct: number) {
  if (pct >= 90) return "#52c41a";
  if (pct >= 70) return "#fa8c16";
  return "#f5222d";
}

function pmColor(pct: number) {
  if (pct >= 90) return "#52c41a";
  if (pct >= 60) return "#fa8c16";
  return "#f5222d";
}

function priorityTag(p: string) {
  const map: Record<string, string> = {
    critical: "red", high: "orange", medium: "blue", low: "default",
  };
  return <Tag color={map[p] || "default"}>{p?.toUpperCase()}</Tag>;
}

function statusTag(s: string) {
  const map: Record<string, string> = {
    resolved: "green", closed: "green", in_progress: "blue",
    open: "default", assigned: "cyan", pending_parts: "orange",
  };
  return <Tag color={map[s] || "default"}>{s?.replace(/_/g, " ")}</Tag>;
}

// ─── AMC Consolidated Report Panel ───────────────────────────────────────────

function AMCConsolidatedPanel() {
  const [contracts, setContracts] = useState<AMCOption[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [preview, setPreview] = useState<ConsolidatedReport | null>(null);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [customerNames, setCustomerNames] = useState<Record<string, string>>({});

  // Load AMC contracts list
  useEffect(() => {
    apiClient.get("/amc", { params: { limit: 200 } })
      .then(({ data }) => {
        const list: AMCOption[] = Array.isArray(data) ? data : data.items ?? data;
        setContracts(list);
      })
      .catch(() => message.error("Failed to load AMC contracts"));
  }, []);

  // When a contract is selected, auto-fill the date range
  const handleContractChange = (id: string) => {
    setSelectedId(id);
    setPreview(null);
    const c = contracts.find((x) => x.id === id);
    if (c) {
      setDateRange([dayjs(c.start_date), dayjs(c.end_date)]);
    }
  };

  const generatePreview = async () => {
    if (!selectedId || !dateRange) {
      message.warning("Please select a contract and date range");
      return;
    }
    setGenerating(true);
    setPreview(null);
    try {
      const { data } = await apiClient.get("/reports/amc-consolidated", {
        params: {
          amc_id: selectedId,
          from_date: dateRange[0].format("YYYY-MM-DD"),
          to_date: dateRange[1].format("YYYY-MM-DD"),
        },
      });
      setPreview(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  const doExport = async (fmt: "pdf" | "xlsx") => {
    if (!selectedId || !dateRange) return;
    setExporting(fmt);
    const mime = fmt === "pdf" ? "application/pdf"
      : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    try {
      const resp = await apiClient.get("/reports/amc-consolidated/export", {
        params: {
          amc_id: selectedId,
          from_date: dateRange[0].format("YYYY-MM-DD"),
          to_date: dateRange[1].format("YYYY-MM-DD"),
          fmt,
        },
        responseType: "blob",
      });
      const contract = contracts.find((c) => c.id === selectedId);
      const cn = contract?.contract_number ?? selectedId;
      downloadBlob(resp.data, `AMC-${cn}-Report.${fmt}`, mime);
    } catch (e: any) {
      if (e?.response?.status === 503) {
        message.warning("PDF rendering unavailable — use Excel export.");
      } else {
        message.error("Export failed");
      }
    } finally {
      setExporting(null);
    }
  };

  const selectedContract = contracts.find((c) => c.id === selectedId);
  const canGenerate = !!selectedId && !!dateRange;
  const canExport = canGenerate && !!preview;

  return (
    <Card
      id="amc-consolidated-report-panel"
      style={{ marginBottom: 28, borderColor: "#1d4ed8", borderWidth: 1.5 }}
      styles={{ header: { background: "linear-gradient(135deg, #0f2a43 0%, #1e4d72 100%)", borderRadius: "8px 8px 0 0" } }}
      title={
        <Space>
          <SafetyCertificateOutlined style={{ color: "#93c5fd", fontSize: 18 }} />
          <span style={{ color: "#fff", fontWeight: 700, fontSize: 15 }}>
            Consolidated AMC Performance &amp; Service Report
          </span>
          <Tag color="blue" style={{ marginLeft: 4, fontSize: 10 }}>PROOF OF WORK · RENEWAL · PAYMENT</Tag>
        </Space>
      }
    >
      {/* ── Controls ── */}
      <Row gutter={[16, 12]} align="middle" style={{ marginBottom: 20 }}>
        <Col xs={24} md={8}>
          <Text type="secondary" style={{ display: "block", marginBottom: 4, fontSize: 12 }}>
            AMC Contract
          </Text>
          <Select
            id="amc-contract-select"
            placeholder="Select AMC Contract…"
            style={{ width: "100%" }}
            value={selectedId}
            onChange={handleContractChange}
            showSearch
            optionFilterProp="children"
          >
            {contracts.map((c) => (
              <Option key={c.id} value={c.id}>
                <Space>
                  <span style={{ fontWeight: 600 }}>{c.contract_number}</span>
                  <Tag color={c.status === "active" ? "green" : "orange"} style={{ fontSize: 10 }}>
                    {c.status}
                  </Tag>
                </Space>
              </Option>
            ))}
          </Select>
        </Col>
        <Col xs={24} md={10}>
          <Text type="secondary" style={{ display: "block", marginBottom: 4, fontSize: 12 }}>
            Report Period
          </Text>
          <RangePicker
            id="amc-report-date-range"
            style={{ width: "100%" }}
            value={dateRange}
            onChange={(v) => setDateRange(v as [Dayjs, Dayjs] | null)}
            format="YYYY-MM-DD"
          />
        </Col>
        <Col xs={24} md={6} style={{ paddingTop: 20 }}>
          <Space wrap>
            <Button
              id="amc-generate-preview-btn"
              type="primary"
              icon={<FileSearchOutlined />}
              loading={generating}
              disabled={!canGenerate}
              onClick={generatePreview}
              style={{ background: "#0f2a43", borderColor: "#0f2a43" }}
            >
              Generate Preview
            </Button>
            <Tooltip title="Download PDF">
              <Button
                id="amc-export-pdf-btn"
                icon={<FilePdfOutlined />}
                loading={exporting === "pdf"}
                disabled={!canExport}
                onClick={() => doExport("pdf")}
                danger
              />
            </Tooltip>
            <Tooltip title="Download Excel">
              <Button
                id="amc-export-excel-btn"
                icon={<FileExcelOutlined />}
                loading={exporting === "xlsx"}
                disabled={!canExport}
                onClick={() => doExport("xlsx")}
                style={{ color: "#16a34a", borderColor: "#16a34a" }}
              />
            </Tooltip>
          </Space>
        </Col>
      </Row>

      {/* ── Loading ── */}
      {generating && (
        <div style={{ textAlign: "center", padding: "48px 0" }}>
          <Spin size="large" tip="Aggregating report data…" />
        </div>
      )}

      {/* ── Preview ── */}
      {!generating && preview && (
        <>
          {/* KPI Cards */}
          <Divider orientation="left" style={{ fontWeight: 700, color: "#0f2a43", fontSize: 13 }}>
            Executive Summary — {preview.report_period.from_date} to {preview.report_period.to_date}
          </Divider>
          <Row gutter={[14, 14]} style={{ marginBottom: 20 }}>
            {/* SLA Compliance */}
            <Col xs={24} sm={12} md={8}>
              <MetricProgressGauge
                title="SLA Compliance"
                percent={preview.kpis.sla_compliance_pct}
                status={preview.kpis.sla_compliance_pct >= 90 ? "success" : (preview.kpis.sla_compliance_pct >= 70 ? "warning" : "danger")}
                subtext={`${preview.kpis.sla_met} met · ${preview.kpis.sla_breached} breached`}
              />
            </Col>

            {/* PM Adherence */}
            <Col xs={24} sm={12} md={8}>
              <MetricProgressGauge
                title="PM Adherence"
                percent={preview.kpis.pm_adherence_pct}
                status={preview.kpis.pm_adherence_pct >= 90 ? "success" : (preview.kpis.pm_adherence_pct >= 60 ? "warning" : "danger")}
                subtext={`${preview.kpis.pm_done} done · ${preview.kpis.pm_skipped} skipped`}
              />
            </Col>

            {/* Engineer Visits */}
            <Col xs={24} sm={12} md={8}>
              <SmartCard
                title="Engineer Visits"
                value={preview.kpis.total_visits}
                prefix={<ToolOutlined />}
                suffix={
                  <span style={{ fontSize: "11px", color: "#9ca3af" }}>
                    {preview.kpis.corrective_visits} corrective · {preview.kpis.preventive_visits} preventive
                  </span>
                }
              />
            </Col>

            {/* Tickets Resolved */}
            <Col xs={24} sm={12} md={8}>
              <SmartCard
                title="Tickets Resolved"
                value={preview.kpis.tickets_resolved}
                prefix={<AuditOutlined />}
                suffix={
                  <span style={{ fontSize: "11px", color: "#9ca3af" }}>
                    of {preview.kpis.total_tickets} service tickets closed
                  </span>
                }
              />
            </Col>

            {/* Amount Collected */}
            <Col xs={24} sm={12} md={8}>
              <SmartCard
                title="Amount Collected"
                value={fmtINR(preview.kpis.total_collected)}
                prefix={<DollarOutlined />}
                status="success"
                suffix={
                  <span style={{ fontSize: "11px", color: "#9ca3af" }}>
                    of {fmtINR(preview.kpis.total_billed)} billed
                  </span>
                }
              />
            </Col>

            {/* Outstanding Balance */}
            <Col xs={24} sm={12} md={8}>
              <SmartCard
                title="Outstanding Balance"
                value={fmtINR(preview.kpis.outstanding_balance)}
                prefix={<ExclamationCircleOutlined />}
                status={preview.kpis.outstanding_balance > 0 ? "warning" : "success"}
                suffix={
                  <span style={{ fontSize: "11px", color: "#9ca3af" }}>
                    remaining receivables pending
                  </span>
                }
              />
            </Col>
          </Row>

          {/* Download CTA */}
          <div style={{ background: "#f0f9ff", borderRadius: 8, padding: "12px 16px", marginBottom: 20, border: "1px solid #bae6fd", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div>
              <Text strong style={{ color: "#0f2a43" }}>Report ready.</Text>
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>Generated at {preview.generated_at}</Text>
            </div>
            <Space>
              <Button
                id="amc-download-pdf-btn"
                type="primary"
                danger
                icon={<FilePdfOutlined />}
                loading={exporting === "pdf"}
                onClick={() => doExport("pdf")}
              >
                Download PDF
              </Button>
              <Button
                id="amc-download-excel-btn"
                icon={<FileExcelOutlined />}
                loading={exporting === "xlsx"}
                onClick={() => doExport("xlsx")}
                style={{ color: "#16a34a", borderColor: "#16a34a" }}
              >
                Download Excel
              </Button>
            </Space>
          </div>

          {/* Collapsible detail tables */}
          <Collapse
            defaultActiveKey={["contract"]}
            style={{ background: "transparent" }}
          >
            {/* Contract + Customer */}
            <Panel
              key="contract"
              header={<Space><SafetyCertificateOutlined /> Contract &amp; Customer Details</Space>}
            >
              <Row gutter={24}>
                <Col xs={24} md={12}>
                  <Descriptions title="Contract" size="small" column={1} bordered>
                    <Descriptions.Item label="Number">{preview.contract.contract_number}</Descriptions.Item>
                    <Descriptions.Item label="Status"><Tag color={preview.contract.status === "active" ? "green" : "orange"}>{preview.contract.status}</Tag></Descriptions.Item>
                    <Descriptions.Item label="Period">{preview.contract.start_date} → {preview.contract.end_date}</Descriptions.Item>
                    <Descriptions.Item label="Annual Value">{fmtINR(preview.contract.annual_amount)}</Descriptions.Item>
                    <Descriptions.Item label="Payment Frequency">{preview.contract.payment_frequency || "—"}</Descriptions.Item>
                    <Descriptions.Item label="PM Visits/Year">{preview.contract.preventive_visits_per_year ?? "—"}</Descriptions.Item>
                  </Descriptions>
                </Col>
                <Col xs={24} md={12}>
                  <Descriptions title="Customer" size="small" column={1} bordered>
                    <Descriptions.Item label="Name">{preview.customer.name}</Descriptions.Item>
                    <Descriptions.Item label="Category">{preview.customer.category || "—"}</Descriptions.Item>
                    <Descriptions.Item label="GSTIN">{preview.customer.gstin || "—"}</Descriptions.Item>
                    <Descriptions.Item label="Phone">{preview.customer.phone || "—"}</Descriptions.Item>
                    <Descriptions.Item label="Contact Person">{preview.customer.contact_person_name || "—"}</Descriptions.Item>
                    <Descriptions.Item label="Address">{preview.customer.address || "—"}</Descriptions.Item>
                  </Descriptions>
                </Col>
              </Row>
            </Panel>

            {/* Assets */}
            <Panel
              key="assets"
              header={
                <Space>
                  <BarChartOutlined />
                  Covered CCTV Assets
                  <Badge count={preview.assets.length} style={{ backgroundColor: "#0f2a43" }} />
                </Space>
              }
            >
              {preview.assets.length ? (
                <Table
                  id="amc-assets-table"
                  size="small"
                  rowKey="id"
                  dataSource={preview.assets}
                  scroll={{ x: true }}
                  pagination={false}
                  columns={[
                    { title: "#", render: (_: any, __: any, i: number) => i + 1, width: 40 },
                    { title: "Serial", dataIndex: "serial_number", key: "serial_number", render: (v: string) => v || "—" },
                    { title: "Make / Model", key: "make_model", render: (r: any) => `${r.make || ""} ${r.model || ""}`.trim() || "—" },
                    { title: "Type", dataIndex: "asset_type", key: "asset_type", render: (v: string) => v || "—" },
                    { title: "Location", dataIndex: "location_description", key: "location_description", render: (v: string) => v || "—" },
                    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={v === "active" ? "green" : v === "faulty" ? "red" : "orange"}>{v}</Tag> },
                    { title: "Install Date", dataIndex: "installation_date", key: "installation_date", render: (v: string) => v || "—" },
                    { title: "Warranty Expiry", dataIndex: "warranty_expiry", key: "warranty_expiry", render: (v: string) => v || "—" },
                  ]}
                />
              ) : <Empty description="No assets linked to this contract" />}
            </Panel>

            {/* Tickets */}
            <Panel
              key="tickets"
              header={
                <Space>
                  <AuditOutlined />
                  Service Ticket Log
                  <Badge count={preview.tickets.length} style={{ backgroundColor: "#0f2a43" }} />
                  {preview.kpis.sla_breached > 0 && (
                    <Tag color="red"><CloseCircleOutlined /> {preview.kpis.sla_breached} SLA Breached</Tag>
                  )}
                  {preview.kpis.sla_breached === 0 && preview.tickets.length > 0 && (
                    <Tag color="green"><CheckCircleOutlined /> All SLA Met</Tag>
                  )}
                </Space>
              }
            >
              {preview.tickets.length ? (
                <Table
                  id="amc-tickets-table"
                  size="small"
                  rowKey="id"
                  dataSource={preview.tickets}
                  scroll={{ x: true }}
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: "Ticket #", dataIndex: "ticket_number", key: "ticket_number" },
                    { title: "Date", dataIndex: "created_at", key: "created_at" },
                    { title: "Priority", dataIndex: "priority", key: "priority", render: (v: string) => priorityTag(v) },
                    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => statusTag(v) },
                    {
                      title: "SLA", dataIndex: "sla_breached", key: "sla",
                      render: (v: boolean) => v
                        ? <Tag color="red" icon={<CloseCircleOutlined />}>Breached</Tag>
                        : <Tag color="green" icon={<CheckCircleOutlined />}>Met</Tag>
                    },
                    { title: "Complaint", dataIndex: "complaint", key: "complaint", ellipsis: true },
                    { title: "Resolution", dataIndex: "resolution_notes", key: "resolution_notes", ellipsis: true, render: (v: string) => v || "—" },
                    { title: "Resolved At", dataIndex: "resolved_at", key: "resolved_at", render: (v: string) => v || "—" },
                  ]}
                />
              ) : <Empty description="No tickets in this period" />}
            </Panel>

            {/* Visits */}
            <Panel
              key="visits"
              header={
                <Space>
                  <ToolOutlined />
                  Engineer Visit Log
                  <Badge count={preview.visits.length} style={{ backgroundColor: "#0f2a43" }} />
                </Space>
              }
            >
              {preview.visits.length ? (
                <Table
                  id="amc-visits-table"
                  size="small"
                  rowKey="id"
                  dataSource={preview.visits}
                  scroll={{ x: true }}
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: "Type", dataIndex: "visit_type", key: "visit_type", render: (v: string) => <Tag color={v === "preventive" ? "blue" : "orange"}>{v}</Tag> },
                    { title: "Check-in", dataIndex: "checkin_at", key: "checkin_at", render: (v: string) => v || "—" },
                    { title: "Check-out", dataIndex: "checkout_at", key: "checkout_at", render: (v: string) => v || "—" },
                    { title: "Duration (hrs)", dataIndex: "duration_hrs", key: "duration_hrs", render: (v: number) => v != null ? v : "—" },
                    { title: "Work Performed", dataIndex: "work_performed", key: "work_performed", ellipsis: true, render: (v: string) => v || "—" },
                    {
                      title: "Parts Used", dataIndex: "parts_used", key: "parts_used",
                      render: (v: any[]) => v?.length ? v.map((p: any, i: number) => <Tag key={i}>{p.description || JSON.stringify(p)}</Tag>) : "—"
                    },
                    { title: "Feedback", dataIndex: "customer_feedback", key: "customer_feedback", ellipsis: true, render: (v: string) => v || "—" },
                  ]}
                />
              ) : <Empty description="No visits in this period" />}
            </Panel>

            {/* PM Schedule */}
            <Panel
              key="pm"
              header={
                <Space>
                  <ClockCircleOutlined />
                  Preventive Maintenance Tracker
                  <Badge count={preview.pm_schedules.length} style={{ backgroundColor: "#0f2a43" }} />
                </Space>
              }
            >
              {preview.pm_schedules.length ? (
                <Table
                  id="amc-pm-table"
                  size="small"
                  rowKey="id"
                  dataSource={preview.pm_schedules}
                  pagination={false}
                  columns={[
                    { title: "Seq #", dataIndex: "sequence_no", key: "seq", width: 60 },
                    { title: "Scheduled Date", dataIndex: "scheduled_date", key: "scheduled_date" },
                    {
                      title: "Status", dataIndex: "status", key: "status",
                      render: (v: string) => {
                        const cfg: Record<string, { color: string; label: string }> = {
                          done: { color: "green", label: "✓ Done" },
                          skipped: { color: "red", label: "✕ Skipped" },
                          rescheduled: { color: "orange", label: "↻ Rescheduled" },
                          planned: { color: "default", label: "Planned" },
                        };
                        const c = cfg[v] || { color: "default", label: v };
                        return <Tag color={c.color}>{c.label}</Tag>;
                      }
                    },
                    { title: "Reason Code", dataIndex: "reason_code", key: "reason_code", render: (v: string) => v || "—" },
                    { title: "Notes", dataIndex: "notes", key: "notes", ellipsis: true, render: (v: string) => v || "—" },
                  ]}
                />
              ) : <Empty description="No PM schedule entries found" />}
            </Panel>

            {/* Financial Ledger */}
            <Panel
              key="financial"
              header={
                <Space>
                  <DollarOutlined />
                  Financial Ledger
                  <Tag color={preview.kpis.outstanding_balance > 0 ? "orange" : "green"}>
                    {preview.kpis.outstanding_balance > 0
                      ? `₹${preview.kpis.outstanding_balance.toLocaleString("en-IN")} Outstanding`
                      : "Fully Settled"}
                  </Tag>
                </Space>
              }
            >
              <Text strong style={{ display: "block", marginBottom: 8 }}>Invoices</Text>
              {preview.invoices.length ? (
                <Table
                  id="amc-invoices-table"
                  size="small"
                  rowKey="id"
                  dataSource={preview.invoices}
                  pagination={false}
                  scroll={{ x: true }}
                  summary={() => (
                    <Table.Summary.Row style={{ background: "#f0f9ff", fontWeight: 700 }}>
                      <Table.Summary.Cell index={0} colSpan={5}>Totals</Table.Summary.Cell>
                      <Table.Summary.Cell index={5} align="right">{fmtINR(preview.kpis.total_billed)}</Table.Summary.Cell>
                      <Table.Summary.Cell index={6} align="right" className={preview.kpis.outstanding_balance > 0 ? "amount-warning" : ""}>{fmtINR(preview.kpis.total_collected)}</Table.Summary.Cell>
                      <Table.Summary.Cell index={7} align="right">
                        <Text type={preview.kpis.outstanding_balance > 0 ? "warning" : "success"} strong>
                          {fmtINR(preview.kpis.outstanding_balance)}
                        </Text>
                      </Table.Summary.Cell>
                    </Table.Summary.Row>
                  )}
                  columns={[
                    { title: "Invoice #", dataIndex: "invoice_number", key: "invoice_number" },
                    { title: "Date", dataIndex: "invoice_date", key: "invoice_date" },
                    { title: "Due Date", dataIndex: "due_date", key: "due_date", render: (v: string) => v || "—" },
                    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={v === "paid" ? "green" : v === "partially_paid" ? "orange" : "blue"}>{v?.replace(/_/g, " ")}</Tag> },
                    { title: "Subtotal (₹)", dataIndex: "subtotal", key: "subtotal", align: "right", render: (v: number) => v.toLocaleString("en-IN", { minimumFractionDigits: 2 }) },
                    { title: "Total (₹)", dataIndex: "total_amount", key: "total_amount", align: "right", render: (v: number) => v.toLocaleString("en-IN", { minimumFractionDigits: 2 }) },
                    { title: "Paid (₹)", dataIndex: "amount_paid", key: "amount_paid", align: "right", render: (v: number) => <Text type="success">{v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</Text> },
                    { title: "Balance (₹)", dataIndex: "balance", key: "balance", align: "right", render: (v: number) => <Text type={v > 0 ? "warning" : "success"}>{v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</Text> },
                  ]}
                />
              ) : <Empty description="No invoices for this contract" />}

              <Text strong style={{ display: "block", margin: "16px 0 8px" }}>Payments Received</Text>
              {preview.payments.length ? (
                <Table
                  id="amc-payments-table"
                  size="small"
                  rowKey="id"
                  dataSource={preview.payments}
                  pagination={false}
                  columns={[
                    { title: "Payment Date", dataIndex: "payment_date", key: "payment_date" },
                    { title: "Mode", dataIndex: "mode", key: "mode", render: (v: string) => <Tag>{v?.toUpperCase()}</Tag> },
                    { title: "Reference #", dataIndex: "reference_number", key: "reference_number", render: (v: string) => v || "—" },
                    { title: "Amount (₹)", dataIndex: "amount", key: "amount", align: "right", render: (v: number) => <Text type="success" strong>{v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</Text> },
                    { title: "Notes", dataIndex: "notes", key: "notes", ellipsis: true, render: (v: string) => v || "—" },
                  ]}
                />
              ) : <Empty description="No payments recorded" />}
            </Panel>
          </Collapse>
        </>
      )}

      {!generating && !preview && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <span>
              Select a contract and date range, then click{" "}
              <Text strong>Generate Preview</Text> to load the consolidated report.
            </span>
          }
          style={{ padding: "32px 0" }}
        />
      )}
    </Card>
  );
}

// ─── Standard Reports Panel (existing, preserved) ────────────────────────────

function StandardReportsPanel() {
  const [reports, setReports] = useState<ReportMeta[]>([]);
  const [active, setActive] = useState<ReportMeta | null>(null);
  const [data, setData] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get("/reports/catalogue")
      .then(({ data }) => setReports(data.reports))
      .catch((e) => message.error(e?.response?.data?.detail || "Failed to load reports"));
  }, []);

  const run = async (r: ReportMeta) => {
    setActive(r); setRunning(true); setData(null);
    try {
      const { data } = await apiClient.get(`/reports/${r.key}`);
      setData(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to run report");
    } finally {
      setRunning(false);
    }
  };

  const doExport = async (fmt: "csv" | "xlsx" | "pdf") => {
    if (!active) return;
    setExporting(fmt);
    const mime = fmt === "csv" ? "text/csv"
      : fmt === "xlsx" ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      : "application/pdf";
    try {
      const resp = await apiClient.get(`/reports/${active.key}/export`, { params: { fmt }, responseType: "blob" });
      downloadBlob(resp.data, `${active.key}.${fmt}`, mime);
    } catch (e: any) {
      if (e?.response?.status === 503) {
        message.warning("PDF export is unavailable — use CSV or Excel.");
      } else {
        message.error("Export failed");
      }
    } finally {
      setExporting(null);
    }
  };

  const isList = Array.isArray(data);
  const columns = isList && data.length
    ? Object.keys(data[0]).map((k) => ({
        title: k.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
        dataIndex: k, key: k,
        render: (v: any) => typeof v === "number" ? v.toLocaleString("en-IN") : String(v ?? "—"),
      }))
    : [];

  return (
    <Card
      id="standard-reports-panel"
      title={
        <Space>
          <BarChartOutlined />
          <span>Standard Operational Reports</span>
        </Space>
      }
    >
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
        <Card title="Available Reports" style={{ width: 300, flexShrink: 0 }} styles={{ body: { padding: 0 } }}>
          <List
            dataSource={reports}
            renderItem={(r) => (
              <List.Item
                id={`report-item-${r.key}`}
                style={{ padding: "10px 16px", cursor: "pointer", background: active?.key === r.key ? "#e6f4ff" : undefined }}
                onClick={() => run(r)}
                actions={[<PlayCircleOutlined key="run" />]}
              >
                <Text>{r.title}</Text>
              </List.Item>
            )}
            locale={{ emptyText: "Loading…" }}
          />
        </Card>

        <Card
          style={{ flex: 1, minWidth: 360 }}
          title={active ? active.title : "Select a report"}
          extra={active && (
            <Space>
              <Button id="export-csv-btn" icon={<FileTextOutlined />} loading={exporting === "csv"} onClick={() => doExport("csv")}>CSV</Button>
              <Button id="export-xlsx-btn" icon={<FileExcelOutlined />} loading={exporting === "xlsx"} onClick={() => doExport("xlsx")}>Excel</Button>
              <Button id="export-pdf-btn" icon={<FilePdfOutlined />} loading={exporting === "pdf"} onClick={() => doExport("pdf")}>PDF</Button>
            </Space>
          )}
        >
          {!active && <Empty description="Pick a report from the list to run it" />}
          {running && <Spin style={{ display: "block", margin: "40px auto" }} />}
          {!running && active && isList && (
            data.length
              ? <Table id="standard-report-table" rowKey={(_, i) => String(i)} columns={columns} dataSource={data} size="small" scroll={{ x: true }} />
              : <Empty description="No data for this report" />
          )}
          {!running && active && !isList && data && (
            <Descriptions bordered column={1} size="small">
              {Object.entries(data).map(([k, v]) => (
                <Descriptions.Item key={k} label={k.replace(/_/g, " ")}>
                  {typeof v === "object" ? <Tag>{JSON.stringify(v)}</Tag> : String(v)}
                </Descriptions.Item>
              ))}
            </Descriptions>
          )}
        </Card>
      </div>
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  return (
    <div id="reports-page">
      <Title level={4} style={{ marginBottom: 20 }}>
        <BarChartOutlined style={{ marginRight: 8, color: "#0f2a43" }} />
        Reports &amp; Exports
      </Title>

      <AMCConsolidatedPanel />
      <StandardReportsPanel />
    </div>
  );
}
