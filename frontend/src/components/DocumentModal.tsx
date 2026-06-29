import { useEffect, useState } from "react";
import { Modal, Select, Upload, Button, List, Tag, Space, message } from "antd";
import { UploadOutlined, FileOutlined, InboxOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Option } = Select;

const DOC_TYPES = ["contract", "invoice", "receipt", "audit", "warranty", "photo", "other"];

interface Document {
  id: string;
  doc_type: string;
  file_name: string;
  url?: string;
}

interface DocumentModalProps {
  open: boolean;
  entityType: string;
  entityId: string | null;
  entityName: string;
  onClose: () => void;
}

export default function DocumentModal({ open, entityType, entityId, entityName, onClose }: DocumentModalProps) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [docType, setDocType] = useState("other");
  const [uploading, setUploading] = useState(false);

  const load = async () => {
    if (!entityId) return;
    setLoading(true);
    try {
      const { data } = await apiClient.get("/documents", {
        params: { entity_type: entityType, entity_id: entityId }
      });
      setDocs(data);
    } catch {
      setDocs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && entityId) {
      load();
    } else {
      setDocs([]);
    }
  }, [open, entityId, entityType]);

  const handleUpload = async (file: File) => {
    if (!entityId) return false;
    setUploading(true);
    const fd = new FormData();
    fd.append("entity_type", entityType);
    fd.append("entity_id", entityId);
    fd.append("doc_type", docType);
    fd.append("file", file);
    try {
      await apiClient.post("/documents", fd, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      message.success("Document uploaded");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
    return false; // prevent antd auto-upload
  };

  const handleViewFile = async (d: Document) => {
    try {
      const response = await apiClient.get(`/documents/${d.id}/view`, {
        responseType: "blob"
      });
      const contentType = (response.headers["content-type"] as string) || "application/octet-stream";
      const blob = new Blob([response.data], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => window.URL.revokeObjectURL(url), 60000);
    } catch {
      message.error("Failed to load/view document");
    }
  };

  const handleDeleteFile = async (d: Document) => {
    try {
      await apiClient.delete(`/documents/${d.id}`);
      message.success("Document deleted");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  return (
    <Modal
      title={`Documents — ${entityName}`}
      open={open}
      footer={null}
      onCancel={onClose}
      loading={loading}
    >
      <Space style={{ marginBottom: 12 }}>
        <Select value={docType} onChange={setDocType} style={{ width: 180 }}>
          {DOC_TYPES.map(d => (
            <Option key={d} value={d}>{d.toUpperCase()}</Option>
          ))}
        </Select>
        <Upload 
          beforeUpload={(f) => handleUpload(f as File)} 
          showUploadList={false}
          accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
        >
          <Button icon={<UploadOutlined />} loading={uploading}>Upload</Button>
        </Upload>
      </Space>
      <List
        dataSource={docs}
        locale={{ emptyText: <span><InboxOutlined /> No documents yet</span> }}
        renderItem={(d) => (
          <List.Item
            actions={[
              <Button key="v" type="link" size="small" style={{ padding: 0 }} onClick={() => handleViewFile(d)}>View</Button>,
              <Button key="d" type="link" size="small" danger style={{ padding: 0 }} onClick={() => handleDeleteFile(d)}>Delete</Button>
            ]}
          >
            <List.Item.Meta
              avatar={<FileOutlined />}
              title={d.file_name}
              description={<Tag>{d.doc_type.toUpperCase()}</Tag>}
            />
          </List.Item>
        )}
      />
    </Modal>
  );
}
