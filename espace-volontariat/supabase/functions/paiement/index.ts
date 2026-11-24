// Fonction serveur Supabase : paiement PayPal / carte bancaire.
//  - action "create"  : crée la commande PayPal au bon prix (selon le contrat signé)
//  - action "capture" : encaisse, vérifie montant + devise + candidat, marque le dossier comme payé
// Le montant n'est JAMAIS pris depuis le navigateur.
//
// Secrets à définir (voir README) : PAYPAL_CLIENT_ID, PAYPAL_SECRET, PAYPAL_ENV ("live" ou "sandbox")

import { createClient } from "npm:@supabase/supabase-js@2.45.4";

// ⚠️ Doit correspondre aux prix de js/contrat.js
const PRIX: Record<string, number> = { long: 1500, court: 1200 };

const PAYPAL_API = Deno.env.get("PAYPAL_ENV") === "live"
  ? "https://api-m.paypal.com"
  : "https://api-m.sandbox.paypal.com";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });

async function paypalToken(): Promise<string> {
  const auth = btoa(`${Deno.env.get("PAYPAL_CLIENT_ID")}:${Deno.env.get("PAYPAL_SECRET")}`);
  const r = await fetch(`${PAYPAL_API}/v1/oauth2/token`, {
    method: "POST",
    headers: { Authorization: `Basic ${auth}`, "Content-Type": "application/x-www-form-urlencoded" },
    body: "grant_type=client_credentials",
  });
  if (!r.ok) throw new Error("Connexion à PayPal impossible.");
  return (await r.json()).access_token;
}

async function paypal(token: string, path: string, body: unknown) {
  const r = await fetch(`${PAYPAL_API}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", Prefer: "return=representation" },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    console.error("PayPal", r.status, JSON.stringify(data));
    throw new Error(data?.details?.[0]?.description || "PayPal a refusé l'opération.");
  }
  return data;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  try {
    const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
    const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer /, "");
    const { data: { user } } = await db.auth.getUser(jwt);
    if (!user) return json({ error: "Connecte-toi pour payer." }, 401);

    const { action, orderID } = await req.json();

    const { data: contract } = await db.from("contracts")
      .select("contract_type, duration").eq("user_id", user.id).maybeSingle();
    if (!contract) return json({ error: "Signe d'abord ton contrat." }, 400);

    const { data: profile } = await db.from("profiles").select("paid_at").eq("id", user.id).single();
    if (profile?.paid_at) return json({ error: "Ton accompagnement est déjà payé." }, 400);

    const amount = PRIX[contract.contract_type];
    if (!amount) return json({ error: "Formule inconnue." }, 400);
    const token = await paypalToken();

    if (action === "create") {
      const order = await paypal(token, "/v2/checkout/orders", {
        intent: "CAPTURE",
        purchase_units: [{
          amount: { currency_code: "EUR", value: amount.toFixed(2) },
          description: `Lougha — accompagnement volontariat en Allemagne (${contract.duration})`,
          custom_id: user.id,
        }],
        application_context: { brand_name: "Lougha Online", shipping_preference: "NO_SHIPPING", user_action: "PAY_NOW" },
      });
      return json({ id: order.id });
    }

    if (action === "capture") {
      if (typeof orderID !== "string" || !/^[A-Z0-9]{5,40}$/.test(orderID)) return json({ error: "Commande invalide." }, 400);
      const r = await paypal(token, `/v2/checkout/orders/${orderID}/capture`, {});
      const unit = r.purchase_units?.[0];
      const cap = unit?.payments?.captures?.[0];
      const ok = r.status === "COMPLETED" && cap?.status === "COMPLETED"
        && cap.amount?.currency_code === "EUR" && Number(cap.amount?.value) === amount
        && (cap.custom_id ?? unit?.custom_id) === user.id;
      if (!ok) {
        console.error("Capture non conforme", JSON.stringify(r));
        return json({ error: "Le paiement n'a pas été confirmé. Contacte-nous si ton compte a été débité." }, 400);
      }
      const method = r.payment_source?.card ? "carte" : "paypal";
      const { error } = await db.from("profiles").update({
        paid_at: new Date().toISOString(), paid_amount: amount, payment_method: method, payment_ref: cap.id,
      }).eq("id", user.id);
      if (error) throw error;
      return json({ ok: true, method });
    }

    return json({ error: "Action inconnue." }, 400);
  } catch (e) {
    console.error(e);
    return json({ error: e instanceof Error ? e.message : "Erreur serveur." }, 500);
  }
});
