# Espace Volontariat en Allemagne — Lougha Online

Site pour les candidats au volontariat en Allemagne :

| Page | Pour qui | Ce qu'on y fait |
|---|---|---|
| `index.html` | public | Page de présentation + boutons « Créer mon espace » / « Se connecter » |
| `connexion.html` | candidats | Inscription, connexion, mot de passe oublié |
| `espace.html` | candidats | 1ʳᵉ connexion : choix de la formule + infos + **signature du contrat**, puis **paiement** (PayPal ou carte). Ensuite : suivi des 6 étapes, envoi des documents, messages et dates |
| `admin.html` | ton équipe | Liste des candidats, contrat signé (PDF), paiements, validation/refus des documents, changement d'étape, dates (test, entretien, visa), message au candidat |

Formules : **1 an → 1 500 €** · **moins de 3 mois → 1 200 €**.

Les 6 étapes : Contrat → Dossier → Test d'allemand → Entretiens → Visa → Départ.

## Tester tout de suite (mode démo)

Sans rien configurer, le site tourne en **mode démo** (les données restent dans le navigateur).
Ouvre le dossier avec un petit serveur local, par exemple :

```bash
cd espace-volontariat
python3 -m http.server 8000
# puis ouvre http://localhost:8000
```

Crée un compte candidat, signe le contrat, envoie un document. Puis crée un 2ᵉ compte avec un email qui
commence par `admin` (ex. `admin@test.com`) et ouvre `admin.html` pour voir l'espace équipe.

## Mettre en ligne pour de vrai (≈ 20 minutes, gratuit pour démarrer)

### 1. Supabase (comptes, base de données, fichiers)
1. Crée un compte sur [supabase.com](https://supabase.com) → **New project** (région : Frankfurt, c'est en Europe).
2. **SQL Editor → New query** : colle tout le contenu de `supabase/schema.sql` → **Run**.
3. **Project Settings → API** : copie *Project URL* et la clé *anon public* dans `js/config.js`.
4. **Authentication → URL Configuration** : mets l'adresse de ton site dans *Site URL*
   (ex. `https://volontariat.lougha.online`) et ajoute-la aussi dans *Redirect URLs*.
5. Inscris-toi sur le site avec ton email, puis dans **SQL Editor** :
   ```sql
   update public.profiles set role = 'admin' where email = 'ton@email.com';
   ```
   Tu as maintenant accès à `admin.html`. Fais pareil pour chaque membre de l'équipe.

### 1 bis. PayPal (paiement par PayPal ou carte Visa / Mastercard)
Un seul compte suffit : PayPal gère les deux boutons (« PayPal » et « Carte bancaire »). Le candidat n'a
**pas besoin** de compte PayPal pour payer par carte.
1. Crée (ou utilise) un compte **PayPal Business**.
2. Va sur [developer.paypal.com](https://developer.paypal.com) → **Apps & Credentials** → onglet **Live** →
   **Create App**. Copie le *Client ID* et le *Secret*.
   (Pour tester sans vrai argent, fais pareil dans l'onglet **Sandbox**.)
3. Colle le *Client ID* dans `js/config.js` (`PAYPAL_CLIENT_ID`).
4. Installe la [CLI Supabase](https://supabase.com/docs/guides/cli), puis depuis le dossier `espace-volontariat` :
   ```bash
   supabase login
   supabase link --project-ref TON_ID_DE_PROJET
   supabase secrets set PAYPAL_CLIENT_ID=... PAYPAL_SECRET=... PAYPAL_ENV=live
   supabase functions deploy paiement
   ```
   (`PAYPAL_ENV=sandbox` pour les tests.)

Comment c'est sécurisé : le prix est fixé par le serveur selon le contrat signé (pas par le navigateur), et le
dossier n'est marqué « payé » qu'après confirmation de PayPal. Si un candidat paie autrement (espèces, virement),
l'équipe clique sur **Marquer comme payé** dans `admin.html`.

### 2. Hébergement
Ce sont des fichiers statiques : n'importe quel hébergeur marche.
Le plus simple : [Netlify](https://app.netlify.com/drop) → glisser-déposer le dossier `espace-volontariat`.
Ensuite, relie un sous-domaine, par exemple `volontariat.lougha.online`, et ajoute un lien depuis Lougha Online.

## Personnaliser

- **Les prix** → à changer à 3 endroits : `js/contrat.js` (`prix`), `supabase/functions/paiement/index.ts` (`PRIX`,
  puis redéployer la fonction) et la section « Nos formules » de `index.html`.
- **Les contrats** → `js/contrat.js`. Il y a deux contrats : `long` (1 an) et `court` (moins de 3 mois).
  Le candidat choisit sa formule avant de signer, et le bon contrat s'affiche. Remplace les textes provisoires par tes
  vrais contrats. Les champs `{{prenom}}`, `{{nom}}`, `{{passeport}}`, `{{duree}}`… sont remplis automatiquement.
  **Change `version` à chaque modification d'un texte.**
- **Les étapes et la liste des documents** → `js/etapes.js`.
- **Liens, email de contact** → `js/config.js`.
- **Couleurs** → haut de `css/style.css`.

## Sécurité

- Chaque candidat ne voit **que** son profil, son contrat et ses documents (règles RLS dans `schema.sql`).
- Les fichiers sont dans un stockage **privé**, ouverts via des liens temporaires (1 h).
- Un contrat signé ne peut plus être modifié. On garde : la version du texte, une empreinte SHA-256 du texte exact
  accepté, l'image de la signature, la date/heure du serveur et le navigateur utilisé.
- Seule l'équipe peut changer l'étape d'un candidat ou valider un document.

> Pour la valeur juridique de la signature électronique dans ton pays, fais valider ton contrat par un juriste.
