"use strict";

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const send = document.querySelector("#send");
const conversation = document.querySelector("#conversation");
const status = document.querySelector("#status");
const restart = document.querySelector("#restart");
const welcome = conversation.querySelector(".welcome").cloneNode(true);
function readTabValue(key, fallback = null) {
  try { return JSON.parse(sessionStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
}

function writeTabValue(key, value) {
  try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* Storage may be disabled. */ }
}

let sessionId = readTabValue("bibs.session");
const recovery = document.querySelector("#recover-session");
let pending = false;

function appendFormattedText(element, text) {
  const tokens = text.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g);
  for (const token of tokens) {
    if (token.startsWith("**") && token.endsWith("**")) {
      const strong = document.createElement("strong");
      strong.textContent = token.slice(2, -2);
      element.append(strong);
      continue;
    }
    const link = token.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (link) {
      const anchor = document.createElement("a");
      anchor.textContent = link[1];
      anchor.href = link[2];
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      element.append(anchor);
      continue;
    }
    element.append(document.createTextNode(token));
  }
}

function displayAssistantResponse(element, text) {
  element.replaceChildren();
  element.classList.add("formatted-response");
  let list = null;
  for (const line of text.split("\n")) {
    const item = line.match(/^\s*(?:(\d+)\.\s+|[-*]\s+)(.*)$/);
    if (item) {
      const tag = item[1] ? "OL" : "UL";
      if (!list || list.tagName !== tag) {
        list = document.createElement(tag.toLowerCase());
        if (item[1]) list.start = Number(item[1]);
        element.append(list);
      }
      const entry = document.createElement("li");
      appendFormattedText(entry, item[2]);
      list.append(entry);
    } else {
      list = null;
      if (!line.trim()) continue;
      const paragraph = document.createElement("p");
      appendFormattedText(paragraph, line.replace(/^#{1,6}\s+/, ""));
      element.append(paragraph);
    }
  }
}

function appendMessage(role, content, loading = false) {
  const article = document.createElement("article");
  article.className = `msg ${role === "You" ? "user" : "assistant"}${loading ? " loading" : ""}`;
  const heading = document.createElement("div");
  heading.className = "role";
  heading.textContent = role;
  const text = document.createElement("div");
  text.className = "content";
  text.textContent = content;
  article.append(heading, text);
  conversation.append(article);
  conversation.scrollTop = conversation.scrollHeight;
  return article;
}

function displayToolCall(call, before) {
  const details = document.createElement("details");
  details.className = `tool${call.result?.ok === false ? " failed" : ""}`;
  const summary = document.createElement("summary");
  const payload = document.createElement("pre");
  summary.textContent = `Tool call · ${call.name}${call.result?.ok === false ? " · Failed" : ""}`;
  payload.textContent = JSON.stringify({ args: call.args, result: call.result }, null, 2);
  details.append(summary, payload);
  conversation.insertBefore(details, before);
}

conversation.addEventListener("click", (event) => {
  const example = event.target.closest(".example");
  if (!example || pending) return;
  if (example.dataset.action === "sample-roster") {
    window.dispatchEvent(new Event("load-sample-roster"));
    return;
  }
  input.value = example.dataset.prompt;
  input.focus();
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (!pending) form.requestSubmit();
  }
});

async function readChatResponse(response) {
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = result?.detail;
    const error = new Error(detail?.message || (response.status >= 500
      ? "The server couldn't complete your request. Try again shortly."
      : "The request was rejected. Check your message and try again."));
    error.code = detail?.code;
    throw error;
  }
  if (!result || typeof result !== "object") throw new Error("The server returned an unreadable response. Try again.");
  return result;
}

function setChatPending(value) {
  pending = value;
  send.disabled = value;
  input.disabled = value;
  restart.disabled = value;
  recovery.disabled = value;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (pending || !message) return;
  setChatPending(true);
  recovery.hidden = true;
  conversation.querySelector(".welcome")?.remove();
  appendMessage("You", message);
  input.value = "";
  const reply = appendMessage("bibs", "Thinking…", true);
  status.textContent = "Working on it…";
  const request = { message };
  if (sessionId && !request.session_id) request.session_id = sessionId;
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const result = await readChatResponse(response);
    sessionId = result.session_id;
    writeTabValue("bibs.session", sessionId);
    for (const call of result.tool_calls || []) displayToolCall(call, reply);
    displayAssistantResponse(reply.querySelector(".content"), result.response);
    status.textContent = "";
  } catch (error) {
    reply.classList.add("error");
    reply.querySelector(".content").textContent = error.name === "TimeoutError"
      ? "The connection timed out. Completed operations may still have been saved."
      : error instanceof TypeError ? "Unable to reach the server. Check your connection."
      : error.message || "The request failed. Please try again.";
    const expired = error.code === "SESSION_EXPIRED";
    recovery.hidden = !expired;
    status.textContent = expired ? "Start again with your bench roster." : "Check your connection. Completed operations may still have been saved.";
  } finally {
    reply.classList.remove("loading");
    setChatPending(false);
    conversation.scrollTop = conversation.scrollHeight;
    input.focus();
  }
});

async function restoreCompletedSession() {
  if (!sessionId) return;
  setChatPending(true);
  try {
    const result = await readChatResponse(await fetch(`/session?session_id=${encodeURIComponent(sessionId)}`, {
      signal: AbortSignal.timeout(10000),
    }));
    conversation.replaceChildren();
    if (!result.turns.length) conversation.append(welcome.cloneNode(true));
    for (const turn of result.turns) {
      appendMessage("You", turn.message);
      const reply = appendMessage("bibs", "");
      for (const call of turn.tool_calls) displayToolCall(call, reply);
      displayAssistantResponse(reply.querySelector(".content"), turn.response);
    }
    window.dispatchEvent(new CustomEvent("restore-roster", { detail: result.state.roster || [] }));
  } catch (error) {
    recovery.hidden = error.code !== "SESSION_EXPIRED";
    status.textContent = error.message;
  } finally { setChatPending(false); }
}

// sessionStorage survives refresh. A duplicated tab must claim a fresh session.
async function initializeTabSession() {
  setChatPending(true);
  if (typeof BroadcastChannel !== "undefined") {
    const channel = new BroadcastChannel("bibs.tabs");
    const token = crypto.randomUUID();
    let claimed = false;
    channel.onmessage = ({ data }) => {
      if (!sessionId || data.session !== sessionId) return;
      if (data.query) channel.postMessage({ session: sessionId, owner: data.query });
      if (data.owner === token) claimed = true;
    };
    if (sessionId) {
      channel.postMessage({ session: sessionId, query: token });
      await new Promise((resolve) => setTimeout(resolve, 150));
    }
    if (claimed) {
      sessionId = null;
      writeTabValue("bibs.session", null);
    }
    // Keep answering ownership checks for subsequently duplicated tabs.
  }
  await restoreCompletedSession();
  setChatPending(false);
}
const chatReady = initializeTabSession();

restart.addEventListener("click", () => {
  if (pending) return;
  sessionId = null;
  writeTabValue("bibs.session", null);
  recovery.hidden = true;
  conversation.replaceChildren(welcome.cloneNode(true));
  input.value = "";
  status.textContent = "New conversation ready.";
  input.focus();
});

recovery.addEventListener("click", () => {
  restart.click();
  if (benchPlayers.filter(Boolean).length >= 3) useRoster.click();
  else { location.hash = "team"; benchStatus.textContent = "Add at least 3 players to restart with a roster."; }
});
