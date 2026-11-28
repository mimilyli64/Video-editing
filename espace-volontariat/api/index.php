<?php
// ═══════════════════════════════════════════════════════════════════
//  API — Espace volontariat Lougha Online (PHP 8 + MySQL)
//  Un seul point d'entrée : POST api/index.php  { action: "...", ... }
//  Fichiers : GET api/index.php?action=file&id=...
// ═══════════════════════════════════════════════════════════════════
declare(strict_types=1);
define('LOUGHA', true);
require __DIR__ . '/config.php';

date_default_timezone_set('UTC');
ini_set('display_errors', '0');

const MAX_FILE = 10 * 1024 * 1024;
const EXT_OK = ['pdf' => 'application/pdf', 'jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png',
                'webp' => 'image/webp', 'heic' => 'image/heic'];

// ── Session ─────────────────────────────────────────────────────────
$https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
session_name('lougha_vol');
session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'secure' => $https, 'httponly' => true, 'samesite' => 'Lax']);
session_start();

// ── Utilitaires ─────────────────────────────────────────────────────
function out(array $data, int $code = 200): never {
  http_response_code($code);
  header('Content-Type: application/json; charset=utf-8');
  header('Cache-Control: no-store');
  echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
  exit;
}
function fail(string $msg, int $code = 400): never { out(['error' => $msg], $code); }

function db(): PDO {
  static $pdo = null;
  if ($pdo) return $pdo;
  if (DB_NAME === '') fail("Le serveur n'est pas encore configuré (api/config.php).", 500);
  try {
    $pdo = new PDO('mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4', DB_USER, DB_PASS, [
      PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
      PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
      PDO::ATTR_EMULATE_PREPARES => false,
    ]);
  } catch (Throwable $e) {
    error_log('Lougha DB: ' . $e->getMessage());
    fail('Base de données indisponible.', 500);
  }
  $pdo->exec("SET time_zone = '+00:00'");
  install($pdo);
  return $pdo;
}

