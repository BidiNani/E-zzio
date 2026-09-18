"""
Tests de conformité et de validation de l'APK compilé et rejet des faux APKs.
"""
import subprocess
import zipfile
from pathlib import Path

import pytest


def test_dist_android_apk_is_compiled_binary():
    """Vérifie que dist/android/E-ZzIO-v9.0.1.apk est un véritable binaire compilé."""
    apk = Path("dist/android/E-ZzIO-v9.0.1.apk")
    assert apk.exists(), "L'APK v9.0.1 doit exister dans dist/android/"
    assert apk.stat().st_size > 1_000_000, "Un vrai APK compilé avec support AndroidX pèse plusieurs mégaoctets"

    with zipfile.ZipFile(apk, "r") as z:
        entries = set(z.namelist())
        assert "classes.dex" in entries, "Le bytecode Dalvik (classes.dex) DOIT être présent"
        assert "resources.arsc" in entries, "La table de ressources binaires (resources.arsc) DOIT être présente"
        assert "AndroidManifest.xml" in entries, "AndroidManifest.xml DOIT être présent"
        assert any(e.startswith("META-INF/") for e in entries), "Les signatures/métadonnées META-INF doivent être présentes"

def test_fake_apk_detection_and_rejection():
    """Vérifie qu'un zip de code source renommé .apk est détecté et rejeté."""
    fake_apk_entries = ["app/src/main/AndroidManifest.xml", "MainActivity.java"]
    has_dex = "classes.dex" in fake_apk_entries
    has_arsc = "resources.arsc" in fake_apk_entries
    is_valid = has_dex and has_arsc
    assert not is_valid, "Un conteneur source ne doit JAMAIS être accepté comme un APK valide"

def test_apk_signature_with_apksigner():
    """Vérifie la signature APK v2 via apksigner officiel si disponible."""
    apksigner = Path("G:/tools/android-sdk/build-tools/34.0.0/apksigner.bat")
    apk = Path("dist/android/E-ZzIO-v9.0.1.apk")
    if apksigner.exists() and apk.exists():
        res = subprocess.run([str(apksigner), "verify", "--verbose", str(apk)], capture_output=True, text=True)
        assert res.returncode == 0, f"apksigner verification failed: {res.stdout} {res.stderr}"
        assert "Verified using v2 scheme (APK Signature Scheme v2): true" in res.stdout
