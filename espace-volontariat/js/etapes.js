// Les étapes du parcours et les documents demandés à chaque étape.
// Tu peux modifier les textes, ajouter ou retirer des documents ici.

export const ETAPES = [
  { id: 0, court: "Contrat", titre: "Signature du contrat",
    desc: "Lis ton contrat d'accompagnement, complète tes informations et signe-le en ligne." },
  { id: 1, court: "Dossier", titre: "Dossier initial",
    desc: "Envoie-nous tes documents de base. Nous les vérifions et te disons si quelque chose manque." },
  { id: 2, court: "Test d'allemand", titre: "Test officiel d'allemand",
    desc: "Inscription et passage du certificat officiel (Goethe-Institut, ÖSD ou telc). Dépose ton certificat dès que tu l'as." },
  { id: 3, court: "Entretiens", titre: "Entretiens avec les organismes",
    desc: "Nous transmettons ton dossier aux structures d'accueil du volontariat et organisons tes entretiens." },
  { id: 4, court: "Visa", titre: "Démarches visa",
    desc: "Constitution du dossier visa et rendez-vous à l'ambassade ou au consulat d'Allemagne." },
  { id: 5, court: "Départ", titre: "Départ en Allemagne",
    desc: "Ton visa est accepté : on prépare ton arrivée. Viel Erfolg !" },
];

export const DOCUMENTS = [
  { type: "passeport",    etape: 1, requis: true,  label: "Passeport (page d'identité)" },
  { type: "photo",        etape: 1, requis: true,  label: "Photo d'identité biométrique" },
  { type: "cv",           etape: 1, requis: true,  label: "CV en allemand (Lebenslauf)" },
  { type: "motivation",   etape: 1, requis: true,  label: "Lettre de motivation (Motivationsschreiben)" },
  { type: "diplomes",     etape: 1, requis: true,  label: "Diplômes et relevés de notes" },
  { type: "casier",       etape: 1, requis: false, label: "Extrait de casier judiciaire" },
  { type: "certificat_allemand", etape: 2, requis: true, label: "Certificat d'allemand (Goethe, ÖSD, telc)" },
  { type: "convention",   etape: 3, requis: true,  label: "Convention de volontariat signée (Vereinbarung)" },
  { type: "formulaire_visa", etape: 4, requis: true, label: "Formulaire de demande de visa" },
  { type: "rdv_visa",     etape: 4, requis: true,  label: "Confirmation du rendez-vous visa" },
  { type: "assurance",    etape: 4, requis: false, label: "Attestation d'assurance" },
  { type: "visa",         etape: 5, requis: true,  label: "Copie du visa obtenu" },
];

export const STATUTS_DOC = {
  en_attente: { label: "En vérification", cls: "badge-wait" },
  valide:     { label: "Validé",          cls: "badge-ok" },
  refuse:     { label: "À refaire",       cls: "badge-ko" },
};
