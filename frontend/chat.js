"use strict";

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const send = document.querySelector("#send");
const conversation = document.querySelector("#conversation");
const status = document.querySelector("#status");
const restart = document.querySelector("#restart");
const welcome = conversation.querySelector(".welcome").cloneNode(true);
let sessionId = null;
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (pending || !message) return;
  pending = true;
  send.disabled = true;
  input.disabled = true;
  restart.disabled = true;
  conversation.querySelector(".welcome")?.remove();
  appendMessage("You", message);
  input.value = "";
  const reply = appendMessage("bibs", "Thinking…", true);
  status.textContent = "Working on it…";
  const request = { message };
  if (sessionId) request.session_id = sessionId;
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail?.message || "Message could not be sent. Please try again.");
    }
    sessionId = result.session_id;
    for (const call of result.tool_calls || []) displayToolCall(call, reply);
    displayAssistantResponse(reply.querySelector(".content"), result.response);
    status.textContent = "";
  } catch (error) {
    reply.classList.add("error");
    reply.querySelector(".content").textContent = error instanceof Error ? error.message : "Unable to send the message.";
    input.value = message;
    status.textContent = "Your message is ready to retry.";
  } finally {
    reply.classList.remove("loading");
    pending = false;
    send.disabled = false;
    input.disabled = false;
    restart.disabled = false;
    conversation.scrollTop = conversation.scrollHeight;
    input.focus();
  }
});

restart.addEventListener("click", () => {
  if (pending) return;
  sessionId = null;
  conversation.replaceChildren(welcome.cloneNode(true));
  input.value = "";
  status.textContent = "New conversation ready.";
  input.focus();
});
