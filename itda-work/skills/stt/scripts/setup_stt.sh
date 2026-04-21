#!/bin/bash
echo "=== STT Environment Setup ==="

echo "[1/2] Installing faster-whisper..."
pip3 install faster-whisper --break-system-packages -q 2>/dev/null || pip3 install faster-whisper -q
python3 -c "from faster_whisper import WhisperModel; print('  faster-whisper OK')"

echo "[2/2] Verifying CPU mode..."
python3 -c "
from faster_whisper import WhisperModel
m = WhisperModel('tiny', device='cpu', compute_type='int8')
print('  CPU mode OK (model: tiny)')
" 2>/dev/null && echo "  Verification passed" || echo "  WARN: Verification failed (model may download on first use)"

echo ""
echo "=== Setup Complete ==="
echo "  Usage: from faster_whisper import WhisperModel"
echo "  Model: WhisperModel('base', device='cpu', compute_type='int8')"
