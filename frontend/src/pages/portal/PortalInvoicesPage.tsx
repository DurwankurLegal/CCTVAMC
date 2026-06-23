import { useEffect, useState } from "react";
import { Table, Tag, Typography, message, Spin } from "antd";
import portalClient from "../../api/portalClient";

const { Title } = Typography;

interface Invoice {
  id: string; invoice_number: string; status: string;
  invoice_date?: string | null; due_date?: string | null;
  total_amount: number; amount_paid: number;
}

const statusColor: Record<string, string> = {
  paid: "green", issued: "blue", overdue: "red", draft: "default", cancelled: "default",
};

export default function PortalInvoicesPage() {
  const [rows, setRows] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setRows((await portalClient.get("/invoices")).data);
      } catch (e: any) {
        message.error(e?.response?.data?.detail || "Failed to load invoices");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Spin style={{ display: "block", margin: "80px auto" }} />;

  const inr = (v: number) => "₹" + v.toLocaleString("en-IN", { minimumFractionDigits: 2 });
  const columns = [
    { title: "Invoice #", dataIndex: "invoice_number", key: "invoice_number" },
    { title: "Date", dataIndex: "invoice_date", key: "invoice_date", render: (v?: string | null) => v || "—" },
    { title: "Due", dataIndex: "due_date", key: "due_date", render: (v?: string | null) => v || "—" },
    { title: "Total", dataIndex: "total_amount", key: "total_amount", render: inr },
    { title: "Paid", dataIndex: "amount_paid", key: "amount_paid", render: inr },
    { title: "Balance", key: "balance",
      render: (_: unknown, r: Invoice) => inr(Math.max(0, r.total_amount - r.amount_paid)) },
    { title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v}</Tag> },
  ];

  return (
    <div>
      <Title level={4}>Invoices</Title>
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading}
        locale={{ emptyText: "No invoices" }} scroll={{ x: true }} />
    </div>
  );
}
