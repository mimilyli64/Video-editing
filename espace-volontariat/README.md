# Espace Volontariat en Allemagne — Lougha Online

Site HTML/CSS/JS + API **PHP 8 / MySQL**, à héberger tel quel sur Hostinger (aucun service externe,
aucun build).

| Chemin | Rôle |
|---|---|
| `index.html` | page publique |
| `connexion.html` | inscription, connexion, mot de passe oublié |
| `espace.html` + `js/espace.js` | espace candidat : formule, contrat, signature, reçu de paiement, suivi du dossier, documents |
| `admin.html` + `js/admin.js` | espace équipe : candidats, reçus, documents, étapes, messages, signature Lougha, envoi du PDF |
| `api/index.php` | API (sessions PHP, MySQL, fichiers, emails via `mail()`) |
| `api/config.php` | **à remplir** : identifiants MySQL, emails |
| `api/storage/` | fichiers des candidats (non accessibles directement, servis par l'API après contrôle d'accès) |
| `js/contrat.js` | textes officiels des contrats 1 an / 3 mois |
| `js/etapes.js` | étapes et documents demandés |
| `js/config.js` | WhatsApp, email de contact, `MODE_DEMO` |

## Mise en route
1. Déposer le dossier (sous-domaine ou sous-dossier).
2. Créer une base MySQL et remplir `DB_NAME`, `DB_USER`, `DB_PASS` dans `api/config.php`.
   Les tables (`vol_users`, `vol_contracts`, `vol_documents`) sont créées automatiquement au premier appel.
3. `EMAIL_FROM` : une adresse du domaine (ex. `no-reply@loughaonline.com`) pour que `mail()` ne finisse pas en spam.
4. Les emails listés dans `ADMIN_EMAILS` deviennent comptes équipe à l'inscription (`lougha.online3@gmail.com`).
5. Conseillé : `STORAGE_DIR` hors de `public_html`. Sinon `api/storage/.htaccess` bloque l'accès direct.

PHP requis : 8.1+, extensions `pdo_mysql`, `fileinfo`, `mbstring`. Envoi de fichiers : 10 Mo max par document
(`upload_max_filesize` ≥ 12M, `post_max_size` ≥ 40M pour le PDF du contrat).

## Sécurité
- Mots de passe : `password_hash`. Sessions PHP (cookie HttpOnly, SameSite=Lax, Secure en HTTPS).
- Anti-CSRF : chaque appel POST exige l'en-tête `X-Lougha: 1` (impossible depuis un autre site sans CORS).
- Un candidat n'accède qu'à ses données ; les actions équipe exigent `role = admin`.
- Contrat : une seule signature candidat, non modifiable ; signature Lougha une seule fois ; horodatage serveur,
  version et empreinte SHA-256 du texte accepté.
- Documents : PDF/JPG/PNG/WEBP/HEIC vérifiés (`finfo`), noms de fichiers aléatoires, téléchargement contrôlé.
- Avant validation du paiement, seul le reçu peut être envoyé.

## Modifier
Texte des contrats → `js/contrat.js` (incrémenter `version`). Prix → `js/contrat.js` et `PRIX` dans
`api/config.php`. Étapes/documents → `js/etapes.js`. Couleurs → haut de `css/style.css`.
