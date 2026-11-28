// Couche d'accès aux données.
// - Mode réel : le serveur PHP + MySQL du site (dossier api/), hébergé avec le site.
// - Mode démo : tout est gardé dans le navigateur (localStorage), pour tester le site.

import { MODE_DEMO } from "./config.js";

export const DEMO = !!MODE_DEMO;
const API = "api/index.php";

// ═════════════════════════════════ SERVEUR PHP ═════════════════════════════════
function makePhpApi() {
  async function call(action, body = {}) {
    const isForm = body instanceof FormData;
    if (isForm) body.append("action", action);
    let r;
    try {
      r = await fetch(API, {
        method: "POST",
        credentials: "same-origin",
        headers: isForm ? { "X-Lougha": "1" } : { "X-Lougha": "1", "Content-Type": "application/json" },
        body: isForm ? body : JSON.stringify({ action, ...body }),
      });
    } catch {
      throw new Error("Connexion impossible. Vérifie ta connexion internet et réessaie.");
    }
    let data = null;
    try { data = await r.json(); } catch {}
    if (!r.ok || data?.error) throw new Error(data?.error || "Une erreur est survenue. Réessaie dans un instant.");
    return data;
  }

  return {
    onAuth: () => {},
    async getUser() { return (await call("session")).user; },
    async signUp(email, password, full_name) { return call("signup", { email, password, full_name }); },
    async signIn(email, password) { return call("signin", { email, password }); },
    async signOut() { await call("signout"); },
    async resetPassword(email) { return call("reset_password", { email }); },
    async updatePassword(password, token) { return call("update_password", { password, token }); },

    async getProfile(id) { return (await call("get_profile", { user_id: id })).profile; },
    async getContract(userId) { return (await call("get_contract", { user_id: userId })).contract; },
    async signContract(c) { return (await call("sign_contract", { contract: c })).contract; },
    async listDocuments(userId) { return (await call("list_documents", { user_id: userId })).documents; },
    async uploadDocument(docType, file) {
      const fd = new FormData();
      fd.append("doc_type", docType);
      fd.append("file", file);
      return (await call("upload_document", fd)).document;
    },
    async deleteDocument(doc) { await call("delete_document", { id: doc.id }); },
    async docUrl(doc) { return `${API}?action=file&id=${encodeURIComponent(doc.id)}`; },

    // ── équipe ──
    async listCandidates() { return (await call("list_candidates")).candidates; },
    async updateProfile(id, patch) { return (await call("update_profile", { user_id: id, patch })).profile; },
    async reviewDocument(id, status, comment) {
      return (await call("review_document", { id, status, comment: comment || null })).document;
    },
    async signAsProvider(userId, { provider_signature_data, provider_signer }) {
      return (await call("sign_provider", { user_id: userId, provider_signature_data, provider_signer })).contract;
    },
    // Envoie au candidat la copie PDF du contrat signé par les deux parties (+ copie à Lougha).
    async sendContractEmail(userId, pdfBase64, filename) {
      return call("send_contract", { user_id: userId, pdf: pdfBase64, filename });
    },
  };
}

