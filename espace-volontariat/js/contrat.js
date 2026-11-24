// ─────────────────────────────────────────────────────────────
//  LES CONTRATS (texte officiel fourni par Lougha Online)
// ─────────────────────────────────────────────────────────────
// Deux contrats : 1 an (1 500 €) et 3 mois maximum (1 200 €).
// Le candidat choisit sa formule avant de signer et le texte correspondant s'affiche.
//
// Les champs entre {{ }} sont remplis automatiquement avec les infos du candidat :
//   {{prenom}} {{nom}} {{date_naissance}} {{passeport}} {{email}} {{date}}
//
// Change "version" à chaque modification d'un texte : chaque contrat signé
// garde la version et une empreinte (hash) du texte exact accepté.

// Partie commune aux deux contrats. Les seules différences sont passées en paramètres.
function contrat({ duree, testA2, prixChiffres, prixLettres, dureeLogement, remboursementVisa }) {
  return `
<p>Le présent contrat d'accompagnement, valant également engagement de confidentialité, est établi
entre le Prestataire et la personne suivante :</p>
<p>Nom et prénom : <strong>{{prenom}} {{nom}}</strong><br>
Né(e) le : <strong>{{date_naissance}}</strong><br>
Numéro de passeport : <strong>{{passeport}}</strong><br>
E-mail : <strong>{{email}}</strong></p>
<p>dénommé(e) « le Bénéficiaire ».</p>

<h3 style="text-align:center">Conditions du contrat</h3>

<h3>Article 1 – Objet du contrat</h3>
<p>Le Prestataire s'engage à accompagner le Bénéficiaire pour l'obtention d'un volontariat en
Allemagne d'une durée ${duree}. Dans ce cadre, le Prestataire assure :</p>
<ul>
  <li>La recherche et l'obtention d'un contrat de volontariat auprès de ses collaborateurs en Allemagne.</li>
  <li>L'accompagnement et le suivi du dossier de visa.</li>
  ${testA2 ? "<li>La préparation au test officiel d'allemand niveau A2.</li>" : ""}
  <li>La préparation aux entretiens.</li>
  <li>La rédaction du CV, de la lettre de motivation et la préparation de l'ensemble du dossier.</li>
</ul>

<h3>Article 2 – Prix et paiement</h3>
<p>Le prix total de l'accompagnement est fixé à ${prixChiffres} (${prixLettres}). Ce montant comprend :</p>
<ul>
  <li>Les frais de visa, pour la première demande uniquement.</li>
  <li>Le billet d'avion et l'assurance voyage.</li>
  <li>Les frais des collaborateurs du Prestataire en Allemagne pour l'obtention du contrat de volontariat.</li>
  <li>Les frais d'accompagnement du Prestataire.</li>
  <li>Les frais de logement et de nourriture pendant toute la durée du volontariat en Allemagne (${dureeLogement}).</li>
</ul>
<p>Les frais de visa des demandes suivantes (deuxième demande et au-delà) sont à la charge du Bénéficiaire.</p>
<p>Le montant de ${prixChiffres} est payable en totalité dès la signature du présent contrat.</p>

<h3>Article 3 – Absence de rétractation</h3>
<p>Une fois le contrat signé, le Bénéficiaire ne peut pas se rétracter. Une fois les démarches
commencées, aucun remboursement ne peut être demandé, sauf dans les cas prévus à l'article 6.</p>

<h3>Article 4 – Obligations du Bénéficiaire</h3>
<p>Le Bénéficiaire s'engage à :</p>
<ul>
  <li>Fournir un dossier complet comprenant tous les documents demandés par le Prestataire.</li>
  <li>Fournir l'ensemble de ses documents traduits en allemand.</li>
  <li>Communiquer des informations exactes et véridiques.</li>
  ${testA2 ? "<li>Passer le test officiel d'allemand niveau A2.</li>" : ""}
  <li>Être sérieux et se préparer activement aux entretiens.</li>
  <li>Effectuer une deuxième demande de visa si la première est refusée alors que le contrat de volontariat a été obtenu.</li>
</ul>
<p>Un dossier incomplet, non traduit en allemand ou contenant des informations inexactes libère le
Prestataire de ses obligations, sans remboursement.</p>

<h3>Article 5 – Délai de départ</h3>
<p>Le Bénéficiaire accorde au Prestataire un délai de un (1) à dix (10) mois à compter de la signature
pour les préparatifs et les démarches. Le départ en Allemagne peut ainsi avoir lieu à tout moment
entre un (1) mois et dix (10) mois après la signature.</p>

<h3>Article 6 – Remboursement</h3>
<p>Un remboursement n'est possible que dans les cas suivants :</p>
<ul>
  <li><strong>Aucun contrat de volontariat obtenu</strong> : le Prestataire rembourse la totalité de la somme,
    soit ${prixChiffres}.</li>
  <li><strong>Contrat de volontariat obtenu, mais visa refusé</strong> : si le visa est refusé à la première
    demande, le Bénéficiaire doit obligatoirement faire au moins une deuxième demande, à ses frais.
    Si le visa est refusé une deuxième fois, le Prestataire rembourse ${remboursementVisa}. Les 500 €
    restants correspondent aux frais de gestion du Prestataire, incluant le billet d'avion.</li>
</ul>
<p>Le remboursement est versé au Bénéficiaire dans un délai de deux (2) mois.</p>
<p>Le Bénéficiaire peut renoncer au remboursement et demander un nouveau volontariat. Le
Prestataire lui trouve alors un autre contrat de volontariat et refait son dossier de visa, sans
nouveaux frais d'accompagnement. Dans ce cas, aucun remboursement n'est effectué et les frais de
visa sont à la charge du Bénéficiaire.</p>
<p>En dehors de ces cas, aucun remboursement n'est accordé.</p>

<h3>Article 7 – Confidentialité</h3>
<p>Le présent contrat est un contrat de confidentialité. Il est interdit au Bénéficiaire de divulguer, par
quelque moyen que ce soit (oral, écrit, réseaux sociaux ou autre), toute information concernant :</p>
<ul>
  <li>Les tarifs et les conditions financières.</li>
  <li>Les démarches et le fonctionnement du programme de volontariat.</li>
  <li>Les collaborateurs du Prestataire en Allemagne.</li>
  <li>Le contenu du présent contrat.</li>
</ul>
<p>Une fois arrivé en Allemagne, le Bénéficiaire s'interdit également de divulguer les détails de
l'association ou de la structure d'accueil, ainsi que toute information sur la manière dont il a obtenu
son volontariat et son visa.</p>
<p>Cette obligation s'applique pendant toute la durée du contrat et après sa fin.</p>

<h3>Article 8 – Respect du contrat</h3>
<p>Tout manquement aux obligations prévues par le présent contrat, notamment aux articles 4 et 7,
pourra entraîner la résiliation immédiate du contrat par le Prestataire, sans remboursement.</p>

<p><strong>Accord</strong> — Les deux parties ont lu et accepté les termes de ce contrat.</p>
<p>Fait le : <strong>{{date}}</strong></p>`;
}

