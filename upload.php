<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

function respond(bool $success, array $data = [], int $status = 200): void {
    http_response_code($status);
    echo json_encode(
        array_merge(['success' => $success], $data),
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
    );
    exit;
}

$upload_token = 'YOURTOKEN';

if (!isset($_POST['token']) || !hash_equals($upload_token, (string) $_POST['token'])) {
    respond(false, ['error' => 'Token not found.'], 403);
}

if (!isset($_FILES['image'])) {
    respond(false, ['error' => 'Image upload error.'], 400);
}

$file = $_FILES['image'];

if ($file['error'] !== UPLOAD_ERR_OK) {
    respond(false, ['error' => 'Upload error'], 400);
}

if ($file['size'] <= 0) {
    respond(false, ['error' => 'File empty.'], 400);
}

if ($file['size'] > 5 * 1024 * 1024) {
    respond(false, ['error' => '5Mo max'], 413);
}

$finfo = new finfo(FILEINFO_MIME_TYPE);
$mime = $finfo->file($file['tmp_name']);

$allowed_mimes = [
    'image/png' => 'png',
    'image/jpeg' => 'jpg',
    'image/webp' => 'webp'
];

if (!isset($allowed_mimes[$mime])) {
    respond(false, ['error' => 'only image.'], 415);
}

$extension = $allowed_mimes[$mime];
$filename = bin2hex(random_bytes(16)) . '.' . $extension;

$upload_dir = __DIR__ . '/uploads';

if (!is_dir($upload_dir)) {
    if (!mkdir($upload_dir, 0755, true)) {
        respond(false, ['error' => 'Create upload folder'], 500);
    }
}

$destination = $upload_dir . '/' . $filename;

if (!move_uploaded_file($file['tmp_name'], $destination)) {
    respond(false, ['error' => 'Save error.'], 500);
}

$scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
$host = $_SERVER['HTTP_HOST'] ?? 'urdomain.fr';

$url = $scheme . '://' . $host . '/uploads/' . $filename;

respond(true, [
    'filename' => $filename,
    'url' => $url
]);