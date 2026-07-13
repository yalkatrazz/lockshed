// The LockShed - Content Script
//
// This script never talks to the local app directly anymore - it only
// manipulates the page DOM and asks background.js (which runs with the
// extension's own origin, not the page's) to fetch data on its behalf.
// See background.js for why that split matters.

let injectedBadge = false;

// ── Find login fields ─────────────────────────────────────────────────────────
function findLoginFields() {
  // Password field - visible and not disabled
  const allPw = Array.from(document.querySelectorAll('input[type="password"]'))
    .filter(el => el.offsetParent !== null && !el.disabled && !el.readOnly);
  const pwField = allPw[0];

  // Only proceed if there's an actual password field on the page.
  // This prevents the badge from appearing on search boxes, comment
  // fields, or other unrelated text inputs.
  if (!pwField) return null;

  // Username/email field - search broadly, but only near the password field
  const userSelectors = [
    'input[type="email"]',
    'input[type="text"][name*="user"]',
    'input[type="text"][name*="email"]',
    'input[type="text"][id*="user"]',
    'input[type="text"][id*="email"]',
    'input[type="text"][autocomplete*="username"]',
    'input[type="text"][autocomplete*="email"]',
    'input[autocomplete="username"]',
    'input[autocomplete="email"]',
  ];

  let userField = null;
  for (const sel of userSelectors) {
    const found = Array.from(document.querySelectorAll(sel))
      .filter(el => el.offsetParent !== null && !el.disabled && !el.readOnly);
    if (found.length) { userField = found[0]; break; }
  }

  return { pwField, userField };
}

// ── Fill fields using native setter (works with React/Vue/Angular) ────────────
function setNativeValue(el, value) {
  if (!el) return;
  const proto = el.tagName === "INPUT"
    ? window.HTMLInputElement.prototype
    : window.HTMLTextAreaElement.prototype;
  const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
  if (descriptor && descriptor.set) {
    descriptor.set.call(el, value);
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event("input",  { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  el.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
}

function fillForm(username, password, pwField, userField) {
  if (userField && username) {
    userField.focus();
    setNativeValue(userField, username);
  }
  if (pwField && password) {
    pwField.focus();
    setNativeValue(pwField, password);
  }
}

// ── Inject 🔐 badge on password field ────────────────────────────────────────
function injectBadge() {
  const fields = findLoginFields();
  const targetField = fields?.pwField;  // only target actual password fields
  if (!targetField || injectedBadge) return;

  // Don't inject if badge already exists nearby
  if (targetField.parentElement?.querySelector("#pv-badge")) return;
  injectedBadge = true;

  // Wrap field in relative container
  const parent = targetField.parentElement;
  const wrapper = document.createElement("div");
  wrapper.style.cssText = "position:relative;display:inline-block;width:100%;";
  parent.insertBefore(wrapper, targetField);
  wrapper.appendChild(targetField);

  const badge = document.createElement("button");
  badge.id   = "pv-badge";
  badge.type = "button";
  badge.title = "Fill with The LockShed";
  badge.innerHTML = "🔐";
  badge.style.cssText = `
    position:absolute; right:6px; top:50%; transform:translateY(-50%);
    background:#2563eb; border:none; border-radius:4px;
    color:white; font-size:10px; padding:1px 4px;
    cursor:pointer; z-index:99999; line-height:1.4;
    box-shadow:0 1px 3px rgba(0,0,0,0.3);
    opacity:0.85;
  `;
  badge.addEventListener("mouseenter", () => badge.style.opacity = "1");
  badge.addEventListener("mouseleave", () => badge.style.opacity = "0.85");
  badge.addEventListener("click", async (e) => {
    e.preventDefault(); e.stopPropagation();
    await fetchAndFill(false);
  });
  wrapper.appendChild(badge);
}

// ── Ask background.js to fetch from the app, then fill ────────────────────────
async function fetchAndFill(showAll = false) {
  const domain = window.location.hostname;
  const fields = findLoginFields();

  const res = await chrome.runtime.sendMessage({ action: "lookup", domain, showAll });

  if (!res?.ok) {
    const messages = {
      not_paired: "Not paired yet - open the extension's options page to set it up.",
      forbidden:  "Pairing code rejected. Re-pair in the extension's options page.",
      locked:     "Vault is locked - unlock it in the app first.",
      unreachable:"The LockShed app is not running.",
    };
    showNotification(messages[res?.error] || "The LockShed app is not running.", "error");
    return;
  }

  const data = res.data;
  if (!data.entries?.length) {
    showNotification(`No passwords found for ${domain}`, "warn"); return;
  }
  if (data.entries.length === 1) {
    const e = data.entries[0];
    if (fields) fillForm(e.user, e.pass, fields.pwField, fields.userField);
    showNotification(`Filled: ${e.name}`, "ok");
  } else {
    showPicker(data.entries, fields);
  }
}

// ── Picker for multiple matches ───────────────────────────────────────────────
function showPicker(entries, fields) {
  document.getElementById("pv-picker")?.remove();
  const picker = document.createElement("div");
  picker.id = "pv-picker";
  picker.style.cssText = `
    position:fixed; top:50%; left:50%; transform:translate(-50%,-50%);
    background:#1e293b; color:#e2e8f0; border-radius:12px;
    padding:16px; z-index:2147483647; min-width:290px; max-width:370px;
    box-shadow:0 8px 32px rgba(0,0,0,0.6); font-family:Segoe UI,sans-serif;
  `;
  picker.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <span style="font-weight:600;font-size:14px;">🔐 Choose account</span>
      <button id="pv-close" style="background:none;border:none;color:#94a3b8;font-size:18px;cursor:pointer;">✕</button>
    </div>
    <div id="pv-list"></div>
  `;
  const list = picker.querySelector("#pv-list");
  for (const e of entries) {
    const btn = document.createElement("button");
    btn.style.cssText = `
      display:block;width:100%;text-align:left;background:#16213e;
      border:1px solid #2a4060;border-radius:8px;color:#dce8f8;
      padding:10px 12px;margin-bottom:6px;cursor:pointer;font-size:13px;
      font-family:Segoe UI,sans-serif;transition:background 0.12s;
    `;
    btn.innerHTML = `<strong>${e.name}</strong><br><span style="color:#6b86a8;font-size:12px;">${e.user||"—"}</span>`;
    btn.onmouseenter = () => btn.style.background = "#1e3050";
    btn.onmouseleave = () => btn.style.background = "#16213e";
    btn.addEventListener("click", () => {
      if (fields) fillForm(e.user, e.pass, fields.pwField, fields.userField);
      picker.remove();
      showNotification(`Filled: ${e.name}`, "ok");
    });
    list.appendChild(btn);
  }
  picker.querySelector("#pv-close").addEventListener("click", () => picker.remove());
  document.body.appendChild(picker);
  setTimeout(() => {
    document.addEventListener("click", (ev) => {
      if (!picker.contains(ev.target)) picker.remove();
    }, { once: true });
  }, 100);
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showNotification(msg, type = "ok") {
  document.getElementById("pv-toast")?.remove();
  const bg = { ok:"#16a34a", warn:"#d97706", error:"#dc2626" }[type];
  const toast = document.createElement("div");
  toast.id = "pv-toast";
  toast.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:2147483647;
    background:${bg};color:white;padding:10px 16px;
    border-radius:8px;font-family:Segoe UI,sans-serif;font-size:13px;
    box-shadow:0 4px 12px rgba(0,0,0,0.3);pointer-events:none;
    transition:opacity 0.3s;
  `;
  toast.textContent = "🔐 " + msg;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = "0"; setTimeout(() => toast.remove(), 300); }, 2500);
}

// ── Message listener (from popup) ────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "fill") { fetchAndFill(msg.showAll || false); sendResponse({ok:true}); }
  if (msg.action === "getDomain") { sendResponse({domain: window.location.hostname}); }
  return true;
});

