import { CONTRATS } from "./contrat.js";
import { esc, fmtDate } from "./ui.js";
import { SIGNATURE_PRESTATAIRE, NOM_ORGANISATION } from "./config.js";

export const contratDe = (type) => CONTRATS[type] || CONTRATS.long;

export const euros = (n) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 })
    .format(n).replace(/ /g, " "); // espace insécable classique (affichée par toutes les polices)

// Mention exigée par le contrat avant la signature du Bénéficiaire.
export const MENTION = "Lu et approuvé";
export const mentionOk = (s) =>
  String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toLowerCase()
  === "lu et approuve";

// Remplit le contrat (selon f.contract_type) avec les infos du candidat.
// `highlight` met en évidence les champs pendant la saisie.
export function renderContract(f, highlight = false) {
  const vals = {
    prenom: f.first_name, nom: f.last_name,
    date_naissance: f.birth_date ? fmtDate(f.birth_date) : "",
    passeport: f.passport_number, email: f.email,
    date: fmtDate(f.signed_at || new Date()),
  };
  return contratDe(f.contract_type).texte.replace(/\{\{(\w+)\}\}/g, (_, k) => {
    const v = esc(vals[k] || "") || "………";
    return highlight ? `<span class="ph">${v}</span>` : v;
  });
}

function signaturePrestataire() {
  return SIGNATURE_PRESTATAIRE
    ? `<img class="sig-img" src="${esc(SIGNATURE_PRESTATAIRE)}" alt="Signature du Prestataire">`
    : `<p class="sig-text">${esc(NOM_ORGANISATION)}</p>`;
}

// Bloc complet "contrat signé" (texte + deux signatures + preuve).
export function signedContractHtml(c) {
  return `
    <h2 style="font-size:1.25rem">${esc(contratDe(c.contract_type).titre)}</h2>
    <div class="contract-text">${renderContract(c)}
      <div class="sig-grid">
        <div><p class="sig-label">Signature du Prestataire</p>${signaturePrestataire()}</div>
        <div><p class="sig-label">Signature du Bénéficiaire<br><small>(précédée de la mention « ${MENTION} »)</small></p>
          <p class="sig-mention">${esc(c.mention || MENTION)}</p>
          <img class="sig-img" src="${esc(c.signature_data)}" alt="Signature du Bénéficiaire">
          <p style="margin:6px 0 0">${esc(c.first_name)} ${esc(c.last_name)} — signé le ${fmtDate(c.signed_at, true)}</p></div>
      </div>
      <p class="proof" style="margin-top:18px">Signature électronique. Version du contrat : ${esc(c.contract_version)}<br>Empreinte SHA-256 du texte accepté : ${esc(c.contract_hash)}</p>
    </div>`;
}

// Libellé court, ex. "Volontariat 1 an"
export const formuleLabel = (type, duration) =>
  type ? `${contratDe(type).nom}${duration && !contratDe(type).nom.includes(duration) && !duration.includes("3 mois") ? " · " + duration : ""}` : "";
