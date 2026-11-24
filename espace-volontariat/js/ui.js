import { DEMO } from "./api.js";
import { NOM_ORGANISATION } from "./config.js";

export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];

export function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function toast(msg, type = "ok") {
  let box = $("#toasts");
  if (!box) { box = document.createElement("div"); box.id = "toasts"; document.body.append(box); }
  const t = document.createElement("div");
  t.className = `toast toast-${type}`; t.textContent = msg; box.append(t);
  setTimeout(() => t.classList.add("out"), 3800);
  setTimeout(() => t.remove(), 4300);
}

export function errMsg(e) {
  const m = e?.message || String(e);
  const fr = {
    "Invalid login credentials": "Email ou mot de passe incorrect.",
    "Email not confirmed": "Confirme d'abord ton email (regarde ta boîte de réception et les spams).",
    "User already registered": "Un compte existe déjà avec cet email.",
    "Password should be at least 6 characters.": "Le mot de passe doit faire au moins 6 caractères.",
  };
  return fr[m] || m;
}

export function fmtDate(d, withTime = false) {
  if (!d) return "—";
  const date = new Date(d);
  if (isNaN(date)) return "—";
  return date.toLocaleDateString("fr-FR", withTime
    ? { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "numeric", month: "long", year: "numeric" });
}

export function demoBanner() {
  if (!DEMO) return;
  const b = document.createElement("div");
  b.className = "demo-banner";
  b.innerHTML = `<strong>Mode démo</strong> · les données restent dans ce navigateur.
    <button type="button" class="demo-btn" id="demo-admin">Ouvrir l'espace équipe</button>
    <button type="button" class="demo-btn" id="demo-back" hidden>Revenir au compte candidat</button>`;
  document.body.prepend(b);
  const onAdmin = /admin\.html$/.test(location.pathname);
  import("./api.js").then(({ api }) => {
    b.querySelector("#demo-admin").hidden = onAdmin;
    b.querySelector("#demo-back").hidden = !(onAdmin && api.demoHasCandidate());
    b.querySelector("#demo-admin").addEventListener("click", async () => { await api.demoAdmin(); location.href = "admin.html"; });
    b.querySelector("#demo-back").addEventListener("click", async () => {
      if (await api.demoBack()) location.href = "espace.html";
    });
  });
}

// Bouton WhatsApp flottant (support). Rien ne s'affiche si aucun numéro n'est configuré.
export async function whatsappFab(message = "Bonjour, j'ai une question sur le volontariat en Allemagne.") {
  const { whatsappLink, WA_ICON } = await import("./paiement.js");
  const href = whatsappLink(message);
  if (!href || document.querySelector(".wa-fab")) return;
  const a = document.createElement("a");
  a.className = "wa-fab"; a.href = href; a.target = "_blank"; a.rel = "noopener";
  a.innerHTML = `${WA_ICON}<span>Support WhatsApp</span>`;
  document.body.append(a);
}

export function setTitle(page) { document.title = `${page} · ${NOM_ORGANISATION}`; }

// Fenêtre de confirmation intégrée à la page (remplace confirm() / prompt()).
// ask({ title, message, input: "placeholder" | undefined, ok }) → true / texte saisi, ou null si annulé.
export function ask({ title, message = "", input, ok = "Confirmer", value = "" }) {
  return new Promise((resolve) => {
    const d = document.createElement("div");
    d.className = "modal ask";
    d.innerHTML = `<form class="box" style="max-width:460px" novalidate>
      <h3 style="margin:0 0 8px;font-size:1.15rem">${esc(title)}</h3>
      ${message ? `<p class="hint" style="white-space:pre-line">${esc(message)}</p>` : ""}
      ${input !== undefined ? `<div class="field"><input id="ask-input" value="${esc(value)}" placeholder="${esc(input)}" autocomplete="off"></div>` : ""}
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px">
        <button type="button" class="btn btn-ghost btn-sm" data-no>Annuler</button>
        <button class="btn btn-primary btn-sm">${esc(ok)}</button>
      </div></form>`;
    const close = (v) => { d.remove(); resolve(v); };
    d.addEventListener("click", (e) => { if (e.target === d || e.target.matches("[data-no]")) close(null); });
    d.querySelector("form").addEventListener("submit", (e) => {
      e.preventDefault();
      close(input !== undefined ? d.querySelector("#ask-input").value.trim() : true);
    });
    document.body.append(d);
    (d.querySelector("#ask-input") || d.querySelector(".btn-primary")).focus();
  });
}

