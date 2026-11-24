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
  b.innerHTML = `<strong>Mode démo</strong> — les données restent dans ce navigateur. Astuce : un email qui commence par <code>admin</code> ouvre l'espace équipe.`;
  document.body.prepend(b);
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

export async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
