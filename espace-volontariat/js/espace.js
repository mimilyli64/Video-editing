import { api } from "./api.js";
import { $, $$, esc, toast, errMsg, fmtDate, demoBanner, sha256, whatsappFab, signaturePad, downloadPdf } from "./ui.js";
import { ETAPES, DOCUMENTS, STATUTS_DOC, etapesPour } from "./etapes.js";
import { CONTRATS } from "./contrat.js";
import { renderContract, signedContractHtml, contratDe, formuleLabel, euros, MENTION, mentionOk, signeParLesDeux, nomFichierContrat } from "./contrat-view.js";
import { LIEN_PLATEFORME, EMAIL_CONTACT } from "./config.js";
import { METHODES, TYPE_RECU, whatsappLink, WA_ICON } from "./paiement.js";

demoBanner();
whatsappFab("Bonjour, j'ai une question sur mon dossier de volontariat.");
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
    if (!profile.paid_at) return await renderPayment();
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
        <span class="badge badge-navy">Étape 1 · Contrat</span>
        <h1 style="margin-top:10px">Bienvenue ${esc(first)} 👋</h1>
        <p class="hint" style="margin:6px 0 0">Avant de commencer tes démarches, complète tes informations et signe ton contrat.</p>
      </div></div>

      <form id="f-sign" class="card" novalidate>
        <h2 style="font-size:1.15rem">1. Choisis ta formule et ton paiement</h2>
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

        <h3 style="font-size:1rem;margin:18px 0 10px">Comment souhaites-tu payer ?</h3>
        <div class="formules methodes">
          ${Object.entries(METHODES).map(([k, m]) => `
            <label class="formule">
              <input type="radio" name="paiement" value="${k}">
              <span class="fm-box fm-row">${k === "paypal"
                ? `<span class="pl" style="color:#003087"><i>Pay</i><i style="color:#009cde">Pal</i></span>`
                : `<span class="pl" style="color:#1a1f71">VISA</span>`}<b style="font-size:1.05rem">${esc(m.label.charAt(0).toUpperCase() + m.label.slice(1))}</b></span>
            </label>`).join("")}
        </div>
        <p class="hint" style="margin-top:8px">Après la signature, tu nous contactes sur WhatsApp pour payer, puis tu déposes ton reçu ici.</p>

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
        <div class="field" style="max-width:360px">
          <label for="i-mention">Écris la mention « ${MENTION} »</label>
          <input id="i-mention" data-mention autocomplete="off" placeholder="${MENTION}">
        </div>
        <p class="hint">Puis dessine ta signature avec ton doigt ou ta souris.</p>
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
    o.payment_method = $("input[name=paiement]:checked", form)?.value || null;
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
      return toast("Choisis ta formule : 1 an ou moins de 3 mois.", "err");
    }
    if (!v.payment_method) {
      $(".methodes").scrollIntoView({ behavior: "smooth", block: "center" });
      return toast("Choisis ta méthode de paiement : PayPal ou carte Visa.", "err");
    }
    const missing = $$("input[name]:not([type=radio])", form).filter((i) => !i.value.trim());
    if (missing.length) { missing[0].focus(); return toast("Complète tous les champs.", "err"); }
    if (!mentionOk($("[data-mention]").value)) { $("[data-mention]").focus(); return toast(`Écris la mention « ${MENTION} » avant de signer.`, "err"); }
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
        mention: $("[data-mention]").value.trim(),
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

