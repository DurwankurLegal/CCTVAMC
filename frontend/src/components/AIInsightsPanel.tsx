import React from "react";
import { Card, Space, Tag, Typography, Button } from "antd";
import { BulbOutlined, RightOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

const { Title, Paragraph } = Typography;

interface Insight {
  id: string;
  category: "renewal" | "inventory" | "sla" | "general";
  title: string;
  description: string;
  ctaText?: string;
  destinationRoute?: string;
}

const INSIGHTS: Insight[] = [
  {
    id: "insight-1",
    category: "renewal",
    title: "Upcoming AMC Contract Expirations",
    description: "AMC Contract # AMC-9082 for customer 'Evergreen CHS' is expiring in 12 days. Value: ₹95,000. Suggest initiating renewal quote.",
    ctaText: "Prepare Renewal",
    destinationRoute: "/amc?status=active",
  },
  {
    id: "insight-2",
    category: "inventory",
    title: "Low Inventory Alert",
    description: "Dome Camera model 'Hikvision 4MP HD' stock count is at 2 units (reorder threshold is 5). Reorder required from Apex Electronics.",
    ctaText: "Reorder Stock",
    destinationRoute: "/inventory",
  },
  {
    id: "insight-3",
    category: "sla",
    title: "High Risk SLA Breaches",
    description: "3 Service Tickets in category 'Critical' have been open for over 18 hours without technician visits assigned.",
    ctaText: "Assign Tickets",
    destinationRoute: "/tickets?status=open",
  }
];

export default function AIInsightsPanel() {
  const navigate = useNavigate();

  const getTagColor = (category: string) => {
    switch (category) {
      case "renewal": return "orange";
      case "inventory": return "gold";
      case "sla": return "red";
      default: return "blue";
    }
  };

  return (
    <Card
      className="glass-card"
      styles={{
        header: { borderBottom: "1px solid var(--glass-border)", padding: "16px 24px" },
        body: { padding: "20px 24px" }
      }}
      title={
        <Space>
          <BulbOutlined style={{ color: "#8b5cf6", fontSize: 18 }} />
          <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>AI Operational Insights</span>
        </Space>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {INSIGHTS.map((insight) => (
          <div key={insight.id} className="ai-insight-box">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
              <Space direction="vertical" size={2}>
                <Space>
                  <span style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "14px" }}>
                    {insight.title}
                  </span>
                  <Tag color={getTagColor(insight.category)} style={{ fontSize: "10px" }}>
                    {insight.category.toUpperCase()}
                  </Tag>
                </Space>
                <Paragraph style={{ color: "var(--text-secondary)", fontSize: "12px", margin: 0, marginTop: 4 }}>
                  {insight.description}
                </Paragraph>
              </Space>
              
              {insight.ctaText && (
                <Button 
                  type="text" 
                  size="small" 
                  onClick={() => insight.destinationRoute && navigate(insight.destinationRoute)}
                  style={{ color: "#8b5cf6", display: "flex", alignItems: "center", gap: 4, fontWeight: 500, padding: 0 }}
                >
                  {insight.ctaText} <RightOutlined style={{ fontSize: 10 }} />
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
