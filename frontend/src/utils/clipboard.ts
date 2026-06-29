/**
 * Secure and fallback clipboard utility for copying text.
 * Handles insecure HTTP context (e.g. public IPs) where navigator.clipboard is blocked.
 */
function copyTextFallback(text: string): boolean {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  textArea.style.top = "-9999px";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  
  textArea.focus();
  textArea.select();
  
  try {
    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);
    return successful;
  } catch (err) {
    document.body.removeChild(textArea);
    return false;
  }
}

export async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard && (window.isSecureContext || typeof window.isSecureContext === "undefined")) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return copyTextFallback(text);
    }
  } else {
    return copyTextFallback(text);
  }
}
