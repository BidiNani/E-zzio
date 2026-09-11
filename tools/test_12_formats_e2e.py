"""
E-ZZIO Ingestion Universelle — Test End-to-End Réel sur les 12 Formats Cibles.
Exécute chaque cas contre l'endpoint /perception/perceive ou UnifiedPerception.
"""
import io
import os
import zipfile
import wave
import struct
import json
import time
import sys
from pathlib import Path
import httpx
from PIL import Image, ImageDraw

root = Path("G:/AI/E-zzio")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
fixtures_dir = root / "runtime/test_tmp/e2e_ingestion_fixtures"
fixtures_dir.mkdir(parents=True, exist_ok=True)

results = {}
client = httpx.Client(base_url="http://127.0.0.1:8001", timeout=15.0)

# ==============================================================================
# 1. PDF TEXTE
# ==============================================================================
pdf_text_path = fixtures_dir / "sample_text.pdf"
# Génération d'un PDF texte valide avec pypdf/canvas ou structure PDF standard
pdf_content = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    b"4 0 obj << /Length 55 >> stream\n"
    b"BT /F1 12 Tf 72 712 Td (E-ZZIO SOVEREIGN TEST PDF EXTRACTION) Tj ET\n"
    b"endstream endobj\n"
    b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000350 00000 n \n"
    b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n435\n%%EOF\n"
)
pdf_text_path.write_bytes(pdf_content)

try:
    r1 = client.post("/perception/perceive", json={"target": str(pdf_text_path)})
    results["1_pdf_text"] = {
        "status_code": r1.status_code,
        "response": r1.json()
    }
except Exception as e:
    results["1_pdf_text"] = {"error": str(e)}

# ==============================================================================
# 2. PDF SCANNÉ (IMAGE SEULE)
# ==============================================================================
pdf_scanned_path = fixtures_dir / "sample_scanned.pdf"
# PDF minimal sans flux textuel Tj
pdf_scanned_content = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
    b"4 0 obj << /Length 12 >> stream\n"
    b"q Q\n"
    b"endstream endobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000216 00000 n \n"
    b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n279\n%%EOF\n"
)
pdf_scanned_path.write_bytes(pdf_scanned_content)

try:
    r2 = client.post("/perception/perceive", json={"target": str(pdf_scanned_path)})
    results["2_pdf_scanned"] = {
        "status_code": r2.status_code,
        "response": r2.json()
    }
except Exception as e:
    results["2_pdf_scanned"] = {"error": str(e)}

# ==============================================================================
# 3. DOCX (DOCUMENT WORD)
# ==============================================================================
docx_path = fixtures_dir / "sample_doc.docx"
with zipfile.ZipFile(docx_path, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>')
    z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Rapport d\'Ingestion E-ZZIO DOCX</w:t></w:r></w:p></w:body></w:document>')

try:
    r3 = client.post("/perception/perceive", json={"target": str(docx_path)})
    results["3_docx"] = {
        "status_code": r3.status_code,
        "response": r3.json()
    }
except Exception as e:
    results["3_docx"] = {"error": str(e)}

# ==============================================================================
# 4. XLSX (TABLEUR EXCEL)
# ==============================================================================
xlsx_path = fixtures_dir / "sample_table.xlsx"
with zipfile.ZipFile(xlsx_path, "w") as z:
    z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>')
    z.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="2"><si><t>Budget_2026</t></si><si><t>Total_EUR_15000</t></si></sst>')

try:
    r4 = client.post("/perception/perceive", json={"target": str(xlsx_path)})
    results["4_xlsx"] = {
        "status_code": r4.status_code,
        "response": r4.json()
    }
except Exception as e:
    results["4_xlsx"] = {"error": str(e)}

# ==============================================================================
# 5. PPTX (PRÉSENTATION)
# ==============================================================================
pptx_path = fixtures_dir / "sample_slides.pptx"
with zipfile.ZipFile(pptx_path, "w") as z:
    z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>')
    z.writestr("ppt/slides/slide1.xml", '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Architecture Souveraine E-ZZIO V9.0</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>')

try:
    r5 = client.post("/perception/perceive", json={"target": str(pptx_path)})
    results["5_pptx"] = {
        "status_code": r5.status_code,
        "response": r5.json()
    }
except Exception as e:
    results["5_pptx"] = {"error": str(e)}

# ==============================================================================
# 6. ARCHIVE ZIP (MULTI-FICHIERS + PROTECTION ZIP-BOMB)
# ==============================================================================
zip_path = fixtures_dir / "sample_archive.zip"
with zipfile.ZipFile(zip_path, "w") as z:
    z.writestr("note1.txt", "Première note dans l'archive")
    z.writestr("data/subnote.txt", "Deuxième note sous-dossier")

