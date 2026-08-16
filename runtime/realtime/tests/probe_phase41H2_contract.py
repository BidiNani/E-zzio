import json
from pathlib import Path
import onnxruntime as ort

model = Path(r"G:\AI\E-zzio\runtime\realtime\models\vad\silero_vad.onnx")
report = Path(r"G:\AI\E-zzio\runtime\realtime\tests\reports\phase41H2_contract_probe.json")

session = ort.InferenceSession(
    str(model),
    providers=["CPUExecutionProvider"],
)

payload = {
    "model": str(model),
    "providers": session.get_providers(),
    "inputs": [
        {
            "name": x.name,
            "type": x.type,
            "shape": [str(v) for v in x.shape],
        }
        for x in session.get_inputs()
    ],
    "outputs": [
        {
            "name": x.name,
            "type": x.type,
            "shape": [str(v) for v in x.shape],
        }
        for x in session.get_outputs()
    ],
}

required = {"input", "state", "sr"}
actual = {
    x.name
    for x in session.get_inputs()
}

missing = required - actual

if missing:
    raise RuntimeError(
        f"ONNX contract invalid. Missing={sorted(missing)}"
    )

sr = next(
    x for x in session.get_inputs()
    if x.name == "sr"
)

if sr.type != "tensor(int64)":
    raise RuntimeError(
        f"SR type invalid: {sr.type}"
    )

report.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with open(
    report,
    "w",
    encoding="utf-8",
) as fh:
    json.dump(
        payload,
        fh,
        indent=2,
    )

print("[CONTRACT_OK]")
print(json.dumps(payload, indent=2))