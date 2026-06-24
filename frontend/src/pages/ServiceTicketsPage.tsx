import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Typography, Space, message, Radio, Card, List, Tooltip, Row, Col, Tabs, Upload, ConfigProvider, theme } from "antd";
import { PlusOutlined, EditOutlined, AppstoreOutlined, UnorderedListOutlined, MessageOutlined, FileOutlined, SendOutlined, UploadOutlined, InboxOutlined, ToolOutlined } from "@ant-design/icons";

import { useDispatch, useSelector } from "react-redux";
import { fetchTickets } from "../store/ticketSlice";
import { fetchCustomers } from "../store/customerSlice";
import apiClient from "../api/client";
import type { AppDispatch, RootState } from "../store";
import { useSearchParams } from "react-router-dom";

const { Title, Text } = Typography;
const { Option } = Select;

interface Ticket {
  id: string;
  ticket_number: string;
  customer_id: string;
  status: string;
  priority: string;
  complaint: string;
  resolution_notes?: string | null;
  sla_breached: boolean;
}

const STATUSES = ["open", "assigned", "in_progress", "pending_parts", "resolved", "closed"];
const PRIORITIES = ["low", "medium", "high", "critical"];

export default function ServiceTicketsPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { items, loading } = useSelector((s: RootState) => s.tickets);
  const customers = useSelector((s: RootState) => s.customers.items);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Ticket | null>(null);
  const [form] = Form.useForm();
  
  const [viewMode, setViewMode] = useState<"table" | "kanban">("table");

  // Filters State
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<string | null>(null);
  const [slaFilter, setSlaFilter] = useState<string | null>(null);

  // Drag and drop state
  const [draggedOverColumn, setDraggedOverColumn] = useState<string | null>(null);

  // Comments state
  const [comments, setComments] = useState<any[]>([]);
  const [commentText, setCommentText] = useState("");
  const [postingComment, setPostingComment] = useState(false);
  const [loadingComments, setLoadingComments] = useState(false);

  // Docs state
  const [docs, setDocs] = useState<any[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [docType, setDocType] = useState("other");
  const [uploadingDoc, setUploadingDoc] = useState(false);

  const [activeTab, setActiveTab] = useState<string>("comments");

  const loadComments = async (ticketId: string) => {
    setLoadingComments(true);
    try {
      const { data } = await apiClient.get(`/service-tickets/${ticketId}/comments`);
      setComments(data);
    } catch {
      setComments([]);
    } finally {
      setLoadingComments(false);
    }
  };

  const postComment = async () => {
    if (!editing || !commentText.trim()) return;
    setPostingComment(true);
    try {
      await apiClient.post(`/service-tickets/${editing.id}/comments`, { body: commentText.trim() });
      setCommentText("");
      loadComments(editing.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to post comment");
    } finally {
      setPostingComment(false);
    }
  };

  const loadDocs = async (ticketId: string) => {
    setLoadingDocs(true);
    try {
      const { data } = await apiClient.get("/documents", {
        params: { entity_type: "ticket", entity_id: ticketId }
      });
      setDocs(data);
    } catch {
      setDocs([]);
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleUploadDoc = async (file: File) => {
    if (!editing) return false;
    setUploadingDoc(true);
    const fd = new FormData();
    fd.append("entity_type", "ticket");
    fd.append("entity_id", editing.id);
    fd.append("doc_type", docType);
    fd.append("file", file);
    try {
      await apiClient.post("/documents", fd, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      message.success("Document uploaded");
      loadDocs(editing.id);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Upload failed");
    } finally {
      setUploadingDoc(false);
    }
    return false;
  };

  const [searchParams] = useSearchParams();
  const statusParam = searchParams.get("status");
  const priorityParam = searchParams.get("priority");
  const slaParam = searchParams.get("sla");

  useEffect(() => {
    dispatch(fetchTickets());
    dispatch(fetchCustomers());
  }, [dispatch]);

  const filteredItems = items.filter(item => {
    // 1. Search text filter (matches ticket number, complaint, or customer name)
    if (searchText.trim()) {
      const query = searchText.toLowerCase();
      const matchNo = item.ticket_number.toLowerCase().includes(query);
      const matchComplaint = item.complaint.toLowerCase().includes(query);
      const customerName = customers.find(c => c.id === item.customer_id)?.name || "";
      const matchCustomer = customerName.toLowerCase().includes(query);
      if (!matchNo && !matchComplaint && !matchCustomer) return false;
    }
    // 2. Status filter
    if (statusFilter && item.status !== statusFilter) return false;
    // 3. Priority filter
    if (priorityFilter && item.priority !== priorityFilter) return false;
    // 4. SLA filter
    if (slaFilter) {
      if (slaFilter === "breached" && !item.sla_breached) return false;
      if (slaFilter === "ok" && item.sla_breached) return false;
    }
    // 5. URL search params fallback / override (if specified)
    if (statusParam && item.status !== statusParam) return false;
    if (priorityParam && item.priority !== priorityParam) return false;
    if (slaParam) {
      const isBreached = slaParam === "breached";
      if (item.sla_breached !== isBreached) return false;
    }
    return true;
  });

  const openCreate = () => { 
    setEditing(null); 
    form.resetFields(); 
    form.setFieldsValue({ priority: "medium" }); 
    setOpen(true); 
  };
  const openEdit = (row: Ticket, tab: string = "comments") => { 
    setEditing(row); 
    form.setFieldsValue(row); 
    setActiveTab(tab); 
    setOpen(true); 
    loadComments(row.id);
    loadDocs(row.id);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await apiClient.patch(`/service-tickets/${editing.id}`, {
          status: values.status, priority: values.priority, resolution_notes: values.resolution_notes,
        });
        message.success("Ticket updated");
      } else {
        await apiClient.post("/service-tickets", values);
        message.success("Ticket raised");
      }
      form.resetFields();
      setOpen(false);
      dispatch(fetchTickets());
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const updateTicketStatus = async (ticketId: string, newStatus: string) => {
    try {
      await apiClient.patch(`/service-tickets/${ticketId}`, { status: newStatus });
      message.success("Ticket status updated");
      dispatch(fetchTickets());
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to update status");
    }
  };

  // Drag handlers
  const handleDragStart = (e: React.DragEvent, ticketId: string) => {
    e.dataTransfer.setData("text/plain", ticketId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent, status: string) => {
    e.preventDefault();
    setDraggedOverColumn(status);
  };

  const handleDragLeave = () => {
    setDraggedOverColumn(null);
  };

  const handleDrop = async (e: React.DragEvent, status: string) => {
    e.preventDefault();
    setDraggedOverColumn(null);
    const ticketId = e.dataTransfer.getData("text/plain");
    if (ticketId) {
      await updateTicketStatus(ticketId, status);
    }
  };

  const priorityColor: Record<string, string> = { low: "blue", medium: "orange", high: "red", critical: "purple" };
  const statusColor: Record<string, string> = {
    open: "blue", assigned: "cyan", in_progress: "orange", pending_parts: "gold", resolved: "green", closed: "default",
  };

  const columns = [
    { 
      title: "Ticket #", 
      key: "ticket_number",
      render: (_: any, row: Ticket) => (
        <span style={{ fontWeight: 600, color: "#3b82f6" }}>{row.ticket_number}</span>
      )
    },
    {
      title: "Customer",
      dataIndex: "customer_id",
      key: "customer",
      render: (v: string) => customers.find(c => c.id === v)?.name || "—",
    },
    {
      title: "Status", dataIndex: "status", key: "status",
      render: (v: string) => <Tag color={statusColor[v] ?? "default"}>{v.replace("_", " ")}</Tag>,
    },
    {
      title: "Priority", dataIndex: "priority", key: "priority",
      render: (v: string) => <Tag color={priorityColor[v] ?? "default"}>{v}</Tag>,
    },
    { title: "Complaint", dataIndex: "complaint", key: "complaint", ellipsis: true },
    {
      title: "SLA", dataIndex: "sla_breached", key: "sla_breached",
      render: (v: boolean) => v ? <Tag color="red">Breached</Tag> : <Tag color="green">OK</Tag>,
    },
    {
      title: "Actions", key: "actions",
      render: (_: unknown, row: Ticket) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row, "comments")}>Edit</Button>
          <Tooltip title="Comments">
            <Button 
              size="small" 
              icon={<MessageOutlined />} 
              onClick={() => openEdit(row, "comments")}
            />
          </Tooltip>
          <Tooltip title="Docs & Attachments">
            <Button 
              size="small" 
              icon={<FileOutlined />} 
              onClick={() => openEdit(row, "docs")}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const renderKanbanBoard = () => {
    const getTicketsByStatus = (status: string) => filteredItems.filter(t => t.status === status);
    
    return (
      <div style={{ display: "flex", gap: "16px", overflowX: "auto", paddingBottom: "16px", minHeight: "450px" }}>
        {STATUSES.map(status => {
          const columnTickets = getTicketsByStatus(status);
          return (
            <div 
              key={status} 
              className="glass-card" 
              onDragOver={(e) => handleDragOver(e, status)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, status)}
              style={{ 
                flex: "0 0 280px", 
                display: "flex", 
                flexDirection: "column", 
                gap: "12px", 
                padding: "16px",
                background: draggedOverColumn === status ? "rgba(59, 130, 246, 0.15)" : "rgba(22, 28, 45, 0.4)",
                border: draggedOverColumn === status ? "1px dashed #3b82f6" : "1px solid rgba(255, 255, 255, 0.05)",
                borderRadius: "8px",
                transition: "all 0.2s"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, textTransform: "capitalize", color: "#f3f4f6", fontSize: "13px" }}>
                  {status.replace("_", " ")}
                </span>
                <Tag color="blue" style={{ margin: 0 }}>{columnTickets.length}</Tag>
              </div>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto", flex: 1 }}>
                {columnTickets.map(ticket => (
                  <Card
                    key={ticket.id}
                    size="small"
                    className="interactive-table-row"
                    draggable
                    onDragStart={(e) => handleDragStart(e, ticket.id)}
                    styles={{
                      body: { padding: "12px" }
                    }}
                    style={{ 
                      background: "rgba(11, 15, 25, 0.6)", 
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      borderRadius: "8px",
                      cursor: "grab"
                    }}
                    onClick={() => openEdit(ticket)}
                  >
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontWeight: 600, color: "#3b82f6", fontSize: "11px" }}>
                          {ticket.ticket_number}
                        </span>
                        <Tag color={priorityColor[ticket.priority]} style={{ fontSize: "10px", margin: 0 }}>
                          {ticket.priority}
                        </Tag>
                      </div>
                      <div style={{ fontSize: "11px", color: "#9ca3af", fontWeight: 500 }}>
                        {customers.find(c => c.id === ticket.customer_id)?.name || "—"}
                      </div>
                      <span style={{ color: "#f3f4f6", fontSize: "12px", lineHeight: "1.4" }}>
                        {ticket.complaint}
                      </span>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
                        {ticket.sla_breached ? (
                          <Tag color="red" style={{ fontSize: "9px", margin: 0 }}>
                            SLA Breached
                          </Tag>
                        ) : (
                          <span />
                        )}
                        <Space onClick={e => e.stopPropagation()}>
                          <Tooltip title="Comments">
                            <Button 
                              size="small" 
                              type="text" 
                              icon={<MessageOutlined />} 
                              onClick={() => openEdit(ticket, "comments")} 
                              style={{ color: "#9ca3af", height: 22, width: 22, display: "flex", alignItems: "center", justifyContent: "center" }} 
                            />
                          </Tooltip>
                          <Tooltip title="Attachments">
                            <Button 
                              size="small" 
                              type="text" 
                              icon={<FileOutlined />} 
                              onClick={() => openEdit(ticket, "docs")} 
                              style={{ color: "#9ca3af", height: 22, width: 22, display: "flex", alignItems: "center", justifyContent: "center" }} 
                            />
                          </Tooltip>
                        </Space>
                      </div>
                    </div>
                  </Card>
                ))}
                {columnTickets.length === 0 && (
                  <div style={{ textAlign: "center", color: "#6b7280", padding: "32px 0", fontSize: "12px" }}>
                    No tickets
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorBgContainer: "#161c2d",
          colorBorder: "rgba(255, 255, 255, 0.08)",
          colorText: "#f3f4f6",
          colorTextSecondary: "#9ca3af",
          colorTextHeading: "#ffffff",
          colorPrimary: "#3b82f6",
        },
        components: {
          Table: {
            headerBg: "rgba(255, 255, 255, 0.04)",
            headerColor: "#f3f4f6",
          }
        }
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 4 }}>
          <div>
            <Title level={4} style={{ margin: 0, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
              <ToolOutlined style={{ color: "#3b82f6" }} />
              <span className="gradient-text" style={{ background: "linear-gradient(90deg, #c084fc 0%, #60a5fa 50%, #34d399 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Service Tickets Hub
              </span>
            </Title>
            <Text style={{ color: "#9ca3af", fontSize: "13.5px" }}>
              Log customer complaints, allocate technicians, check SLA performance compliance, and register comments.
            </Text>
          </div>
          <Space>
            <Radio.Group value={viewMode} onChange={e => setViewMode(e.target.value)} size="small">
              <Radio.Button value="table"><UnorderedListOutlined /> Table</Radio.Button>
              <Radio.Button value="kanban"><AppstoreOutlined /> Kanban</Radio.Button>
            </Radio.Group>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)", border: "none", color: "#fff" }}>Raise Ticket</Button>
          </Space>
        </div>

        {/* Search and Filters Bar */}
        <Card 
          className="glass-card"
          style={{ 
            marginBottom: 0
          }}
          styles={{
            body: { padding: "16px 20px" }
          }}
        >
        <Space wrap size={16}>
          <Input 
            placeholder="Search tickets, complaints..." 
            value={searchText} 
            onChange={e => setSearchText(e.target.value)} 
            style={{ width: 220 }} 
            allowClear
          />
          <Select 
            placeholder="Filter by Status" 
            value={statusFilter} 
            onChange={setStatusFilter} 
            style={{ width: 160 }} 
            allowClear
          >
            {STATUSES.map(s => (
              <Option key={s} value={s}>{s.replace("_", " ").toUpperCase()}</Option>
            ))}
          </Select>
          <Select 
            placeholder="Filter by Priority" 
            value={priorityFilter} 
            onChange={setPriorityFilter} 
            style={{ width: 140 }} 
            allowClear
          >
            {PRIORITIES.map(p => (
              <Option key={p} value={p}>{p.toUpperCase()}</Option>
            ))}
          </Select>
          <Select 
            placeholder="SLA Compliance" 
            value={slaFilter} 
            onChange={setSlaFilter} 
            style={{ width: 160 }} 
            allowClear
          >
            <Option value="ok">SLA OK</Option>
            <Option value="breached">SLA Breached</Option>
          </Select>
          <Button 
            onClick={() => {
              setSearchText("");
              setStatusFilter(null);
              setPriorityFilter(null);
              setSlaFilter(null);
            }}
          >
            Reset Filters
          </Button>
        </Space>
      </Card>

      {viewMode === "table" ? (
        <Card
          id="tickets-ledger-panel"
          className="glass-card"
          styles={{
            header: {
              background: "linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0.02) 100%)",
              borderBottom: "1px solid rgba(59, 130, 246, 0.15)",
              borderRadius: "12px 12px 0 0"
            },
            body: { padding: 0 }
          }}
          title={
            <Space>
              <ToolOutlined style={{ color: "#3b82f6", fontSize: 18 }} />
              <span style={{ color: "#f3f4f6", fontWeight: 700, fontSize: 15 }}>
                Active Service Tickets Ledger
              </span>
              <Tag color="blue" style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, background: "rgba(59, 130, 246, 0.12)", border: "1px solid rgba(59, 130, 246, 0.2)" }}>
                TICKETS LEDGER
              </Tag>
            </Space>
          }
        >
          <Table rowKey="id" columns={columns} dataSource={filteredItems} loading={loading} />
        </Card>
      ) : (
        renderKanbanBoard()
      )}

      <Modal
        title={editing ? `Edit ${editing.ticket_number}` : "Raise Service Ticket"}
        open={open} 
        onOk={handleSave} 
        onCancel={() => setOpen(false)} 
        confirmLoading={saving}
        okText={editing ? "Save" : "Create"}
        width={editing ? 950 : 520}
      >
        {editing ? (
          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
                <Form.Item name="status" label="Status">
                  <Select>{STATUSES.map(s => <Option key={s} value={s}>{s.replace("_", " ")}</Option>)}</Select>
                </Form.Item>
                <Form.Item name="priority" label="Priority">
                  <Select>{PRIORITIES.map(p => <Option key={p} value={p}>{p}</Option>)}</Select>
                </Form.Item>
                <Form.Item name="complaint" label="Complaint / Description">
                  <Input.TextArea rows={3} disabled />
                </Form.Item>
                <Form.Item name="resolution_notes" label="Resolution Notes">
                  <Input.TextArea rows={3} />
                </Form.Item>
              </Form>
            </Col>
            <Col xs={24} md={12} style={{ marginTop: 16 }}>
              <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
                {
                  key: "comments",
                  label: `Comments (${comments.length})`,
                  children: (
                    <div>
                      <div style={{ 
                        maxHeight: "260px", 
                        overflowY: "auto", 
                        marginBottom: "12px", 
                        padding: "8px", 
                        background: "rgba(255, 255, 255, 0.02)", 
                        borderRadius: "8px",
                        border: "1px solid rgba(255, 255, 255, 0.05)"
                      }}>
                        <List
                          loading={loadingComments}
                          dataSource={comments}
                          locale={{ emptyText: "No comments yet" }}
                          size="small"
                          renderItem={(c: any) => (
                            <List.Item style={{ padding: "8px 0" }}>
                              <List.Item.Meta
                                title={<span style={{ fontSize: "11px", color: "#9ca3af" }}>{c.created_at ? new Date(c.created_at).toLocaleString("en-IN") : ""}</span>}
                                description={<span style={{ color: "#f3f4f6", fontSize: "13px" }}>{c.body}</span>}
                              />
                            </List.Item>
                          )}
                        />
                      </div>
                      <Space.Compact style={{ width: "100%" }}>
                        <Input value={commentText} onChange={e => setCommentText(e.target.value)} onPressEnter={postComment} placeholder="Add a comment…" />
                        <Button type="primary" icon={<SendOutlined />} loading={postingComment} onClick={postComment}>Send</Button>
                      </Space.Compact>
                    </div>
                  )
                },
                {
                  key: "docs",
                  label: `Docs & Attachments (${docs.length})`,
                  children: (
                    <div>
                      <Space style={{ marginBottom: 12 }} wrap>
                        <Select value={docType} onChange={setDocType} style={{ width: 140 }} size="small">
                          {["contract", "invoice", "receipt", "audit", "warranty", "photo", "other"].map(d => (
                            <Option key={d} value={d}>{d.toUpperCase()}</Option>
                          ))}
                        </Select>
                        <Upload beforeUpload={(f) => handleUploadDoc(f as File)} showUploadList={false}>
                          <Button size="small" icon={<UploadOutlined />} loading={uploadingDoc}>Upload</Button>
                        </Upload>
                      </Space>
                      <div style={{ 
                        maxHeight: "260px", 
                        overflowY: "auto", 
                        padding: "8px", 
                        background: "rgba(255, 255, 255, 0.02)", 
                        borderRadius: "8px",
                        border: "1px solid rgba(255, 255, 255, 0.05)"
                      }}>
                        <List
                          loading={loadingDocs}
                          dataSource={docs}
                          locale={{ emptyText: <span><InboxOutlined /> No documents yet</span> }}
                          size="small"
                          renderItem={(d: any) => (
                            <List.Item
                              style={{ padding: "8px 0" }}
                              actions={d.url ? [<a key="v" href={d.url} target="_blank" rel="noreferrer" style={{ fontSize: "12px" }}>View</a>] : []}
                            >
                              <List.Item.Meta
                                avatar={<FileOutlined style={{ fontSize: "16px", marginTop: "4px" }} />}
                                title={<span style={{ fontSize: "13px", color: "#f3f4f6" }}>{d.file_name}</span>}
                                description={<Tag style={{ fontSize: "10px", lineHeight: "14px" }}>{d.doc_type.toUpperCase()}</Tag>}
                              />
                            </List.Item>
                          )}
                        />
                      </div>
                    </div>
                  )
                }
              ]} />
            </Col>
          </Row>
        ) : (
          <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item name="customer_id" label="Customer" rules={[{ required: true }]}>
              <Select showSearch optionFilterProp="children" placeholder="Select customer">
                {customers.map(c => <Option key={c.id} value={c.id}>{c.name}</Option>)}
              </Select>
            </Form.Item>
            <Form.Item name="priority" label="Priority">
              <Select>{PRIORITIES.map(p => <Option key={p} value={p}>{p}</Option>)}</Select>
            </Form.Item>
            <Form.Item name="complaint" label="Complaint / Description" rules={[{ required: true }]}>
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        )}
      </Modal>
      </div>
    </ConfigProvider>
  );
}
