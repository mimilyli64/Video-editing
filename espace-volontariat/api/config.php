<?php
// ─────────────────────────────────────────────────────────────
//  CONFIGURATION DU SERVEUR — Espace volontariat Lougha Online
// ─────────────────────────────────────────────────────────────
if (!defined('LOUGHA')) { http_response_code(403); exit; }

// Base MySQL (hPanel Hostinger → Bases de données → MySQL)
const DB_HOST = 'localhost';
const DB_NAME = '';          // ex. u123456789_volontariat
const DB_USER = '';          // ex. u123456789_lougha
const DB_PASS = '';

// Comptes "équipe" : ces emails deviennent administrateurs dès leur inscription.
const ADMIN_EMAILS = ['lougha.online3@gmail.com'];

// Emails envoyés par le site (contrat signé, mot de passe oublié).
// EMAIL_FROM doit être une adresse de ton domaine (sinon les emails finissent en spam).
const EMAIL_FROM      = 'Lougha Online <no-reply@loughaonline.com>';
const EMAIL_REPLY_TO  = 'lougha.online3@gmail.com';
const EMAIL_COPIE     = 'lougha.online3@gmail.com';   // reçoit une copie de chaque contrat signé

// Adresse publique du site (pour le lien "mot de passe oublié"). Vide = détectée automatiquement.
const SITE_URL = '';

// Dossier des fichiers envoyés (passeports, reçus…). Protégé par api/storage/.htaccess.
// Conseillé : un dossier hors de public_html, ex. '/home/u123456789/volontariat-storage'.
const STORAGE_DIR = __DIR__ . '/storage';

// Prix des formules (doivent correspondre à js/contrat.js)
const PRIX = ['long' => 1500, 'court' => 1200];
