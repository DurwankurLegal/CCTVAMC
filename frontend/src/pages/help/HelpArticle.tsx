import React, { useState, useEffect } from "react";
import { 
  Typography, 
  Card, 
  Button, 
  Space, 
  Tag, 
  Divider, 
  Rate, 
  Input, 
  message, 
  Collapse, 
  Tooltip,
  Alert,
  List,
  Spin
} from "antd";
import { 
  StarOutlined, 
  StarFilled, 
  PrinterOutlined, 
  LinkOutlined, 
  FilePdfOutlined, 
  LikeOutlined, 
  DislikeOutlined,
  PlayCircleOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  LockOutlined,
  InfoCircleOutlined,
  WarningOutlined
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import apiClient from "../../api/client";
import { copyToClipboard } from "../../utils/clipboard";

const { Title, Paragraph, Text } = Typography;
const { Panel } = Collapse;

interface FAQItem {
  id: string;
  question: string;
  answer: string;
}

interface AttachmentItem {
  id: string;
  file_name: string;
  file_type: string;
  url: string;
}

interface ArticleData {
  id: string;
  title: string;
  slug: string;
  purpose: string;
  prerequisites: string;
  content_markdown: string;
  applicable_module: string;
  version: string;
  updated_at: string;
  faqs: FAQItem[];
  attachments: AttachmentItem[];
}

interface HelpArticleProps {
  slug: string;
  onNavigate: (slug: string) => void;
  nextArticle?: { title: string; slug: string } | null;
  prevArticle?: { title: string; slug: string } | null;
}

const HelpArticle: React.FC<HelpArticleProps> = ({ slug, onNavigate, nextArticle, prevArticle }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [article, setArticle] = useState<ArticleData | null>(null);
  
  // Bookmarks & Feedback states
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [ratingSubmitted, setRatingSubmitted] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState<number | null>(null);
  const [feedbackComments, setFeedbackComments] = useState("");
  const [isOutdated, setIsOutdated] = useState(false);
  const [attachmentBlobUrls, setAttachmentBlobUrls] = useState<Record<string, string>>({});

  useEffect(() => {
    const fetchArticle = async () => {
      setLoading(true);
      setErrorStatus(null);
      setRatingSubmitted(false);
      setFeedbackRating(null);
      setFeedbackComments("");
      setIsOutdated(false);
      try {
        const response = await apiClient.get(`/help/articles/${slug}`);
        const data: ArticleData = response.data;
        setArticle(data);

        // Prefetch attachments as secure blobs
        const urlsMap: Record<string, string> = {};
        await Promise.all(
          data.attachments.map(async (att) => {
            try {
              const res = await apiClient.get(`/help/attachments/${att.id}/download`, {
                responseType: "blob"
              });
              const contentType = (res.headers["content-type"] as string) || "application/octet-stream";
              const blob = new Blob([res.data], { type: contentType });
              urlsMap[att.id] = window.URL.createObjectURL(blob);
            } catch (err) {
              console.error("Failed to load attachment blob for", att.file_name, err);
            }
          })
        );
        setAttachmentBlobUrls(urlsMap);
        
        // Fetch bookmarks to see if this one is saved
        const bResponse = await apiClient.get("/help/bookmarks");
        const bookmarked = bResponse.data.some((b: any) => b.slug === slug);
        setIsBookmarked(bookmarked);
      } catch (err: any) {
        console.error("Error fetching article", err);
        setErrorStatus(err?.response?.status || 500);
      } finally {
        setLoading(false);
      }
    };
    if (slug) fetchArticle();

    return () => {
      setAttachmentBlobUrls((prev) => {
        Object.values(prev).forEach((url) => window.URL.revokeObjectURL(url));
        return {};
      });
    };
  }, [slug]);

  const handleBookmarkToggle = async () => {
    if (!article) return;
    try {
      const { data } = await apiClient.post(`/help/articles/${article.id}/bookmark`);
      setIsBookmarked(data.bookmarked);
      message.success(data.bookmarked ? "Bookmarked article" : "Removed bookmark");
    } catch {
      message.error("Failed to toggle bookmark");
    }
  };

  const handleFeedbackSubmit = async () => {
    if (!article || !feedbackRating) return;
    try {
      await apiClient.post(`/help/articles/${article.id}/feedback`, {
        rating: feedbackRating,
        comments: feedbackComments,
        is_outdated: isOutdated
      });
      setRatingSubmitted(true);
      message.success("Thank you for your feedback!");
    } catch {
      message.error("Failed to submit feedback");
    }
  };

  const handleCopyLink = async () => {
    const ok = await copyToClipboard(window.location.href);
    if (ok) {
      message.success("Article link copied to clipboard!");
    } else {
      message.error("Failed to copy link");
    }
  };

  // Helper to convert Markdown to structured elements
  const parseMarkdown = (markdown: string) => {
    const lines = markdown.split("\n");
    const elements: React.ReactNode[] = [];
    
    let inQuote = false;
    let quoteType: "note" | "tip" | "warning" | "info" = "info";
    let quoteLines: string[] = [];
    
    const flushQuote = (keyIdx: number) => {
      if (quoteLines.length === 0) return;
      const textContent = quoteLines.join("\n");
      
      const typeMap = {
        note: { type: "info" as const, title: "Note", bg: "rgba(59, 130, 246, 0.08)", border: "rgba(59, 130, 246, 0.2)" },
        tip: { type: "success" as const, title: "Tip", bg: "rgba(16, 185, 129, 0.08)", border: "rgba(16, 185, 129, 0.2)" },
        warning: { type: "warning" as const, title: "Warning", bg: "rgba(245, 158, 11, 0.08)", border: "rgba(245, 158, 11, 0.2)" },
        info: { type: "info" as const, title: "Info", bg: "rgba(59, 130, 246, 0.08)", border: "rgba(59, 130, 246, 0.2)" }
      };
      
      const cfg = typeMap[quoteType];
      elements.push(
        <Alert
          key={`quote-${keyIdx}`}
          type={cfg.type}
          showIcon
          message={<span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{cfg.title}</span>}
          description={
            <div style={{ color: "var(--text-secondary)", whiteSpace: "pre-line" }}>
              {textContent}
            </div>
          }
          style={{
            margin: "16px 0",
            backgroundColor: cfg.bg,
            border: `1px solid ${cfg.border}`,
            borderRadius: "8px"
          }}
        />
      );
      quoteLines = [];
    };
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      if (line.startsWith("> ") || (inQuote && line.trim() !== "")) {
        const clean = line.startsWith("> ") ? line.slice(2).trim() : line.trim();
        
        if (clean.startsWith("[!NOTE]")) {
          flushQuote(i);
          inQuote = true;
          quoteType = "note";
          const remainder = clean.slice(7).trim();
          if (remainder) quoteLines.push(remainder);
        } else if (clean.startsWith("[!TIP]")) {
          flushQuote(i);
          inQuote = true;
          quoteType = "tip";
          const remainder = clean.slice(6).trim();
          if (remainder) quoteLines.push(remainder);
        } else if (clean.startsWith("[!WARNING]")) {
          flushQuote(i);
          inQuote = true;
          quoteType = "warning";
          const remainder = clean.slice(10).trim();
          if (remainder) quoteLines.push(remainder);
        } else {
          quoteLines.push(clean);
        }
      } else {
        if (inQuote) {
          flushQuote(i);
          inQuote = false;
        }
        
        // Parse list items
        if (line.startsWith("- ") || line.startsWith("* ")) {
          const parts = line.slice(2).split("**");
          const formatted = parts.map((part, pIdx) => {
            if (pIdx % 2 === 1) return <strong key={pIdx}>{part}</strong>;
            return part;
          });
          elements.push(
            <li key={i} style={{ marginLeft: "20px", margin: "4px 0", color: "var(--text-secondary)" }}>
              {formatted}
            </li>
          );
        } else if (line.match(/^\d+\.\s/)) {
          const parts = line.replace(/^\d+\.\s/, "").split("**");
          const formatted = parts.map((part, pIdx) => {
            if (pIdx % 2 === 1) return <strong key={pIdx}>{part}</strong>;
            return part;
          });
          elements.push(
            <p key={i} style={{ paddingLeft: "16px", margin: "6px 0", color: "var(--text-secondary)" }}>
              <strong>{line.match(/^\d+/)?.[0]}.</strong> {formatted}
            </p>
          );
        } else if (line.startsWith("### ")) {
          elements.push(<Title key={i} level={4} style={{ marginTop: "16px", color: "var(--text-primary)" }}>{line.slice(4)}</Title>);
        } else if (line.startsWith("## ")) {
          elements.push(<Title key={i} level={3} style={{ marginTop: "24px", color: "var(--text-primary)" }}>{line.slice(3)}</Title>);
        } else if (line.startsWith("# ")) {
          elements.push(<Title key={i} level={2} style={{ marginTop: "28px", color: "var(--text-primary)" }}>{line.slice(2)}</Title>);
        } else if (line.trim()) {
          const parts = line.split("**");
          const formattedLine = parts.map((part, pIdx) => {
            if (pIdx % 2 === 1) return <strong key={pIdx}>{part}</strong>;
            return part;
          });
          elements.push(<Paragraph key={i} style={{ color: "var(--text-primary)", lineHeight: "1.6", margin: "12px 0" }}>{formattedLine}</Paragraph>);
        }
      }
    }
    
    if (inQuote) {
      flushQuote(lines.length);
    }
    
    return elements;
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "400px" }}>
        <Spin size="large" />
      </div>
    );
  }

  // Handle Dynamic Subscribed Module Locks (402 Payment Required)
  if (errorStatus === 402) {
    return (
      <Card style={{ margin: "40px auto", maxWidth: "600px", textAlign: "center", borderRadius: "12px", boxShadow: "0 8px 24px rgba(0,0,0,0.06)" }}>
        <LockOutlined style={{ fontSize: "48px", color: "#faad14", marginBottom: "16px" }} />
        <Title level={3}>Module Gated Content</Title>
        <Paragraph type="secondary">
          This article is part of a module not included in your current subscription plan.
        </Paragraph>
        <Paragraph>
          To unlock this documentation page and activate the functional ERP modules, please contact your platform operator or subscribe via Tenant settings.
        </Paragraph>
        <Button type="primary" onClick={() => navigate("/tenant-settings")}>
          Upgrade Plan
        </Button>
      </Card>
    );
  }

  if (errorStatus === 403) {
    return (
      <Card style={{ margin: "40px auto", maxWidth: "600px", textAlign: "center", borderRadius: "12px" }}>
        <WarningOutlined style={{ fontSize: "48px", color: "#ff4d4f", marginBottom: "16px" }} />
        <Title level={3}>Access Restricted</Title>
        <Paragraph type="secondary">
          You do not have the required user roles or permission matrix level to view this article.
        </Paragraph>
      </Card>
    );
  }

  if (errorStatus || !article) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <Title level={3}>Failed to load Help Article</Title>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  // Group attachments
  const images = article.attachments.filter(a => a.file_type === "image" || a.file_type === "gif");
  const videos = article.attachments.filter(a => a.file_type === "video");
  const pdfs = article.attachments.filter(a => a.file_type === "pdf");

  return (
    <div style={{ padding: "8px 24px 40px 24px", maxWidth: "900px", margin: "0 auto" }}>
      {/* Top Controls Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <Space>
          <Tag color="#0F2A43">{article.applicable_module.toUpperCase()} MODULE</Tag>
          <Text type="secondary" style={{ fontSize: "12px" }}>v{article.version}</Text>
        </Space>
        
        <Space>
          <Tooltip title="Copy Link">
            <Button icon={<LinkOutlined />} onClick={handleCopyLink} />
          </Tooltip>
          <Tooltip title="Bookmark Article">
            <Button 
              icon={isBookmarked ? <StarFilled style={{ color: "#faad14" }} /> : <StarOutlined />} 
              onClick={handleBookmarkToggle} 
            />
          </Tooltip>
          <Tooltip title="Print Document">
            <Button icon={<PrinterOutlined />} onClick={() => window.print()} />
          </Tooltip>
        </Space>
      </div>

      {/* Main Title & Purpose */}
      <Title level={1} style={{ margin: "0 0 12px 0", color: "#0F2A43", fontSize: "32px", fontWeight: "bold" }}>
        {article.title}
      </Title>
      
      <Paragraph style={{ fontSize: "16px", color: "#475569", fontStyle: "italic", borderLeft: "4px solid #38bdf8", paddingLeft: "16px", margin: "16px 0 24px 0" }}>
        <strong>Purpose:</strong> {article.purpose}
      </Paragraph>

      {/* Prerequisites Callout */}
      {article.prerequisites && (
        <Alert
          message={<strong>Prerequisites</strong>}
          description={article.prerequisites}
          type="warning"
          showIcon
          style={{ marginBottom: "24px", backgroundColor: "#fffbeb", border: "1px solid #fef3c7" }}
        />
      )}

      <Divider style={{ margin: "16px 0" }} />

      {/* Content Render */}
      <div className="help-article-content" style={{ margin: "24px 0" }}>
        {parseMarkdown(article.content_markdown)}
      </div>

      {/* Attachment Media Gallery */}
      {article.attachments.length > 0 && (
        <div style={{ marginTop: "40px" }}>
          <Title level={3} style={{ color: "#0F2A43" }}>Visual & PDF Resources</Title>
          
          {/* Images */}
          {images.map(img => (
            <Card key={img.id} style={{ marginBottom: "20px", borderRadius: "8px", overflow: "hidden" }} bodyStyle={{ padding: 0 }}>
              <img src={attachmentBlobUrls[img.id] || img.url} alt={img.file_name} style={{ width: "100%", maxHeight: "400px", objectFit: "contain", display: "block" }} />
              <div style={{ padding: "8px 12px", backgroundColor: "#f8fafc", textAlign: "center" }}>
                <Text type="secondary">{img.file_name}</Text>
              </div>
            </Card>
          ))}

          {/* Videos */}
          {videos.map(vid => (
            <Card key={vid.id} style={{ marginBottom: "20px", borderRadius: "8px", overflow: "hidden" }}>
              <div style={{ position: "relative", paddingBottom: "56.25%", height: 0 }}>
                <video controls src={attachmentBlobUrls[vid.id] || vid.url} style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }} />
              </div>
              <div style={{ padding: "12px 0 0 0" }}>
                <Space>
                  <PlayCircleOutlined style={{ color: "#0F2A43" }} />
                  <Text strong>{vid.file_name} Video Walkthrough</Text>
                </Space>
              </div>
            </Card>
          ))}

          {/* PDFs */}
          {pdfs.length > 0 && (
            <List
              header={<Text strong>Downloads</Text>}
              bordered
              dataSource={pdfs}
              renderItem={pdf => (
                <List.Item actions={[
                  <Button 
                    type="link" 
                    icon={<FilePdfOutlined />}
                    onClick={() => {
                      const bUrl = attachmentBlobUrls[pdf.id];
                      if (bUrl) {
                        window.open(bUrl, "_blank");
                      } else {
                        message.error("PDF not loaded yet");
                      }
                    }}
                  >
                    View PDF
                  </Button>
                ]}>
                  <Text>{pdf.file_name}</Text>
                </List.Item>
              )}
            />
          )}
        </div>
      )}

      {/* Frequently Asked Questions */}
      {article.faqs.length > 0 && (
        <div style={{ marginTop: "40px" }}>
          <Title level={3} style={{ color: "#0F2A43" }}>FAQ Details</Title>
          <Collapse ghost expandIconPosition="end">
            {article.faqs.map(faq => (
              <Panel header={<Text strong style={{ color: "#334155" }}>{faq.question}</Text>} key={faq.id}>
                <Paragraph style={{ color: "#475569" }}>{faq.answer}</Paragraph>
              </Panel>
            ))}
          </Collapse>
        </div>
      )}

      <Divider style={{ margin: "40px 0 20px 0" }} />

      {/* Pagination Previous & Next */}
      <div style={{ display: "flex", justifyContent: "space-between", margin: "20px 0 40px 0" }}>
        {prevArticle ? (
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => onNavigate(prevArticle.slug)}
            style={{ height: "48px", borderRadius: "8px", display: "flex", alignItems: "center" }}
          >
            <div style={{ textAlign: "left", marginLeft: "8px" }}>
              <div style={{ fontSize: "10px", color: "#64748b" }}>PREVIOUS</div>
              <div style={{ fontSize: "14px", fontWeight: "bold" }}>{prevArticle.title}</div>
            </div>
          </Button>
        ) : <div />}

        {nextArticle ? (
          <Button 
            onClick={() => onNavigate(nextArticle.slug)}
            style={{ height: "48px", borderRadius: "8px", display: "flex", alignItems: "center" }}
          >
            <div style={{ textAlign: "right", marginRight: "8px" }}>
              <div style={{ fontSize: "10px", color: "#64748b" }}>NEXT</div>
              <div style={{ fontSize: "14px", fontWeight: "bold" }}>{nextArticle.title}</div>
            </div>
            <ArrowRightOutlined />
          </Button>
        ) : <div />}
      </div>

      {/* Article Feedback Submission */}
      <Card style={{ backgroundColor: "#f8fafc", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
        {!ratingSubmitted ? (
          <div>
            <Title level={4} style={{ color: "#0F2A43", margin: "0 0 16px 0" }}>Was this article helpful?</Title>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <Space size="large">
                <Button icon={<LikeOutlined />} onClick={() => setFeedbackRating(5)}>Yes, helpful</Button>
                <Button icon={<DislikeOutlined />} onClick={() => setFeedbackRating(2)}>No, needs work</Button>
              </Space>

              {feedbackRating !== null && (
                <div>
                  <div style={{ marginBottom: "8px" }}>
                    <Text>Rate article quality: </Text>
                    <Rate value={feedbackRating} onChange={setFeedbackRating} />
                  </div>
                  <Input.TextArea
                    placeholder="Tell us more about how we can improve this documentation..."
                    rows={3}
                    value={feedbackComments}
                    onChange={e => setFeedbackComments(e.target.value)}
                    style={{ marginBottom: "12px" }}
                  />
                  <div style={{ marginBottom: "16px" }}>
                    <Button 
                      type="text" 
                      danger={isOutdated} 
                      onClick={() => setIsOutdated(!isOutdated)}
                      style={{ padding: 0 }}
                    >
                      {isOutdated ? "✓ Marked as Outdated Content" : "⚠ Report this content as outdated/obsolete"}
                    </Button>
                  </div>
                  <Button type="primary" onClick={handleFeedbackSubmit}>Submit Feedback</Button>
                </div>
              )}
            </Space>
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "12px 0" }}>
            <Text strong style={{ color: "#16a34a" }}>Thank you! Your feedback helps us improve the platform.</Text>
          </div>
        )}
      </Card>
    </div>
  );
};

export default HelpArticle;
