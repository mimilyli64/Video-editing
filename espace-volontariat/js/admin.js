import { api } from "./api.js";
import { $, $$, esc, toast, errMsg, fmtDate, demoBanner } from "./ui.js";
import { ETAPES, DOCUMENTS, STATUTS_DOC, etapesPour } from "./etapes.js";
import { signedContractHtml, formuleLabel, contratDe, euros } from "./contrat-view.js";
import { CONTRATS } from "./contrat.js";
import { METHODES, TYPE_RECU } from "./paiement.js";

demoBanner();
const app = $("#app");
const user = await api.getUser();
if (!user) location.replace("connexion.html");
$("#b-logout").addEventListener("click", async () => { await api.signOut(); location.replace("index.html"); });

const me = await api.getProfile().catch(() => null);
if (me?.role !== "admin") {
  app.innerHTML = `<div class="card empty">Cette page est réservée à l'équipe.<br><br><a class="btn btn-primary" href="espace.html">Aller à mon espace</a></div>`;
  throw new Error("not admin");
}

let candidates = [], selected = null, filter = { q: "", stage: "all", type: "all", pending: false };

async function loadList() {
  candidates = await api.listCandidates();
  renderShell();
}

function renderShell() {
  const n = (f) => candidates.filter(f).length;
  app.innerHTML = `
    <div class="stats">
      <div class="stat"><b>${candidates.length}</b><span>candidats</span></div>
      <div class="stat"><b>${n((c) => !c.paid_at)}</b><span>pas encore signé ou payé</span></div>
      <div class="stat"><b>${candidates.reduce((s, c) => s + c.docs_pending, 0)}</b><span>documents à vérifier</span></div>
      <div class="stat"><b>${n((c) => c.stage === 5)}</b><span>visas obtenus</span></div>
    </div>
    <div class="admin-layout">
      <div class="card cand-list">
        <div class="search">
          <input id="q" placeholder="Rechercher un nom ou un email" value="${esc(filter.q)}">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <select id="st"><option value="all">Toutes les étapes</option>
              ${ETAPES.map((e) => `<option value="${e.id}" ${String(e.id) === filter.stage ? "selected" : ""}>${e.id + 1}. ${e.court}</option>`).join("")}</select>
            <select id="ty"><option value="all">Toutes formules</option>
              ${Object.entries(CONTRATS).map(([k, c]) => `<option value="${k}" ${k === filter.type ? "selected" : ""}>${esc(c.nom)} (${esc(c.sousTitre)})</option>`).join("")}</select>
            <label class="check" style="white-space:nowrap;align-items:center;margin:0;grid-column:1/-1"><input type="checkbox" id="pd" ${filter.pending ? "checked" : ""}> À vérifier</label>
          </div>
        </div>
        <div id="list"></div>
      </div>
      <div id="detail"><div class="card empty">Sélectionne un candidat dans la liste.</div></div>
    </div>`;
  $("#q").addEventListener("input", (e) => { filter.q = e.target.value; renderList(); });
  $("#st").addEventListener("change", (e) => { filter.stage = e.target.value; renderList(); });
  $("#pd").addEventListener("change", (e) => { filter.pending = e.target.checked; renderList(); });
  $("#ty").addEventListener("change", (e) => { filter.type = e.target.value; renderList(); });
  renderList();
  if (selected) openCandidate(selected);
}

function renderList() {
  const q = filter.q.toLowerCase();
  const rows = candidates.filter((c) =>
    (!q || `${c.full_name} ${c.email}`.toLowerCase().includes(q)) &&
    (filter.stage === "all" || String(c.stage || 0) === filter.stage) &&
    (filter.type === "all" || c.contract_type === filter.type) &&
    (!filter.pending || c.docs_pending > 0));
  $("#list").innerHTML = rows.length ? rows.map((c) => `
    <button class="cand ${c.id === selected ? "on" : ""}" data-id="${c.id}">
      <div class="nm">${esc(c.full_name || c.email)}</div>
      <div class="hint">${esc(c.email)}</div>
      <div class="meta">
        <span class="badge badge-navy">${(c.stage || 0) + 1}. ${ETAPES[c.stage || 0].court}</span>
        ${c.contract_type ? `<span class="badge badge-none">${esc(formuleLabel(c.contract_type, c.duration))}</span>` : ""}
        ${c.contract_type && !c.paid_at ? `<span class="badge badge-wait">Non payé</span>` : ""}
        ${c.docs_pending ? `<span class="badge badge-wait">${c.docs_pending} à vérifier</span>` : ""}
      </div>
    </button>`).join("") : `<p class="empty">Aucun candidat.</p>`;
  $$(".cand").forEach((b) => b.addEventListener("click", () => openCandidate(b.dataset.id)));
}

