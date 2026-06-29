import React, { useState } from "react";
import { Upload, Button, message, Space } from "antd";
import { UploadOutlined, DeleteOutlined, EyeOutlined } from "@ant-design/icons";
import type { UploadFile, RcFile } from "antd/es/upload/interface";

interface BrandedFileUploadProps {
  value?: string | null;
  onChange?: (value: string | null) => void;
  label?: string;
  maxSizeMB?: number;
}

export const BrandedFileUpload: React.FC<BrandedFileUploadProps> = ({
  value = null,
  onChange,
  label = "Upload Image",
  maxSizeMB = 2
}) => {
  const [loading, setLoading] = useState(false);

  const beforeUpload = (file: RcFile) => {
    const isAcceptedFormat = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"].includes(file.type);
    if (!isAcceptedFormat) {
      message.error("You can only upload PNG, JPG, JPEG, or SVG files!");
      return Upload.LIST_IGNORE;
    }
    const isLtMax = file.size / 1024 / 1024 < maxSizeMB;
    if (!isLtMax) {
      message.error(`Image must be smaller than ${maxSizeMB}MB!`);
      return Upload.LIST_IGNORE;
    }
    return true;
  };

  const handleCustomUpload = async (options: any) => {
    const { file, onSuccess, onError } = options;
    setLoading(true);

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      if (onChange) {
        onChange(dataUrl);
      }
      setLoading(false);
      onSuccess?.("ok");
    };
    reader.onerror = (e) => {
      message.error("Failed to read file.");
      setLoading(false);
      onError?.(new Error("File read error"));
    };
    reader.readAsDataURL(file as File);
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onChange) {
      onChange(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {value ? (
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "16px",
            padding: "8px 12px",
            borderRadius: "6px",
            border: "1px solid var(--glass-border)",
            background: "rgba(255, 255, 255, 0.02)",
            maxWidth: "100%"
          }}
        >
          <img
            src={value}
            alt="Preview"
            style={{
              maxHeight: "50px",
              maxWidth: "120px",
              objectFit: "contain",
              borderRadius: "4px",
              background: "rgba(255, 255, 255, 0.05)"
            }}
          />
          <Space>
            <Upload
              accept=".png,.jpg,.jpeg,.svg"
              showUploadList={false}
              beforeUpload={beforeUpload}
              customRequest={handleCustomUpload}
            >
              <Button size="small" icon={<UploadOutlined />} loading={loading}>
                Replace
              </Button>
            </Upload>
            <Button
              size="small"
              danger
              type="text"
              icon={<DeleteOutlined />}
              onClick={handleRemove}
            >
              Remove
            </Button>
          </Space>
        </div>
      ) : (
        <Upload
          accept=".png,.jpg,.jpeg,.svg"
          showUploadList={false}
          beforeUpload={beforeUpload}
          customRequest={handleCustomUpload}
        >
          <Button icon={<UploadOutlined />} loading={loading}>
            {label}
          </Button>
        </Upload>
      )}
    </div>
  );
};
