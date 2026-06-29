import React from "react";
import { Card, Space } from "antd";
import { HistoryOutlined } from "@ant-design/icons";

interface Activity {
  id: string;
  time: string;
  title: string;
  description: string;
  status: "success" | "warning" | "danger" | "violet" | "default";
}

const ACTIVITIES: Activity[] = [
  {
    id: "act-1",
    time: "10 mins ago",
    title: "Technician Check-out Successful",
    description: "Technician Rohit K. completed check-out at Customer site 'Ganesh Temple Complex'.",
    status: "success",
  },
  {
    id: "act-2",
    time: "1 hour ago",
    title: "Invoice Paid",
    description: "Customer 'City Mall CHS' settled invoice #INV-9280 for ₹34,500.",
    status: "violet",
  },
  {
    id: "act-3",
    time: "2 hours ago",
    title: "Critical Ticket Raised",
    description: "Customer 'Supreme Office Hub' logged critical ticket #TKT-8271 regarding main gate camera offline.",
    status: "danger",
  },
  {
    id: "act-4",
    time: "4 hours ago",
    title: "AMC Renewal Draft Created",
    description: "Auto-generated renewal proposal for contract #AMC-4311.",
    status: "warning",
  }
];

export default function ActivityTimeline() {
  return (
    <Card
      className="glass-card"
      styles={{
        header: { borderBottom: "1px solid var(--glass-border)", padding: "16px 24px" },
        body: { padding: "20px 24px" }
      }}
      title={
        <Space>
          <HistoryOutlined style={{ color: "#3b82f6", fontSize: 18 }} />
          <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>Recent Activities</span>
        </Space>
      }
    >
      <div className="timeline-container">
        {ACTIVITIES.map((act) => (
          <div key={act.id} className="timeline-node">
            <div className={`timeline-node-dot ${act.status}`} />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
                {act.title}
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                {act.time}
              </span>
            </div>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
              {act.description}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
