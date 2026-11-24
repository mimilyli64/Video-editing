// Méthodes de paiement proposées au candidat (le paiement se fait hors du site,
// puis le candidat dépose son reçu dans son espace).
import { WHATSAPP } from "./config.js";

export const METHODES = {
  paypal: { label: "PayPal", aide: "Paie avec ton compte PayPal à l'adresse que nous t'envoyons sur WhatsApp, puis fais une capture d'écran de la confirmation." },
  carte:  { label: "carte Visa", aide: "Paie par carte Visa avec le lien ou les informations que nous t'envoyons sur WhatsApp, puis garde le reçu (capture d'écran ou PDF)." },
};

// Type de document utilisé pour le reçu de paiement.
export const TYPE_RECU = "recu_paiement";

// Lien WhatsApp avec un message pré-rempli (null si aucun numéro configuré).
export function whatsappLink(message = "") {
  const num = String(WHATSAPP || "").replace(/\D/g, "");
  if (!num) return null;
  return `https://wa.me/${num}${message ? "?text=" + encodeURIComponent(message) : ""}`;
}

export const WA_ICON = `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.5 14.4c-.3-.1-1.8-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.8 1-.9 1.2-.2.2-.3.2-.6.1-.3-.1-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.4-.5c.2-.2.2-.3.3-.5.1-.2 0-.4 0-.5l-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.1-.3-.2-.6-.3zM12 21.8c-1.8 0-3.5-.5-5-1.4l-.4-.2-3.7 1 1-3.6-.2-.4A9.8 9.8 0 1 1 12 21.8zm8.4-18.2A11.8 11.8 0 0 0 1.7 17.8L0 24l6.4-1.7A11.8 11.8 0 0 0 24 12a11.7 11.7 0 0 0-3.6-8.4z"/></svg>`;
