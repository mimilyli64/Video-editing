# Guide d'installation — Espace Volontariat Lougha Online

Pour le développeur qui met le site en ligne sur Hostinger. Durée estimée : **1 h à 1 h 30**.

## 1. Ce que c'est

Un site **100 % statique** (HTML + CSS + JavaScript, aucun build, aucun npm) à déposer sur Hostinger, avec
**Supabase** comme backend (comptes, base Postgres, stockage des fichiers) et **Resend** pour les emails.
Hostinger sert uniquement les fichiers : il n'y a ni PHP ni base MySQL à configurer.

```
Navigateur ──► Hostinger (fichiers statiques)
     │
     └──► Supabase : Auth (email + mot de passe) · Postgres (RLS) · Storage (bucket privé "documents")
                     · Edge Function "envoyer-contrat" ──► Resend (email + PDF en pièce jointe)
```

| Fichier | Rôle |
|---|---|
| `index.html` | page publique de présentation |
| `connexion.html` | inscription / connexion / mot de passe oublié |
| `espace.html` + `js/espace.js` | espace candidat : formule, contrat, signature, reçu de paiement, documents, suivi |
| `admin.html` + `js/admin.js` | espace équipe : candidats, reçus, documents, étapes, signature Lougha, envoi du PDF |
| `js/config.js` | **seul fichier à modifier** (clés Supabase) |
| `js/contrat.js` | textes officiels des 2 contrats (1 an / 3 mois) |
| `js/api.js` | accès Supabase (et mode démo localStorage si la config est vide) |
| `supabase/schema.sql` | tables, RLS, triggers, bucket de stockage |
| `supabase/functions/envoyer-contrat/` | Edge Function d'envoi du contrat par email |
| `.htaccess` | HTTPS forcé, `.md/.sql/.ts` et `supabase/` non servis |

Librairies chargées par CDN (aucune installation) : `@supabase/supabase-js@2.45.4` (jsDelivr),
`html2pdf.js@0.10.1` (cdnjs), police Outfit (Google Fonts).

> ⚠️ Les comptes candidats sont **séparés** des comptes de la plateforme de cours loughaonline.com
> (Supabase Auth dédié). Un candidat crée son compte sur l'espace volontariat avec son email.

## 2. Supabase (≈ 20 min)

