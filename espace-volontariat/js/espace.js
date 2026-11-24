import { api } from "./api.js";
import { $, $$, esc, toast, errMsg, fmtDate, demoBanner, sha256 } from "./ui.js";
import { ETAPES, DOCUMENTS, STATUTS_DOC } from "./etapes.js";
import { TITRE, VERSION } from "./contrat.js";
import { renderContract, signedContractHtml } from "./contrat-view.js";
import { LIEN_PLATEFORME, EMAIL_CONTACT } from "./config.js";

demoBanner();
$$("[data-plateforme]").forEach((a) => (a.href = LIEN_PLATEFORME));

const user = await api.getUser();
if (!user) location.replace("connexion.html");

$("#b-logout").addEventListener("click", async () => { await api.signOut(); location.replace("index.html"); });

const app = $("#app");
let profile, contract, docs;

async function load() {
  try {
    [profile, contract] = await Promise.all([api.getProfile(), api.getContract()]);
    if (!profile) throw new Error("Profil introuvable. Déconnecte-toi puis reconnecte-toi.");
    $("#l-admin").hidden = profile.role !== "admin";
    if (!contract) return renderSign();
    docs = await api.listDocuments();
    renderDashboard();
  } catch (e) {
    app.innerHTML = `<div class="card empty">${esc(errMsg(e))}</div>`;
  }
}

// ═════════════════════ 1. SIGNATURE DU CONTRAT ═════════════════════
function renderSign() {
  const [first = "", ...rest] = (profile.full_name || "").split(" ");
  const f = { first_name: first, last_name: rest.join(" "), email: user.email };

  app.innerHTML = `
    <div class="narrow" style="margin:0 auto">
      <div class="hello"><div>
        <span class="badge badge-navy">Étape 1 sur 6</span>
        <h1 style="margin-top:10px">Bienvenue ${esc(first)} 👋</h1>
        <p class="hint" style="margin:6px 0 0">Avant de commencer tes démarches, complète tes informations et signe ton contrat.</p>
      </div></div>

      <form id="f-sign" class="card" novalidate>
        <h2 style="font-size:1.15rem">1. Tes informations</h2>
        <p class="hint">Exactement comme sur ton passeport.</p>
        <div class="grid-2">
          ${field("first_name", "Prénom", f.first_name, "given-name")}
          ${field("last_name", "Nom", f.last_name, "family-name")}
          ${field("birth_date", "Date de naissance", "", "bday", "date")}
          ${field("birth_place", "Lieu de naissance", "")}
          ${field("nationality", "Nationalité", "")}
          ${field("passport_number", "Numéro de passeport", "")}
          ${field("phone", "Téléphone (WhatsApp)", "", "tel", "tel")}
          ${field("address", "Adresse complète", "", "street-address")}
        </div>

        <h2 style="font-size:1.15rem;margin-top:12px">2. Lis ton contrat</h2>
        <p style="font-weight:700;margin-bottom:10px">${esc(TITRE)}</p>
        <div class="contract-text" id="c-text"></div>

        <h2 style="font-size:1.15rem;margin-top:24px">3. Signe</h2>
        <p class="hint">Dessine ta signature avec ton doigt ou ta souris.</p>
        <div class="sigpad" id="sigpad"><canvas></canvas><div class="ph-text">Signe ici</div></div>
        <p style="text-align:right;margin:8px 0 18px"><button type="button" class="btn btn-ghost btn-sm" id="b-clear">Effacer</button></p>

        <label class="check field"><input type="checkbox" id="agree"> <span>J'ai lu le contrat en entier, mes informations sont exactes et j'accepte les conditions.</span></label>
        <button class="btn btn-gold btn-block" id="b-sign">Signer mon contrat</button>
      </form>
    </div>`;

  const form = $("#f-sign");
  const values = () => {
    const o = { email: user.email };
    $$("input[name]", form).forEach((i) => (o[i.name] = i.value.trim()));
    return o;
  };
  const refresh = () => ($("#c-text").innerHTML = renderContract(values(), true));
  form.addEventListener("input", refresh);
  refresh();

  const pad = signaturePad($("#sigpad"));
  $("#b-clear").addEventListener("click", pad.clear);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const v = values();
    const missing = $$("input[name]", form).filter((i) => !i.value.trim());
    if (missing.length) { missing[0].focus(); return toast("Complète tous les champs.", "err"); }
    if (pad.isEmpty()) return toast("Ajoute ta signature.", "err");
    if (!$("#agree").checked) return toast("Coche la case pour accepter le contrat.", "err");

    const btn = $("#b-sign"); btn.disabled = true; btn.textContent = "Signature en cours…";
    try {
      const accepted = renderContract({ ...v, signed_at: new Date() });
      const { email, ...fields } = v;
      await api.signContract({
        ...fields,
        contract_version: VERSION,
        contract_hash: await sha256(accepted),
        signature_data: pad.toDataURL(),
        user_agent: navigator.userAgent.slice(0, 300),
      });
      toast("Contrat signé ✔ Tu peux commencer tes démarches.");
      window.scrollTo(0, 0);
      await load();
    } catch (err) {
      toast(errMsg(err), "err");
      btn.disabled = false; btn.textContent = "Signer mon contrat";
    }
  });
}

