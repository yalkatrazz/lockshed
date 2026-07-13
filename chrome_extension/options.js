const input  = document.getElementById("secret-input");
const status = document.getElementById("status-box");

function showStatus(msg, type) {
  status.textContent = msg;
  status.className = "status " + type;
}

chrome.storage.local.get("pairingSecret", ({ pairingSecret }) => {
  if (pairingSecret) input.value = pairingSecret;
});

document.getElementById("save-btn").addEventListener("click", async () => {
  const value = input.value.trim();
  if (!value) {
    showStatus("Paste the pairing code from the app's Settings first.", "error");
    return;
  }
  await chrome.storage.local.set({ pairingSecret: value });

  // Verify it actually works against the running app before declaring victory.
  const res = await chrome.runtime.sendMessage({ action: "ping" });
  if (res?.ok) {
    showStatus("✓ Paired successfully. You're all set.", "ok");
  } else if (res?.error === "forbidden") {
    showStatus("Saved, but the app rejected this code. Double-check you copied it correctly, or it may have been regenerated.", "error");
  } else if (res?.error === "locked") {
    showStatus("✓ Code accepted. The vault is currently locked - unlock it in the app to use autofill.", "ok");
  } else {
    showStatus("Saved, but couldn't reach the app. Make sure The LockShed is running, then try again.", "error");
  }
});
