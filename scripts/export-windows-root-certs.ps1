$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$certDir = Join-Path $projectRoot "certs"
New-Item -ItemType Directory -Force -Path $certDir | Out-Null

$stores = @("Cert:\CurrentUser\Root", "Cert:\LocalMachine\Root")
$exported = 0

foreach ($store in $stores) {
    if (-not (Test-Path $store)) { continue }

    Get-ChildItem $store | ForEach-Object {
        $cert = $_
        $safeName = ($cert.Subject -replace '[^a-zA-Z0-9._-]', '_')
        if ($safeName.Length -gt 80) { $safeName = $safeName.Substring(0, 80) }
        if ([string]::IsNullOrWhiteSpace($safeName)) { $safeName = $cert.Thumbprint }

        $target = Join-Path $certDir ("{0}-{1}.crt" -f $safeName, $cert.Thumbprint)
        if (Test-Path $target) { return }

        $bytes = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
        $base64 = [Convert]::ToBase64String($bytes, [Base64FormattingOptions]::InsertLineBreaks)
        $pem = "-----BEGIN CERTIFICATE-----`n$base64`n-----END CERTIFICATE-----`n"
        Set-Content -LiteralPath $target -Value $pem -Encoding ascii
        $script:exported++
    }
}

Write-Host "Exported $exported certificate(s) to $certDir"
Write-Host "Now run: docker compose build --no-cache metrics-exporter auto-healer airflow-init airflow-webserver airflow-scheduler"
Write-Host "Then run: docker compose up"
