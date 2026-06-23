import { useEffect, useState, useCallback } from "react";
import {
  Card, Descriptions, Tag, Button, Input, List, Typography, Space, message, Spin, Result,
} from "antd";
import { ArrowLeftOutlined, SendOutlined } from "@ant-design/icons";
import { useParams, useNavigate } from "react-router-dom";
import portalClient from "../../api/portalClient";

const { Title } = Typography;

const statusColor: Record<string, string> = {
  open: "blue", assigned: "cyan", in_progress: "gold", pending_parts: "orange",
  resolved: "green", closed: "default",
};

interface Comment { id: string; body: string; created_at?: string }
interface Ticket {
  id: string; ticket_number: string; status: string; priority: string;
  complaint: string; resolution_notes?: string | null; created_at?: string; comments: Comment[];
}

export default function PortalTicketDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [comment, setComment] = useState("");
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await portalClient.get(`/tickets/${id}`);
      setTicket(data);
    } catch (e: any) {
      if (e?.response?.status === 404) setNotFound(true);
      else message.error(e?.response?.data?.detail || "Failed to load ticket");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const postComment = async () => {
    if (!comment.trim()) return;
    setPosting(true);
    try {
      await portalClient.post(`/tickets/${id}/comments`, { body: comment.trim() });
      setComment("");
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to post comment");
    } finally {
      setPosting(false);
    }
  };

  if (loading) return <Spin style={{ display: "block", margin: "80px auto" }} />;
  if (notFound) return <Result status="404" title="Ticket not found"
    extra={<Button onClick={() => navigate("/portal/tickets")}>Back to tickets</Button>} />;
  if (!ticket) return null;

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/portal/tickets")}>Back</Button>
        <Title level={4} style={{ margin: 0 }}>{ticket.ticket_number}</Title>
        <Tag color={statusColor[ticket.status] ?? "default"}>{ticket.status.replace("_", " ")}</Tag>
      </Space>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="Complaint">{ticket.complaint}</Descriptions.Item>
          <Descriptions.Item label="Priority"><Tag>{ticket.priority}</Tag></Descriptions.Item>
          {ticket.resolution_notes && (
            <Descriptions.Item label="Resolution">{ticket.resolution_notes}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title="Updates & Comments">
        <List
          dataSource={ticket.comments}
          locale={{ emptyText: "No updates yet" }}
          renderItem={(c) => (
            <List.Item>
              <List.Item.Meta
                title={c.created_at ? new Date(c.created_at).toLocaleString("en-IN") : ""}
                description={c.body} />
            </List.Item>
          )}
        />
        <Space.Compact style={{ width: "100%", marginTop: 16 }}>
          <Input value={comment} onChange={(e) => setComment(e.target.value)}
            onPressEnter={postComment} placeholder="Add a comment…" />
          <Button type="primary" icon={<SendOutlined />} loading={posting} onClick={postComment}>Send</Button>
        </Space.Compact>
      </Card>
    </div>
  );
}
