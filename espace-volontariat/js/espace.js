import { api } from "./api.js";
import { $, $$, esc, toast, errMsg, fmtDate, demoBanner, sha256 } from "./ui.js";
import { ETAPES, DOCUMENTS, STATUTS_DOC } from "./etapes.js";
import { CONTRATS } from "./contrat.js";
import { renderContract, signedContractHtml, contratDe, formuleLabel, euros } from "./contrat-view.js";
import { LIEN_PLATEFORME, EMAIL_CONTACT, PAYPAL_CLIENT_ID } from "./config.js";

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
    if (!profile.paid_at) return renderPayment();
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
        <h2 style="font-size:1.15rem">1. Choisis ta formule</h2>
        <p class="hint">Le contrat affiché plus bas correspond à la formule choisie.</p>
        <div class="formules">
          ${Object.entries(CONTRATS).flatMap(([type, c]) => c.durees.map((d) => `
            <label class="formule">
              <input type="radio" name="formule" value="${type}|${esc(d)}">
              <span class="fm-box"><b>${esc(d.charAt(0).toUpperCase() + d.slice(1))}</b>
                <span class="fm-price">${euros(c.prix)}</span>
                <span class="fm-name">${esc(c.nom)}</span>
                <span class="hint">${esc(c.description)}</span></span>
            </label>`)).join("")}
        </div>

        <h2 style="font-size:1.15rem;margin-top:22px">2. Tes informations</h2>
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

        <h2 style="font-size:1.15rem;margin-top:12px">3. Lis ton contrat</h2>
        <p style="font-weight:700;margin-bottom:10px" id="c-title"></p>
        <div class="contract-text" id="c-text"></div>

        <h2 style="font-size:1.15rem;margin-top:24px">4. Signe</h2>
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
    $$("input[name]:not([type=radio])", form).forEach((i) => (o[i.name] = i.value.trim()));
    const [type, duree] = ($("input[name=formule]:checked", form)?.value || "").split("|");
    o.contract_type = type || null;
    o.duration = duree || "";
    return o;
  };
  const refresh = () => {
    const v = values();
    $("#c-title").textContent = v.contract_type ? contratDe(v.contract_type).titre : "Choisis d'abord ta formule ci-dessus.";
    $("#c-text").hidden = !v.contract_type;
    $("#c-text").innerHTML = v.contract_type ? renderContract(v, true) : "";
  };
  form.addEventListener("input", refresh);
  form.addEventListener("change", refresh);
  refresh();

  const pad = signaturePad($("#sigpad"));
  $("#b-clear").addEventListener("click", pad.clear);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const v = values();
    if (!v.contract_type) {
      $(".formules").scrollIntoView({ behavior: "smooth", block: "center" });
      return toast("Choisis ta formule : 6 mois, 1 an ou moins de 3 mois.", "err");
    }
    const missing = $$("input[name]:not([type=radio])", form).filter((i) => !i.value.trim());
    if (missing.length) { missing[0].focus(); return toast("Complète tous les champs.", "err"); }
    if (pad.isEmpty()) return toast("Ajoute ta signature.", "err");
    if (!$("#agree").checked) return toast("Coche la case pour accepter le contrat.", "err");

    const btn = $("#b-sign"); btn.disabled = true; btn.textContent = "Signature en cours…";
    try {
      const accepted = renderContract({ ...v, signed_at: new Date() });
      const { email, ...fields } = v;
      await api.signContract({
        ...fields,
        contract_version: contratDe(v.contract_type).version,
        contract_hash: await sha256(accepted),
        signature_data: pad.toDataURL(),
        user_agent: navigator.userAgent.slice(0, 300),
      });
      toast("Contrat signé ✔");
      window.scrollTo(0, 0);
      await load();
    } catch (err) {
      toast(errMsg(err), "err");
      btn.disabled = false; btn.textContent = "Signer mon contrat";
    }
  });
}

