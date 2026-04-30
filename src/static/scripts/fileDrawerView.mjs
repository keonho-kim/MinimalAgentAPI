import { elements } from "./dom.mjs";
import { fileMetaText } from "./format.mjs";

export function setFileDrawerOpen(open) {
  elements.fileDrawer.classList.toggle("open", open);
  elements.fileDrawer.setAttribute("aria-hidden", String(!open));
  elements.fileDrawerToggle.setAttribute("aria-expanded", String(open));
}

export function renderFileList(files) {
  elements.fileList.replaceChildren();

  if (files.length === 0) {
    const empty = document.createElement("li");
    empty.className = "file-empty";
    empty.textContent = "업로드된 파일이 없습니다.";
    elements.fileList.appendChild(empty);
    return;
  }

  for (const file of files) {
    const item = document.createElement("li");
    item.className = `file-item ${file.status || file.type || "file"}`;

    const name = document.createElement("span");
    name.className = "file-name";
    name.textContent = file.path || file.filename || file.name;

    const meta = document.createElement("span");
    meta.className = "file-meta";
    meta.textContent = file.file_id
      ? `${file.file_id} · ${file.file_type}`
      : fileMetaText(file);

    const status = document.createElement("span");
    status.className = "file-status";
    status.textContent = file.status || file.type || "file";

    item.append(name, meta, status);

    if (file.error) {
      const error = document.createElement("span");
      error.className = "file-error";
      error.textContent = file.error;
      item.appendChild(error);
    }

    elements.fileList.appendChild(item);
  }
}

export function setFileDrawerStatus(text) {
  elements.fileDrawerStatus.textContent = text;
}
