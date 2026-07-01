import React from "react";
import { Card, Space } from "antd";

interface MetricProgressGaugeProps {
  title: React.ReactNode;
  percent: number;
  subtext?: React.ReactNode;
  status?: "success" | "warning" | "danger" | "info" | "default";
  onClick?: () => void;
}

export default function MetricProgressGauge({
  title,
  percent,
  subtext,
  status = "default",
  onClick,
}: MetricProgressGaugeProps) {
  // Normalize percent between 0 and 100
  const normalized = Math.min(Math.max(percent, 0), 100);
  
  // SVG arc calculation parameters
  const radius = 36;
  const strokeWidth = 6;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalized / 100) * circumference;

  // Determine colors based on status or value
  const colorMap = {
    success: "#10b981",
    warning: "#f59e0b",
    danger: "#ef4444",
    info: "#3b82f6",
    default: "#3b82f6",
  };
  const activeColor = colorMap[status];

  const classes = ["glass-card"];
  if (onClick) {
    classes.push("interactive-card");
    if (status !== "default") {
      classes.push(`interactive-card-${status}`);
    }
  }

  return (
    <Card 
      className={classes.join(" ")}
      onClick={onClick}
      style={{ height: "100%", width: "100%", background: "#ecfeff", border: "1px solid #cffafe" }}
      styles={{
        body: { padding: "20px 24px", display: "flex", alignItems: "center", gap: "20px", height: "100%" }
      }}
    >
      {/* Gauge SVG Circle */}
      <div style={{ position: "relative", width: "80px", height: "80px", flexShrink: 0 }}>
        <svg width="80" height="80" viewBox="0 0 80 80">
          <defs>
            <filter id={`glow-${status}`} x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>
          
          {/* Background circle */}
          <circle
            cx="40"
            cy="40"
            r={radius}
            fill="none"
            stroke="rgba(0, 0, 0, 0.06)"
            strokeWidth={strokeWidth}
          />
          
          {/* Active progress circle */}
          <circle
            className="gauge-svg-circle"
            cx="40"
            cy="40"
            r={radius}
            fill="none"
            stroke={activeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            transform="rotate(-90 40 40)"
            filter={`url(#glow-${status})`}
          />
        </svg>
        <div style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column"
        }}>
          <span style={{ fontSize: "16px", fontWeight: 700, color: "#111827" }}>
            {percent.toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Info details */}
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <span style={{ fontSize: "14px", fontWeight: 500, color: "#4b5563" }}>
          {title}
        </span>
        {subtext && (
          <div style={{ fontSize: "12px", color: "#6b7280", marginTop: "2px" }}>
            {subtext}
          </div>
        )}
      </div>
    </Card>
  );
}
