import React, { useState, useEffect } from "react";
import { Input, Menu, Typography, Space, Spin } from "antd";
import { 
  BookOutlined, 
  SearchOutlined, 
  FolderOutlined, 
  FileTextOutlined, 
  FolderOpenOutlined 
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../../api/client";

const { Text } = Typography;

interface ArticleItem {
  id: string;
  title: string;
  slug: string;
  applicable_module: string;
}

interface CategoryNode {
  id: string;
  name: string;
  slug: string;
  icon?: string;
  articles: ArticleItem[];
  subcategories: CategoryNode[];
}

interface HelpSidebarProps {
  onSelectArticle: (slug: string) => void;
}

const HelpSidebar: React.FC<HelpSidebarProps> = ({ onSelectArticle }) => {
  const navigate = useNavigate();
  const { articleSlug } = useParams<{ articleSlug?: string }>();
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [openKeys, setOpenKeys] = useState<string[]>([]);

  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const response = await apiClient.get("/help/menu");
        setCategories(response.data);
        // Automatically expand the category of the active article if open
        if (articleSlug) {
          const findCategoryKeys = (nodes: CategoryNode[], activeSlug: string, path: string[] = []): string[] | null => {
            for (const node of nodes) {
              const hasArticle = node.articles.some(a => a.slug === activeSlug);
              if (hasArticle) return [...path, node.id];
              const subPath = findCategoryKeys(node.subcategories, activeSlug, [...path, node.id]);
              if (subPath) return subPath;
            }
            return null;
          };
          const keys = findCategoryKeys(response.data, articleSlug);
          if (keys) setOpenKeys(keys);
        }
      } catch (error) {
        console.error("Error loading help menu", error);
      } finally {
        setLoading(false);
      }
    };
    fetchMenu();
  }, [articleSlug]);

  const handleMenuClick = (info: any) => {
    if (info.key) {
      onSelectArticle(info.key);
      navigate(`/help/${info.key}`);
    }
  };

  // Filter tree based on search query
  const getFilteredMenu = (nodes: CategoryNode[], query: string): CategoryNode[] => {
    if (!query) return nodes;

    const lowerQuery = query.toLowerCase();

    return nodes
      .map(node => {
        const filteredArticles = node.articles.filter(art => 
          art.title.toLowerCase().includes(lowerQuery)
        );
        const filteredSub = getFilteredMenu(node.subcategories, query);

        if (
          node.name.toLowerCase().includes(lowerQuery) || 
          filteredArticles.length > 0 || 
          filteredSub.length > 0
        ) {
          return {
            ...node,
            articles: filteredArticles,
            subcategories: filteredSub
          };
        }
        return null;
      })
      .filter((node): node is CategoryNode => node !== null);
  };

  const filteredCategories = getFilteredMenu(categories, searchQuery);

  // Generate Ant Design menu items
  const renderMenuItems = (nodes: CategoryNode[]): any[] => {
    return nodes.map(node => {
      const children: any[] = [];

      // Subcategories
      if (node.subcategories.length > 0) {
        children.push(...renderMenuItems(node.subcategories));
      }

      // Articles
      if (node.articles.length > 0) {
        children.push(
          ...node.articles.map(art => ({
            key: art.slug,
            label: art.title,
            icon: <FileTextOutlined style={{ fontSize: "14px" }} />
          }))
        );
      }

      return {
        key: node.id,
        label: (
          <Text strong style={{ color: "#eef2f5" }}>
            {node.name}
          </Text>
        ),
        icon: openKeys.includes(node.id) ? <FolderOpenOutlined /> : <FolderOutlined />,
        children: children.length > 0 ? children : undefined
      };
    });
  };

  const menuItems = renderMenuItems(filteredCategories);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}>
        <Spin size="medium" />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Sidebar Header */}
      <div style={{ padding: "16px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
        <Space size="middle" style={{ marginBottom: "12px" }}>
          <BookOutlined style={{ fontSize: "20px", color: "#38bdf8" }} />
          <Text strong style={{ color: "#ffffff", fontSize: "16px" }}>
            Documentation
          </Text>
        </Space>
        <Input
          prefix={<SearchOutlined style={{ color: "rgba(255,255,255,0.45)" }} />}
          placeholder="Filter tree..."
          allowClear
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          style={{
            backgroundColor: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.12)",
            color: "#ffffff"
          }}
        />
      </div>

      {/* Navigation Tree */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
        {menuItems.length > 0 ? (
          <Menu
            mode="inline"
            theme="dark"
            openKeys={openKeys}
            onOpenChange={keys => setOpenKeys(keys)}
            selectedKeys={articleSlug ? [articleSlug] : []}
            onClick={handleMenuClick}
            style={{ backgroundColor: "transparent", borderRight: "none" }}
            items={menuItems}
          />
        ) : (
          <div style={{ padding: "24px", textAlign: "center" }}>
            <Text type="secondary" style={{ color: "rgba(255,255,255,0.4)" }}>
              No matches found
            </Text>
          </div>
        )}
      </div>
    </div>
  );
};

export default HelpSidebar;