// ═════════════════════════════════ DÉMO ═════════════════════════════════
function makeDemoApi() {
  const KEY = "lougha_volontariat_demo";
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; } };
  const save = (db) => { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) {
    throw new Error("Stockage du navigateur plein (mode démo) : essaie un fichier plus petit."); } };
  const db = () => load() || { users: [], profiles: [], contracts: [], documents: [], session: null };
  const rid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
  const listeners = [];
  const me = () => db().session;

  return {
    onAuth: (cb) => { listeners.push(cb); },
    async getUser() { const d = db(); return d.users.find((u) => u.id === d.session) || null; },
    async signUp(email, password, full_name) {
      const d = db();
      email = email.trim().toLowerCase();
      if (d.users.some((u) => u.email === email)) throw new Error("Un compte existe déjà avec cet email.");
      const id = rid();
      d.users.push({ id, email, password });
      // En démo : un email qui commence par "admin" crée un compte équipe.
      d.profiles.push({ id, email, full_name, role: email.startsWith("admin") ? "admin" : "candidat",
        stage: 0, admin_message: "", test_date: null, test_result: "", interview_date: null,
        visa_appointment: null, created_at: new Date().toISOString() });
      d.session = id; save(d);
      return { user: { id, email }, session: { user: { id, email } } };
    },
    async signIn(email, password) {
      const d = db();
      const u = d.users.find((x) => x.email === email.trim().toLowerCase() && x.password === password);
      if (!u) throw new Error("Email ou mot de passe incorrect.");
      d.session = u.id; save(d); return { user: u };
    },
    async signOut() { const d = db(); d.session = null; save(d); },
    // Démo : se connecter directement avec un compte équipe (créé au besoin).
    async demoAdmin() {
      const d = db();
      let u = d.users.find((x) => x.email === "admin@demo.lougha");
      if (!u) {
        u = { id: rid(), email: "admin@demo.lougha", password: "demo" };
        d.users.push(u);
        d.profiles.push({ id: u.id, email: u.email, full_name: "Équipe Lougha", role: "admin", stage: 0,
          admin_message: "", created_at: new Date().toISOString() });
      }
      // garde le compte candidat en cours pour pouvoir y revenir
      const cur = d.profiles.find((x) => x.id === d.session);
      if (cur && cur.role !== "admin") d.demoCandidate = cur.id;
      d.session = u.id; save(d);
    },
    // Démo : revenir au dernier compte candidat utilisé.
    async demoBack() {
      const d = db();
      if (!d.demoCandidate || !d.users.some((x) => x.id === d.demoCandidate)) return false;
      d.session = d.demoCandidate; save(d); return true;
    },
    demoHasCandidate() { const d = db(); return !!d.demoCandidate; },
    // Démo : faire comme si l'équipe avait validé le paiement du candidat connecté.
    async demoValidatePayment() {
      const d = db(); const p = d.profiles.find((x) => x.id === me());
      const c = d.contracts.find((x) => x.user_id === me());
      d.documents.filter((x) => x.user_id === me() && x.doc_type === "recu_paiement" && x.status === "en_attente")
        .forEach((x) => Object.assign(x, { status: "valide", reviewed_at: new Date().toISOString() }));
      Object.assign(p, { paid_at: new Date().toISOString(), paid_amount: c.contract_type === "court" ? 1200 : 1500,
        payment_method: c.payment_method, payment_ref: "Validé (démo)" });
      save(d);
    },
    async resetPassword() { throw new Error("Mode démo : la réinitialisation par email n'est pas disponible."); },
    async updatePassword() {},

    async getProfile(id) { return db().profiles.find((p) => p.id === (id || me())); },
    async getContract(userId) { return db().contracts.find((c) => c.user_id === (userId || me())) || null; },
    async signContract(c) {
      const d = db();
      if (d.contracts.some((x) => x.user_id === me())) throw new Error("Contrat déjà signé.");
      const row = { ...c, id: rid(), user_id: me(), signed_at: new Date().toISOString() };
      d.contracts.push(row);
      const p = d.profiles.find((x) => x.id === me()); if (p.stage < 1) p.stage = 1;
      p.contract_type = c.contract_type; p.duration = c.duration; p.payment_method = c.payment_method;
      save(d); return row;
    },
    async listDocuments(userId) {
      return db().documents.filter((x) => x.user_id === (userId || me()))
        .sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at));
    },
    async uploadDocument(docType, file) {
      const dataUrl = file.size < 1.5e6 ? await new Promise((res, rej) => {
        const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file);
      }) : null;
      const d = db();
      const row = { id: rid(), user_id: me(), doc_type: docType, file_path: dataUrl, file_name: file.name,
        file_size: file.size, status: "en_attente", comment: null, uploaded_at: new Date().toISOString() };
      d.documents.push(row); save(d); return row;
    },
    async deleteDocument(doc) { const d = db(); d.documents = d.documents.filter((x) => x.id !== doc.id); save(d); },
    async docUrl(doc) {
      if (!doc.file_path) throw new Error("Mode démo : fichier trop gros pour être gardé dans le navigateur.");
      return doc.file_path;
    },

    async listCandidates() {
      const d = db();
      return d.profiles.filter((p) => p.role === "candidat").map((p) => ({
        ...p,
        docs_total: d.documents.filter((x) => x.user_id === p.id).length,
        docs_pending: d.documents.filter((x) => x.user_id === p.id && x.status === "en_attente").length,
        to_sign: d.contracts.some((c) => c.user_id === p.id && !c.provider_signed_at),
      }));
    },
    async updateProfile(id, patch) {
      const d = db(); const p = d.profiles.find((x) => x.id === id); Object.assign(p, patch); save(d); return p;
    },
    async signAsProvider(userId, { provider_signature_data, provider_signer }) {
      const d = db(); const c = d.contracts.find((x) => x.user_id === userId);
      if (c.provider_signature_data) throw new Error("Le contrat est déjà signé par le Prestataire.");
      Object.assign(c, { provider_signature_data, provider_signer, provider_signed_at: new Date().toISOString() });
      save(d); return c;
    },
    async sendContractEmail(userId) {
      // Mode démo : aucun email n'est réellement envoyé.
      const d = db(); const c = d.contracts.find((x) => x.user_id === userId);
      c.emailed_at = new Date().toISOString(); save(d);
      return { demo: true };
    },
    async reviewDocument(id, status, comment) {
      const d = db(); const x = d.documents.find((y) => y.id === id);
      Object.assign(x, { status, comment: comment || null, reviewed_at: new Date().toISOString() });
      save(d); return x;
    },
  };
}

export const api = DEMO ? makeDemoApi() : makePhpApi();
api.DEMO_MODE = DEMO;