async function openCandidate(id) {
  selected = id;
  $$(".cand").forEach((b) => b.classList.toggle("on", b.dataset.id === id));
  const det = $("#detail");
  det.innerHTML = `<div class="card empty">Chargement…</div>`;
  try {
    const [p, c, docs] = await Promise.all([api.getProfile(id), api.getContract(id), api.listDocuments(id)]);
    renderDetail(p, c, docs);
    if (innerWidth < 900) det.scrollIntoView({ behavior: "smooth" });
  } catch (e) { det.innerHTML = `<div class="card empty">${esc(errMsg(e))}</div>`; }
}

const toLocalInput = (d) => (d ? new Date(new Date(d).getTime() - new Date(d).getTimezoneOffset() * 6e4).toISOString().slice(0, 16) : "");

function renderDetail(p, c, docs) {
  const det = $("#detail");
  det.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:start">
        <div><h2 style="font-size:1.35rem;margin:0">${esc(p.full_name || p.email)}</h2>
          <p class="hint" style="margin:4px 0 0">${esc(p.email)} · inscrit le ${fmtDate(p.created_at)}</p></div>
        ${c ? `<button class="btn btn-ghost btn-sm" id="b-c">📄 Voir le contrat signé</button>` : `<span class="badge badge-wait">Contrat pas encore signé</span>`}
      </div>
      ${c ? `<dl class="kv" style="margin-top:18px">
        <dt>Formule</dt><dd>${esc(formuleLabel(c.contract_type, c.duration))}</dd>
        <dt>Nom complet</dt><dd>${esc(c.first_name)} ${esc(c.last_name)}</dd>
        <dt>Naissance</dt><dd>${fmtDate(c.birth_date)} à ${esc(c.birth_place)}</dd>
        <dt>Nationalité</dt><dd>${esc(c.nationality)}</dd>
        <dt>Passeport</dt><dd>${esc(c.passport_number)}</dd>
        <dt>Téléphone</dt><dd><a href="tel:${esc(c.phone)}">${esc(c.phone)}</a></dd>
        <dt>Adresse</dt><dd>${esc(c.address)}</dd>
        <dt>Contrat signé le</dt><dd>${fmtDate(c.signed_at, true)} (version ${esc(c.contract_version)})</dd>
        <dt>Paiement</dt><dd>${euros(contratDe(c.contract_type).prix)} par ${esc(METHODES[c.payment_method]?.label || "—")} ·
          ${p.paid_at
          ? `<span class="badge badge-ok">Payé</span> le ${fmtDate(p.paid_at)}${p.payment_ref ? ` <span class="hint">(${esc(p.payment_ref)})</span>` : ""}`
          : docs.some((x) => x.doc_type === TYPE_RECU && x.status === "en_attente")
            ? `<span class="badge badge-wait">Reçu à vérifier ↓</span>`
            : `<span class="badge badge-none">En attente du reçu</span>
               <button class="btn btn-ok btn-sm" id="b-paid" style="margin-left:6px">Marquer comme payé</button>`}</dd>
      </dl>` : ""}
    </div>

    <form class="card" id="f-p">
      <h2 style="font-size:1.1rem">Suivi du dossier</h2>
      <div class="grid-2">
        <div class="field"><label>Étape actuelle</label>
          <select name="stage" ${c ? "" : "disabled"}>${etapesPour(c?.contract_type || "long").map((e) => `<option value="${e.id}" ${e.id === (p.stage || 0) ? "selected" : ""} ${e.id === 0 && c ? "disabled" : ""}>${e.id + 1}. ${e.titre}</option>`).join("")}</select></div>
        <div class="field"><label>Date du test d'allemand</label><input type="date" name="test_date" value="${esc(p.test_date || "")}"></div>
        <div class="field"><label>Résultat du test</label><input name="test_result" placeholder="Ex. B1 Goethe — réussi" value="${esc(p.test_result || "")}"></div>
        <div class="field"><label>Date d'entretien</label><input type="datetime-local" name="interview_date" value="${toLocalInput(p.interview_date)}"></div>
        <div class="field"><label>Rendez-vous visa</label><input type="datetime-local" name="visa_appointment" value="${toLocalInput(p.visa_appointment)}"></div>
      </div>
      <div class="field"><label>Message affiché au candidat</label>
        <textarea name="admin_message" rows="3" placeholder="Ex. Ton CV doit être traduit en allemand avant vendredi.">${esc(p.admin_message || "")}</textarea></div>
      <button class="btn btn-primary">Enregistrer</button>
    </form>

    <div class="card docgroup">
      <h2 style="font-size:1.1rem">Documents (${docs.length})</h2>
      ${[{ titre: "Paiement", types: [{ type: TYPE_RECU, label: `Reçu de paiement — ${c ? euros(contratDe(c.contract_type).prix) + " par " + (METHODES[c.payment_method]?.label || "") : ""}` }] },
         ...etapesPour(c?.contract_type || "long").slice(1).map((e) => ({ titre: e.titre, types: DOCUMENTS.filter((d) => d.etape === e.id) }))].map((g) => {
        const types = g.types;
        if (!types.length) return "";
        return `<h3>${esc(g.titre)}</h3>` + types.map((t) => {
          const files = docs.filter((x) => x.doc_type === t.type);
          return `<div class="doc"><div>
            <div class="name">${esc(t.label)}</div>
            ${files.length ? files.map((x) => `<div class="files"><div class="f">
              <a data-open="${x.id}">${esc(x.file_name)}</a>
              <span class="badge ${STATUTS_DOC[x.status].cls}">${STATUTS_DOC[x.status].label}</span>
              <span class="hint">${fmtDate(x.uploaded_at)}</span>
              ${x.comment ? `<span class="comment">— ${esc(x.comment)}</span>` : ""}
              </div>
              <div class="f" style="margin-top:4px">
                ${x.status !== "valide" ? `<button class="btn btn-ok btn-sm" data-ok="${x.id}">✓ Valider</button>` : ""}
                ${x.status !== "refuse" ? `<button class="btn btn-danger btn-sm" data-ko="${x.id}">✕ Demander de refaire</button>` : ""}
              </div></div>`).join("") : `<div class="files">Pas encore envoyé</div>`}
          </div></div>`;
        }).join("");
      }).join("")}
    </div>`;

  $("#b-c")?.addEventListener("click", () => {
    $("#modal-body").innerHTML = signedContractHtml({ ...c, email: p.email });
    $("#modal").hidden = false;
  });

  $("#b-paid")?.addEventListener("click", async () => {
    const note = prompt(`Paiement de ${euros(contratDe(c.contract_type).prix)} reçu sans reçu sur le site.\nNote (ex. « reçu envoyé sur WhatsApp le 12/01 ») :`);
    if (note === null) return;
    try {
      await api.updateProfile(p.id, { paid_at: new Date().toISOString(), paid_amount: contratDe(c.contract_type).prix,
        payment_method: c.payment_method, payment_ref: note.trim() || "Validé par l'équipe" });
      toast("Paiement enregistré ✔"); await refresh();
    } catch (err) { toast(errMsg(err), "err"); }
  });

  $("#f-p").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const patch = {
      test_date: fd.get("test_date") || null,
      test_result: fd.get("test_result").trim(),
      interview_date: fd.get("interview_date") ? new Date(fd.get("interview_date")).toISOString() : null,
      visa_appointment: fd.get("visa_appointment") ? new Date(fd.get("visa_appointment")).toISOString() : null,
      admin_message: fd.get("admin_message").trim(),
    };
    if (fd.get("stage") !== null) patch.stage = Number(fd.get("stage"));
    try { await api.updateProfile(p.id, patch); toast("Dossier mis à jour ✔"); await refresh(); }
    catch (err) { toast(errMsg(err), "err"); }
  });

  $$("[data-open]", det).forEach((a) => a.addEventListener("click", async (e) => {
    e.preventDefault();
    const w = window.open("", "_blank");
    try {
      const url = await api.docUrl(docs.find((x) => x.id === a.dataset.open));
      if (w) { if (url.startsWith("data:")) w.document.write(`<iframe src="${url}" style="border:0;width:100%;height:100%"></iframe>`); else w.location = url; }
    } catch (err) { w?.close(); toast(errMsg(err), "err"); }
  }));
  $$("[data-ok]", det).forEach((b) => b.addEventListener("click", async () => {
    const doc = docs.find((x) => x.id === b.dataset.ok);
    if (doc.doc_type === TYPE_RECU && c && !p.paid_at) {
      if (!confirm(`Valider ce reçu de ${euros(contratDe(c.contract_type).prix)} ?\nLe dossier du candidat s'ouvrira.`)) return;
      try {
        await api.reviewDocument(doc.id, "valide");
        await api.updateProfile(p.id, { paid_at: new Date().toISOString(), paid_amount: contratDe(c.contract_type).prix,
          payment_method: c.payment_method, payment_ref: "Reçu validé" });
        toast("Paiement validé ✔ Le dossier du candidat est ouvert."); await refresh();
      } catch (err) { toast(errMsg(err), "err"); }
      return;
    }
    review(doc.id, "valide");
  }));
  $$("[data-ko]", det).forEach((b) => b.addEventListener("click", () => {
    const why = prompt("Que doit corriger le candidat ? (ce message lui sera affiché)");
    if (why !== null) review(b.dataset.ko, "refuse", why);
  }));
}

async function review(id, status, comment) {
  try { await api.reviewDocument(id, status, comment); toast(status === "valide" ? "Document validé ✔" : "Demande envoyée au candidat"); await refresh(); }
  catch (e) { toast(errMsg(e), "err"); }
}

async function refresh() {
  candidates = await api.listCandidates();
  const scroll = scrollY;
  renderShell();
  scrollTo(0, scroll);
}

$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal" || e.target.matches("[data-close]")) $("#modal").hidden = true; });
$("#b-print").addEventListener("click", () => { document.body.classList.add("printing"); window.print(); document.body.classList.remove("printing"); });

loadList().catch((e) => (app.innerHTML = `<div class="card empty">${esc(errMsg(e))}</div>`));
