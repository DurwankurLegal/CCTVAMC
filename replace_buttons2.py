import os
import re

directory = r"d:\Antigravity projects folder\CCTVAMC\frontend\src\pages"

def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"(<div style=\{\{\s*display:\s*\"flex\",\s*justifyContent:\s*\"space-between\",\s*alignItems:\s*\"center\",\s*marginBottom:\s*16\s*\}\}>\s*<Title[^>]*>.*?</Title>\s*)<Button([^>]*)>([^<]+)</Button>\s*</div>",
        re.DOTALL
    )

    def replacer(match):
        prefix_and_title = match.group(1)
        button_attrs = match.group(2)
        button_text = match.group(3)

        if "position:" in button_attrs:
            return match.group(0)

        replacement = f"""{prefix_and_title}</div>
      <Button{button_attrs}
        shape="circle"
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
        title="{button_text.strip()}"
      />"""
        return replacement

    new_content = pattern.sub(replacer, content)
    
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".tsx"):
            process_file(os.path.join(root, file))