try:
    r6 = client.post("/perception/perceive", json={"target": str(zip_path)})
    results["6_zip_archive"] = {
        "status_code": r6.status_code,
        "response": r6.json()
    }
except Exception as e:
    results["6_zip_archive"] = {"error": str(e)}

# ==============================================================================
# 7. IMAGE SIMPLE (PNG)
# ==============================================================================
img_path = fixtures_dir / "sample_vision.png"
img = Image.new("RGB", (300, 150), color=(30, 40, 60))
d = ImageDraw.Draw(img)
d.text((20, 50), "E-ZZIO VISION TEST", fill=(255, 255, 255))
img.save(img_path)

try:
    r7 = client.post("/perception/perceive", json={"target": str(img_path)})
    results["7_image_simple"] = {
        "status_code": r7.status_code,
        "response": r7.json()
    }
except Exception as e:
    results["7_image_simple"] = {"error": str(e)}

# ==============================================================================
# 8. QR CODE (ENCODAGE / DÉCODAGE VIA QR ENGINE)
# ==============================================================================
qr_path = fixtures_dir / "sample_qr.png"
try:
    from core.perception.qr_engine import QREngine
    qr_engine = QREngine()
    qr_engine.generate_qrcode("https://ezzio.ai/sovereign-auth-key-9988", qr_path)
    r8 = client.post("/perception/perceive", json={"target": str(qr_path)})
    results["8_qr_code"] = {
        "status_code": r8.status_code,
        "response": r8.json()
    }
except Exception as e:
    results["8_qr_code"] = {"error": str(e)}

# ==============================================================================
# 9. AUDIO (WAV)
# ==============================================================================
wav_path = fixtures_dir / "sample_audio.wav"
with wave.open(str(wav_path), "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(struct.pack("<" + "h" * 16000, *([100] * 16000)))

try:
    r9 = client.post("/perception/perceive", json={"target": str(wav_path)})
    results["9_audio_wav"] = {
        "status_code": r9.status_code,
        "response": r9.json()
    }
except Exception as e:
    results["9_audio_wav"] = {"error": str(e)}

# ==============================================================================
# 10. LIEN WEB GÉNÉRIQUE (ARTICLE/DOC VIA SAFE FETCHER)
# ==============================================================================
try:
    # Test d'une URL web statique autorisée (ex: RFC ou doc officielle python)
    r10 = client.post("/perception/perceive", json={"target": "https://httpbin.org/html"})
    results["10_web_generic"] = {
        "status_code": r10.status_code,
        "response": r10.json()
    }
except Exception as e:
    results["10_web_generic"] = {"error": str(e)}

# ==============================================================================
# 11. RÉSEAU SOCIAL / YOUTUBE (EXTRACTION VIA YT-DLP)
# ==============================================================================
try:
    # Test sur une URL YouTube publique
    r11 = client.post("/perception/perceive", json={"target": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    results["11_social_youtube"] = {
        "status_code": r11.status_code,
        "response": r11.json()
    }
except Exception as e:
    results["11_social_youtube"] = {"error": str(e)}

# ==============================================================================
# 12. FORMAT VOLONTAIREMENT NON SUPPORTÉ / EXÉCUTABLE DÉGUISÉ (PE)
# ==============================================================================
pe_fake_path = fixtures_dir / "disguised_file.txt"
# Faux fichier .txt avec magic bytes MZ (exécutable PE)
pe_fake_path.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00Malicious Executable Payload")

try:
    r12 = client.post("/perception/perceive", json={"target": str(pe_fake_path)})
    results["12_unsupported_pe_disguised"] = {
        "status_code": r12.status_code,
        "response": r12.json()
    }
except Exception as e:
    results["12_unsupported_pe_disguised"] = {"error": str(e)}

# Enregistrement des résultats
out_e2e = root / "state/audit/optimization/universal_ingestion_e2e_evidence.json"
out_e2e.parent.mkdir(parents=True, exist_ok=True)
out_e2e.write_text(json.dumps(results, indent=2), encoding="utf-8")
print("E2E INGESTION EVIDENCE SAVED TO:", out_e2e)
print("SUMMARY OF EXECUTED CASES:")
for k, v in results.items():
    code = v.get("status_code", "ERR")
    ok = v.get("response", {}).get("ok") if "response" in v else False
    inp_type = v.get("response", {}).get("input_type") or v.get("response", {}).get("type") or "N/A"
    print(f"  • {k:30} -> HTTP {code} | ok={ok} | type={inp_type}")
