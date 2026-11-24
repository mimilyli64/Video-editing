import { api } from "./api.js";
import { $, $$, esc, toast, errMsg, fmtDate, demoBanner, signaturePad, downloadPdf, pdfBase64, ask, showDoc } from "./ui.js";
import { ETAPES, DOCUMENTS, STATUTS_DOC, etapesPour } from "./etapes.js";
import { signedContractHtml, formuleLabel, contratDe, euros, signeParLesDeux, nomFichierContrat } from "./contrat-view.js";
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
      <div class="stat"><b>${n((c) => c.to_sign)}</b><span>contrats à signer par Lougha</span></div>
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
        ${c.to_sign ? `<span class="badge badge-wait">✍️ À signer</span>` : ""}
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
        ${c ? `<button class="btn btn-ghost btn-sm" id="b-c">📄 Voir le contrat</button>` : `<span class="badge badge-wait">Contrat pas encore signé</span>`}
      </div>
      ${c ? `<div class="sign-box ${signeParLesDeux(c) ? "ok" : "todo"}">
        ${signeParLesDeux(c)
          ? `<div><strong>✓ Contrat signé par les deux parties</strong>
               <p class="hint" style="margin:2px 0 0">Signé pour Lougha Online${c.provider_signer ? ` par ${esc(c.provider_signer)}` : ""} le ${fmtDate(c.provider_signed_at, true)}
               · ${c.emailed_at ? `copie envoyée à ${esc(p.email)} le ${fmtDate(c.emailed_at, true)}` : "copie pas encore envoyée"}</p></div>
             <button class="btn btn-ghost btn-sm" id="b-mail">📧 ${c.emailed_at ? "Renvoyer" : "Envoyer"} la copie par email</button>`
          : `<div><strong>✍️ À signer par Lougha Online</strong>
               <p class="hint" style="margin:2px 0 0">Le candidat a signé le ${fmtDate(c.signed_at)}. Signe à ton tour : la copie lui sera envoyée par email automatiquement.</p></div>
             <button class="btn btn-primary btn-sm" id="b-sign">Signer le contrat</button>`}
      </div>` : ""}
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

  $("#b-c")?.addEventListener("click", () => openModal({ ...c, email: p.email }));
  $("#b-sign")?.addEventListener("click", () => openProviderSign({ ...c, email: p.email }));
  $("#b-mail")?.addEventListener("click", async (e) => {
    e.target.disabled = true;
    try { await emailCopy({ ...c, email: p.email }); await refresh(); }
    catch (err) { toast(errMsg(err), "err"); e.target.disabled = false; }
  });

  $("#b-paid")?.addEventListener("click", async () => {
    const note = await ask({ title: "Marquer comme payé",
      message: `Paiement de ${euros(contratDe(c.contract_type).prix)} reçu en dehors du site. Le dossier du candidat s'ouvrira.`,
      input: "Note (ex. reçu envoyé sur WhatsApp le 12/01)", ok: "Marquer comme payé" });
    if (note === null) return;
    try {
      await api.updateProfile(p.id, { paid_at: new Date().toISOString(), paid_amount: contratDe(c.contract_type).prix,
        payment_method: c.payment_method, payment_ref: note || "Validé par l'équipe" });
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
    const doc = docs.find((x) => x.id === a.dataset.open);
    try { showDoc(await api.docUrl(doc), doc.file_name); }
    catch (err) { toast(errMsg(err), "err"); }
  }));
  $$("[data-ok]", det).forEach((b) => b.addEventListener("click", async () => {
    const doc = docs.find((x) => x.id === b.dataset.ok);
    if (doc.doc_type === TYPE_RECU && c && !p.paid_at) {
      if (!await ask({ title: "Valider ce reçu ?", message: `Paiement de ${euros(contratDe(c.contract_type).prix)}. Le dossier du candidat s'ouvrira.`, ok: "Valider le reçu" })) return;
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
  $$("[data-ko]", det).forEach((b) => b.addEventListener("click", async () => {
    const why = await ask({ title: "Demander de refaire ce document", message: "Ce message sera affiché au candidat.",
      input: "Ex. Photo floue, merci de la reprendre", ok: "Envoyer la demande" });
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
// ── Contrat : affichage, signature du Prestataire, envoi par email ──
let modalContract = null;
function openModal(c, extraHtml = "") {
  modalContract = c;
  $("#modal-title").textContent = signeParLesDeux(c) ? "Contrat signé par les deux parties" : "Contrat";
  $("#modal-body").innerHTML = signedContractHtml(c) + extraHtml;
  $("#modal").hidden = false;
}
$("#b-print").addEventListener("click", async (e) => {
  if (!modalContract) return;
  e.target.disabled = true;
  try { await downloadPdf(signedContractHtml(modalContract), nomFichierContrat(modalContract)); }
  catch (err) { toast(errMsg(err), "err"); }
  e.target.disabled = false;
});

function openProviderSign(c) {
  openModal(c, `
    <form id="f-psign" class="card" style="margin-top:20px" novalidate>
      <h3 style="font-size:1.1rem;margin:0 0 6px">Signature de Lougha Online (Prestataire)</h3>
      <p class="hint">Vérifie le contrat ci-dessus, puis signe. Une copie PDF sera envoyée automatiquement à <strong>${esc(c.email)}</strong>.</p>
      <div class="field" style="max-width:360px"><label for="p-name">Signé par (nom et prénom)</label>
        <input id="p-name" value="${esc(me.full_name || "")}" autocomplete="name"></div>
      <div class="sigpad" id="p-sigpad"><canvas></canvas><div class="ph-text">Signe ici</div></div>
      <p style="text-align:right;margin:8px 0 14px"><button type="button" class="btn btn-ghost btn-sm" id="p-clear">Effacer</button></p>
      <button class="btn btn-primary btn-block" id="p-submit">Signer et envoyer la copie au candidat</button>
    </form>`);
  const pad = signaturePad($("#p-sigpad"));
  $("#p-clear").addEventListener("click", pad.clear);
  $("#f-psign").scrollIntoView({ behavior: "smooth", block: "start" });
  setTimeout(pad.resize, 400);
  $("#f-psign").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = $("#p-name").value.trim();
    if (name.length < 3) { $("#p-name").focus(); return toast("Indique le nom de la personne qui signe.", "err"); }
    if (pad.isEmpty()) return toast("Ajoute ta signature.", "err");
    const btn = $("#p-submit"); btn.disabled = true; btn.textContent = "Signature…";
    try {
      const signed = await api.signAsProvider(c.user_id, { provider_signature_data: pad.toDataURL(), provider_signer: name });
      btn.textContent = "Envoi de la copie par email…";
      let mailed = false;
      try { await emailCopy({ ...signed, email: c.email }); mailed = true; }
      catch (err) { toast("Contrat signé ✔ mais l'email n'est pas parti : " + errMsg(err), "err"); }
      $("#modal").hidden = true;
      if (mailed) toast("Contrat signé ✔ Copie envoyée au candidat.");
      await refresh();
    } catch (err) {
      toast(errMsg(err), "err"); btn.disabled = false; btn.textContent = "Signer et envoyer la copie au candidat";
    }
  });
}

async function emailCopy(c) {
  const b64 = await pdfBase64(signedContractHtml(c), nomFichierContrat(c));
  const r = await api.sendContractEmail(c.user_id, b64, nomFichierContrat(c));
  toast(r?.demo ? "Mode démo : l'email n'est pas réellement envoyé." : `Copie envoyée à ${c.email} ✔`);
}

loadList().catch((e) => (app.innerHTML = `<div class="card empty">${esc(errMsg(e))}</div>`));
