import React, { useState, useEffect } from "react";
import { Layout, Button, Input, List, Typography, Space, Drawer, Card } from "antd";
import { 
  MenuUnfoldOutlined, 
  MenuFoldOutlined, 
  ArrowLeftOutlined, 
  SearchOutlined,
  CloseCircleOutlined
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import HelpSidebar from "./HelpSidebar";
import HelpArticle from "./HelpArticle";
import apiClient from "../../api/client";

const { Sider, Content, Header } = Layout;
const { Text, Title } = Typography;

interface FlatArticle {
  title: string;
  slug: string;
}

const HelpCenter: React.FC = () => {
  const navigate = useNavigate();
  const { articleSlug } = useParams<{ articleSlug?: string }>();
  const activeSlug = articleSlug || "introduction";

  // Sidebar responsive layout state
  const [collapsed, setCollapsed] = useState(false);
  const [mobileVisible, setMobileVisible] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Flat menu list for next/prev pagination calculations
  const [flatArticles, setFlatArticles] = useState<FlatArticle[]>([]);

  useEffect(() => {
    const fetchFlatMenu = async () => {
      try {
        const response = await apiClient.get("/help/menu");
        const list: FlatArticle[] = [];
        
        // Traverse tree recursively to build a flat list in tree order
        const traverse = (nodes: any[]) => {
          for (const node of nodes) {
            if (node.subcategories && node.subcategories.length > 0) {
              traverse(node.subcategories);
            }
            if (node.articles && node.articles.length > 0) {
              list.push(...node.articles.map((a: any) => ({ title: a.title, slug: a.slug })));
            }
          }
        };
        traverse(response.data);
        setFlatArticles(list);
      } catch (err) {
        console.error("Error building flat article list", err);
      }
    };
    fetchFlatMenu();
  }, []);

  // Keyboard shortcut Ctrl+K to focus search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        document.getElementById("global-help-search-input")?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSearch = async (val: string) => {
    setSearchQuery(val);
    if (!val || val.trim().length < 2) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }
    setIsSearching(true);
    try {
      const response = await apiClient.get(`/help/search?q=${val}`);
      setSearchResults(response.data);
    } catch (err) {
      console.error("Search failed", err);
    }
  };

  const handleSelectArticle = (slug: string) => {
    navigate(`/help/${slug}`);
    setSearchQuery("");
    setSearchResults([]);
    setIsSearching(false);
    setMobileVisible(false);
  };

  // Find previous and next articles in pagination index
  const activeIndex = flatArticles.findIndex(a => a.slug === activeSlug);
  const prevArticle = activeIndex > 0 ? flatArticles[activeIndex - 1] : null;
  const nextArticle = activeIndex >= 0 && activeIndex < flatArticles.length - 1 ? flatArticles[activeIndex + 1] : null;

  return (
    <Layout style={{ minHeight: "100vh", backgroundColor: "#ffffff" }}>
      {/* Top Header Bar */}
      <Header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "#0F2A43",
          padding: "0 24px",
          height: "64px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          position: "sticky",
          top: 0,
          zIndex: 100
        }}
      >
        <Space size="large">
          <Button
            type="primary"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate("/dashboard")}
            style={{ backgroundColor: "#1e4d75", border: "none" }}
          >
            Back to ERP
          </Button>
          <Title level={4} style={{ color: "#ffffff", margin: 0, fontWeight: "bold" }}>
            Help Center
          </Title>
        </Space>

        {/* Global Help Search Input */}
        <div style={{ position: "relative", width: "400px" }}>
          <Input
            id="global-help-search-input"
            prefix={<SearchOutlined style={{ color: "rgba(255,255,255,0.4)" }} />}
            placeholder="Search help articles... (Ctrl+K)"
            allowClear
            value={searchQuery}
            onChange={e => handleSearch(e.target.value)}
            style={{
              backgroundColor: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "#ffffff"
            }}
          />

          {/* Search Result Overlay Dropdown */}
          {searchQuery && (
            <Card
              style={{
                position: "absolute",
                top: "46px",
                left: 0,
                right: 0,
                zIndex: 200,
                boxShadow: "0 10px 25px rgba(0,0,0,0.15)",
                maxHeight: "450px",
                overflowY: "auto",
                borderRadius: "8px"
              }}
              bodyStyle={{ padding: "12px" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <Text strong>Search Results</Text>
                <Button 
                  type="text" 
                  size="small" 
                  icon={<CloseCircleOutlined />} 
                  onClick={() => { setSearchQuery(""); setSearchResults([]); }}
                  style={{ color: "#ef4444" }}
                />
              </div>

              {searchResults.length > 0 ? (
                <List
                  itemLayout="vertical"
                  dataSource={searchResults}
                  renderItem={item => (
                    <List.Item
                      key={item.id}
                      onClick={() => handleSelectArticle(item.slug)}
                      style={{ cursor: "pointer", padding: "12px", borderBottom: "1px solid #f1f5f9" }}
                      className="search-result-item"
                    >
                      <List.Item.Meta
                        title={
                          <strong style={{ color: "#0F2A43" }} dangerouslySetInnerHTML={{ __html: item.title }} />
                        }
                        description={<Text type="secondary" style={{ fontSize: "11px" }}>Module: {item.applicable_module.toUpperCase()}</Text>}
                      />
                      <div 
                        style={{ fontSize: "13px", color: "#475569" }}
                        dangerouslySetInnerHTML={{ __html: item.snippet }} 
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <div style={{ padding: "20px 0", textAlign: "center" }}>
                  <Text type="secondary">No articles match your query.</Text>
                </div>
              )}
            </Card>
          )}
        </div>
      </Header>

      <Layout>
        {/* Responsive Sider Navigation (Desktop view) */}
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={value => setCollapsed(value)}
          trigger={null}
          width={280}
          breakpoint="lg"
          collapsedWidth={0}
          onBreakpoint={broken => {
            if (broken) {
              setCollapsed(true);
            }
          }}
          style={{
            backgroundColor: "#0b1c2d",
            borderRight: "1px solid #1e293b",
            position: "sticky",
            top: "64px",
            height: "calc(100vh - 64px)"
          }}
        >
          <HelpSidebar onSelectArticle={handleSelectArticle} />
          
          {/* Toggle Sider Collapse trigger */}
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              position: "absolute",
              bottom: "16px",
              right: collapsed ? "-40px" : "16px",
              backgroundColor: collapsed ? "#0b1c2d" : "transparent",
              color: "#ffffff",
              border: collapsed ? "1px solid #1e293b" : "none",
              borderRadius: "4px"
            }}
          />
        </Sider>

        {/* Mobile Navigation Drawer Trigger */}
        <div style={{ display: "none" }} className="mobile-drawer-trigger">
          <Button 
            type="primary" 
            icon={<MenuUnfoldOutlined />} 
            onClick={() => setMobileVisible(true)}
            style={{ position: "fixed", left: "16px", bottom: "16px", zIndex: 100 }}
          />
        </div>

        {/* Mobile Navigation Drawer */}
        <Drawer
          placement="left"
          onClose={() => setMobileVisible(false)}
          open={mobileVisible}
          bodyStyle={{ padding: 0, backgroundColor: "#0b1c2d" }}
          width={280}
        >
          <HelpSidebar onSelectArticle={handleSelectArticle} />
        </Drawer>

        {/* Main Document Content Panel */}
        <Content style={{ backgroundColor: "#ffffff", overflowY: "auto", height: "calc(100vh - 64px)" }}>
          <HelpArticle 
            slug={activeSlug} 
            onNavigate={handleSelectArticle}
            prevArticle={prevArticle}
            nextArticle={nextArticle}
          />
        </Content>
      </Layout>

      {/* Styled css rule to inject trigger details */}
      <style>{`
        @media (max-width: 992px) {
          .mobile-drawer-trigger {
            display: block !important;
          }
        }
        .search-result-item:hover {
          background-color: #f8fafc !important;
        }
        mark {
          background-color: #fef08a;
          color: #854d0e;
          padding: 0 2px;
          border-radius: 2px;
          font-weight: bold;
        }
      `}</style>
    </Layout>
  );
};

export default HelpCenter;
