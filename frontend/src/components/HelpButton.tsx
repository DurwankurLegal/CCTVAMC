import React from "react";
import { Button, Tooltip } from "antd";
import { QuestionCircleOutlined } from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";

interface HelpButtonProps {
  slug?: string;
  type?: "float" | "button";
}

const HelpButton: React.FC<HelpButtonProps> = ({ slug, type = "button" }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const getSlugFromPath = (path: string): string => {
    // Basic automatic mapping of routes to documentation slugs
    const cleanPath = path.replace(/^\//, "").split("?")[0];
    if (!cleanPath || cleanPath === "help") return "introduction";
    if (cleanPath.startsWith("help/")) {
      return cleanPath.substring(5) || "introduction";
    }
    
    // Map specific paths to user guide articles
    const mappings: Record<string, string> = {
      "dashboard": "introduction",
      "leads": "lead-management",
      "customers": "customer-directory",
      "quotations": "quotations",
      "sales-orders": "sales-orders",
      "invoices": "invoices",
      "payments": "payments",
      "rentals": "rental-contracts",
      "products": "product-catalog",
      "amc": "amc-contracts",
      "service-tickets": "service-tickets",
      "engineer-visits": "engineer-visits",
      "installations": "installations",
      "inventory": "product-catalog",
      "vendors": "vendor-management",
      "reports": "reports",
      "users": "user-management",
      "tenant-settings": "tenant-settings"
    };

    return mappings[cleanPath] || cleanPath;
  };

  const handleHelpClick = () => {
    const targetSlug = slug || getSlugFromPath(location.pathname);
    navigate(`/help/${targetSlug}`);
  };

  if (type === "float") {
    return (
      <Tooltip title="Open Help Center" placement="left">
        <Button
          type="primary"
          shape="circle"
          icon={<QuestionCircleOutlined />}
          size="large"
          onClick={handleHelpClick}
          style={{
            position: "fixed",
            right: 24,
            bottom: 80,
            zIndex: 1000,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            background: "linear-gradient(135deg, #0F2A43, #1e4d75)",
            border: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 48,
            height: 48
          }}
        />
      </Tooltip>
    );
  }

  return (
    <Tooltip title="View page documentation" placement="bottom">
      <Button
        type="text"
        icon={<QuestionCircleOutlined style={{ fontSize: "16px" }} />}
        onClick={handleHelpClick}
        style={{
          display: "flex",
          alignItems: "center",
          color: "#ffffff"
        }}
      >
        Help
      </Button>
    </Tooltip>
  );
};

export default HelpButton;
