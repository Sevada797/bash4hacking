<?php
// minimal logger: append timestamp + raw body to J4_log
if(($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST'){ http_response_code(405); exit; }
$body = file_get_contents('php://input');
$time = (new DateTime())->format('Y-m-d H:i:s');
$entry = "----\nTime: $time\n\n" . $body . "\n\n";
file_put_contents(__DIR__.'/J4_log', $entry, FILE_APPEND | LOCK_EX);
http_response_code(200);
echo "OK\n";
