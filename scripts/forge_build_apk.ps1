$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Build APK CPU/RAM only.
# Requiert Android SDK / Android Studio.

$ProjectRoot = "G:\AI\E-zzio"
$UiRoot = Join-Path $ProjectRoot "ezzio-ui"
$LogRoot = Join-Path $ProjectRoot ("logs\apk_build_cpu_" + (Get-Date -Format "yyyyMMdd_HHmmss"))

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

# GPU OFF
$env:CUDA_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"

# RAM contrôlée pour Java/Gradle
$env:GRADLE_OPTS = "-Xmx4096m -Dorg.gradle.jvmargs=-Xmx4096m -Dfile.encoding=UTF-8"
$env:JAVA_TOOL_OPTIONS = "-Xmx4096m"

if (-not (Test-Path -LiteralPath (Join-Path $UiRoot "package.json"))) {
    throw "package.json introuvable dans $UiRoot"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm introuvable."
}

Set-Location -LiteralPath $UiRoot

npm install | Tee-Object -FilePath (Join-Path $LogRoot "npm_install.log")
npm run build | Tee-Object -FilePath (Join-Path $LogRoot "npm_build.log")

if (-not (Test-Path -LiteralPath "android")) {
    npx cap add android | Tee-Object -FilePath (Join-Path $LogRoot "cap_add_android.log")
}

npx cap sync android | Tee-Object -FilePath (Join-Path $LogRoot "cap_sync_android.log")

if (-not $env:ANDROID_HOME -and -not $env:ANDROID_SDK_ROOT) {
    throw "Android SDK absent. Installe Android Studio ou configure ANDROID_HOME / ANDROID_SDK_ROOT."
}

Set-Location -LiteralPath (Join-Path $UiRoot "android")

.\gradlew.bat assembleDebug --no-daemon --max-workers=4 |
    Tee-Object -FilePath (Join-Path $LogRoot "gradle_assembleDebug.log")

$Apks = Get-ChildItem -LiteralPath (Join-Path $UiRoot "android\app\build\outputs\apk") -Filter "*.apk" -Recurse -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✅ Build APK CPU/RAM terminé." -ForegroundColor Green
Write-Host "Logs : $LogRoot"
$Apks | Select-Object FullName, Length, LastWriteTime
