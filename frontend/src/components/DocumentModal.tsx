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
        <Upload beforeUpload={(f) => handleUpload(f as File)} showUploadList={false}>
          <Button icon={<UploadOutlined />} loading={uploading}>Upload</Button>
        </Upload>
      </Space>
      <List
        dataSource={docs}
        locale={{ emptyText: <span><InboxOutlined /> No documents yet</span> }}
        renderItem={(d) => (
          <List.Item
            actions={d.url ? [<a key="v" href={d.url} target="_blank" rel="noreferrer">View</a>] : []}
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