// ── Init with MutationObserver for SPAs and dynamic popups ───────────────────
function init() {
  injectBadge();

  let debounceTimer = null;
  const observer = new MutationObserver(() => {
    // Debounce: wait for DOM to settle before checking (popups often
    // insert multiple elements in quick succession)
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      // Check if current password field still has our badge attached.
      // If the field changed (e.g. a new popup modal replaced the form),
      // reset and re-inject.
      const fields = findLoginFields();
      const currentField = fields?.pwField || fields?.userField;
      const hasBadge = currentField?.parentElement?.querySelector("#pv-badge");

      if (currentField && !hasBadge) {
        injectedBadge = false;
        injectBadge();
      }
    }, 150);
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // Also catch focus events on password fields directly — this is the most
  // reliable way to detect popups/modals that load instantly on click,
  // since the user must focus the field before typing.
  document.addEventListener("focusin", (e) => {
    if (e.target.tagName === "INPUT" &&
        (e.target.type === "password" || e.target.type === "email" || e.target.type === "text")) {
      const fields = findLoginFields();
      const currentField = fields?.pwField || fields?.userField;
      if (currentField) {
        const hasBadge = currentField.parentElement?.querySelector("#pv-badge");
        if (!hasBadge) {
          injectedBadge = false;
          injectBadge();
        }
      }
    }
  }, true);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  setTimeout(init, 300);
}

// ── Keyboard shortcut fallback: Ctrl+Shift+L triggers autofill manually ──────
// Useful for popup forms where badge injection might be delayed or blocked.
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "l") {
    e.preventDefault();
    fetchAndFill(false);
  }
}, true);