// Crée les tables au premier lancement (aucune manipulation à faire).
function install(PDO $pdo): void {
  $flag = STORAGE_DIR . '/.installed-v1';
  if (is_file($flag)) return;
  $pdo->exec("CREATE TABLE IF NOT EXISTS vol_users (
    id CHAR(32) PRIMARY KEY,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(190) NOT NULL DEFAULT '',
    role ENUM('candidat','admin') NOT NULL DEFAULT 'candidat',
    stage TINYINT NOT NULL DEFAULT 0,
    contract_type VARCHAR(10) NULL, duration VARCHAR(40) NULL,
    admin_message TEXT NULL, test_date DATE NULL, test_result VARCHAR(190) NULL,
    interview_date DATETIME NULL, visa_appointment DATETIME NULL,
    paid_at DATETIME NULL, paid_amount DECIMAL(10,2) NULL, payment_method VARCHAR(20) NULL, payment_ref VARCHAR(190) NULL,
    reset_hash CHAR(64) NULL, reset_expires DATETIME NULL,
    created_at DATETIME NOT NULL
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
  $pdo->exec("CREATE TABLE IF NOT EXISTS vol_contracts (
    id CHAR(32) PRIMARY KEY,
    user_id CHAR(32) NOT NULL UNIQUE,
    contract_type VARCHAR(10) NOT NULL, duration VARCHAR(40) NOT NULL, payment_method VARCHAR(20) NOT NULL,
    first_name VARCHAR(120) NOT NULL, last_name VARCHAR(120) NOT NULL, birth_date DATE NOT NULL,
    birth_place VARCHAR(190) NOT NULL, nationality VARCHAR(120) NOT NULL, passport_number VARCHAR(60) NOT NULL,
    phone VARCHAR(60) NOT NULL, address VARCHAR(255) NOT NULL,
    contract_version VARCHAR(60) NOT NULL, contract_hash CHAR(64) NOT NULL,
    signature_data MEDIUMTEXT NOT NULL, mention VARCHAR(60) NOT NULL, user_agent VARCHAR(300) NULL,
    signed_at DATETIME NOT NULL,
    provider_signature_data MEDIUMTEXT NULL, provider_signer VARCHAR(190) NULL, provider_signed_at DATETIME NULL,
    emailed_at DATETIME NULL,
    CONSTRAINT fk_vol_c_user FOREIGN KEY (user_id) REFERENCES vol_users(id) ON DELETE CASCADE
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
  $pdo->exec("CREATE TABLE IF NOT EXISTS vol_documents (
    id CHAR(32) PRIMARY KEY,
    user_id CHAR(32) NOT NULL,
    doc_type VARCHAR(40) NOT NULL,
    stored_name CHAR(40) NOT NULL, file_name VARCHAR(255) NOT NULL, file_size INT NOT NULL, mime VARCHAR(60) NOT NULL,
    status ENUM('en_attente','valide','refuse') NOT NULL DEFAULT 'en_attente',
    comment TEXT NULL, uploaded_at DATETIME NOT NULL, reviewed_at DATETIME NULL,
    INDEX (user_id),
    CONSTRAINT fk_vol_d_user FOREIGN KEY (user_id) REFERENCES vol_users(id) ON DELETE CASCADE
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
  if (!is_dir(STORAGE_DIR)) @mkdir(STORAGE_DIR, 0750, true);
  @file_put_contents($flag, date('c'));
}

function uid(): string { return bin2hex(random_bytes(16)); }
function now(): string { return gmdate('Y-m-d H:i:s'); }
// DATETIME MySQL (UTC) → ISO 8601 lisible par tous les navigateurs (Safari compris)
function iso(?string $d): ?string { return $d ? str_replace(' ', 'T', $d) . 'Z' : null; }
// ISO venant du navigateur → DATETIME MySQL (UTC)
function toDb(?string $v): ?string {
  if ($v === null || $v === '') return null;
  $t = strtotime($v);
  if ($t === false) fail('Date invalide.');
  return gmdate('Y-m-d H:i:s', $t);
}
function dateOnly(?string $v): ?string {
  if ($v === null || $v === '') return null;
  if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $v)) fail('Date invalide.');
  return $v;
}
function str($v, int $max = 255): string { return mb_substr(trim((string)($v ?? '')), 0, $max); }

function me(): ?array {
  static $u = false;
  if ($u !== false) return $u;
  $id = $_SESSION['uid'] ?? null;
  if (!$id) return $u = null;
  $s = db()->prepare('SELECT * FROM vol_users WHERE id = ?');
  $s->execute([$id]);
  return $u = ($s->fetch() ?: null);
}
function requireUser(): array { $u = me(); if (!$u) fail('Connecte-toi pour continuer.', 401); return $u; }
function requireAdmin(): array { $u = requireUser(); if ($u['role'] !== 'admin') fail("Réservé à l'équipe.", 403); return $u; }
// Un candidat ne voit que ses données ; l'équipe peut voir celles d'un candidat.
function targetUser(array $in): string {
  $u = requireUser();
  $id = $in['user_id'] ?? null;
  if (!$id || $id === $u['id']) return $u['id'];
  if ($u['role'] !== 'admin') fail('Accès refusé.', 403);
  return (string)$id;
}

function profileOut(array $u): array {
  return [
    'id' => $u['id'], 'email' => $u['email'], 'full_name' => $u['full_name'], 'role' => $u['role'],
    'stage' => (int)$u['stage'], 'contract_type' => $u['contract_type'], 'duration' => $u['duration'],
    'admin_message' => $u['admin_message'] ?? '', 'test_date' => $u['test_date'], 'test_result' => $u['test_result'] ?? '',
    'interview_date' => iso($u['interview_date']), 'visa_appointment' => iso($u['visa_appointment']),
    'paid_at' => iso($u['paid_at']), 'paid_amount' => $u['paid_amount'] !== null ? (float)$u['paid_amount'] : null,
    'payment_method' => $u['payment_method'], 'payment_ref' => $u['payment_ref'], 'created_at' => iso($u['created_at']),
  ];
}
function contractOut(?array $c): ?array {
  if (!$c) return null;
  foreach (['signed_at', 'provider_signed_at', 'emailed_at'] as $k) $c[$k] = iso($c[$k]);
  return $c;
}
function docOut(array $d): array {
  unset($d['stored_name']);
  $d['file_size'] = (int)$d['file_size'];
  $d['uploaded_at'] = iso($d['uploaded_at']);
  $d['reviewed_at'] = iso($d['reviewed_at']);
  return $d;
}
function getUserRow(string $id): array {
  $s = db()->prepare('SELECT * FROM vol_users WHERE id = ?'); $s->execute([$id]);
  return $s->fetch() ?: fail('Compte introuvable.', 404);
}
function getContractRow(string $userId): ?array {
  $s = db()->prepare('SELECT * FROM vol_contracts WHERE user_id = ?'); $s->execute([$userId]);
  return $s->fetch() ?: null;
}

function siteUrl(): string {
  if (SITE_URL !== '') return rtrim(SITE_URL, '/');
  $proto = $GLOBALS['https'] ? 'https' : 'http';
  $dir = rtrim(str_replace('\\', '/', dirname(dirname($_SERVER['SCRIPT_NAME'] ?? '/api/index.php'))), '/');
  return $proto . '://' . ($_SERVER['HTTP_HOST'] ?? 'localhost') . $dir;
}

// Envoi d'email (fonction mail() de l'hébergement), avec pièce jointe optionnelle.
function sendMail(string $to, string $subject, string $html, ?array $attachment = null, ?string $bcc = null): bool {
  $boundary = 'b' . bin2hex(random_bytes(12));
  $headers = [
    'From: ' . EMAIL_FROM,
    'Reply-To: ' . EMAIL_REPLY_TO,
    'MIME-Version: 1.0',
  ];
  if ($bcc) $headers[] = 'Bcc: ' . $bcc;
  $text = trim(html_entity_decode(strip_tags(str_replace(['<br>', '</p>'], ["\n", "\n\n"], $html)), ENT_QUOTES, 'UTF-8'));
  if ($attachment) {
    $headers[] = "Content-Type: multipart/mixed; boundary=\"$boundary\"";
    $alt = 'a' . bin2hex(random_bytes(12));
    $body = "--$boundary\r\nContent-Type: multipart/alternative; boundary=\"$alt\"\r\n\r\n"
      . "--$alt\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($text))
      . "--$alt\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($html))
      . "--$alt--\r\n"
      . "--$boundary\r\nContent-Type: {$attachment['type']}; name=\"{$attachment['name']}\"\r\n"
      . "Content-Transfer-Encoding: base64\r\nContent-Disposition: attachment; filename=\"{$attachment['name']}\"\r\n\r\n"
      . chunk_split($attachment['base64']) . "--$boundary--";
  } else {
    $headers[] = "Content-Type: multipart/alternative; boundary=\"$boundary\"";
    $body = "--$boundary\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($text))
      . "--$boundary\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($html))
      . "--$boundary--";
  }
  $encSubject = '=?UTF-8?B?' . base64_encode($subject) . '?=';
  $from = preg_match('/<([^>]+)>/', EMAIL_FROM, $m) ? $m[1] : EMAIL_FROM;
  return mail($to, $encSubject, $body, implode("\r\n", $headers), '-f' . $from);
}
function mailHtml(string $inner): string {
  return '<div style="font-family:Arial,sans-serif;font-size:15px;color:#111827;line-height:1.6">' . $inner
    . '<p>À très vite,<br>L\'équipe Lougha Online</p></div>';
}

// ── Fichier (GET) ───────────────────────────────────────────────────
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
  if (($_GET['action'] ?? '') !== 'file') fail('Action inconnue.', 404);
  $u = requireUser();
  $s = db()->prepare('SELECT * FROM vol_documents WHERE id = ?');
  $s->execute([(string)($_GET['id'] ?? '')]);
  $d = $s->fetch();
  if (!$d || ($d['user_id'] !== $u['id'] && $u['role'] !== 'admin')) fail('Document introuvable.', 404);
  $path = STORAGE_DIR . '/' . $d['user_id'] . '/' . $d['stored_name'];
  if (!is_file($path)) fail('Fichier introuvable sur le serveur.', 404);
  $safe = preg_replace('/[^\w.\- ]+/u', '_', $d['file_name']);
  header('Content-Type: ' . (in_array($d['mime'], EXT_OK, true) ? $d['mime'] : 'application/octet-stream'));
  header('Content-Length: ' . filesize($path));
  header('Content-Disposition: inline; filename="' . $safe . '"');
  header('X-Content-Type-Options: nosniff');
  header('Cache-Control: private, no-store');
  readfile($path);
  exit;
}

