import React from "react";
import { Card, Skeleton, Typography, Space } from "antd";

const { Text } = Typography;

interface SmartCardProps {
  title: React.ReactNode;
  value: React.ReactNode;
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
    success: "#059669",
    warning: "#d97706",
    danger: "#dc2626",
    info: "#2563eb",
    default: "#4b5563",
  };
  const bgMap = {
    success: "#d1fae5",
    warning: "#fef3c7",
    danger: "#fee2e2",
    info: "#dbeafe",
    default: "#ffffff",
  };
  const borderMap = {
    success: "#a7f3d0",
    warning: "#fde68a",
    danger: "#fecaca",
    info: "#bfdbfe",
    default: "#e5e7eb",
  };

  const accentColor = colorMap[status] || colorMap.default;
  const bgColor = bgMap[status] || bgMap.default;
  const borderColor = borderMap[status] || borderMap.default;

  const titleColor = status === "default" ? "#4b5563" : "#4b5563";
  const valueColor = status === "default" ? "#111827" : "#111827";

  return (
    <Card
      className={classes.join(" ")}
      onClick={onClick}
      style={{ height: "100%", width: "100%", background: bgColor, border: `1px solid ${borderColor}`, boxShadow: "0 4px 12px rgba(0,0,0,0.03)" }}
      styles={{
        body: { padding: "20px 24px", height: "100%" }
      }}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 2 }} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", height: "100%", justifyContent: "space-between" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "14px", fontWeight: 500, color: titleColor }}>
                {title}
              </span>
              {prefix && (
                <span style={{ fontSize: "18px", color: accentColor, display: "flex", alignItems: "center" }}>
                  {prefix}
                </span>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "4px" }}>
              <span style={{ fontSize: "28px", fontWeight: 700, color: "#111827", letterSpacing: "-0.5px" }}>
                {value}
              </span>
            </div>
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
