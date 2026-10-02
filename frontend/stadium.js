"use strict";

const homeScreen = document.querySelector("#home-screen");
const chatScreen = document.querySelector("#chat-screen");
const teamScreen = document.querySelector("#team-screen");
const benchSeats = document.querySelector("#bench-seats");
const playerCount = document.querySelector("#player-count");
const rosterProgress = document.querySelector("#roster-progress");
const benchStatus = document.querySelector("#bench-status");
const useRoster = document.querySelector("#use-roster");
const playerDialog = document.querySelector("#player-dialog");
const playerForm = document.querySelector("#player-form");
const playerName = document.querySelector("#player-name");
const playerRating = document.querySelector("#player-rating");
const playerKeeper = document.querySelector("#player-keeper");
const playerError = document.querySelector("#player-error");
const removePlayer = document.querySelector("#remove-player");
let benchPlayers = Array(10).fill(null);
let selectedSeat = null;
let navigationTimer;
let activeScreen = "home";

function showStadiumScreen() {
  clearTimeout(navigationTimer);
  const destination = location.hash === "#chat" ? "chat" : location.hash === "#team" ? "team" : "home";
  homeScreen.classList.remove("zoom-to-bench");
  const reveal = () => {
    homeScreen.hidden = destination === "team";
    chatScreen.hidden = destination !== "chat";
    teamScreen.hidden = destination !== "team";
    document.body.classList.toggle("chat-open", destination === "chat");
    activeScreen = destination;
    if (destination === "chat") input.focus();
    if (destination === "team") {
      teamScreen.classList.remove("bench-enter");
      void teamScreen.offsetWidth;
      teamScreen.classList.add("bench-enter");
      playerCount.focus({ preventScroll: true });
    }
  };
  if (destination === "team" && activeScreen === "home" && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    homeScreen.classList.add("zoom-to-bench");
    navigationTimer = setTimeout(reveal, 700);
  } else reveal();
}

function renderBenchSeats() {
  benchSeats.replaceChildren();
  let benchRow;
  benchPlayers.forEach((player, index) => {
    if (index % 5 === 0) {
      benchRow = document.createElement("div");
      benchRow.className = "bench-row";
      benchSeats.append(benchRow);
    }
    const seat = document.createElement("button");
    seat.type = "button";
    seat.className = `bench-seat${player ? " occupied" : ""}`;
    seat.dataset.index = index;
    seat.setAttribute("aria-label", player ? `Edit ${player.name}, seat ${index + 1}` : `Add player to seat ${index + 1}`);
    const number = document.createElement("span");
    number.className = "seat-number";
    number.textContent = String(index + 1).padStart(2, "0");
    const name = document.createElement("span");
    name.className = "seat-name";
    name.textContent = player ? player.name : "+";
    const detail = document.createElement("span");
    detail.className = "seat-detail";
    detail.textContent = player ? `Rating ${player.rating}${player.goalkeeper_willing ? " · GK" : ""}` : "Add player";
    seat.append(number, name, detail);
    benchRow.append(seat);
  });
  const filled = benchPlayers.filter(Boolean).length;
  rosterProgress.textContent = `${filled} of ${benchPlayers.length} seats filled`;
  useRoster.disabled = filled < 3;
  benchStatus.textContent = filled >= 3 ? "Your roster is ready. Add more players or continue to chat." : "Add at least 3 players to continue.";
}

benchSeats.addEventListener("click", (event) => {
  const seat = event.target.closest(".bench-seat");
  if (!seat) return;
  selectedSeat = Number(seat.dataset.index);
  const player = benchPlayers[selectedSeat];
  playerForm.reset();
  playerError.textContent = "";
  playerName.setCustomValidity("");
  document.querySelector("#player-dialog-title").textContent = `Seat ${selectedSeat + 1} · ${player ? "Edit player" : "Add player"}`;
  playerName.value = player?.name || "";
  playerRating.value = player?.rating || "";
  playerKeeper.checked = player?.goalkeeper_willing || false;
  removePlayer.hidden = !player;
  playerDialog.showModal();
  playerName.focus();
});

playerName.addEventListener("input", () => playerName.setCustomValidity(""));
playerForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const name = playerName.value.trim();
  if (!name) {
    playerName.setCustomValidity("Enter a player name.");
    playerName.reportValidity();
    return;
  }
  if (benchPlayers.some((player, index) => index !== selectedSeat && player?.name.toLocaleLowerCase() === name.toLocaleLowerCase())) {
    playerError.textContent = "That name is already on the bench. Add a surname or initial.";
    return;
  }
  benchPlayers[selectedSeat] = { name, rating: Number(playerRating.value), goalkeeper_willing: playerKeeper.checked };
  renderBenchSeats();
  playerDialog.close();
  benchSeats.querySelectorAll(".bench-seat")[selectedSeat].focus();
});

document.querySelector("#close-player").addEventListener("click", () => playerDialog.close());
removePlayer.addEventListener("click", () => {
  benchPlayers[selectedSeat] = null;
  renderBenchSeats();
  playerDialog.close();
  benchSeats.querySelectorAll(".bench-seat")[selectedSeat].focus();
});
playerCount.addEventListener("change", () => {
  const count = Number(playerCount.value);
  if (!Number.isSafeInteger(count) || count < 3) {
    playerCount.value = benchPlayers.length;
    benchStatus.textContent = "Choose a whole number of at least 3 players.";
    return;
  }
  if (count < benchPlayers.length && benchPlayers.slice(count).some(Boolean)) {
    playerCount.value = benchPlayers.length;
    benchStatus.textContent = "Remove players from the last seats before reducing the bench.";
    return;
  }
  benchPlayers = Array.from({ length: count }, (_, index) => benchPlayers[index] || null);
  renderBenchSeats();
});
useRoster.addEventListener("click", () => {
  if (pending) {
    benchStatus.textContent = "Wait for the current chat response before sending your roster.";
    return;
  }
  const enteredPlayers = benchPlayers.filter(Boolean);
  if (enteredPlayers.length < 3) return;
  const playerLines = enteredPlayers.map((player) =>
    `${player.name} — Rating ${player.rating}/5 — ${player.goalkeeper_willing ? "Willing to play goalkeeper" : "Not willing to play goalkeeper"}`
  );
  input.value = `Please save my complete roster:\n\n${playerLines.join("\n")}\n\nShow me the saved roster.`;
  location.hash = "chat";
  showStadiumScreen();
  form.requestSubmit();
});
window.addEventListener("hashchange", showStadiumScreen);
window.addEventListener("load-sample-roster", () => {
  benchPlayers = [
    { name: "Sara", rating: 5, goalkeeper_willing: true },
    { name: "Ahmed", rating: 4, goalkeeper_willing: false },
    { name: "Maya", rating: 3, goalkeeper_willing: false },
    { name: "Omar", rating: 2, goalkeeper_willing: false },
    { name: "Leo", rating: 1, goalkeeper_willing: false },
    { name: "Nina", rating: 5, goalkeeper_willing: true },
    { name: "Ali", rating: 4, goalkeeper_willing: false },
    { name: "Eva", rating: 3, goalkeeper_willing: false },
    { name: "Sam", rating: 2, goalkeeper_willing: false },
    { name: "Noah", rating: 1, goalkeeper_willing: false },
  ];
  playerCount.value = benchPlayers.length;
  renderBenchSeats();
  location.hash = "team";
});
renderBenchSeats();
showStadiumScreen();
