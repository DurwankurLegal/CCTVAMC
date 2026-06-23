import { useEffect, useState } from "react";
import {
  Card, List, Button, Table, Typography, message, Space, Tag, Descriptions, Empty, Spin,
} from "antd";
import { FileExcelOutlined, FilePdfOutlined, FileTextOutlined, PlayCircleOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title, Text } = Typography;

interface ReportMeta { key: string; title: string }

function downloadBlob(data: BlobPart, filename: string, mime: string) {
  const url = window.URL.createObjectURL(new Blob([data], { type: mime }));
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); window.URL.revokeObjectURL(url);
}

export default function ReportsPage() {
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
      // Error bodies come back as a Blob with responseType:"blob" — read it for the detail.
      if (e?.response?.status === 503) {
        message.warning("PDF export is unavailable in this environment — use CSV or Excel.");
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
    <div>
      <Title level={4}>Reports & Exports</Title>
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
        <Card title="Available Reports" style={{ width: 320, flexShrink: 0 }} styles={{ body: { padding: 0 } }}>
          <List
            dataSource={reports}
            renderItem={(r) => (
              <List.Item
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
              <Button icon={<FileTextOutlined />} loading={exporting === "csv"} onClick={() => doExport("csv")}>CSV</Button>
              <Button icon={<FileExcelOutlined />} loading={exporting === "xlsx"} onClick={() => doExport("xlsx")}>Excel</Button>
              <Button icon={<FilePdfOutlined />} loading={exporting === "pdf"} onClick={() => doExport("pdf")}>PDF</Button>
            </Space>
          )}
        >
          {!active && <Empty description="Pick a report from the list to run it" />}
          {running && <Spin style={{ display: "block", margin: "40px auto" }} />}
          {!running && active && isList && (
            data.length
              ? <Table rowKey={(_, i) => String(i)} columns={columns} dataSource={data} size="small" scroll={{ x: true }} />
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
    </div>
  );
}
