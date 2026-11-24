import { CONTRATS } from "./contrat.js";
import { esc, fmtDate } from "./ui.js";

export const contratDe = (type) => CONTRATS[type] || CONTRATS.long;

export const euros = (n) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 })
    .format(n).replace(/ /g, " "); // espace insécable classique (affichée par toutes les polices)

// Remplit le contrat (selon f.contract_type) avec les infos du candidat.
// `highlight` met en évidence les champs pendant la saisie.
export function renderContract(f, highlight = false) {
  const vals = {
    prenom: f.first_name, nom: f.last_name,
    date_naissance: f.birth_date ? fmtDate(f.birth_date) : "",
    lieu_naissance: f.birth_place, nationalite: f.nationality, adresse: f.address,
    telephone: f.phone, passeport: f.passport_number, email: f.email, duree: f.duration,
    prix: f.contract_type ? euros(contratDe(f.contract_type).prix) : "",
    date: fmtDate(f.signed_at || new Date()),
  };
  return contratDe(f.contract_type).texte.replace(/\{\{(\w+)\}\}/g, (_, k) => {
    const v = esc(vals[k] || "") || "………";
    return highlight ? `<span class="ph">${v}</span>` : v;
  });
}

// Bloc complet "contrat signé" (texte + signature + preuve).
export function signedContractHtml(c) {
  return `
    <h2 style="font-size:1.25rem">${esc(contratDe(c.contract_type).titre)}</h2>
    <div class="contract-text">${renderContract(c)}
      <div style="margin-top:24px">
        <p style="margin-bottom:6px"><strong>Signature du candidat :</strong></p>
        <img class="sig-img" src="${esc(c.signature_data)}" alt="Signature">
        <p style="margin-top:8px">${esc(c.first_name)} ${esc(c.last_name)} — signé le ${fmtDate(c.signed_at, true)}</p>
        <p class="proof">Version du contrat : ${esc(c.contract_version)}<br>Empreinte SHA-256 du texte accepté : ${esc(c.contract_hash)}</p>
      </div>
    </div>`;
}

// Libellé court, ex. "Volontariat long · 1 an"
export const formuleLabel = (type, duration) =>
  type ? `${contratDe(type).nom}${duration ? " · " + duration : ""}` : "";
