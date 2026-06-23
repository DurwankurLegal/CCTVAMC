import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Tag, Space, Typography, message, Descriptions, Image, List, Empty,
} from "antd";
import { EyeOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Title } = Typography;

const typeColor: Record<string, string> = { corrective: "volcano", preventive: "green" };
const fmt = (v?: string) => (v ? new Date(v).toLocaleString("en-IN") : "—");

interface Visit {
  id: string; ticket_id?: string; amc_contract_id?: string; technician_id: string;
  visit_type: string; checkin_at?: string; checkout_at?: string;
  checkin_lat?: number; checkin_lng?: number;
  work_performed?: string; parts_used: any[]; photo_urls: any[]; signature_url?: string;
  is_synced: boolean;
}

export default function EngineerVisitsPage() {
  const [rows, setRows] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<Visit | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setRows((await apiClient.get("/engineer-visits", { params: { limit: 200 } })).data); }
    catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load visits"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const statusTag = (v: Visit) => {
    if (v.checkout_at) return <Tag color="green">completed</Tag>;
    if (v.checkin_at) return <Tag color="gold">in progress</Tag>;
    return <Tag>scheduled</Tag>;
  };

  const columns = [
    { title: "Type", dataIndex: "visit_type", key: "visit_type", render: (v: string) => <Tag color={typeColor[v] ?? "default"}>{v}</Tag> },
    { title: "Ticket", dataIndex: "ticket_id", key: "ticket_id", render: (v?: string) => v ? v.slice(0, 8) : "—" },
    { title: "Check-in", dataIndex: "checkin_at", key: "checkin_at", render: fmt },
    { title: "Check-out", dataIndex: "checkout_at", key: "checkout_at", render: fmt },
    { title: "Progress", key: "progress", render: (_: unknown, v: Visit) => statusTag(v) },
    { title: "Synced", dataIndex: "is_synced", key: "is_synced", render: (v: boolean) => <Tag color={v ? "green" : "orange"}>{v ? "synced" : "pending"}</Tag> },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, v: Visit) => <Button size="small" icon={<EyeOutlined />} onClick={() => setDetail(v)}>View</Button>,
    },
  ];

  return (
    <div>
      <Title level={4}>Engineer Visits</Title>
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No engineer visits" }} />

      <Modal title="Visit Details" open={!!detail} footer={null} onCancel={() => setDetail(null)} width={680}>
        {detail && (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Type"><Tag color={typeColor[detail.visit_type] ?? "default"}>{detail.visit_type}</Tag></Descriptions.Item>
              <Descriptions.Item label="Check-in">{fmt(detail.checkin_at)}</Descriptions.Item>
              <Descriptions.Item label="Check-out">{fmt(detail.checkout_at)}</Descriptions.Item>
              <Descriptions.Item label="Check-in GPS">
                {detail.checkin_lat != null ? `${detail.checkin_lat}, ${detail.checkin_lng}` : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Work Performed">{detail.work_performed || "—"}</Descriptions.Item>
            </Descriptions>

            <Title level={5}>Parts Used</Title>
            {detail.parts_used?.length ? (
              <List size="small" dataSource={detail.parts_used}
                renderItem={(p: any) => <List.Item>{p.description || p.item_id} × {p.quantity}</List.Item>} />
            ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No parts used" />}

            <Title level={5} style={{ marginTop: 16 }}>Photos</Title>
            {detail.photo_urls?.length ? (
              <Image.PreviewGroup>
                <Space wrap>{detail.photo_urls.map((u: string, i: number) => <Image key={i} width={96} src={u} />)}</Space>
              </Image.PreviewGroup>
            ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No photos" />}

            {detail.signature_url && (
              <>
                <Title level={5} style={{ marginTop: 16 }}>Customer Signature</Title>
                <Image width={200} src={detail.signature_url} />
              </>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}
