# Espace Volontariat en Allemagne — Lougha Online

Site pour les candidats au volontariat en Allemagne :

| Page | Pour qui | Ce qu'on y fait |
|---|---|---|
| `index.html` | public | Page de présentation + boutons « Créer mon espace » / « Se connecter » |
| `connexion.html` | candidats | Inscription, connexion, mot de passe oublié |
| `espace.html` | candidats | 1ʳᵉ connexion : infos + lecture + **signature du contrat**. Ensuite : suivi des 6 étapes, envoi des documents, messages et dates |
| `admin.html` | ton équipe | Liste des candidats, contrat signé (PDF), validation/refus des documents, changement d'étape, dates (test, entretien, visa), message au candidat |

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

### 2. Hébergement
Ce sont des fichiers statiques : n'importe quel hébergeur marche.
Le plus simple : [Netlify](https://app.netlify.com/drop) → glisser-déposer le dossier `espace-volontariat`.
Ensuite, relie un sous-domaine, par exemple `volontariat.lougha.online`, et ajoute un lien depuis Lougha Online.

## Personnaliser

- **Le contrat** → `js/contrat.js`. Remplace le texte provisoire par ton contrat. Les champs `{{prenom}}`, `{{nom}}`,
  `{{passeport}}`… sont remplis automatiquement. **Change `VERSION` à chaque modification du texte.**
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