export const CONTRATS = {
  // ── Contrat 1 : volontariat d'un an ─────────────────────────
  long: {
    version: "long-officiel-v1",
    nom: "Volontariat 1 an",
    sousTitre: "1 an",
    description: "Volontariat d'un an en Allemagne. Logement, nourriture, billet d'avion et premier visa inclus. Test d'allemand A2.",
    durees: ["1 an"],
    prix: 1500,                      // en euros
    testAllemand: true,
    titre: "Contrat d'accompagnement – Programme de volontariat en Allemagne (1 an)",
    texte: contrat({
      duree: "d'un (1) an",
      testA2: true,
      prixChiffres: "1 500 €",
      prixLettres: "mille cinq cents euros",
      dureeLogement: "1 an",
      remboursementVisa: "1 000 €",
    }),
  },

  // ── Contrat 2 : 3 mois maximum ──────────────────────────────
  court: {
    version: "court-officiel-v1",
    nom: "Volontariat 3 mois",
    sousTitre: "3 mois maximum",
    description: "Volontariat de 3 mois maximum en Allemagne. Logement, nourriture, billet d'avion et premier visa inclus.",
    durees: ["3 mois maximum"],
    prix: 1200,                      // en euros
    testAllemand: false,
    titre: "Contrat d'accompagnement – Programme de volontariat en Allemagne (3 mois maximum)",
    texte: contrat({
      duree: "de trois (3) mois maximum",
      testA2: false,
      prixChiffres: "1 200 €",
      prixLettres: "mille deux cents euros",
      dureeLogement: "3 mois maximum",
      remboursementVisa: "700 €",
    }),
  },
};
