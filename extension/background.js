"use strict";

const HOST = "app.music_rpc_linux";
let port = null;
let retry = 1000;
let retryTimer = null;
const byTab = new Map();
let activeTab = null;

function connect() {
  if (port) return;
  try {
    port = chrome.runtime.connectNative(HOST);
    port.onMessage.addListener((message) => {
      if (!message?.ok) console.warn("Music RPC host rejected a message", message?.error || "");
      retry = 1000;
    });
    port.onDisconnect.addListener(() => {
      port = null;
      if (retryTimer) clearTimeout(retryTimer);
      retryTimer = setTimeout(connect, retry);
      retry = Math.min(30000, retry * 2);
    });
    port.postMessage({ type: "ping" });
  } catch (error) {
    console.warn("Music RPC native host is not available yet", error);
    if (retryTimer) clearTimeout(retryTimer);
    retryTimer = setTimeout(connect, retry);
    retry = Math.min(30000, retry * 2);
  }
}

function publishActive() {
  if (!port) connect();
  if (!port || activeTab === null) return;
  const track = byTab.get(activeTab);
  port.postMessage(track ? { type: "update", track: { ...track, site: "youtube_music" } }
                        : { type: "remove", site: "youtube_music" });
}

chrome.runtime.onMessage.addListener((message, sender) => {
  const id = sender.tab?.id;
  if (id === undefined || !message) return;
  if (message.type === "update" && message.track) byTab.set(id, message.track);
  else if (message.type === "remove") byTab.delete(id);
  if (id === activeTab) publishActive();
});

chrome.tabs.onActivated.addListener(({ tabId }) => {
  activeTab = tabId;
  publishActive();
});

chrome.tabs.onRemoved.addListener((tabId) => {
  byTab.delete(tabId);
  if (activeTab === tabId) {
    activeTab = null;
    publishActive();
  }
});

chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
  if (tabs[0]) activeTab = tabs[0].id;
  connect();
});

