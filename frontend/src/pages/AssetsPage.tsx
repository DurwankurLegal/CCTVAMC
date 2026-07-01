import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Typography, message,
  DatePicker, Upload, List, Tooltip,
} from "antd";
import { PlusOutlined, EditOutlined, FileOutlined, UploadOutlined, InboxOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import apiClient from "../api/client";

const { Title } = Typography;
const { Option } = Select;

const STATUSES = ["active", "faulty", "under_repair", "replaced", "decommissioned"];
const statusColor: Record<string, string> = {
  active: "green", faulty: "red", under_repair: "orange", replaced: "default", decommissioned: "default",
};
const DOC_TYPES = ["warranty_card", "amc_agreement", "signed_report", "photo", "invoice", "other"];

interface Site { id: string; name: string }
interface Asset {
  id: string; site_id: string; serial_number?: string; make?: string; model?: string;
  asset_type?: string; warranty_expiry?: string; status: string; location_description?: string;
}
interface Doc { id: string; doc_type: string; file_name: string; url?: string }

function warrantyTag(expiry?: string) {
  if (!expiry) return <Tag>—</Tag>;
  const days = dayjs(expiry).diff(dayjs(), "day");
  if (days < 0) return <Tag color="red">expired {dayjs(expiry).format("DD MMM YYYY")}</Tag>;
  if (days <= 30) return <Tag color="orange">{expiry} ({days}d left)</Tag>;
  return <Tag color="green">{expiry}</Tag>;
}

export default function AssetsPage() {
  const [rows, setRows] = useState<Asset[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Asset | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  // documents modal
  const [docAsset, setDocAsset] = useState<Asset | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [docType, setDocType] = useState("warranty_card");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, s] = await Promise.all([
        apiClient.get("/assets", { params: { limit: 200 } }),
        apiClient.get("/customers/sites"),
      ]);
      setRows(a.data); setSites(s.data);
    } catch (e: any) { message.error(e?.response?.data?.detail || "Failed to load assets"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const siteName = (id: string) => sites.find(s => s.id === id)?.name || id.slice(0, 8);

  const openCreate = () => { setEditing(null); form.resetFields(); form.setFieldsValue({ status: "active" }); setOpen(true); };
  const openEdit = (r: Asset) => {
    setEditing(r);
    form.setFieldsValue({ ...r, warranty_expiry: r.warranty_expiry ? dayjs(r.warranty_expiry) : undefined });
    setOpen(true);
  };

  const save = async () => {
    const v = await form.validateFields();
    const payload = {
      ...v,
      warranty_expiry: v.warranty_expiry ? v.warranty_expiry.format("YYYY-MM-DD") : null,
      installation_date: v.installation_date ? v.installation_date.format("YYYY-MM-DD") : null,
    };
    setSaving(true);
    try {
      if (editing) {
        const { site_id, installation_date, ...changes } = payload;
        await apiClient.patch(`/assets/${editing.id}`, changes);
      } else {
        await apiClient.post("/assets", payload);
      }
      message.success("Saved"); setOpen(false); load();
    } catch (e: any) { message.error(e?.response?.data?.detail || "Save failed"); }
    finally { setSaving(false); }
  };

  const openDocs = async (asset: Asset) => {
    setDocAsset(asset);
    try { setDocs((await apiClient.get("/documents", { params: { entity_type: "asset", entity_id: asset.id } })).data); }
    catch { setDocs([]); }
  };

  const uploadDoc = async (file: File) => {
    if (!docAsset) return;
    const fd = new FormData();
    fd.append("entity_type", "asset");
    fd.append("entity_id", docAsset.id);
    fd.append("doc_type", docType);
    fd.append("file", file);
    try {
      await apiClient.post("/documents", fd, { headers: { "Content-Type": "multipart/form-data" } });
      message.success("Document uploaded");
      openDocs(docAsset);
    } catch (e: any) { message.error(e?.response?.data?.detail || "Upload failed"); }
    return false; // prevent antd auto-upload
  };

  const columns = [
    { title: "Serial", dataIndex: "serial_number", key: "serial_number", render: (v?: string) => v || "—" },
    { title: "Make/Model", key: "mm", render: (_: unknown, r: Asset) => [r.make, r.model].filter(Boolean).join(" ") || "—" },
    { title: "Type", dataIndex: "asset_type", key: "asset_type", render: (v?: string) => v || "—" },
    { title: "Site", dataIndex: "site_id", key: "site_id", render: siteName },
    { title: "Warranty", dataIndex: "warranty_expiry", key: "warranty", render: warrantyTag },
    { title: "Status", dataIndex: "status", key: "status", render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v.replace(/_/g, " ")}</Tag> },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, r: Asset) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>Edit</Button>
          <Tooltip title="Documents & warranty card">
            <Button size="small" icon={<FileOutlined />} onClick={() => openDocs(r)}>Docs</Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Assets & Warranties</Title>
      </div>
      <Button
        type="primary"
        shape="circle"
        icon={<PlusOutlined />}
        onClick={openCreate}
        size="large"
        style={{
          position: "fixed",
          bottom: 40,
          right: 40,
          width: 56,
          height: 56,
          zIndex: 1000,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "22px"
        }}
        title="Add Asset"
      />
      <Table rowKey="id" columns={columns} dataSource={rows} loading={loading} locale={{ emptyText: "No assets" }} />

      <Modal title={editing ? "Edit Asset" : "Add Asset"} open={open} onOk={save} onCancel={() => setOpen(false)} confirmLoading={saving} okText={editing ? "Save" : "Create"}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {!editing && (
            <Form.Item name="site_id" label="Site" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="children" placeholder="Select site">
                {sites.map(s => <Option key={s.id} value={s.id}>{s.name}</Option>)}
              </Select>
            </Form.Item>
          )}
          <Form.Item name="serial_number" label="Serial Number"><Input /></Form.Item>
          <Space>
            <Form.Item name="make" label="Make"><Input /></Form.Item>
            <Form.Item name="model" label="Model"><Input /></Form.Item>
          </Space>
          <Form.Item name="asset_type" label="Type"><Input placeholder="dome / bullet / DVR / NVR" /></Form.Item>
          {!editing && <Form.Item name="installation_date" label="Installation Date"><DatePicker style={{ width: "100%" }} /></Form.Item>}
          <Form.Item name="warranty_expiry" label="Warranty Expiry"><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item name="status" label="Status"><Select>{STATUSES.map(s => <Option key={s} value={s}>{s.replace(/_/g, " ")}</Option>)}</Select></Form.Item>
          <Form.Item name="location_description" label="Location"><Input /></Form.Item>
        </Form>
      </Modal>

      <Modal title={`Documents — ${docAsset?.serial_number || docAsset?.model || "Asset"}`} open={!!docAsset} footer={null} onCancel={() => setDocAsset(null)}>
        <Space style={{ marginBottom: 12 }}>
          <Select value={docType} onChange={setDocType} style={{ width: 180 }}>
            {DOC_TYPES.map(d => <Option key={d} value={d}>{d.replace(/_/g, " ")}</Option>)}
          </Select>
          <Upload beforeUpload={(f) => uploadDoc(f as File)} showUploadList={false}>
            <Button icon={<UploadOutlined />}>Upload</Button>
          </Upload>
        </Space>
        <List
          dataSource={docs}
          locale={{ emptyText: <span><InboxOutlined /> No documents yet</span> }}
          renderItem={(d) => (
            <List.Item actions={d.url ? [<a key="v" href={d.url} target="_blank" rel="noreferrer">view</a>] : []}>
              <List.Item.Meta avatar={<FileOutlined />} title={d.file_name} description={<Tag>{d.doc_type}</Tag>} />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
}
