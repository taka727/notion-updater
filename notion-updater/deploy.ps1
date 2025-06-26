Write-Host "== SAM Build =="
sam build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed"
    exit $LASTEXITCODE
}

Write-Host "== SAM Deploy =="
sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
if ($LASTEXITCODE -ne 0) {
    Write-Error "Deploy failed"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Deploy complete"
