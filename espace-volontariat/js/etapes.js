// Les étapes du parcours et les documents demandés à chaque étape.
// Tu peux modifier les textes, ajouter ou retirer des documents ici.
// `formule: "long"` = étape seulement pour la formule 1 an (le contrat 3 mois n'a pas de test d'allemand).

export const ETAPES = [
  { id: 0, court: "Contrat", titre: "Contrat et paiement",
    desc: "Choisis ta formule, signe ton contrat en ligne, puis envoie ton reçu de paiement." },
  { id: 1, court: "Dossier", titre: "Dossier initial",
    desc: "Envoie-nous tes documents, traduits en allemand. Nous rédigeons ton CV et ta lettre de motivation et préparons l'ensemble de ton dossier." },
  { id: 2, court: "Test d'allemand", titre: "Test officiel d'allemand (A2)", formule: "long",
    desc: "Préparation et passage du test officiel d'allemand niveau A2. Dépose ton certificat dès que tu l'as." },
  { id: 3, court: "Entretiens", titre: "Entretiens",
    desc: "Nous cherchons ton contrat de volontariat auprès de nos collaborateurs en Allemagne et te préparons aux entretiens." },
  { id: 4, court: "Visa", titre: "Démarches visa",
    desc: "Nous constituons et suivons ton dossier de visa jusqu'au rendez-vous à l'ambassade ou au consulat." },
  { id: 5, court: "Départ", titre: "Départ en Allemagne",
    desc: "Ton visa est accepté : on prépare ton départ. Viel Erfolg !" },
];

// Étapes affichées pour une formule donnée ("long" ou "court").
export const etapesPour = (formule) => ETAPES.filter((e) => !e.formule || e.formule === formule);

export const DOCUMENTS = [
  { type: "passeport",    etape: 1, requis: true,  label: "Passeport (page d'identité)" },
  { type: "photo",        etape: 1, requis: true,  label: "Photo d'identité biométrique" },
  { type: "diplomes",     etape: 1, requis: true,  label: "Diplômes et relevés de notes (traduits en allemand)" },
  { type: "casier",       etape: 1, requis: false, label: "Extrait de casier judiciaire (traduit en allemand)" },
  { type: "autres",       etape: 1, requis: false, label: "Autres documents demandés (traduits en allemand)" },
  { type: "certificat_allemand", etape: 2, requis: true, label: "Certificat officiel d'allemand A2" },
  { type: "convention",   etape: 3, requis: true,  label: "Contrat de volontariat signé" },
  { type: "formulaire_visa", etape: 4, requis: true, label: "Formulaire de demande de visa" },
  { type: "rdv_visa",     etape: 4, requis: true,  label: "Confirmation du rendez-vous visa" },
  { type: "visa",         etape: 5, requis: true,  label: "Copie du visa obtenu" },
];

export const STATUTS_DOC = {
  en_attente: { label: "En vérification", cls: "badge-wait" },
  valide:     { label: "Validé",          cls: "badge-ok" },
  refuse:     { label: "À refaire",       cls: "badge-ko" },
};
