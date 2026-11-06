from pathlib import Path
import hashlib
import urllib.request

root = Path(__file__).resolve().parent
path = root / 'hand_landmarker.task'
url = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
expected = 'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1'
if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
    print('Hand model already present and verified.')
else:
    print('Downloading Google hand landmark model...')
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(20_000_000)
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit('Model checksum mismatch; file not installed.')
    path.write_bytes(data)
    print('Hand model verified and installed.')
