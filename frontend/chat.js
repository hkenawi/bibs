"use strict";

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const send = document.querySelector("#send");
const conversation = document.querySelector("#conversation");
const status = document.querySelector("#status");
const restart = document.querySelector("#restart");
let sessionId = null;
let pending = false;

function appendMessage(label, content) {
  const article = document.createElement("article");
  const heading = document.createElement("strong");
  const text = document.createElement("p");
  heading.textContent = label;
  text.textContent = content;
  article.append(heading, text);
  conversation.append(article);
  article.scrollIntoView({ block: "nearest" });
  return article;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (pending || !message) return;
  pending = true;
  send.disabled = true;
  input.disabled = true;
  status.textContent = "Sending…";
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
      if (response.status === 404) restart.hidden = false;
      throw new Error(result.detail?.message || "Message could not be sent. Please try again.");
    }
    sessionId = result.session_id;
    conversation.querySelector(".welcome")?.remove();
    appendMessage("You", message);
    const article = appendMessage("bibs", result.response);
    for (const call of result.tool_calls) {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      const payload = document.createElement("pre");
      summary.textContent = call.name;
      payload.textContent = JSON.stringify({ args: call.args, result: call.result }, null, 2);
      details.append(summary, payload);
      article.append(details);
    }
    input.value = "";
    status.textContent = "";
  } catch (error) {
    status.textContent = error instanceof Error ? error.message : "Unable to send the message.";
  } finally {
    pending = false;
    send.disabled = false;
    input.disabled = false;
    input.focus();
  }
});

restart.addEventListener("click", () => {
  if (pending) return;
  sessionId = null;
  conversation.replaceChildren();
  restart.hidden = true;
  status.textContent = "Ready for a new conversation. Send your message again.";
});
