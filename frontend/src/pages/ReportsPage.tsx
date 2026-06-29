import { useEffect, useState } from "react";
import dayjs, { type Dayjs } from "dayjs";
import {
  Card, List, Button, Table, Typography, message, Space, Tag, Descriptions,
  Empty, Spin, Select, DatePicker, Row, Col, Statistic, Progress, Divider,
  Collapse, Badge, Tooltip, ConfigProvider, theme
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
  return "₹" + (v ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
  return <Tag color={map[s] || "default"}>{s?.replace(/_/g, " ").toUpperCase()}</Tag>;
}

// ─── AMC Consolidated Report Panel ───────────────────────────────────────────

function AMCConsolidatedPanel() {
  const [contracts, setContracts] = useState<AMCOption[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [preview, setPreview] = useState<ConsolidatedReport | null>(null);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);

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
  // Direct download enabled immediately once parameters are selected
  const canExport = canGenerate;

  return (
    <Card
      id="amc-consolidated-report-panel"
      className="glass-card"
      style={{ marginBottom: 28 }}
      styles={{
        header: {
          background: "linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0.02) 100%)",
          borderBottom: "1px solid rgba(59, 130, 246, 0.15)",
          borderRadius: "12px 12px 0 0"
        },
        body: { padding: "24px" }
      }}
      title={
        <Space>
          <SafetyCertificateOutlined style={{ color: "#3b82f6", fontSize: 18 }} />
          <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
            Consolidated AMC Performance &amp; Service Report
          </span>
          <Tag color="blue" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(59, 130, 246, 0.12)", border: "1px solid rgba(59, 130, 246, 0.2)" }}>
            PROOF OF WORK · RENEWAL · PAYMENT
          </Tag>
        </Space>
      }
    >
      {/* ── Controls ── */}
      <Row gutter={[16, 12]} align="middle" style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <Text style={{ display: "block", marginBottom: 6, fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
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
                    {c.status.toUpperCase()}
                  </Tag>
                </Space>
              </Option>
            ))}
          </Select>
        </Col>
        <Col xs={24} md={10}>
          <Text style={{ display: "block", marginBottom: 6, fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
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
        <Col xs={24} md={6} style={{ paddingTop: 22 }}>
          <Space wrap>
            <Button
              id="amc-generate-preview-btn"
              type="primary"
              icon={<FileSearchOutlined />}
              loading={generating}
              disabled={!canGenerate}
              onClick={generatePreview}
              style={{
                background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
                border: "none",
                color: "#fff"
              }}
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
                style={{
                  border: "1px solid rgba(239, 68, 68, 0.2)",
                  background: !canExport ? undefined : "rgba(239, 68, 68, 0.1)"
                }}
              />
            </Tooltip>
            <Tooltip title="Download Excel">
              <Button
                id="amc-export-excel-btn"
                icon={<FileExcelOutlined />}
                loading={exporting === "xlsx"}
                disabled={!canExport}
                onClick={() => doExport("xlsx")}
                style={{
                  color: "#16a34a",
                  borderColor: "rgba(22, 163, 74, 0.3)",
                  background: !canExport ? undefined : "rgba(22, 163, 74, 0.1)"
                }}
              />
            </Tooltip>
          </Space>
        </Col>
      </Row>

      {/* ── Loading ── */}
      {generating && (
        <div style={{ textAlign: "center", padding: "64px 0" }}>
          <Spin size="large" tip="Consolidating AMC metrics ledger..." />
        </div>
      )}

      {/* ── Preview ── */}
      {!generating && preview && (
        <>
          {/* KPI Cards */}
          <Divider orientation="left" style={{ fontWeight: 600, color: "var(--text-primary)", borderColor: "var(--glass-border)", fontSize: 13, marginBottom: 20 }}>
            Executive Summary — {preview.report_period.from_date} to {preview.report_period.to_date}
          </Divider>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
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
                subtext={`${preview.kpis.pm_done} executed · ${preview.kpis.pm_skipped} skipped`}
              />
            </Col>

            {/* Engineer Visits */}
            <Col xs={24} sm={12} md={8}>
              <SmartCard
                title="Engineer Visits"
                value={preview.kpis.total_visits}
                prefix={<ToolOutlined />}
                suffix={
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
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
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
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
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
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
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                    remaining receivables pending
                  </span>
                }
              />
            </Col>
          </Row>

          {/* Download CTA */}
          <div style={{
            background: "rgba(59, 130, 246, 0.06)",
            borderRadius: 8,
            padding: "16px 20px",
            marginBottom: 24,
            border: "1px solid rgba(59, 130, 246, 0.2)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12
          }}>
            <div>
              <Text strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>Consolidated Report Ready</Text>
              <Text type="secondary" style={{ marginLeft: 12, fontSize: 12, display: "inline-block" }}>
                Compiled at {preview.generated_at}
              </Text>
            </div>
            <Space>
              <Button
                id="amc-download-pdf-btn"
                type="primary"
                danger
                icon={<FilePdfOutlined />}
                loading={exporting === "pdf"}
                onClick={() => doExport("pdf")}
                style={{ background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)", border: "none" }}
              >
                Download PDF
              </Button>
              <Button
                id="amc-download-excel-btn"
                icon={<FileExcelOutlined />}
                loading={exporting === "xlsx"}
                onClick={() => doExport("xlsx")}
                style={{
                  color: "#fff",
                  background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                  border: "none"
                }}
              >
                Download Excel
              </Button>
            </Space>
          </div>

          {/* Collapsible detail tables */}
          <Collapse
            bordered={false}
            defaultActiveKey={["contract"]}
            style={{ background: "transparent" }}
            expandIconPosition="end"
          >
            {/* Contract + Customer */}
            <Panel
              key="contract"
              header={<span style={{ color: "var(--text-primary)", fontWeight: 600 }}><SafetyCertificateOutlined style={{ marginRight: 8, color: "#3b82f6" }} /> Contract &amp; Customer Details</span>}
              style={{ background: "rgba(255, 255, 255, 0.01)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 8, marginBottom: 12, overflow: "hidden" }}
            >
              <Row gutter={[24, 24]}>
                <Col xs={24} md={12}>
                  <Descriptions title={<span style={{ color: "#e5e7eb", fontSize: "13px" }}>Contract Identity</span>} size="small" column={1} bordered>
                    <Descriptions.Item label="Number">{preview.contract.contract_number}</Descriptions.Item>
                    <Descriptions.Item label="Status"><Tag color={preview.contract.status === "active" ? "green" : "orange"}>{preview.contract.status.toUpperCase()}</Tag></Descriptions.Item>
                    <Descriptions.Item label="Period">{preview.contract.start_date} → {preview.contract.end_date}</Descriptions.Item>
                    <Descriptions.Item label="Annual Value">{fmtINR(preview.contract.annual_amount)}</Descriptions.Item>
                    <Descriptions.Item label="Payment Frequency">{preview.contract.payment_frequency || "—"}</Descriptions.Item>
                    <Descriptions.Item label="PM Visits/Year">{preview.contract.preventive_visits_per_year ?? "—"}</Descriptions.Item>
                  </Descriptions>
                </Col>
                <Col xs={24} md={12}>
                  <Descriptions title={<span style={{ color: "#e5e7eb", fontSize: "13px" }}>Customer Identity</span>} size="small" column={1} bordered>
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
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                  <BarChartOutlined style={{ marginRight: 8, color: "#a855f7" }} />
                  Covered CCTV Assets
                  <Badge count={preview.assets.length} style={{ backgroundColor: "#3b82f6", marginLeft: 8 }} />
                </span>
              }
              style={{ background: "rgba(255, 255, 255, 0.01)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 8, marginBottom: 12, overflow: "hidden" }}
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
                    { title: "Serial", dataIndex: "serial_number", key: "serial_number", render: (v: string) => <span style={{ color: "#3b82f6", fontWeight: 600 }}>{v || "—"}</span> },
                    { title: "Make / Model", key: "make_model", render: (r: any) => `${r.make || ""} ${r.model || ""}`.trim() || "—" },
                    { title: "Type", dataIndex: "asset_type", key: "asset_type", render: (v: string) => v || "—" },
                    { title: "Location", dataIndex: "location_description", key: "location_description", render: (v: string) => v || "—" },
                    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={v === "active" ? "green" : v === "faulty" ? "red" : "orange"}>{v.toUpperCase()}</Tag> },
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
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                  <AuditOutlined style={{ marginRight: 8, color: "#10b981" }} />
                  Service Ticket Log
                  <Badge count={preview.tickets.length} style={{ backgroundColor: "#3b82f6", marginLeft: 8 }} />
                  {preview.kpis.sla_breached > 0 ? (
                    <Tag color="red" style={{ marginLeft: 8 }}><CloseCircleOutlined /> {preview.kpis.sla_breached} SLA Breached</Tag>
                  ) : preview.tickets.length > 0 ? (
                    <Tag color="green" style={{ marginLeft: 8 }}><CheckCircleOutlined /> All SLA Met</Tag>
                  ) : null}
                </span>
              }
              style={{ background: "rgba(255, 255, 255, 0.01)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 8, marginBottom: 12, overflow: "hidden" }}
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
                    { title: "Ticket #", dataIndex: "ticket_number", key: "ticket_number", render: (v) => <span style={{ color: "#3b82f6", fontWeight: 600 }}>{v}</span> },
                    { title: "Date", dataIndex: "created_at", key: "created_at", render: (v) => v ? new Date(v).toLocaleDateString("en-IN") : "—" },
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
                    { title: "Resolved At", dataIndex: "resolved_at", key: "resolved_at", render: (v: string) => v ? new Date(v).toLocaleDateString("en-IN") : "—" },
                  ]}
                />
              ) : <Empty description="No tickets in this period" />}
            </Panel>

            {/* Visits */}
            <Panel
              key="visits"
              header={
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                  <ToolOutlined style={{ marginRight: 8, color: "#f59e0b" }} />
                  Engineer Visit Log
                  <Badge count={preview.visits.length} style={{ backgroundColor: "#3b82f6", marginLeft: 8 }} />
                </span>
              }
              style={{ background: "rgba(255, 255, 255, 0.01)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 8, marginBottom: 12, overflow: "hidden" }}
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
                    { title: "Type", dataIndex: "visit_type", key: "visit_type", render: (v: string) => <Tag color={v === "preventive" ? "blue" : "orange"}>{v.toUpperCase()}</Tag> },
                    { title: "Check-in", dataIndex: "checkin_at", key: "checkin_at", render: (v: string) => v || "—" },
                    { title: "Check-out", dataIndex: "checkout_at", key: "checkout_at", render: (v: string) => v || "—" },
                    { title: "Duration (hrs)", dataIndex: "duration_hrs", key: "duration_hrs", render: (v: number) => v != null ? `${v.toFixed(1)} hrs` : "—" },
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
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                  <ClockCircleOutlined style={{ marginRight: 8, color: "#ec4899" }} />
                  Preventive Maintenance Tracker
                  <Badge count={preview.pm_schedules.length} style={{ backgroundColor: "#3b82f6", marginLeft: 8 }} />
                </span>
              }
              style={{ background: "rgba(255, 255, 255, 0.01)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 8, marginBottom: 12, overflow: "hidden" }}
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
                <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                  <DollarOutlined style={{ marginRight: 8, color: "#14b8a6" }} />
                  Financial Ledger
                  <Tag color={preview.kpis.outstanding_balance > 0 ? "orange" : "green"} style={{ marginLeft: 8 }}>
                    {preview.kpis.outstanding_balance > 0
                      ? `${fmtINR(preview.kpis.outstanding_balance)} Outstanding`
                      : "Fully Settled"}
                  </Tag>
                </span>
              }
              style={{ background: "rgba(255, 255, 255, 0.01)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 8, marginBottom: 12, overflow: "hidden" }}
            >
              <Text strong style={{ display: "block", marginBottom: 12, color: "#e5e7eb", fontSize: "13px" }}>Invoices Summary</Text>
              {preview.invoices.length ? (
                <Table
                  id="amc-invoices-table"
                  size="small"
                  rowKey="id"
                  dataSource={preview.invoices}
                  pagination={false}
                  scroll={{ x: true }}
                  summary={() => (
                    <Table.Summary.Row style={{ background: "rgba(255, 255, 255, 0.02)", fontWeight: 700 }}>
                      <Table.Summary.Cell index={0} colSpan={5}>Ledger Totals</Table.Summary.Cell>
                      <Table.Summary.Cell index={5} align="right">{fmtINR(preview.kpis.total_billed)}</Table.Summary.Cell>
                      <Table.Summary.Cell index={6} align="right">
                        <Text type="success">{fmtINR(preview.kpis.total_collected)}</Text>
                      </Table.Summary.Cell>
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
                    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={v === "paid" ? "green" : v === "partially_paid" ? "orange" : "blue"}>{v?.replace(/_/g, " ").toUpperCase()}</Tag> },
                    { title: "Subtotal", dataIndex: "subtotal", key: "subtotal", align: "right", render: (v: number) => v.toLocaleString("en-IN", { minimumFractionDigits: 2 }) },
                    { title: "Total", dataIndex: "total_amount", key: "total_amount", align: "right", render: (v: number) => <span style={{ fontWeight: 600 }}>{v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span> },
                    { title: "Paid", dataIndex: "amount_paid", key: "amount_paid", align: "right", render: (v: number) => <span style={{ color: "#10b981", fontWeight: 600 }}>{v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span> },
                    { title: "Balance", dataIndex: "balance", key: "balance", align: "right", render: (v: number) => <span style={{ color: v > 0 ? "#f59e0b" : "#10b981" }}>{v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span> },
                  ]}
                />
              ) : <Empty description="No invoices for this contract" />}

              <Text strong style={{ display: "block", margin: "24px 0 12px", color: "#e5e7eb", fontSize: "13px" }}>Payments Received</Text>
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
                    { title: "Amount", dataIndex: "amount", key: "amount", align: "right", render: (v: number) => <span style={{ color: "#10b981", fontWeight: 600 }}>{fmtINR(v)}</span> },
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

// ─── Standard Reports Panel ──────────────────────────────────────────────────

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
      className="glass-card"
      style={{ marginBottom: 24 }}
      styles={{
        header: {
          background: "linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(139, 92, 246, 0.02) 100%)",
          borderBottom: "1px solid rgba(139, 92, 246, 0.15)",
          borderRadius: "12px 12px 0 0"
        },
        body: { padding: "24px" }
      }}
      title={
        <Space>
          <BarChartOutlined style={{ color: "#8b5cf6", fontSize: 18 }} />
          <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 16 }}>
            Standard Operational Reports
          </span>
          <Tag color="purple" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(139, 92, 246, 0.12)", border: "1px solid rgba(139, 92, 246, 0.2)" }}>
            OPERATIONAL CATALOG
          </Tag>
        </Space>
      }
    >
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
        {/* Left Side: Available Reports */}
        <Card
          title={<span style={{ color: "var(--text-primary)", fontWeight: 600 }}>Available Templates</span>}
          style={{ width: 300, flexShrink: 0, background: "rgba(255, 255, 255, 0.01)", borderColor: "rgba(255, 255, 255, 0.06)" }}
          styles={{ body: { padding: 0 } }}
        >
          <List
            dataSource={reports}
            renderItem={(r) => {
              const isActive = active?.key === r.key;
              return (
                <List.Item
                  id={`report-item-${r.key}`}
                  style={{
                    padding: "12px 20px",
                    cursor: "pointer",
                    background: isActive ? "rgba(139, 92, 246, 0.12)" : "transparent",
                    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                    transition: "var(--transition-smooth)"
                  }}
                  onClick={() => run(r)}
                  actions={[<PlayCircleOutlined key="run" style={{ color: isActive ? "#8b5cf6" : "#9ca3af" }} />]}
                >
                  <Text style={{ color: isActive ? "#c084fc" : "#e5e7eb", fontWeight: isActive ? 600 : 400 }}>{r.title}</Text>
                </List.Item>
              );
            }}
            locale={{ emptyText: "Syncing templates..." }}
          />
        </Card>

        {/* Right Side: Report Workspace Output */}
        <Card
          style={{ flex: 1, minWidth: 360, background: "rgba(255, 255, 255, 0.01)", borderColor: "rgba(255, 255, 255, 0.06)" }}
          title={<span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{active ? active.title : "Workspace Output"}</span>}
          extra={active && (
            <Space>
              <Button id="export-csv-btn" icon={<FileTextOutlined />} loading={exporting === "csv"} onClick={() => doExport("csv")}>CSV</Button>
              <Button id="export-xlsx-btn" icon={<FileExcelOutlined />} loading={exporting === "xlsx"} onClick={() => doExport("xlsx")} style={{ color: "#10b981", borderColor: "#10b981" }}>Excel</Button>
              <Button id="export-pdf-btn" icon={<FilePdfOutlined />} loading={exporting === "pdf"} onClick={() => doExport("pdf")} danger>PDF</Button>
            </Space>
          )}
        >
          {!active && <Empty description="Pick an operational report template to execute" />}
          {running && <Spin style={{ display: "block", margin: "40px auto" }} />}
          {!running && active && isList && (
            data.length
              ? <Table id="standard-report-table" rowKey={(_, i) => String(i)} columns={columns} dataSource={data} size="small" scroll={{ x: true }} />
              : <Empty description="No data generated in this period" />
          )}
          {!running && active && !isList && data && (
            <Descriptions bordered column={1} size="small">
              {Object.entries(data).map(([k, v]) => (
                <Descriptions.Item key={k} label={k.replace(/_/g, " ").toUpperCase()}>
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

// ─── SLA Compliance Report Panel ─────────────────────────────────────────────

function SLAReportPanel() {
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const generateReport = async () => {
    if (!dateRange) {
      message.warning("Please select a date range");
      return;
    }
    setLoading(true);
    setData(null);
    try {
      const { data: resData } = await apiClient.get("/reports/sla", {
        params: {
          from_date: dateRange[0].format("YYYY-MM-DD"),
          to_date: dateRange[1].format("YYYY-MM-DD"),
        },
      });
      setData(resData);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to generate SLA report");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      id="sla-report-panel"
      className="glass-card"
      style={{ marginBottom: 28 }}
      styles={{
        header: {
          background: "linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.02) 100%)",
          borderBottom: "1px solid rgba(16, 185, 129, 0.15)",
          borderRadius: "12px 12px 0 0"
        },
        body: { padding: "24px" }
      }}
      title={
        <Space>
          <BarChartOutlined style={{ color: "#10b981", fontSize: 18 }} />
          <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: 15 }}>
            SLA Compliance Report
          </span>
          <Tag color="green" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(16, 185, 129, 0.12)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
            SERVICE LEVEL AGREEMENT
          </Tag>
        </Space>
      }
    >
      <Row gutter={[16, 12]} align="middle" style={{ marginBottom: 24 }}>
        <Col xs={24} md={18}>
          <Text style={{ display: "block", marginBottom: 6, fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Report Period
          </Text>
          <RangePicker
            id="sla-report-date-range"
            style={{ width: "100%" }}
            value={dateRange}
            onChange={(v) => setDateRange(v as [Dayjs, Dayjs] | null)}
            format="YYYY-MM-DD"
          />
        </Col>
        <Col xs={24} md={6} style={{ paddingTop: 22 }}>
          <Button
            id="sla-generate-btn"
            type="primary"
            icon={<FileSearchOutlined />}
            loading={loading}
            disabled={!dateRange}
            onClick={generateReport}
            style={{
              background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
              border: "none",
              width: "100%"
            }}
          >
            Generate Report
          </Button>
        </Col>
      </Row>

      {loading && (
        <div style={{ textAlign: "center", padding: "64px 0" }}>
          <Spin size="large" tip="Calculating SLA compliance..." />
        </div>
      )}

      {!loading && data && (
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <SmartCard
              title="Total Tickets"
              value={data.total_tickets}
              prefix={<ToolOutlined />}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <SmartCard
              title="SLA Met"
              value={data.sla_met}
              prefix={<CheckCircleOutlined />}
              status="success"
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <SmartCard
              title="SLA Breached"
              value={data.sla_breached}
              prefix={<CloseCircleOutlined />}
              status={data.sla_breached > 0 ? "danger" : "success"}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <MetricProgressGauge
              title="SLA Compliance"
              percent={data.compliance_pct}
              status={data.compliance_pct >= 90 ? "success" : (data.compliance_pct >= 70 ? "warning" : "danger")}
              subtext="Compliance target is 90%+"
            />
          </Col>
        </Row>
      )}

      {!loading && !data && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <span>
              Select a date range, then click <Text strong style={{ color: "var(--text-primary)" }}>Generate Report</Text> to view SLA stats.
            </span>
          }
          style={{ padding: "32px 0" }}
        />
      )}
    </Card>
  );
}

// ─── Main Reports Hub Page ───────────────────────────────────────────────────

export default function ReportsPage() {
  return (
    <ConfigProvider theme={{}}>
      <div id="reports-page" style={{ padding: "8px 0 24px 0" }}>
        {/* Page Header */}
        <div style={{ marginBottom: 28 }}>
          <Title level={4} style={{ margin: 0, marginBottom: 6, display: "flex", alignItems: "center", gap: 10 }}>
            <BarChartOutlined style={{ color: "#3b82f6" }} />
            <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Analytics &amp; Intelligence Hub
            </span>
          </Title>
          <Text style={{ color: "var(--text-secondary)", fontSize: "13.5px" }}>
            Real-time service execution metrics, operational SLA tracking, and financial contract assessments.
          </Text>
        </div>

        <SLAReportPanel />
        <AMCConsolidatedPanel />
        <StandardReportsPanel />
      </div>
    </ConfigProvider>
  );
}
