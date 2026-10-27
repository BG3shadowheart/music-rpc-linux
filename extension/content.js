"use strict";

(() => {
  let lastKey = "";
  let timer = null;

  function text(selector) {
    const node = document.querySelector(selector);
    return (node?.textContent || node?.getAttribute("title") || "").replace(/\s+/g, " ").trim();
  }

  function currentTrack() {
    const player = document.querySelector("ytmusic-player-bar");
    const video = document.querySelector("video");
    if (!player || !video) return null;
    const title = text("ytmusic-player-bar .title");
    if (!title) return null;

    const byline = player.querySelector(".byline");
    const links = [...(byline?.querySelectorAll("a") || [])]
      .map((item) => (item.textContent || "").trim()).filter(Boolean);
    const artist = links[0] || text("ytmusic-player-bar .byline").split(/[•·]/)[0].trim();
    const album = links.length > 1 ? links[links.length - 1] : "";
    const id = new URL(location.href).searchParams.get("v") || "";
    const artwork = id ? `https://i.ytimg.com/vi/${id}/maxresdefault.jpg`
      : (player.querySelector("img")?.src || "");
    const duration = Number.isFinite(video.duration) ? Math.round(video.duration * 1000) : 0;
    const position = Number.isFinite(video.currentTime) ? Math.round(video.currentTime * 1000) : 0;
    return {
      site: "youtube_music", title, artist, album, video_id: id, artwork,
      playing: !video.paused && !video.ended,
      status: video.ended ? "stopped" : video.paused ? "paused" : "playing",
      duration_ms: duration, position_ms: position
    };
  }

  function send() {
    timer = null;
    const track = currentTrack();
    if (!track) {
      if (lastKey) chrome.runtime.sendMessage({ type: "remove" });
      lastKey = "";
      return;
    }
    const key = JSON.stringify([track.title, track.artist, track.album, track.status, track.video_id,
                                Math.floor(track.position_ms / 5000)]);
    if (key !== lastKey) {
      lastKey = key;
      chrome.runtime.sendMessage({ type: "update", track }).catch(() => {});
    }
  }

  function schedule() {
    if (!timer) timer = setTimeout(send, 100);
  }

  const observer = new MutationObserver(schedule);
  observer.observe(document.documentElement, { subtree: true, childList: true, characterData: true });
  document.addEventListener("play", schedule, true);
  document.addEventListener("pause", schedule, true);
  document.addEventListener("ended", schedule, true);
  setInterval(send, 2500);
  window.addEventListener("pagehide", () => chrome.runtime.sendMessage({ type: "remove" }));
  send();
})();
