# Espace Volontariat en Allemagne — Lougha Online

> 👉 **Pour le développeur qui installe le site sur Hostinger : voir [GUIDE-DEVELOPPEUR.md](GUIDE-DEVELOPPEUR.md).**

Site pour les candidats au volontariat en Allemagne :

| Page | Pour qui | Ce qu'on y fait |
|---|---|---|
| `index.html` | public | Page de présentation + boutons « Créer mon espace » / « Se connecter » |
| `connexion.html` | candidats | Inscription, connexion, mot de passe oublié |
| `espace.html` | candidats | 1ʳᵉ connexion : choix de la formule et de la méthode de paiement (PayPal ou carte Visa) + infos + **signature du contrat**, puis contact WhatsApp et **dépôt du reçu de paiement**. Une fois le reçu validé : suivi des 6 étapes, envoi des documents, messages et dates |
| `admin.html` | ton équipe | Liste des candidats, contrat signé (PDF), validation des reçus de paiement, validation/refus des documents, changement d'étape, dates (test, entretien, visa), message au candidat |

Formules : **1 an → 1 500 €** · **3 mois maximum → 1 200 €**. Les prix ne sont affichés qu'aux candidats
connectés (article 7 du contrat : confidentialité des tarifs).

Les étapes : Contrat → Dossier → Test d'allemand A2 (formule 1 an seulement) → Entretiens → Visa → Départ.

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
   (ex. `https://volontariat.loughaonline.com`) et ajoute-la aussi dans *Redirect URLs*.
5. Inscris-toi sur le site avec ton email, puis dans **SQL Editor** :
   ```sql
   update public.profiles set role = 'admin' where email = 'ton@email.com';
   ```
   Tu as maintenant accès à `admin.html`. Fais pareil pour chaque membre de l'équipe.

### 1 bis. WhatsApp et paiement
Le paiement ne se fait **pas** sur le site :
1. Au moment de signer, le candidat choisit sa méthode : **PayPal** ou **carte Visa**.
2. Après la signature, il clique sur **« Nous écrire sur WhatsApp »** (message pré-rempli avec son nom, sa formule,
   le montant et la méthode choisie). Vous lui envoyez les informations pour payer.
3. Il dépose son **reçu de paiement** dans son espace.
4. Dans `admin.html`, vous cliquez sur **✓ Valider** sur le reçu : le candidat est marqué « payé » et son dossier
   s'ouvre (envoi des documents, suivi des étapes).

Si le reçu a été envoyé directement sur WhatsApp, le bouton **Marquer comme payé** fait la même chose.

👉 Mets ton numéro WhatsApp dans `js/config.js` (`WHATSAPP`, format international, chiffres seulement).
Il sert aussi au bouton flottant **« Support WhatsApp »** affiché sur toutes les pages.

### 1 ter. Signature des deux parties et envoi de la copie par email
1. Le candidat signe en premier, depuis son espace (avec la mention « Lu et approuvé »).
2. Dans `admin.html`, le candidat apparaît avec **✍️ À signer**. Ouvre sa fiche → **Signer le contrat** →
   relis le contrat, indique ton nom, signe au doigt ou à la souris → **Signer et envoyer la copie au candidat**.
3. Le site génère le PDF du contrat signé par les deux parties et l'envoie automatiquement à l'email du candidat,
   avec une copie à `lougha.online3@gmail.com`. Le bouton **Renvoyer la copie par email** permet de le renvoyer.
4. Le candidat peut aussi télécharger son contrat en PDF à tout moment depuis son espace.

L'envoi des emails passe par **[Resend](https://resend.com)** (gratuit jusqu'à 3 000 emails/mois) :
1. Crée un compte Resend → **Domains → Add domain** → `loughaonline.com` → ajoute chez ton hébergeur de domaine
   les enregistrements DNS indiqués (quelques minutes). C'est ce qui permet d'envoyer depuis
   `contrats@loughaonline.com` sans finir en spam.
2. **API Keys → Create API key** et copie la clé.
3. Installe la [CLI Supabase](https://supabase.com/docs/guides/cli), puis depuis le dossier `espace-volontariat` :
   ```bash
   supabase login
   supabase link --project-ref TON_ID_DE_PROJET
   supabase secrets set RESEND_API_KEY=re_xxx EMAIL_FROM="Lougha Online <contrats@loughaonline.com>" EMAIL_COPIE=lougha.online3@gmail.com
   supabase functions deploy envoyer-contrat
   ```

Tant que Resend n'est pas configuré, la signature fonctionne quand même : l'équipe voit un message d'erreur
pour l'email et peut télécharger le PDF pour l'envoyer à la main.

### 2. Hébergement
Ce sont des fichiers statiques : n'importe quel hébergeur marche.
Le plus simple : [Netlify](https://app.netlify.com/drop) → glisser-déposer le dossier `espace-volontariat`.
Ensuite, relie un sous-domaine, par exemple `volontariat.loughaonline.com`, et ajoute un lien depuis Lougha Online.

## Personnaliser

- **Les contrats** → `js/contrat.js`. Ce sont les textes officiels « Contrat d'accompagnement – Programme de
  volontariat en Allemagne » : `long` (1 an, 1 500 €) et `court` (3 mois maximum, 1 200 €). Le tronc commun est
  écrit une seule fois ; les différences (durée, test A2, prix, montant remboursé) sont en bas du fichier.
  Les champs `{{prenom}}`, `{{nom}}`, `{{date_naissance}}`, `{{passeport}}`, `{{email}}`, `{{date}}` sont remplis
  automatiquement. **Change `version` à chaque modification d'un texte.**
- **Les prix** → `prix` dans `js/contrat.js` (et les montants écrits dans le texte du contrat).
- **Les méthodes de paiement** et leurs explications → `js/paiement.js`.
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