function field(name, label, value = "", ac = "off", type = "text") {
  return `<div class="field"><label for="i-${name}">${label}</label>
    <input id="i-${name}" name="${name}" type="${type}" value="${esc(value)}" autocomplete="${ac}" required></div>`;
}

function signaturePad(wrap) {
  const c = $("canvas", wrap), ctx = c.getContext("2d");
  let drawing = false, empty = true, last = null;
  function size() {
    const r = c.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    const prev = empty ? null : c.toDataURL();
    c.width = r.width * dpr; c.height = r.height * dpr;
    ctx.scale(dpr, dpr);
    ctx.lineWidth = 2.4; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = "#16233f";
    if (prev) { const img = new Image(); img.onload = () => ctx.drawImage(img, 0, 0, r.width, r.height); img.src = prev; }
  }
  const pos = (e) => { const r = c.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  c.addEventListener("pointerdown", (e) => { drawing = true; last = pos(e); c.setPointerCapture(e.pointerId); });
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
  };
}

// ═════════════════════ 2. TABLEAU DE BORD ═════════════════════
function renderDashboard() {
  const stage = Math.max(1, profile.stage || 1);
  const et = ETAPES[stage];
  const first = contract.first_name || (profile.full_name || "").split(" ")[0];
  const required = DOCUMENTS.filter((d) => d.requis && d.etape <= stage);
  const okCount = required.filter((d) => docs.some((x) => x.doc_type === d.type && x.status === "valide")).length;

  const dates = [
    profile.test_date && ["Test d'allemand", fmtDate(profile.test_date)],
    profile.test_result && ["Résultat du test", esc(profile.test_result)],
    profile.interview_date && ["Entretien", fmtDate(profile.interview_date, true)],
    profile.visa_appointment && ["Rendez-vous visa", fmtDate(profile.visa_appointment, true)],
  ].filter(Boolean);

  app.innerHTML = `
    <div class="hello">
      <div><p class="hint" style="margin:0">Mon dossier volontariat</p><h1>Hallo ${esc(first)} !</h1></div>
      <button class="btn btn-ghost btn-sm" id="b-contract">📄 Mon contrat signé</button>
    </div>

    <div class="card">
      <div class="stepper">
        ${ETAPES.map((e) => `<div class="s ${e.id < stage || stage === 5 ? "done" : e.id === stage ? "cur" : ""}">
          <div class="dot">${e.id < stage || stage === 5 ? "✓" : e.id + 1}</div><span class="lbl">${e.court}</span></div>`).join("")}
      </div>
    </div>

    <div class="card current">
      <div>
        <span class="badge badge-navy">Étape ${stage + 1} sur 6</span>
        <h2 style="margin-top:10px">${esc(et.titre)}</h2>
        <p style="margin:0">${esc(et.desc)}</p>
        ${profile.admin_message ? `<div class="msg"><strong>Message de ton conseiller :</strong><br>${esc(profile.admin_message)}</div>` : ""}
        ${dates.length ? `<div class="dates">${dates.map(([k, v]) => `<div class="d"><strong>${k}</strong>${v}</div>`).join("")}</div>` : ""}
      </div>
      <div style="text-align:center;min-width:130px">
        <div class="count">${okCount}/${required.length}</div>
        <div class="hint">documents validés</div>
      </div>
    </div>

    <div class="card docgroup">
      <h2 style="font-size:1.2rem">Mes documents</h2>
      <p class="hint">PDF, JPG ou PNG — 10 Mo maximum par fichier. Une photo nette prise au téléphone suffit.</p>
      ${ETAPES.slice(1).map((e) => docGroup(e, stage)).join("")}
    </div>

    <p class="hint" style="text-align:center;margin-top:24px">Une question ? Écris-nous à <a href="mailto:${esc(EMAIL_CONTACT)}">${esc(EMAIL_CONTACT)}</a></p>`;

  $("#b-contract").addEventListener("click", openContract);
  $$("input[type=file]", app).forEach((inp) => inp.addEventListener("change", () => upload(inp)));
  $$("[data-open]", app).forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); openDoc(a.dataset.open); }));
  $$("[data-del]", app).forEach((b) => b.addEventListener("click", () => removeDoc(b.dataset.del)));
}

