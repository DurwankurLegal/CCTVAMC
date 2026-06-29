import React from "react";
import { Card, Skeleton, Typography, Space } from "antd";

const { Text } = Typography;

interface SmartCardProps {
  title: React.ReactNode;
  value: string | number;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  onClick?: () => void;
  status?: "success" | "warning" | "danger" | "info" | "default";
  loading?: boolean;
}

export default function SmartCard({
  title,
  value,
  prefix,
  suffix,
  onClick,
  status = "default",
  loading = false,
}: SmartCardProps) {
  // Determine card interactive classes
  const classes = ["glass-card"];
  if (onClick) {
    classes.push("interactive-card");
    if (status !== "default") {
      classes.push(`interactive-card-${status}`);
    }
  }

  // Determine accent color for icons/text
  const colorMap = {
    success: "#10b981",
    warning: "#f59e0b",
    danger: "#ef4444",
    info: "#3b82f6",
    default: "#3b82f6",
  };
  const accentColor = colorMap[status];

  return (
    <Card
      className={classes.join(" ")}
      onClick={onClick}
      styles={{
        body: { padding: "20px 24px" }
      }}
      style={{ height: "100%" }}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 2 }} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)" }}>
              {title}
            </span>
            {prefix && (
              <span style={{ fontSize: "18px", color: accentColor, display: "flex", alignItems: "center" }}>
                {prefix}
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "4px" }}>
            <span style={{ fontSize: "28px", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.5px" }}>
              {value}
            </span>
          </div>
          {suffix && (
            <div style={{ marginTop: "4px", display: "flex", alignItems: "center" }}>
              {suffix}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
