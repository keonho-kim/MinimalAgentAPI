import { scrollToBottom } from "./dom.mjs";
import {
  activityPath,
  activityRenderKey,
  activityStatusText,
  activityTitleText,
  formatActivitySummary,
  shouldRenderActivity,
} from "./format.mjs";

export function upsertActivity(turn, activityCards, activity) {
  if (!shouldRenderActivity(activity)) {
    return;
  }

  const renderKey = activityRenderKey(activity);
  let card = activityCards.get(renderKey);

  if (!card) {
    card = createActivityCard();
    activityCards.set(renderKey, card);
    turn.body.appendChild(card.element);
  }

  renderActivityCard(card, activity);
  scrollToBottom();
}

function createActivityCard() {
  const element = document.createElement("section");
  element.className = "activity-card";

  const header = document.createElement("div");
  header.className = "activity-header";

  const status = document.createElement("span");
  status.className = "activity-status";

  const title = document.createElement("span");
  title.className = "activity-title";

  const path = document.createElement("span");
  path.className = "activity-path";

  const details = document.createElement("details");
  details.className = "activity-details";

  const summary = document.createElement("summary");
  summary.textContent = "Details";

  const body = document.createElement("pre");
  body.className = "activity-payload";

  details.append(summary, body);
  header.append(status, title);
  element.append(header, path, details);

  return {
    element,
    status,
    title,
    path,
    details,
    body,
  };
}

function renderActivityCard(card, activity) {
  card.element.className = `activity-card ${activity.type} ${activity.status}`;
  card.status.textContent = activityStatusText(activity.status);
  card.title.textContent = activityTitleText(activity);

  const path = activityPath(activity);
  card.path.textContent = path;
  card.path.hidden = !path;

  const details = formatActivitySummary(activity.summary || {});
  card.body.textContent = details;
  card.details.hidden = !details;
}
