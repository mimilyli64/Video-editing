// ─────────────────────────────────────────────────────────────
//  LE CONTRAT
// ─────────────────────────────────────────────────────────────
// ⚠️  Texte PROVISOIRE : remplace-le par ton vrai contrat.
// Les champs entre {{ }} sont remplis automatiquement avec les infos
// saisies par le candidat : {{prenom}} {{nom}} {{date_naissance}}
// {{lieu_naissance}} {{nationalite}} {{adresse}} {{telephone}}
// {{passeport}} {{email}} {{date}}
//
// Change VERSION à chaque modification du texte : chaque contrat signé
// garde la version et une empreinte (hash) du texte exact accepté.

export const VERSION = "2026-11-v1";

export const TITRE = "Contrat d'accompagnement — Volontariat en Allemagne";

export const TEXTE = `
<p><strong>Entre :</strong> Lougha Online, ci-après « l'accompagnateur »,</p>
<p><strong>Et :</strong> {{prenom}} {{nom}}, né(e) le {{date_naissance}} à {{lieu_naissance}},
de nationalité {{nationalite}}, demeurant {{adresse}}, téléphone {{telephone}},
email {{email}}, passeport n° {{passeport}}, ci-après « le candidat ».</p>

<h3>Article 1 — Objet</h3>
<p>Le présent contrat a pour objet l'accompagnement du candidat dans ses démarches en vue d'un
volontariat en Allemagne : constitution du dossier, préparation au test officiel d'allemand,
mise en relation avec les organismes d'accueil, préparation aux entretiens et accompagnement
dans les démarches de visa.</p>

<h3>Article 2 — Engagements de l'accompagnateur</h3>
<p>[Texte provisoire — à remplacer par le contrat définitif.]</p>

<h3>Article 3 — Engagements du candidat</h3>
<p>Le candidat s'engage à fournir des documents authentiques et à jour, à respecter les délais
communiqués et à informer l'accompagnateur de tout changement de situation.</p>

<h3>Article 4 — Tarifs et modalités de paiement</h3>
<p>[À compléter.]</p>

<h3>Article 5 — Durée et résiliation</h3>
<p>[À compléter.]</p>

<h3>Article 6 — Données personnelles</h3>
<p>Les informations et documents transmis sont utilisés uniquement pour les démarches du
volontariat et ne sont partagés qu'avec les organismes concernés par le dossier du candidat.</p>

<p>Fait le {{date}}, signé électroniquement.</p>
`;