function docGroup(etape, stage) {
  const list = DOCUMENTS.filter((d) => d.etape === etape.id);
  if (!list.length) return "";
  const locked = etape.id > stage;
  return `<div class="${locked ? "locked" : ""}">
    <h3>${esc(etape.titre)} ${locked ? '<span class="badge badge-none">🔒 Plus tard</span>' : ""}</h3>
    ${list.map((d) => docRow(d, locked)).join("")}
  </div>`;
}

function docRow(d, locked) {
  const files = docs.filter((x) => x.doc_type === d.type);
  const best = files.find((x) => x.status === "valide") || files[0];
  const st = best ? STATUTS_DOC[best.status] : null;
  const refused = files.find((x) => x.status === "refuse" && x.comment);
  return `<div class="doc">
    <div>
      <div class="name">${esc(d.label)} ${d.requis ? "" : '<span class="hint">(si demandé)</span>'}</div>
      ${files.length ? `<div class="files">${files.map((x) => `<div class="f">
          <a data-open="${x.id}">${esc(x.file_name)}</a>
          <span class="badge ${STATUTS_DOC[x.status].cls}">${STATUTS_DOC[x.status].label}</span>
          ${x.status === "en_attente" ? `<button class="linkbtn" data-del="${x.id}">supprimer</button>` : ""}
        </div>`).join("")}</div>` : ""}
      ${refused ? `<div class="comment">↳ ${esc(refused.comment)}</div>` : ""}
    </div>
    <div class="actions">
      ${st ? `<span class="badge ${st.cls}">${st.label}</span>` : '<span class="badge badge-none">À envoyer</span>'}
      ${locked || best?.status === "valide" ? "" : `<label class="btn btn-primary btn-sm upload-btn">${files.length ? "Renvoyer" : "Envoyer"}
        <input type="file" accept=".pdf,.jpg,.jpeg,.png,.heic,.webp" data-type="${d.type}"></label>`}
    </div>
  </div>`;
}

async function upload(inp) {
  const file = inp.files[0];
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) { inp.value = ""; return toast("Fichier trop lourd (10 Mo maximum).", "err"); }
  const label = inp.closest("label"); label.classList.add("disabled"); label.firstChild.textContent = "Envoi… ";
  try {
    await api.uploadDocument(inp.dataset.type, file);
    toast("Document envoyé ✔ Nous allons le vérifier.");
    docs = await api.listDocuments(); renderDashboard();
  } catch (e) { toast(errMsg(e), "err"); renderDashboard(); }
}

async function openDoc(id) {
  const w = window.open("", "_blank");
  try {
    const url = await api.docUrl(docs.find((x) => x.id === id));
    if (w) { if (url.startsWith("data:")) w.document.write(`<iframe src="${url}" style="border:0;width:100%;height:100%"></iframe>`); else w.location = url; }
  } catch (e) { w?.close(); toast(errMsg(e), "err"); }
}

async function removeDoc(id) {
  if (!confirm("Supprimer ce fichier ?")) return;
  try { await api.deleteDocument(docs.find((x) => x.id === id)); docs = await api.listDocuments(); renderDashboard(); }
  catch (e) { toast(errMsg(e), "err"); }
}

// ═════════════════════ CONTRAT SIGNÉ (modal) ═════════════════════
function openContract() {
  $("#modal-body").innerHTML = signedContractHtml({ ...contract, email: user.email });
  $("#modal").hidden = false;
}
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal" || e.target.matches("[data-close]")) $("#modal").hidden = true; });
$("#b-print").addEventListener("click", () => {
  document.body.classList.add("printing");
  window.print();
  document.body.classList.remove("printing");
});

load();