1. Créer un projet sur [supabase.com](https://supabase.com) (région **Frankfurt / eu-central-1**).
2. **SQL Editor** → coller tout `supabase/schema.sql` → **Run**. (Idempotent : peut être relancé.)
3. **Project Settings → API** : copier *Project URL* et la clé **anon public** dans `js/config.js` :
   ```js
   export const SUPABASE_URL = "https://xxxx.supabase.co";
   export const SUPABASE_ANON_KEY = "eyJ...";
   ```
   (La clé anon est publique par conception ; la sécurité repose sur les règles RLS du schéma.
   Ne **jamais** mettre la clé `service_role` dans le site.)
4. **Authentication → URL Configuration** :
   - *Site URL* : `https://volontariat.loughaonline.com`
   - *Redirect URLs* : `https://volontariat.loughaonline.com/**`
5. **Authentication → Providers → Email** : laisser activé. « Confirm email » activé conseillé
   (le site gère l'écran « Vérifie tes emails »).
6. Optionnel mais conseillé : **Authentication → Emails → SMTP Settings** avec les identifiants Resend
   (host `smtp.resend.com`, port 465, user `resend`, mot de passe = clé API Resend), sinon Supabase limite
   l'envoi des emails de confirmation à quelques-uns par heure.

## 3. Emails du contrat signé : Resend + Edge Function (≈ 20 min)

1. Compte [resend.com](https://resend.com) → **Domains → Add domain** → `loughaonline.com` → ajouter les
   enregistrements DNS dans **Hostinger → Domaines → DNS / Nameservers** → attendre « Verified ».
2. **API Keys → Create** → copier la clé `re_...`.
3. Déployer la fonction (depuis le dossier du projet, [CLI Supabase](https://supabase.com/docs/guides/cli)) :
   ```bash
   supabase login
   supabase link --project-ref <ID_DU_PROJET>
   supabase secrets set RESEND_API_KEY=re_xxx \
     EMAIL_FROM="Lougha Online <contrats@loughaonline.com>" \
     EMAIL_COPIE=lougha.online3@gmail.com
   supabase functions deploy envoyer-contrat
   ```
   La fonction vérifie que l'appelant est admin, que le contrat porte les deux signatures, prend l'email du
   candidat en base (jamais celui envoyé par le navigateur) et envoie le PDF.

## 4. Hostinger (≈ 10 min)

1. **hPanel → Domaines → Sous-domaines** → créer `volontariat` (→ `volontariat.loughaonline.com`).
   Hostinger crée un dossier, par ex. `public_html/volontariat/` (ou `domains/.../public_html/volontariat`).
2. **SSL** : activer le certificat (gratuit) pour le sous-domaine.
3. **Gestionnaire de fichiers** → ouvrir ce dossier → **Upload** du ZIP → **Extract**, de façon à avoir
   `index.html` directement à la racine du sous-domaine (pas dans un sous-dossier `espace-volontariat/`).
   Vérifier que `.htaccess` est bien présent (fichier caché).
4. Sur le site principal loughaonline.com, ajouter un lien vers `https://volontariat.loughaonline.com`
   (menu « Recrutement » ou « Volontariat en Allemagne »).

> Variante sans sous-domaine : déposer le dossier dans `public_html/volontariat/` →
> `https://loughaonline.com/volontariat/`. **Attention** : si loughaonline.com est une application
> Next.js/Node, ses routes peuvent intercepter `/volontariat` — le sous-domaine est plus sûr.
> Adapter alors *Site URL / Redirect URLs* de Supabase.

## 5. Créer les comptes de l'équipe

S'inscrire sur le site avec l'email de chaque membre, puis dans Supabase **SQL Editor** :
```sql
update public.profiles set role = 'admin' where email = 'lougha.online3@gmail.com';
```
L'espace équipe est sur `/admin.html` (lien « Espace équipe » visible dans le menu pour les admins).

## 6. Recette (à faire avant d'annoncer le site)

- [ ] `index.html` s'affiche en HTTPS, sans bandeau « Mode démo » (sinon `config.js` est vide).
- [ ] Inscription d'un candidat test → email de confirmation reçu → connexion.
- [ ] Formule 1 an + PayPal → infos → « Lu et approuvé » → signature → page paiement.
- [ ] Bouton WhatsApp ouvre une conversation avec +33 7 80 23 77 21, message pré-rempli.
- [ ] Dépôt d'un reçu (PDF ou photo).
- [ ] Compte admin → candidat visible avec « ✍️ À signer » → valider le reçu → dossier du candidat ouvert.
- [ ] « Signer le contrat » → signature → email reçu par le candidat **et** copie sur lougha.online3@gmail.com,
      PDF lisible avec les deux signatures.
- [ ] Candidat : envoi d'un document, « Mon contrat signé » → Télécharger (PDF).
- [ ] Formule 3 mois : pas d'étape « Test d'allemand ».
- [ ] Un candidat ne voit pas les données d'un autre (tester avec 2 comptes).
- [ ] `https://volontariat.loughaonline.com/supabase/schema.sql` renvoie 403/404.

## 7. Modifications courantes

| Quoi | Où |
|---|---|
| Texte des contrats | `js/contrat.js` (**incrémenter `version`** à chaque changement) |
| Prix | `prix` dans `js/contrat.js` + montants du texte du contrat |
| Étapes / documents demandés | `js/etapes.js` |
| Méthodes de paiement | `js/paiement.js` |
| Email / WhatsApp / lien plateforme | `js/config.js` |
| Couleurs | variables en haut de `css/style.css` |

Après modification : ré-uploader les fichiers concernés sur Hostinger (pas de build).

## 8. Points d'attention

- **Données personnelles** (passeports, etc.) stockées chez Supabase (UE si région Frankfurt), bucket privé,
  liens signés valables 1 h. Prévoir une mention RGPD / politique de confidentialité sur le site.
- La signature est une **signature électronique simple** (image + mention + horodatage serveur + empreinte
  SHA-256 du texte accepté). Faire valider par un juriste si une valeur probante renforcée est nécessaire.
- Plan gratuit Supabase : le projet est mis en pause après 7 jours sans activité. Passer au plan Pro (≈ 25 $/mois)
  une fois en production, ou s'assurer d'une activité régulière.