// ═════════════════════ 1 bis. PAIEMENT ═════════════════════
function renderPayment() {
  const c = contratDe(contract.contract_type);
  app.innerHTML = `
    <div class="narrow" style="margin:0 auto">
      <div class="hello"><div>
        <span class="badge badge-ok">✓ Contrat signé</span>
        <h1 style="margin-top:10px">Dernière étape : le paiement</h1>
        <p class="hint" style="margin:6px 0 0">Dès que ton paiement est confirmé, ton espace s'ouvre et tu peux commencer tes démarches.</p>
      </div></div>

      <div class="card">
        <div class="pay-sum">
          <div><p class="hint" style="margin:0">Ta formule</p>
            <h2 style="margin:4px 0 2px;font-size:1.3rem">${esc(c.nom)}</h2>
            <p class="hint" style="margin:0">${esc(c.titre)}</p></div>
          <div class="pay-amount">${euros(c.prix)}</div>
        </div>

        <h3 style="font-size:1rem;margin:26px 0 12px">Choisis ton moyen de paiement</h3>
        <div id="pay-buttons" class="pay-buttons"><p class="hint">Chargement du paiement sécurisé…</p></div>
        <p class="pay-note">🔒 Paiement sécurisé par PayPal. <strong>Pas besoin de compte PayPal</strong> pour payer par carte (Visa, Mastercard).</p>
      </div>

      <p class="hint" style="text-align:center;margin-top:20px">
        <a href="#" id="l-contract">Revoir mon contrat signé</a> ·
        Un problème pour payer ? <a href="mailto:${esc(EMAIL_CONTACT)}">${esc(EMAIL_CONTACT)}</a></p>
    </div>`;
  $("#l-contract").addEventListener("click", (e) => { e.preventDefault(); openContract(); });
  mountPaymentButtons($("#pay-buttons"));
}

async function paid(method) {
  toast("Paiement confirmé ✔ Merci ! Ton dossier est ouvert.");
  window.scrollTo(0, 0);
  await load();
}

async function mountPaymentButtons(box) {
  // Mode démo : boutons simulés (aucun argent n'est prélevé).
  if (api.DEMO_MODE) {
    box.innerHTML = `
      <button class="btn pay-btn pay-paypal" data-m="paypal"><b>Pay</b><i>Pal</i></button>
      <button class="btn pay-btn pay-card" data-m="carte">💳 Carte bancaire · Visa / Mastercard</button>
      <p class="hint" style="margin:4px 0 0;text-align:center">Mode démo : le paiement est simulé.</p>`;
    $$("[data-m]", box).forEach((b) => b.addEventListener("click", async () => {
      b.disabled = true;
      try { await api.capturePayment("DEMO-" + Date.now(), b.dataset.m); await paid(); }
      catch (e) { toast(errMsg(e), "err"); b.disabled = false; }
    }));
    return;
  }
  if (!PAYPAL_CLIENT_ID) {
    box.innerHTML = `<p class="msg">Le paiement en ligne sera bientôt disponible. Contacte-nous à
      <a href="mailto:${esc(EMAIL_CONTACT)}">${esc(EMAIL_CONTACT)}</a> pour régler ton accompagnement.</p>`;
    return;
  }
  try {
    await loadScript(`https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(PAYPAL_CLIENT_ID)}&currency=EUR&intent=capture&components=buttons&locale=fr_FR`);
  } catch {
    box.innerHTML = `<p class="msg">Impossible de charger PayPal. Vérifie ta connexion puis recharge la page.</p>`;
    return;
  }
  box.innerHTML = "";
  const paypal = window.paypal;
  let rendered = 0;
  for (const source of [paypal.FUNDING.PAYPAL, paypal.FUNDING.CARD]) {
    const btn = paypal.Buttons({
      fundingSource: source,
      style: { shape: "pill", height: 48, ...(source === paypal.FUNDING.PAYPAL ? { color: "gold" } : {}) },
      createOrder: () => api.createPaymentOrder(),                 // montant fixé côté serveur
      onApprove: async (data) => {
        try { await api.capturePayment(data.orderID); await paid(); }
        catch (e) { toast(errMsg(e), "err"); }
      },
      onError: () => toast("Le paiement n'a pas abouti. Réessaie ou contacte-nous.", "err"),
    });
    if (btn.isEligible()) { const d = document.createElement("div"); box.append(d); btn.render(d); rendered++; }
  }
  if (!rendered) box.innerHTML = `<p class="msg">Le paiement en ligne n'est pas disponible depuis ton pays. Contacte-nous à <a href="mailto:${esc(EMAIL_CONTACT)}">${esc(EMAIL_CONTACT)}</a>.</p>`;
}

function loadScript(src) {
  return new Promise((res, rej) => {
    if (window.paypal) return res();
    const s = document.createElement("script");
    s.src = src; s.onload = res; s.onerror = rej;
    document.head.append(s);
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
      <div><p class="hint" style="margin:0">Mon dossier · <span class="badge badge-navy">${esc(formuleLabel(contract.contract_type, contract.duration))}</span></p><h1 style="margin-top:6px">Hallo ${esc(first)} !</h1></div>
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
