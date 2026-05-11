const state = {
  bootstrap: null,
  selectedProjectId: null,
};

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: "Request failed" }));
    throw new Error(payload.error || "Request failed");
  }
  return response.json();
}

function renderSummary(summary) {
  const root = document.getElementById("summary-grid");
  root.innerHTML = "";
  const items = [
    ["Projects", summary.project_count],
    ["Open Tasks", summary.open_tasks],
    ["Notes", summary.note_count],
    ["Energy", `${summary.avg_energy}%`],
  ];
  items.forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<strong>${value}</strong><span>${label}</span>`;
    root.appendChild(card);
  });

  const radar = document.getElementById("radar");
  radar.innerHTML = "";
  summary.radar.forEach((item) => {
    const row = document.createElement("div");
    row.className = "radar-row";
    row.innerHTML = `
      <span>${item.label}</span>
      <div class="bar"><span style="width:${item.value}%"></span></div>
      <strong>${item.value}</strong>
    `;
    radar.appendChild(row);
  });
}

function renderHardware(hardware) {
  const root = document.getElementById("hardware");
  root.innerHTML = "";
  const groups = [
    ["CPU", hardware.cpu],
    ["GPU", hardware.gpu],
    ["NPU / AI", hardware.npu],
  ];
  groups.forEach(([title, items]) => {
    const card = document.createElement("div");
    card.className = "hardware-card";
    const chips = items.length
      ? items.map((item) => `<span class="hardware-chip">${item}</span>`).join("")
      : `<span class="hardware-chip">탐지된 항목 없음</span>`;
    card.innerHTML = `<h4>${title}</h4><div class="chip-row">${chips}</div>`;
    root.appendChild(card);
  });

  hardware.ideas.forEach((idea) => {
    const card = document.createElement("div");
    card.className = "hardware-card";
    card.innerHTML = `<h4>${idea.title}</h4><p>${idea.description}</p>`;
    root.appendChild(card);
  });
}

function renderProjectCards(projects) {
  const root = document.getElementById("project-list");
  const template = document.getElementById("project-card-template");
  root.innerHTML = "";

  projects.forEach((project) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.dataset.projectId = project.id;
    node.querySelector(".project-name").textContent = project.name;
    node.querySelector(".project-meta").textContent = `${project.area || "general"} / ${project.priority} / ${project.path || "경로 없음"}`;
    node.querySelector(".project-energy").textContent = `${project.energy}% energy`;
    node.querySelector(".project-summary").textContent = project.summary || "요약 없음";
    node.querySelector(".project-status").textContent = project.status;
    node.querySelector(".project-tasks").textContent = `${project.open_tasks} open tasks`;
    node.addEventListener("click", () => selectProject(project.id));
    root.appendChild(node);
  });
}

function detailSection(title, content) {
  return `<section><p class="section-label">${title}</p>${content}</section>`;
}

function renderProjectDetail(project) {
  const root = document.getElementById("project-detail");
  root.classList.remove("empty-state");

  const taskItems = project.tasks.length
    ? project.tasks.map((task) => `
      <div class="task-item">
        <div>
          <strong>${task.title}</strong>
          <p>${task.status}${task.due ? ` / due ${task.due}` : ""}</p>
        </div>
        ${task.status !== "done" ? `<button data-task-id="${task.id}">done</button>` : "<span>done</span>"}
      </div>
    `).join("")
    : `<div class="task-item"><div><strong>열린 할 일이 없습니다.</strong></div></div>`;

  const logItems = project.logs.length
    ? project.logs.map((log) => `
      <div class="timeline-item">
        <strong>${log.summary}</strong>
        <p>${log.status}${log.progress !== null ? ` / ${log.progress}%` : ""} / ${log.created_at}</p>
      </div>
    `).join("")
    : `<div class="timeline-item"><strong>진행 로그가 아직 없습니다.</strong></div>`;

  const noteItems = project.notes.length
    ? project.notes.map((note) => `
      <div class="note-item">
        <strong>${note.kind}</strong>
        <p>${note.content}</p>
      </div>
    `).join("")
    : `<div class="note-item"><strong>메모가 아직 없습니다.</strong></div>`;

  const linkItems = project.links.length
    ? project.links.map((link) => `
      <div class="link-item">
        <strong>${link.label}</strong>
        <p>${link.kind} / ${link.value}</p>
      </div>
    `).join("")
    : `<div class="link-item"><strong>연결된 링크가 없습니다.</strong></div>`;

  root.innerHTML = `
    <h2>${project.name}</h2>
    <p>${project.summary || ""}</p>
    <div class="status-inline">
      <span>${project.status}</span>
      <span>${project.priority}</span>
      <span>${project.area || "general"}</span>
      <span>${project.energy}% energy</span>
      <span>${project.path || "path not set"}</span>
    </div>
    <div class="detail-grid">
      <div class="detail-stat"><strong>Vision</strong><p>${project.vision || "장기 비전이 아직 없습니다."}</p></div>
      <div class="detail-stat"><strong>Updated</strong><p>${project.updated_at}</p></div>
      <div class="detail-stat"><strong>Linked Surface</strong><p>${project.links.length} links, ${project.notes.length} notes</p></div>
    </div>
    ${detailSection("Open Tasks", `<div class="task-list">${taskItems}</div>`)}
    ${detailSection("Activity Stream", `<div class="timeline">${logItems}</div>`)}
    ${detailSection("Notes", `<div class="note-list">${noteItems}</div>`)}
    ${detailSection("Links", `<div class="link-list">${linkItems}</div>`)}
  `;

  root.querySelectorAll("button[data-task-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await request("/api/tasks/status", {
        method: "PATCH",
        body: JSON.stringify({ task_id: Number(button.dataset.taskId), status: "done" }),
      });
      await refreshAndReselect(project.id);
    });
  });

  document.querySelectorAll(".project-card").forEach((card) => {
    card.classList.toggle("active", Number(card.dataset.projectId) === project.id);
  });
}

async function selectProject(projectId) {
  state.selectedProjectId = projectId;
  const project = await request(`/api/project?id=${projectId}`);
  renderProjectDetail(project);
}

async function refreshBootstrap() {
  state.bootstrap = await request("/api/bootstrap");
  renderSummary(state.bootstrap.summary);
  renderHardware(state.bootstrap.hardware);
  renderProjectCards(state.bootstrap.projects);
}

async function refreshAndReselect(projectId) {
  await refreshBootstrap();
  const nextId = projectId || state.selectedProjectId || state.bootstrap.projects[0]?.id;
  if (nextId) {
    await selectProject(nextId);
  } else {
    document.getElementById("project-detail").textContent = "프로젝트를 추가해 첫 흐름을 시작해보세요.";
  }
}

function parseQuickCapture(projectId, type, line1, line2) {
  if (type === "task") {
    return {
      url: "/api/tasks",
      payload: { project_id: projectId, title: line1, due: line2 || "" },
    };
  }
  if (type === "log") {
    const [status, progressText] = (line2 || "").split("/");
    return {
      url: "/api/logs",
      payload: {
        project_id: projectId,
        summary: line1,
        status: (status || "working").trim(),
        progress: progressText ? Number(progressText.trim()) : null,
      },
    };
  }
  if (type === "note") {
    return {
      url: "/api/notes",
      payload: { project_id: projectId, content: line1, kind: (line2 || "memo").trim() },
    };
  }
  return {
    url: "/api/links",
    payload: {
      project_id: projectId,
      label: line1,
      kind: "reference",
      value: line2 || "",
    },
  };
}

function wireForms() {
  document.getElementById("project-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await request("/api/projects", {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        area: form.get("area"),
        path: form.get("path"),
        summary: form.get("summary"),
        vision: form.get("vision"),
        priority: form.get("priority"),
        energy: Number(form.get("energy") || 50),
        status: "idea",
      }),
    });
    event.currentTarget.reset();
    await refreshAndReselect();
  });

  document.getElementById("entry-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.selectedProjectId) {
      alert("먼저 프로젝트를 선택해주세요.");
      return;
    }
    const form = new FormData(event.currentTarget);
    const entry = parseQuickCapture(
      state.selectedProjectId,
      form.get("type"),
      form.get("line1"),
      form.get("line2"),
    );
    await request(entry.url, {
      method: "POST",
      body: JSON.stringify(entry.payload),
    });
    event.currentTarget.reset();
    await refreshAndReselect(state.selectedProjectId);
  });
}

async function boot() {
  wireForms();
  await refreshAndReselect();
}

boot().catch((error) => {
  document.getElementById("project-detail").textContent = error.message;
});
