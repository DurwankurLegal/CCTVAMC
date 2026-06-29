import React, { useRef, useEffect } from "react";
import { Button, Space, Tooltip } from "antd";
import {
  BoldOutlined,
  ItalicOutlined,
  OrderedListOutlined,
  UnorderedListOutlined,
  UndoOutlined,
  RedoOutlined,
  ClearOutlined
} from "@ant-design/icons";

interface RichTextEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  minHeight?: number;
}

export const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value = "",
  onChange,
  placeholder = "Enter text here...",
  minHeight = 150
}) => {
  const editorRef = useRef<HTMLDivElement>(null);

  // Sync internal HTML with parent value when value changes externally
  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== value) {
      editorRef.current.innerHTML = value || "";
    }
  }, [value]);

  const handleInput = () => {
    if (editorRef.current && onChange) {
      onChange(editorRef.current.innerHTML);
    }
  };

  const executeCommand = (command: string, arg: string = "") => {
    document.execCommand(command, false, arg);
    handleInput();
  };

  return (
    <div
      style={{
        border: "1px solid var(--glass-border)",
        borderRadius: "8px",
        background: "var(--glass-bg)",
        overflow: "hidden",
        width: "100%"
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          padding: "6px 8px",
          borderBottom: "1px solid var(--glass-border)",
          background: "var(--glass-bg)",
          display: "flex",
          flexWrap: "wrap",
          gap: "4px"
        }}
        onMouseDown={(e) => e.preventDefault()} // Prevent editor from losing focus
      >
        <Space size={2}>
          <Tooltip title="Bold">
            <Button
              type="text"
              size="small"
              icon={<BoldOutlined />}
              onClick={() => executeCommand("bold")}
              style={{ color: "var(--text-secondary)" }}
            />
          </Tooltip>
          <Tooltip title="Italic">
            <Button
              type="text"
              size="small"
              icon={<ItalicOutlined />}
              onClick={() => executeCommand("italic")}
              style={{ color: "var(--text-secondary)" }}
            />
          </Tooltip>
          <DividerLine />
          <Tooltip title="Numbered List">
            <Button
              type="text"
              size="small"
              icon={<OrderedListOutlined />}
              onClick={() => executeCommand("insertOrderedList")}
              style={{ color: "var(--text-secondary)" }}
            />
          </Tooltip>
          <Tooltip title="Bulleted List">
            <Button
              type="text"
              size="small"
              icon={<UnorderedListOutlined />}
              onClick={() => executeCommand("insertUnorderedList")}
              style={{ color: "var(--text-secondary)" }}
            />
          </Tooltip>
          <DividerLine />
          <Tooltip title="Undo">
            <Button
              type="text"
              size="small"
              icon={<UndoOutlined />}
              onClick={() => executeCommand("undo")}
              style={{ color: "var(--text-secondary)" }}
            />
          </Tooltip>
          <Tooltip title="Redo">
            <Button
              type="text"
              size="small"
              icon={<RedoOutlined />}
              onClick={() => executeCommand("redo")}
              style={{ color: "var(--text-secondary)" }}
            />
          </Tooltip>
          <DividerLine />
          <Tooltip title="Clear Formatting">
            <Button
              type="text"
              size="small"
              icon={<ClearOutlined />}
              onClick={() => executeCommand("removeFormat")}
              style={{ color: "var(--text-secondary)" }}
            />
          </Tooltip>
        </Space>
      </div>

      {/* Editor Body */}
      <div
        ref={editorRef}
        contentEditable
        onInput={handleInput}
        onBlur={handleInput}
        data-placeholder={placeholder}
        style={{
          padding: "12px",
          minHeight: `${minHeight}px`,
          outline: "none",
          color: "var(--text-primary)",
          background: "transparent",
          cursor: "text"
        }}
        className="custom-rich-editor"
      />

      {/* Placeholder stylesheet */}
      <style>{`
        .custom-rich-editor:empty:before {
          content: attr(data-placeholder);
          color: var(--text-secondary);
          opacity: 0.7;
          cursor: text;
        }
        .custom-rich-editor ul {
          margin: 0 0 10px 20px;
          padding: 0;
          list-style-type: disc;
        }
        .custom-rich-editor ol {
          margin: 0 0 10px 20px;
          padding: 0;
          list-style-type: decimal;
        }
        .custom-rich-editor li {
          margin-bottom: 4px;
        }
      `}</style>
    </div>
  );
};

const DividerLine: React.FC = () => (
  <div style={{ width: "1px", height: "14px", background: "var(--glass-border)", margin: "0 6px", alignSelf: "center" }} />
);
