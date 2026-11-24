// Couche d'accès aux données.
// - Mode réel : Supabase (connexion, base de données, stockage des fichiers).
// - Mode démo : tout est gardé dans le navigateur (localStorage), pour tester le site.

import { SUPABASE_URL, SUPABASE_ANON_KEY } from "./config.js";

export const DEMO = !SUPABASE_URL || !SUPABASE_ANON_KEY;
const BUCKET = "documents";

function safeName(name) {
  return name.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-zA-Z0-9._-]/g, "_").slice(-80);
}

// ═════════════════════════════════ SUPABASE ═════════════════════════════════
async function makeSupabaseApi() {
  const { createClient } = await import("https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm");
  const sb = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  const must = ({ data, error }) => { if (error) throw error; return data; };
  const uid = async () => (await sb.auth.getUser()).data.user?.id;
  const base = () => location.href.replace(/[^/]*([?#].*)?$/, "");
  async function payFn(body) {
    const { data, error } = await sb.functions.invoke("paiement", { body });
    if (error) {
      let msg = "Le paiement n'a pas pu être traité.";
      try { msg = (await error.context.json()).error || msg; } catch {}
      throw new Error(msg);
    }
    return data;
  }

  return {
    onAuth: (cb) => sb.auth.onAuthStateChange((evt, session) => cb(evt, session)),
    async getUser() { return (await sb.auth.getSession()).data.session?.user || null; },
    async signUp(email, password, full_name) {
      return must(await sb.auth.signUp({
        email, password,
        options: { data: { full_name }, emailRedirectTo: base() + "espace.html" },
      }));
    },
    async signIn(email, password) { return must(await sb.auth.signInWithPassword({ email, password })); },
    async signOut() { await sb.auth.signOut(); },
    async resetPassword(email) {
      return must(await sb.auth.resetPasswordForEmail(email, { redirectTo: base() + "connexion.html?reset=1" }));
    },
    async updatePassword(password) { return must(await sb.auth.updateUser({ password })); },

    async getProfile(id) {
      return must(await sb.from("profiles").select("*").eq("id", id || await uid()).single());
    },
    async getContract(userId) {
      return must(await sb.from("contracts").select("*").eq("user_id", userId || await uid()).maybeSingle());
    },
    async signContract(c) {
      return must(await sb.from("contracts").insert({ ...c, user_id: await uid() }).select().single());
    },
    async listDocuments(userId) {
      return must(await sb.from("documents").select("*").eq("user_id", userId || await uid())
        .order("uploaded_at", { ascending: false }));
    },
    async uploadDocument(docType, file) {
      const id = await uid();
      const path = `${id}/${docType}/${Date.now()}-${safeName(file.name)}`;
      must(await sb.storage.from(BUCKET).upload(path, file, { contentType: file.type || undefined }));
      return must(await sb.from("documents").insert({
        user_id: id, doc_type: docType, file_path: path, file_name: file.name, file_size: file.size,
      }).select().single());
    },
    async deleteDocument(doc) {
      must(await sb.from("documents").delete().eq("id", doc.id));
      await sb.storage.from(BUCKET).remove([doc.file_path]);
    },
    async docUrl(doc) {
      return must(await sb.storage.from(BUCKET).createSignedUrl(doc.file_path, 3600)).signedUrl;
    },

    // ── paiement (fonction serveur supabase/functions/paiement) ──
    async createPaymentOrder() {
      return (await payFn({ action: "create" })).id;
    },
    async capturePayment(orderID) {
      return payFn({ action: "capture", orderID });
    },

    // ── admin ──
    async listCandidates() {
      const profiles = must(await sb.from("profiles").select("*").eq("role", "candidat")
        .order("created_at", { ascending: false }));
      const docs = must(await sb.from("documents").select("user_id,status"));
      return profiles.map((p) => ({
        ...p,
        docs_total: docs.filter((d) => d.user_id === p.id).length,
        docs_pending: docs.filter((d) => d.user_id === p.id && d.status === "en_attente").length,
      }));
    },
    async updateProfile(id, patch) {
      return must(await sb.from("profiles").update(patch).eq("id", id).select().single());
    },
    async reviewDocument(id, status, comment) {
      return must(await sb.from("documents")
        .update({ status, comment: comment || null, reviewed_at: new Date().toISOString() })
        .eq("id", id).select().single());
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
      p.contract_type = c.contract_type; p.duration = c.duration;
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

    async createPaymentOrder() { return "DEMO"; },
    async capturePayment(orderID, method) {
      const d = db(); const p = d.profiles.find((x) => x.id === me());
      const c = d.contracts.find((x) => x.user_id === me());
      Object.assign(p, { paid_at: new Date().toISOString(), paid_amount: c.contract_type === "court" ? 1200 : 1500,
        payment_method: method, payment_ref: orderID });
      save(d); return { ok: true };
    },

    async listCandidates() {
      const d = db();
      return d.profiles.filter((p) => p.role === "candidat").map((p) => ({
        ...p,
        docs_total: d.documents.filter((x) => x.user_id === p.id).length,
        docs_pending: d.documents.filter((x) => x.user_id === p.id && x.status === "en_attente").length,
      }));
    },
    async updateProfile(id, patch) {
      const d = db(); const p = d.profiles.find((x) => x.id === id); Object.assign(p, patch); save(d); return p;
    },
    async reviewDocument(id, status, comment) {
      const d = db(); const x = d.documents.find((y) => y.id === id);
      Object.assign(x, { status, comment: comment || null, reviewed_at: new Date().toISOString() });
      save(d); return x;
    },
  };
}

export const api = DEMO ? makeDemoApi() : await makeSupabaseApi();
api.DEMO_MODE = DEMO;
