"""
Tests unitaires et de conformité pour le projet Android natif d'E-ZzIO.
"""
from pathlib import Path
import re
import pytest

def test_android_project_files_integrity():
    """Vérifie la présence de tous les fichiers du sous-projet Android."""
    root = Path("android")
    assert (root / "build.gradle").exists(), "root build.gradle manquant"
    assert (root / "settings.gradle").exists(), "settings.gradle manquant"
    assert (root / "gradle.properties").exists(), "gradle.properties manquant"
    assert (root / "gradlew.bat").exists(), "gradlew.bat manquant"
    assert (root / "gradle/wrapper/gradle-wrapper.jar").exists(), "gradle-wrapper.jar manquant"
    assert (root / "app/build.gradle").exists(), "app/build.gradle manquant"
    assert (root / "app/src/main/AndroidManifest.xml").exists(), "AndroidManifest.xml manquant"
    assert (root / "app/src/main/java/ai/ezzio/office/MainActivity.java").exists(), "MainActivity.java manquant"
    assert (root / "app/src/main/res/layout/activity_main.xml").exists(), "activity_main.xml manquant"

def test_android_gradle_configuration():
    """Vérifie que la configuration Gradle spécifie les SDKs cibles et AndroidX."""
    gradle_props = Path("android/gradle.properties").read_text(encoding="utf-8")
    assert "android.useAndroidX=true" in gradle_props

    app_gradle = Path("android/app/build.gradle").read_text(encoding="utf-8")
    assert "compileSdk 34" in app_gradle
    assert "minSdk 26" in app_gradle
    assert "targetSdk 34" in app_gradle
    assert 'versionName "9.0.1"' in app_gradle
    assert "versionCode 901" in app_gradle
    assert "JavaVersion.VERSION_17" in app_gradle

def test_android_security_no_hardcoded_secrets():
    """Vérifie l'absence absolue de clés API ou tokens secrets dans le projet Android."""
    forbidden = [
        re.compile(r"AIza[0-9A-Za-z-_]{35}"),
        re.compile(r"gsk_[0-9A-Za-z]{40,}"),
        re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*"),
        re.compile(r"-----BEGIN (RSA )?PRIVATE KEY-----")
    ]
    android_dir = Path("android")
    for f in android_dir.rglob("*"):
        if f.is_file() and not any(part in f.parts for part in ["build", ".gradle"]):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                for pattern in forbidden:
                    assert not pattern.search(content), f"Secret trouvé dans {f}"
            except Exception:
                pass
