import { TEXTE, TITRE } from "./contrat.js";
import { esc, fmtDate } from "./ui.js";

// Remplit le contrat avec les infos du candidat. `highlight` met en
// évidence les champs (pendant la saisie).
export function renderContract(f, highlight = false) {
  const vals = {
    prenom: f.first_name, nom: f.last_name,
    date_naissance: f.birth_date ? fmtDate(f.birth_date) : "",
    lieu_naissance: f.birth_place, nationalite: f.nationality, adresse: f.address,
    telephone: f.phone, passeport: f.passport_number, email: f.email,
    date: fmtDate(f.signed_at || new Date()),
  };
  return TEXTE.replace(/\{\{(\w+)\}\}/g, (_, k) => {
    const v = esc(vals[k] || "") || "………";
    return highlight ? `<span class="ph">${v}</span>` : v;
  });
}

// Bloc complet "contrat signé" (texte + signature + preuve).
export function signedContractHtml(c) {
  return `
    <h2 style="font-size:1.25rem">${esc(TITRE)}</h2>
    <div class="contract-text">${renderContract(c)}
      <div style="margin-top:24px">
        <p style="margin-bottom:6px"><strong>Signature du candidat :</strong></p>
        <img class="sig-img" src="${esc(c.signature_data)}" alt="Signature">
        <p style="margin-top:8px">${esc(c.first_name)} ${esc(c.last_name)} — signé le ${fmtDate(c.signed_at, true)}</p>
        <p class="proof">Version du contrat : ${esc(c.contract_version)}<br>Empreinte SHA-256 du texte accepté : ${esc(c.contract_hash)}</p>
      </div>
    </div>`;
}