// ── Actions (POST) ──────────────────────────────────────────────────
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') fail('Méthode non autorisée.', 405);
// Protection CSRF : en-tête personnalisé (impossible à envoyer depuis un autre site sans CORS).
if (($_SERVER['HTTP_X_LOUGHA'] ?? '') !== '1') fail('Requête refusée.', 403);

$in = str_starts_with($_SERVER['CONTENT_TYPE'] ?? '', 'application/json')
  ? (json_decode(file_get_contents('php://input') ?: '{}', true) ?: [])
  : $_POST;
$action = (string)($in['action'] ?? '');

try {
switch ($action) {

  // ── Compte ────────────────────────────────────────────────────────
  case 'session':
    $u = me();
    out(['user' => $u ? ['id' => $u['id'], 'email' => $u['email']] : null]);

  case 'signup': {
    $email = mb_strtolower(str($in['email'] ?? '', 190));
    $pw = (string)($in['password'] ?? '');
    $name = str($in['full_name'] ?? '', 190);
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) fail('Entre un email valide.');
    if (mb_strlen($pw) < 6) fail('Le mot de passe doit faire au moins 6 caractères.');
    if (mb_strlen($name) < 3) fail('Entre ton nom et prénom.');
    $s = db()->prepare('SELECT 1 FROM vol_users WHERE email = ?'); $s->execute([$email]);
    if ($s->fetch()) fail('Un compte existe déjà avec cet email.');
    $id = uid();
    $role = in_array($email, array_map('mb_strtolower', ADMIN_EMAILS), true) ? 'admin' : 'candidat';
    db()->prepare('INSERT INTO vol_users (id, email, password_hash, full_name, role, created_at) VALUES (?,?,?,?,?,?)')
      ->execute([$id, $email, password_hash($pw, PASSWORD_DEFAULT), $name, $role, now()]);
    session_regenerate_id(true);
    $_SESSION['uid'] = $id;
    out(['user' => ['id' => $id, 'email' => $email], 'session' => true]);
  }

  case 'signin': {
    $email = mb_strtolower(str($in['email'] ?? '', 190));
    $s = db()->prepare('SELECT * FROM vol_users WHERE email = ?'); $s->execute([$email]);
    $u = $s->fetch();
    if (!$u || !password_verify((string)($in['password'] ?? ''), $u['password_hash'])) {
      usleep(400000);
      fail('Email ou mot de passe incorrect.', 401);
    }
    session_regenerate_id(true);
    $_SESSION['uid'] = $u['id'];
    out(['user' => ['id' => $u['id'], 'email' => $u['email']], 'session' => true]);
  }

  case 'signout':
    $_SESSION = [];
    session_destroy();
    out(['ok' => true]);

  case 'reset_password': {
    $email = mb_strtolower(str($in['email'] ?? '', 190));
    $s = db()->prepare('SELECT id FROM vol_users WHERE email = ?'); $s->execute([$email]);
    if ($u = $s->fetch()) {
      $token = bin2hex(random_bytes(24));
      db()->prepare('UPDATE vol_users SET reset_hash = ?, reset_expires = ? WHERE id = ?')
        ->execute([hash('sha256', $token), gmdate('Y-m-d H:i:s', time() + 3600), $u['id']]);
      $link = siteUrl() . '/connexion.html?token=' . $token;
      sendMail($email, 'Choisis un nouveau mot de passe — Lougha Online', mailHtml(
        '<p>Bonjour,</p><p>Pour choisir un nouveau mot de passe, clique sur ce lien (valable 1 heure) :</p>'
        . '<p><a href="' . htmlspecialchars($link) . '">' . htmlspecialchars($link) . '</a></p>'
        . "<p>Si tu n'as rien demandé, ignore cet email.</p>"));
    }
    out(['ok' => true]); // même réponse que le compte existe ou non
  }

  case 'update_password': {
    $pw = (string)($in['password'] ?? '');
    if (mb_strlen($pw) < 6) fail('Le mot de passe doit faire au moins 6 caractères.');
    $token = (string)($in['token'] ?? '');
    if ($token !== '') {
      $s = db()->prepare('SELECT id FROM vol_users WHERE reset_hash = ? AND reset_expires > ?');
      $s->execute([hash('sha256', $token), now()]);
      $u = $s->fetch() ?: fail('Ce lien a expiré. Refais une demande de mot de passe oublié.');
      $id = $u['id'];
    } else {
      $id = requireUser()['id'];
    }
    db()->prepare('UPDATE vol_users SET password_hash = ?, reset_hash = NULL, reset_expires = NULL WHERE id = ?')
      ->execute([password_hash($pw, PASSWORD_DEFAULT), $id]);
    session_regenerate_id(true);
    $_SESSION['uid'] = $id;
    out(['ok' => true]);
  }

  // ── Dossier du candidat ───────────────────────────────────────────
  case 'get_profile':
    out(['profile' => profileOut(getUserRow(targetUser($in)))]);

  case 'get_contract':
    out(['contract' => contractOut(getContractRow(targetUser($in)))]);

  case 'sign_contract': {
    $u = requireUser();
    if (getContractRow($u['id'])) fail('Ton contrat est déjà signé.');
    $c = is_array($in['contract'] ?? null) ? $in['contract'] : fail('Contrat manquant.');
    $type = (string)($c['contract_type'] ?? '');
    $pay = (string)($c['payment_method'] ?? '');
    if (!isset(PRIX[$type])) fail('Choisis ta formule.');
    if (!in_array($pay, ['paypal', 'carte'], true)) fail('Choisis ta méthode de paiement.');
    $fields = ['first_name', 'last_name', 'birth_place', 'nationality', 'passport_number', 'phone', 'address', 'duration',
               'contract_version', 'mention'];
    $v = [];
    foreach ($fields as $f) { $v[$f] = str($c[$f] ?? ''); if ($v[$f] === '') fail('Complète tous les champs.'); }
    $birth = dateOnly($c['birth_date'] ?? '') ?? fail('Indique ta date de naissance.');
    $hash = (string)($c['contract_hash'] ?? '');
    if (!preg_match('/^[a-f0-9]{64}$/', $hash)) fail('Contrat invalide.');
    $sig = (string)($c['signature_data'] ?? '');
    if (!str_starts_with($sig, 'data:image/png;base64,') || strlen($sig) > 2_000_000) fail('Signature invalide.');
    db()->beginTransaction();
    db()->prepare('INSERT INTO vol_contracts (id, user_id, contract_type, duration, payment_method, first_name, last_name,
        birth_date, birth_place, nationality, passport_number, phone, address, contract_version, contract_hash,
        signature_data, mention, user_agent, signed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)')
      ->execute([uid(), $u['id'], $type, $v['duration'], $pay, $v['first_name'], $v['last_name'], $birth, $v['birth_place'],
        $v['nationality'], $v['passport_number'], $v['phone'], $v['address'], $v['contract_version'], $hash, $sig,
        $v['mention'], str($c['user_agent'] ?? '', 300), now()]);
    db()->prepare('UPDATE vol_users SET stage = GREATEST(stage, 1), contract_type = ?, duration = ?, payment_method = ? WHERE id = ?')
      ->execute([$type, $v['duration'], $pay, $u['id']]);
    db()->commit();
    out(['contract' => contractOut(getContractRow($u['id']))]);
  }

  case 'list_documents': {
    $s = db()->prepare('SELECT * FROM vol_documents WHERE user_id = ? ORDER BY uploaded_at DESC');
    $s->execute([targetUser($in)]);
    out(['documents' => array_map('docOut', $s->fetchAll())]);
  }

  case 'upload_document': {
    $u = requireUser();
    $type = (string)($in['doc_type'] ?? '');
    if (!preg_match('/^[a-z_]{2,40}$/', $type)) fail('Type de document invalide.');
    if (!getContractRow($u['id'])) fail("Signe d'abord ton contrat.");
    if ($type !== 'recu_paiement' && !$u['paid_at']) fail('Tes documents pourront être envoyés après la validation de ton paiement.');
    $f = $_FILES['file'] ?? null;
    if (!$f || ($f['error'] ?? 1) !== UPLOAD_ERR_OK) fail("Le fichier n'a pas pu être envoyé (10 Mo maximum).");
    if ($f['size'] > MAX_FILE) fail('Fichier trop lourd (10 Mo maximum).');
    $ext = strtolower(pathinfo((string)$f['name'], PATHINFO_EXTENSION));
    if (!isset(EXT_OK[$ext])) fail('Format accepté : PDF, JPG, PNG, WEBP ou HEIC.');
    $mime = (new finfo(FILEINFO_MIME_TYPE))->file($f['tmp_name']) ?: '';
    if (!in_array($mime, array_values(EXT_OK), true) && !($ext === 'heic' && str_contains($mime, 'heif'))) {
      fail("Ce fichier n'est pas une image ou un PDF valide.");
    }
    $dir = STORAGE_DIR . '/' . $u['id'];
    if (!is_dir($dir) && !@mkdir($dir, 0750, true)) fail("Stockage indisponible sur le serveur.", 500);
    $stored = bin2hex(random_bytes(20));
    if (!move_uploaded_file($f['tmp_name'], "$dir/$stored")) fail("Le fichier n'a pas pu être enregistré.", 500);
    $id = uid();
    db()->prepare('INSERT INTO vol_documents (id, user_id, doc_type, stored_name, file_name, file_size, mime, uploaded_at)
        VALUES (?,?,?,?,?,?,?,?)')
      ->execute([$id, $u['id'], $type, $stored, str($f['name']), (int)$f['size'], EXT_OK[$ext], now()]);
    $s = db()->prepare('SELECT * FROM vol_documents WHERE id = ?'); $s->execute([$id]);
    out(['document' => docOut($s->fetch())]);
  }

  case 'delete_document': {
    $u = requireUser();
    $s = db()->prepare('SELECT * FROM vol_documents WHERE id = ?'); $s->execute([(string)($in['id'] ?? '')]);
    $d = $s->fetch() ?: fail('Document introuvable.', 404);
    $own = $d['user_id'] === $u['id'] && $d['status'] === 'en_attente';
    if (!$own && $u['role'] !== 'admin') fail('Ce document ne peut plus être supprimé.', 403);
    db()->prepare('DELETE FROM vol_documents WHERE id = ?')->execute([$d['id']]);
    @unlink(STORAGE_DIR . '/' . $d['user_id'] . '/' . $d['stored_name']);
    out(['ok' => true]);
  }

  // ── Espace équipe ─────────────────────────────────────────────────
  case 'list_candidates': {
    requireAdmin();
    $rows = db()->query("SELECT u.*,
        (SELECT COUNT(*) FROM vol_documents d WHERE d.user_id = u.id) AS docs_total,
        (SELECT COUNT(*) FROM vol_documents d WHERE d.user_id = u.id AND d.status = 'en_attente') AS docs_pending,
        (SELECT COUNT(*) FROM vol_contracts c WHERE c.user_id = u.id AND c.provider_signed_at IS NULL) AS to_sign
      FROM vol_users u WHERE u.role = 'candidat' ORDER BY u.created_at DESC")->fetchAll();
    out(['candidates' => array_map(fn($r) => profileOut($r) + [
      'docs_total' => (int)$r['docs_total'], 'docs_pending' => (int)$r['docs_pending'], 'to_sign' => (int)$r['to_sign'] > 0,
    ], $rows)]);
  }

  case 'update_profile': {
    requireAdmin();
    $id = (string)($in['user_id'] ?? '');
    getUserRow($id);
    $p = is_array($in['patch'] ?? null) ? $in['patch'] : [];
    $set = []; $vals = [];
    $map = [
      'stage' => fn($v) => max(0, min(5, (int)$v)),
      'admin_message' => fn($v) => str($v, 5000),
      'test_result' => fn($v) => str($v, 190),
      'test_date' => fn($v) => dateOnly($v),
      'interview_date' => fn($v) => toDb($v),
      'visa_appointment' => fn($v) => toDb($v),
      'paid_at' => fn($v) => toDb($v),
      'paid_amount' => fn($v) => $v === null ? null : (float)$v,
      'payment_method' => fn($v) => in_array($v, ['paypal', 'carte'], true) ? $v : null,
      'payment_ref' => fn($v) => $v === null ? null : str($v, 190),
    ];
    foreach ($map as $k => $fn) if (array_key_exists($k, $p)) { $set[] = "$k = ?"; $vals[] = $fn($p[$k]); }
    if ($set) { $vals[] = $id; db()->prepare('UPDATE vol_users SET ' . implode(', ', $set) . ' WHERE id = ?')->execute($vals); }
    out(['profile' => profileOut(getUserRow($id))]);
  }

  case 'review_document': {
    requireAdmin();
    $status = (string)($in['status'] ?? '');
    if (!in_array($status, ['en_attente', 'valide', 'refuse'], true)) fail('Statut invalide.');
    $id = (string)($in['id'] ?? '');
    db()->prepare('UPDATE vol_documents SET status = ?, comment = ?, reviewed_at = ? WHERE id = ?')
      ->execute([$status, isset($in['comment']) ? str($in['comment'], 2000) : null, now(), $id]);
    $s = db()->prepare('SELECT * FROM vol_documents WHERE id = ?'); $s->execute([$id]);
    out(['document' => docOut($s->fetch() ?: fail('Document introuvable.', 404))]);
  }

  case 'sign_provider': {
    requireAdmin();
    $id = (string)($in['user_id'] ?? '');
    $c = getContractRow($id) ?: fail("Le candidat n'a pas encore signé.");
    if ($c['provider_signature_data']) fail('Le contrat est déjà signé par Lougha Online.');
    $sig = (string)($in['provider_signature_data'] ?? '');
    if (!str_starts_with($sig, 'data:image/png;base64,') || strlen($sig) > 2_000_000) fail('Signature invalide.');
    $name = str($in['provider_signer'] ?? '', 190);
    if (mb_strlen($name) < 3) fail('Indique le nom de la personne qui signe.');
    db()->prepare('UPDATE vol_contracts SET provider_signature_data = ?, provider_signer = ?, provider_signed_at = ? WHERE user_id = ?')
      ->execute([$sig, $name, now(), $id]);
    out(['contract' => contractOut(getContractRow($id))]);
  }

  case 'send_contract': {
    requireAdmin();
    $id = (string)($in['user_id'] ?? '');
    $c = getContractRow($id) ?: fail('Contrat introuvable.', 404);
    if (!$c['signature_data'] || !$c['provider_signature_data']) fail('Le contrat doit être signé par les deux parties.');
    $pdf = preg_replace('/\s+/', '', (string)($in['pdf'] ?? ''));
    if (strlen($pdf) < 1000 || strlen($pdf) > 15_000_000 || !str_starts_with(base64_decode(substr($pdf, 0, 12), true) ?: '', '%PDF')) {
      fail('PDF invalide.');
    }
    $cand = getUserRow($id);
    $file = preg_replace('/[^\w.\-]+/', '_', (string)($in['filename'] ?? 'Contrat-volontariat.pdf'));
    $ok = sendMail($cand['email'], "Ton contrat d'accompagnement signé — Lougha Online", mailHtml(
      '<p>Bonjour ' . htmlspecialchars($c['first_name']) . ',</p>'
      . "<p>Ton contrat d'accompagnement pour le programme de volontariat en Allemagne a été signé par les deux parties. "
      . 'Tu trouveras ta copie en pièce jointe (PDF).</p>'
      . "<p>Tu peux suivre l'avancement de ton dossier à tout moment depuis ton espace personnel.</p>"),
      ['name' => $file, 'type' => 'application/pdf', 'base64' => $pdf], EMAIL_COPIE ?: null);
    if (!$ok) fail("L'email n'a pas pu être envoyé par le serveur.", 502);
    db()->prepare('UPDATE vol_contracts SET emailed_at = ? WHERE user_id = ?')->execute([now(), $id]);
    out(['ok' => true, 'to' => $cand['email']]);
  }

  default:
    fail('Action inconnue.', 404);
}
} catch (Throwable $e) {
  if (db()->inTransaction()) db()->rollBack();
  error_log('Lougha API: ' . $e->getMessage());
  fail('Erreur du serveur. Réessaie dans un instant.', 500);
}