// ═════════════════════ 1 bis. PAIEMENT (hors site) + REÇU ═════════════════════
// Le candidat paie avec la méthode choisie (on lui envoie les infos sur WhatsApp),
// puis dépose son reçu. L'équipe valide le reçu → le dossier s'ouvre.
async function renderPayment() {
  const c = contratDe(contract.contract_type);
  const m = METHODES[contract.payment_method] || METHODES.paypal;
  docs = await api.listDocuments();
  const recus = docs.filter((x) => x.doc_type === TYPE_RECU);
  const last = recus[0];
  const name = `${contract.first_name} ${contract.last_name}`;
  const wa = whatsappLink(`Bonjour, je suis ${name} (${user.email}). J'ai signé mon contrat « ${c.nom} » (${euros(c.prix)}) et je souhaite payer par ${m.label}.`);

  const etat = !last
    ? `<span class="badge badge-none">Reçu pas encore envoyé</span>`
    : `<span class="badge ${STATUTS_DOC[last.status].cls}">${last.status === "en_attente" ? "Reçu en vérification" : STATUTS_DOC[last.status].label}</span>`;

  app.innerHTML = `
    <div class="narrow" style="margin:0 auto">
      <div class="hello"><div>
        <span class="badge badge-ok">✓ Contrat signé</span>
        <h1 style="margin-top:10px">Dernière étape : le paiement</h1>
        <p class="hint" style="margin:6px 0 0">Dès que ton reçu est validé par notre équipe, ton espace s'ouvre et tu peux commencer tes démarches.</p>
      </div></div>

      <div class="card">
        <div class="pay-sum">
          <div><p class="hint" style="margin:0">Ta formule</p>
            <h2 style="margin:4px 0 2px;font-size:1.3rem">${esc(c.nom)}</h2>
            <p class="hint" style="margin:0">Paiement par <strong>${esc(m.label)}</strong></p></div>
          <div class="pay-amount">${euros(c.prix)}</div>
        </div>

        <ol class="pay-steps">
          <li><div><strong>Contacte-nous sur WhatsApp</strong>
            <p class="hint">On t'envoie les informations pour payer par ${esc(m.label)} et on répond à tes questions.</p>
            ${wa ? `<a class="btn btn-wa" href="${wa}" target="_blank" rel="noopener">${WA_ICON} Nous écrire sur WhatsApp</a>`
                 : `<a class="btn btn-ghost" href="mailto:${esc(EMAIL_CONTACT)}">Nous écrire : ${esc(EMAIL_CONTACT)}</a>`}
          </div></li>
          <li><div><strong>Effectue le paiement de ${euros(c.prix)}</strong>
            <p class="hint">${esc(m.aide)}</p></div></li>
          <li><div><strong>Envoie ton reçu de paiement ici</strong> ${etat}
            <p class="hint">Capture d'écran ou PDF du reçu (PDF, JPG, PNG — 10 Mo max).</p>
            ${recus.length ? `<div class="doc" style="border:0;padding:4px 0 10px"><div class="files">${recus.map((x) => `<div class="f">
                <a data-open="${x.id}">${esc(x.file_name)}</a>
                <span class="badge ${STATUTS_DOC[x.status].cls}">${STATUTS_DOC[x.status].label}</span>
                ${x.status === "en_attente" ? `<button class="linkbtn" data-del="${x.id}">supprimer</button>` : ""}
              </div>${x.status === "refuse" && x.comment ? `<div class="comment">↳ ${esc(x.comment)}</div>` : ""}`).join("")}</div></div>` : ""}
            ${last?.status === "en_attente" ? `<p class="msg" style="margin-top:6px">Merci ! Ton reçu est en cours de vérification. Tu recevras l'accès à ton dossier très vite.</p>` : ""}
            <label class="btn btn-primary upload-btn" style="margin-top:6px">${recus.length ? "Envoyer un autre reçu" : "Envoyer mon reçu"}
              <input type="file" accept=".pdf,.jpg,.jpeg,.png,.heic,.webp" data-type="${TYPE_RECU}"></label>
          </div></li>
        </ol>
      </div>

      <p class="hint" style="text-align:center;margin-top:20px"><a href="#" id="l-contract">Revoir mon contrat signé</a></p>
    </div>`;

  $("#l-contract").addEventListener("click", (e) => { e.preventDefault(); openContract(); });
  $$("input[type=file]", app).forEach((inp) => inp.addEventListener("change", () => upload(inp)));
  $$("[data-open]", app).forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); openDoc(a.dataset.open); }));
  $$("[data-del]", app).forEach((b) => b.addEventListener("click", () => removeDoc(b.dataset.del)));
}

function field(name, label, value = "", ac = "off", type = "text") {
  return `<div class="field"><label for="i-${name}">${label}</label>
    <input id="i-${name}" name="${name}" type="${type}" value="${esc(value)}" autocomplete="${ac}" required></div>`;
}


// ═════════════════════ 2. TABLEAU DE BORD ═════════════════════
function renderDashboard() {
  const stage = Math.max(1, profile.stage || 1);
  const first = contract.first_name || (profile.full_name || "").split(" ")[0];
  // Étapes de la formule du candidat (ex. pas de test d'allemand pour la formule 3 mois)
  const visibles = etapesPour(contract.contract_type);
  const ids = visibles.map((e) => e.id);
  const fini = stage === 5;
  const rang = Math.max(0, visibles.findIndex((e) => e.id >= stage));
  const et = visibles[rang];
  const required = DOCUMENTS.filter((d) => d.requis && d.etape <= stage && ids.includes(d.etape));
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
      <button class="btn btn-ghost btn-sm" id="b-contract">📄 Mon contrat ${signeParLesDeux(contract) ? "signé" : "· en attente de signature Lougha"}</button>
    </div>

    <div class="card">
      <div class="stepper" style="grid-template-columns:repeat(${visibles.length},1fr)">
        ${visibles.map((e, i) => `<div class="s ${e.id < stage || fini ? "done" : i === rang ? "cur" : ""}">
          <div class="dot">${e.id < stage || fini ? "✓" : i + 1}</div><span class="lbl">${e.court}</span></div>`).join("")}
      </div>
    </div>

    <div class="card current">
      <div>
        <span class="badge badge-navy">Étape ${rang + 1} sur ${visibles.length}</span>
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
      <p class="hint">PDF, JPG ou PNG — 10 Mo maximum par fichier. Une photo nette prise au téléphone suffit.
        <strong>Tous les documents doivent être traduits en allemand.</strong></p>
      ${visibles.slice(1).map((e) => docGroup(e, stage)).join("")}
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
    await load();
  } catch (e) { toast(errMsg(e), "err"); await load(); }
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
  try { await api.deleteDocument(docs.find((x) => x.id === id)); await load(); }
  catch (e) { toast(errMsg(e), "err"); }
}

// ═════════════════════ CONTRAT SIGNÉ (modal) ═════════════════════
function openContract() {
  $("#modal-title").textContent = signeParLesDeux(contract) ? "Mon contrat signé par les deux parties" : "Mon contrat";
  $("#modal-body").innerHTML = signedContractHtml({ ...contract, email: user.email })
    + (signeParLesDeux(contract) ? "" : `<p class="hint" style="margin-top:14px">Ton contrat sera signé par Lougha Online très bientôt. Tu recevras alors ta copie par email.</p>`);
  $("#modal").hidden = false;
}
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal" || e.target.matches("[data-close]")) $("#modal").hidden = true; });
$("#b-print").addEventListener("click", async (e) => {
  e.target.disabled = true;
  const c = { ...contract, email: user.email };
  try { await downloadPdf(signedContractHtml(c), nomFichierContrat(c)); }
  catch (err) { toast(errMsg(err), "err"); }
  e.target.disabled = false;
});

load();