// Visionneuse de document dans la page (image ou PDF), avec lien d'ouverture dans un onglet.
export function showDoc(url, name = "") {
  const isImg = /\.(jpe?g|png|webp|gif|heic)$/i.test(name) || url.startsWith("data:image");
  const d = document.createElement("div");
  d.className = "modal";
  d.innerHTML = `<div class="box" style="width:min(900px,100%)">
    <header><strong style="overflow-wrap:anywhere">${esc(name)}</strong>
      <span style="display:flex;gap:8px">${url.startsWith("data:") ? "" : `<a class="btn btn-ghost btn-sm" href="${esc(url)}" target="_blank" rel="noopener">Ouvrir dans un onglet</a>`}
      <button class="btn btn-ghost btn-sm" data-no>Fermer</button></span></header>
    ${isImg ? `<img src="${esc(url)}" alt="${esc(name)}" style="display:block;margin:0 auto;border-radius:8px">`
            : `<iframe src="${esc(url)}" title="${esc(name)}" style="width:100%;height:70vh;border:0;border-radius:8px;background:#fff"></iframe>`}
  </div>`;
  d.addEventListener("click", (e) => { if (e.target === d || e.target.matches("[data-no]")) d.remove(); });
  document.body.append(d);
}

// Zone de signature au doigt / à la souris (dans un élément .sigpad contenant un <canvas>).
export function signaturePad(wrap) {
  const c = $("canvas", wrap), ctx = c.getContext("2d");
  let drawing = false, empty = true, last = null;
  function size() {
    const r = c.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    if (!r.width) return;
    const prev = empty ? null : c.toDataURL();
    c.width = r.width * dpr; c.height = r.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineWidth = 2.4; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = "#16233f";
    if (prev) { const img = new Image(); img.onload = () => ctx.drawImage(img, 0, 0, r.width, r.height); img.src = prev; }
  }
  const pos = (e) => { const r = c.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  c.addEventListener("pointerdown", (e) => { if (!c.width) size(); drawing = true; last = pos(e); c.setPointerCapture(e.pointerId); });
  c.addEventListener("pointermove", (e) => {
    if (!drawing) return;
    const p = pos(e);
    ctx.beginPath(); ctx.moveTo(last.x, last.y); ctx.lineTo(p.x, p.y); ctx.stroke();
    last = p; if (empty) { empty = false; wrap.classList.add("has"); }
  });
  ["pointerup", "pointercancel"].forEach((ev) => c.addEventListener(ev, () => (drawing = false)));
  window.addEventListener("resize", size);
  size();
  return {
    isEmpty: () => empty,
    clear: () => { ctx.clearRect(0, 0, c.width, c.height); empty = true; wrap.classList.remove("has"); },
    toDataURL: () => c.toDataURL("image/png"),
    resize: size,
  };
}

// ── PDF du contrat (généré dans le navigateur avec html2pdf.js) ──
const HTML2PDF = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
function loadHtml2pdf() {
  if (window.html2pdf) return Promise.resolve();
  return new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = HTML2PDF; s.onload = res; s.onerror = () => rej(new Error("Impossible de générer le PDF (connexion)."));
    document.head.append(s);
  });
}
function pdfWorker(html, filename) {
  const el = document.createElement("div");
  el.className = "pdf-page";
  el.innerHTML = html;
  return window.html2pdf().set({
    margin: [12, 12, 14, 12], filename,
    image: { type: "jpeg", quality: 0.92 },
    html2canvas: { scale: 2, backgroundColor: "#ffffff" },
    jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
    pagebreak: { mode: ["css", "legacy"], avoid: ["li", "p", ".sig-grid"] },
  }).from(el);
}
// Télécharge le PDF.
export async function downloadPdf(html, filename) {
  await loadHtml2pdf();
  await pdfWorker(html, filename).save();
}
// Renvoie le PDF encodé en base64 (pour l'envoyer par email).
export async function pdfBase64(html, filename) {
  await loadHtml2pdf();
  const uri = await pdfWorker(html, filename).outputPdf("datauristring");
  return uri.slice(uri.indexOf(",") + 1);
}

export async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
