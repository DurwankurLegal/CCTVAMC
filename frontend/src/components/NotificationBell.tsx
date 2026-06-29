import { useEffect, useState, useCallback } from "react";
import { Badge, Dropdown, Button, List, Typography, Empty, theme } from "antd";
import { BellOutlined } from "@ant-design/icons";
import apiClient from "../api/client";

const { Text } = Typography;

interface Note {
  id: string; event_type: string; subject?: string; body?: string;
  read_at?: string | null; created_at?: string;
}

export default function NotificationBell() {
  const { token } = theme.useToken();
  const [items, setItems] = useState<Note[]>([]);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await apiClient.get("/notifications", { params: { limit: 20 } });
      setItems(data);
    } catch { /* silent — bell is non-critical */ }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000); // poll once a minute
    return () => clearInterval(t);
  }, [load]);

  const unread = items.filter((n) => !n.read_at).length;

  const markRead = async (id: string) => {
    try {
      await apiClient.post(`/notifications/${id}/read`);
      setItems((prev) => prev.map((n) => n.id === id ? { ...n, read_at: new Date().toISOString() } : n));
    } catch { /* ignore */ }
  };

  const content = (
    <div style={{ 
      width: 340, 
      maxHeight: 420, 
      overflow: "auto", 
      background: token.colorBgContainer, 
      border: `1px solid ${token.colorBorder}`,
      borderRadius: 8, 
      boxShadow: token.boxShadowSecondary || "0 6px 16px rgba(0,0,0,0.12)" 
    }}>
      <div style={{ 
        padding: "10px 16px", 
        borderBottom: `1px solid ${token.colorBorderSecondary}`, 
        fontWeight: 600,
        color: token.colorText
      }}>
        Notifications
      </div>
      {items.length === 0
        ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No notifications" style={{ padding: 24 }} />
        : (
          <List
            dataSource={items}
            renderItem={(n) => (
              <List.Item
                style={{ 
                  padding: "10px 16px", 
                  cursor: "pointer", 
                  background: n.read_at ? undefined : token.colorFillAlter,
                  borderBottom: `1px solid ${token.colorBorderSecondary}`
                }}
                onClick={() => !n.read_at && markRead(n.id)}
              >
                <List.Item.Meta
                  title={<Text strong={!n.read_at} style={{ color: token.colorText }}>{n.subject || n.event_type.replace(/_/g, " ")}</Text>}
                  description={<span style={{ fontSize: 12, color: token.colorTextDescription }}>{n.body}</span>}
                />
              </List.Item>
            )}
          />
        )}
    </div>
  );

  return (
    <Dropdown open={open} onOpenChange={setOpen} trigger={["click"]}
      dropdownRender={() => content} placement="bottomRight">
      <Badge count={unread} size="small" offset={[-2, 4]}>
        <Button type="text" icon={<BellOutlined style={{ fontSize: 18, color: "#fff" }} />} />
      </Badge>
    </Dropdown>
  );
}
