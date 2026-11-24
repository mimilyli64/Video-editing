// Fonction serveur Supabase : envoie au candidat la copie PDF de son contrat signé
// par les deux parties (avec une copie à Lougha Online).
// Appelée depuis l'espace équipe, juste après la signature du Prestataire.
//
// Envoi des emails via Resend (resend.com). Secrets à définir (voir README) :
//   RESEND_API_KEY   clé API Resend
//   EMAIL_FROM       ex. "Lougha Online <contrats@loughaonline.com>" (domaine vérifié sur Resend)
//   EMAIL_COPIE      ex. "lougha.online3@gmail.com" (reçoit une copie de chaque contrat)

import { createClient } from "npm:@supabase/supabase-js@2.45.4";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
const esc = (s: unknown) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  try {
    const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
    const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer /, "");
    const { data: { user } } = await db.auth.getUser(jwt);
    if (!user) return json({ error: "Non connecté." }, 401);
    const { data: me } = await db.from("profiles").select("role").eq("id", user.id).single();
    if (me?.role !== "admin") return json({ error: "Réservé à l'équipe." }, 403);

    const { user_id, pdf, filename } = await req.json();
    if (typeof pdf !== "string" || pdf.length < 1000) return json({ error: "PDF manquant." }, 400);
    if (pdf.length > 15_000_000) return json({ error: "PDF trop volumineux." }, 400);

    const { data: c } = await db.from("contracts").select("*").eq("user_id", user_id).maybeSingle();
    if (!c) return json({ error: "Contrat introuvable." }, 404);
    if (!c.signature_data || !c.provider_signature_data) return json({ error: "Le contrat doit être signé par les deux parties." }, 400);

    // L'adresse vient du compte du candidat (jamais du navigateur).
    const { data: cand } = await db.from("profiles").select("email").eq("id", user_id).single();
    if (!cand?.email) return json({ error: "Email du candidat introuvable." }, 400);

    const copie = Deno.env.get("EMAIL_COPIE");
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${Deno.env.get("RESEND_API_KEY")}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: Deno.env.get("EMAIL_FROM"),
        to: [cand.email],
        bcc: copie ? [copie] : undefined,
        reply_to: copie || undefined,
        subject: "Ton contrat d'accompagnement signé — Lougha Online",
        html: `
          <div style="font-family:Arial,sans-serif;font-size:15px;color:#111827;line-height:1.6">
            <p>Bonjour ${esc(c.first_name)},</p>
            <p>Ton contrat d'accompagnement pour le programme de volontariat en Allemagne a été signé
            par les deux parties. Tu trouveras ta copie en pièce jointe (PDF).</p>
            <p>Tu peux suivre l'avancement de ton dossier à tout moment depuis ton espace personnel.</p>
            <p>À très vite,<br>L'équipe Lougha Online</p>
          </div>`,
        attachments: [{ filename: String(filename || "Contrat-volontariat.pdf").replace(/[^\w.-]+/g, "_"), content: pdf }],
      }),
    });
    if (!r.ok) {
      console.error("Resend", r.status, await r.text());
      return json({ error: "Le service d'email a refusé l'envoi. Vérifie la configuration Resend." }, 502);
    }

    await db.from("contracts").update({ emailed_at: new Date().toISOString() }).eq("user_id", user_id);
    return json({ ok: true, to: cand.email });
  } catch (e) {
    console.error(e);
    return json({ error: e instanceof Error ? e.message : "Erreur serveur." }, 500);
  }
});
