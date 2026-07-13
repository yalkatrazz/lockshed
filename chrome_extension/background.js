// The LockShed - Background service worker
//
// All network calls to the local app now happen HERE, not in content.js.
// Why: a content script's fetch() runs with the Origin of the page it's
// injected into (e.g. https://evil.example.com), because that's how the
// browser's CORS model treats content scripts. That meant ANY website's
// JavaScript could previously make the exact same request and read your
// passwords - the app had no way to tell "our content script" apart from
// "some page's own script".
//
// A background service worker's fetch(), by contrast, always carries
// Origin: chrome-extension://<this-extension-id> - a value no web page can
// forge. The app (see password_manager.py / LocalAPIServer) now only
// accepts requests with that Origin, so routing everything through here
// closes the hole entirely.

const API_BASE = "http://localhost:19485";

async function getSecret() {
  const { pairingSecret } = await chrome.storage.local.get("pairingSecret");
  return pairingSecret || "";
}

async function callApi(path, options = {}) {
  const secret = await getSecret();
  if (!secret) {
    return { ok: false, error: "not_paired" };
  }
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        "X-Secret": secret,
      },
    });
    if (res.status === 403) return { ok: false, error: "forbidden" };
    if (res.status === 423) return { ok: false, error: "locked" };
    if (!res.ok) return { ok: false, error: "not_ok" };
    const data = await res.json();
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: "unreachable" };
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "ping") {
    callApi("/ping").then(sendResponse);
    return true; // keep the message channel open for the async response
  }
  if (msg.action === "lookup") {
    callApi("/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain: msg.domain, show_all: !!msg.showAll }),
    }).then(sendResponse);
    return true;
  }
  return false;
});
