async function listSummaries() {
  const { websiteEndpoint, resultsPrefix } = window.APP_CONFIG;
  const prefix = `${resultsPrefix}/`;

  // S3 Static Website no expone ListBucket; asumimos una "índice" básica escaneando por convención
  // Estrategia simple: probamos a descubrir los últimos 10 subdirectorios mediante un archivo "index.json".
  // Para MVP: el usuario puede pegar IDs o refrescar conocidos. Aquí implementamos un "descubridor" simple:
  // -> Hacemos fetch de un archivo opcional "results/index.json" si existe.
  let indexUrl = `http://${websiteEndpoint}/${resultsPrefix}/index.json`;
  try {
    const res = await fetch(indexUrl);
    if (res.ok) {
      const ids = await res.json();
      return ids; // array de upload_ids
    }
  } catch(e) { /* ignore */ }

  // Si no hay índice, pedimos al usuario el ID manualmente
  return [];
}

async function fetchJSON(path) {
  const { websiteEndpoint } = window.APP_CONFIG;
  const url = `http://${websiteEndpoint}/${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

function summarizeCounts(counts) {
  const frag = document.createDocumentFragment();
  Object.entries(counts).forEach(([k,v]) => {
    const span = document.createElement("span");
    span.textContent = `${k}: ${v}`;
    frag.appendChild(span);
  });
  return frag;
}

async function refresh() {
  const runsEl = document.getElementById("runs");
  runsEl.innerHTML = "";
  const ids = await listSummaries();

  if (!ids.length) {
    runsEl.innerHTML = `<li>No hay índice de runs todavía. Abre la URL directa de un run: <code>/results/{upload_id}/summary.json</code></li>`;
    return;
  }

  for (const id of ids) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${id}</strong> — <button data-id="${id}">Ver</button>`;
    runsEl.appendChild(li);
  }

  runsEl.addEventListener("click", async (e) => {
    if (e.target.tagName === "BUTTON") {
      const id = e.target.getAttribute("data-id");
      await showRun(id);
    }
  }, { once: true });
}

async function showRun(id) {
  const details = document.getElementById("details");
  const runId = document.getElementById("runId");
  const counts = document.getElementById("counts");
  const sample = document.getElementById("sample");

  runId.textContent = id;

  const summary = await fetchJSON(`${APP_CONFIG.resultsPrefix}/${id}/summary.json`);
  counts.innerHTML = "";
  counts.appendChild(summarizeCounts(summary.counts));

  const jsonlUrl = `http://${APP_CONFIG.websiteEndpoint}/${APP_CONFIG.resultsPrefix}/${id}/predictions.jsonl`;
  const res = await fetch(jsonlUrl);
  const text = await res.text();
  const lines = text.trim().split("\n").slice(0, 5);
  sample.textContent = lines.join("\n");

  details.classList.remove("hidden");
}

document.getElementById("refresh").addEventListener("click", refresh);

// Primer render
window.addEventListener("DOMContentLoaded", refresh);
