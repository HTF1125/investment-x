"""Text-to-Speech endpoint using Microsoft Edge TTS (free, neural voices)."""

import asyncio
import io
import re
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ix.api.rate_limit import limiter as _limiter
from pydantic import BaseModel
import edge_tts

router = APIRouter(prefix="/tts", tags=["tts"])

# Neural voices — high quality, natural sounding
VOICES = {
    "en": "en-US-GuyNeural",         # Male, professional newsreader tone
    "en-f": "en-US-AriaNeural",       # Female alternative
    "kr": "ko-KR-InJoonNeural",       # Male Korean
    "kr-f": "ko-KR-SunHiNeural",      # Female Korean
    "cn": "zh-CN-YunxiNeural",        # Male Chinese
    "cn-f": "zh-CN-XiaoxiaoNeural",   # Female Chinese
    "jp": "ja-JP-KeitaNeural",        # Male Japanese
    "jp-f": "ja-JP-NanamiNeural",     # Female Japanese
}

RATE_MAP = {
    "en": "+15%",
    "kr": "+10%",
    "cn": "+10%",
    "jp": "+10%",
}


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting for cleaner speech."""
    # Remove bold markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Remove table rows (pipes)
    text = re.sub(r'\|[^\n]+\|', '', text)
    # Remove table separator rows
    text = re.sub(r'\|[-:\s|]+\|', '', text)
    # Remove markdown headers
    text = re.sub(r'^#{1,4}\s+', '', text, flags=re.MULTILINE)
    # Remove list bullets
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)
    # Clean up multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    return text.strip()


class TTSRequest(BaseModel):
    text: str
    lang: str = "en"
    voice: str | None = None  # Override voice if desired


@router.post("/speak")
@_limiter.limit("5/minute")
async def speak(req: TTSRequest, request: Request):
    """Generate speech audio from text using Edge TTS neural voices.

    Returns audio/mpeg stream. Accepts text up to 5000 chars.
    """
    if len(req.text) > 50000:
        raise HTTPException(400, "Text too long (max 50000 chars)")

    # Select voice
    voice = req.voice or VOICES.get(req.lang, VOICES["en"])
    rate = RATE_MAP.get(req.lang, "+0%")

    # Clean markdown
    clean_text = _strip_markdown(req.text)
    if not clean_text:
        raise HTTPException(400, "No speakable text after cleaning")

    try:
        communicate = edge_tts.Communicate(clean_text, voice, rate=rate)

        async def audio_stream():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        return StreamingResponse(
            audio_stream(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "public, max-age=3600",
            },
        )
    except Exception as e:
        raise HTTPException(500, f"TTS generation failed: {str(e)}")


@router.get("/voices")
@_limiter.limit("30/minute")
async def list_voices(request: Request):
    """List available neural voices."""
    return {
        "voices": VOICES,
        "default": {lang: v for lang, v in VOICES.items() if "-f" not in lang},
    }
