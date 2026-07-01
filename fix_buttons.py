import os
import re

directory = r"d:\Antigravity projects folder\CCTVAMC\frontend\src\pages"

def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"<Button[^>]*icon=\{<PlusOutlined /\s*"
        r"shape=\"circle\"\s*"
        r"size=\"large\"\s*"
        r"style=\{\{.*?"
        r"fontSize:\s*\"22px\"\s*"
        r"\}\}\s*"
        r"title=\"\}\s*onClick=(.*?)>(.*?)\"\s*"
        r"/>",
        re.DOTALL
    )

    def replacer(match):
        onclick_val = match.group(1).strip()
        if onclick_val.startswith("{") and onclick_val.endswith("}"):
            onclick_val = onclick_val[1:-1]
        button_text = match.group(2).strip()

        replacement = f"""<Button
        type="primary"
        shape="circle"
        icon={{<PlusOutlined />}}
        onClick={{{onclick_val}}}
        size="large"
        style={{{{
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
        }}}}
        title="{button_text}"
      />"""
        return replacement

    new_content = pattern.sub(replacer, content)
    
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed {filepath}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".tsx"):
            process_file(os.path.join(root, file))

