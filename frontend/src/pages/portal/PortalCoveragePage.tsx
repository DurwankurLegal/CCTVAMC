import { useEffect, useState } from "react";
import { Card, Table, Tag, Typography, message, Spin } from "antd";
import portalClient from "../../api/portalClient";

const { Title } = Typography;

interface AMC { id: string; contract_number: string; status: string; start_date: string; end_date: string; annual_amount: number }
interface Asset { id: string; serial_number?: string; model?: string; status: string; warranty_expiry?: string | null }

const amcStatusColor: Record<string, string> = { active: "green", draft: "default", expired: "red", suspended: "orange" };

export default function PortalCoveragePage() {
  const [amc, setAmc] = useState<AMC[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [a, s] = await Promise.all([portalClient.get("/amc"), portalClient.get("/assets")]);
        setAmc(a.data);
        setAssets(s.data);
      } catch (e: any) {
        message.error(e?.response?.data?.detail || "Failed to load coverage");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Spin style={{ display: "block", margin: "80px auto" }} />;

  const amcCols = [
    { title: "Contract #", dataIndex: "contract_number", key: "contract_number" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={amcStatusColor[v] ?? "default"}>{v}</Tag> },
    { title: "Valid From", dataIndex: "start_date", key: "start_date" },
    { title: "Valid Until", dataIndex: "end_date", key: "end_date" },
    { title: "Annual (₹)", dataIndex: "annual_amount", key: "annual_amount",
      render: (v: number) => v.toLocaleString("en-IN", { minimumFractionDigits: 2 }) },
  ];
  const assetCols = [
    { title: "Serial", dataIndex: "serial_number", key: "serial_number", render: (v?: string) => v || "—" },
    { title: "Model", dataIndex: "model", key: "model", render: (v?: string) => v || "—" },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag>{v}</Tag> },
    { title: "Warranty Until", dataIndex: "warranty_expiry", key: "warranty_expiry", render: (v?: string | null) => v || "—" },
  ];

  return (
    <div>
      <Title level={4}>AMC & Assets</Title>
      <Card title="AMC Contracts" style={{ marginBottom: 16 }}>
        <Table rowKey="id" columns={amcCols} dataSource={amc} pagination={false}
          locale={{ emptyText: "No AMC contracts" }} />
      </Card>
      <Card title="Covered Assets">
        <Table rowKey="id" columns={assetCols} dataSource={assets} pagination={false}
          locale={{ emptyText: "No assets on record" }} />
      </Card>
    </div>
  );
}
