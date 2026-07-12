"""景区导览数字人 — Brain 层 HTTP 服务。

文本输入、语音输入（ASR）、形象管理。
"""
import os
import sys
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, HTMLResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).parent.parent / ".env")

import dashscope
from brain.pipeline import handle_user_input

app = FastAPI(title="Scenic Digital Human Brain")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "")


class AskRequest(BaseModel):
    text: str
    sessionid: str = ""
    image_path: str | None = None


class AskResponse(BaseModel):
    reply: str
    delivered: bool
    latency_sec: float
    intent: str


class VoiceRequest(BaseModel):
    voice: str
    name: str = ""


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    result = handle_user_input(text=req.text, image_path=req.image_path, sessionid=req.sessionid)
    return AskResponse(**result)


@app.post("/asr")
async def speech_to_text(file: UploadFile = File(...)):
    """语音转文字。"""
    import whisper
    import soundfile as sf
    import numpy as np
    tmp = tempfile.NamedTemporaryFile(suffix="." + (file.filename or "wav").split(".")[-1], delete=False)
    try:
        tmp.write(await file.read())
        tmp.close()
        audio, sr = sf.read(tmp.name, dtype="float32")
        if audio.ndim > 1: audio = audio.mean(axis=1)
        peak = abs(audio).max()
        if peak > 0: audio = audio / peak * 0.95
        model = whisper.load_model("base")
        result = model.transcribe(audio, language="zh", fp16=False)
        text = result["text"].strip()
        try:
            import zhconv
            text = zhconv.convert(text, 'zh-cn')
        except Exception: pass
        print(f"[ASR] {len(audio)/sr:.0f}s → {text[:120]}", flush=True)
        return {"text": text, "status": "ok"}
    except Exception as e:
        return {"text": "", "status": "error", "message": str(e)}
    finally:
        try: os.unlink(tmp.name)
        except Exception: pass


@app.post("/avatar/voice")
def set_voice(req: VoiceRequest):
    from brain.adapter.livetalking_bridge import update_voice
    update_voice(req.voice, req.name)
    return {"status": "ok", "voice": req.voice, "name": req.name or "小灵"}


@app.get("/avatar/active")
def get_active():
    from brain.adapter.livetalking_bridge import get_active_config
    return get_active_config()


@app.get("/health")
def health():
    return {"status": "ok"}


# ── LiveTalking 代理 ──
import httpx

LT_BASE = "http://127.0.0.1:8010"

@app.api_route("/lt/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def proxy_lt(request: Request, path: str):
    url = f"{LT_BASE}/{path}"
    qs = str(request.url.query)
    if qs: url += "?" + qs
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    async with httpx.AsyncClient(timeout=30.0) as c:
        try:
            r = await c.request(request.method, url, headers=headers, content=body or None)
            print(f"[PROXY] {request.method} {url} → {r.status_code}", flush=True)
            return Response(content=r.content, status_code=r.status_code, headers=dict(r.headers))
        except Exception as e:
            print(f"[PROXY] ERROR {request.method} {url}: {e}", flush=True)
            return Response(content=str(e), status_code=502)


# ── 管理后台路由 ──
sys.path.insert(0, str(Path(__file__).parent.parent / "admin" / "backend"))
from app.routers import avatar as admin_avatar, dashboard, knowledge, report  # noqa: E402
app.include_router(admin_avatar.router)
app.include_router(dashboard.router)
app.include_router(knowledge.router)
app.include_router(report.router)

# ── 页面路由 ──
FRONTEND = Path(__file__).parent.parent / "frontend"

@app.get("/", response_class=HTMLResponse)
def landing():
    return HTMLResponse((FRONTEND / "index.html").read_text(encoding="utf-8"))

@app.get("/tourist", response_class=HTMLResponse)
def tourist():
    return HTMLResponse((FRONTEND / "tourist.html").read_text(encoding="utf-8"))

@app.get("/guide2", response_class=HTMLResponse)
def guide2():
    return HTMLResponse((FRONTEND / "guide.html").read_text(encoding="utf-8"))

@app.get("/test_webrtc", response_class=HTMLResponse)
def test_webrtc():
    return HTMLResponse((FRONTEND / "webrtc_test.html").read_text(encoding="utf-8"))

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return HTMLResponse((Path(__file__).parent.parent / "admin" / "frontend" / "index.html").read_text(encoding="utf-8"))

# ── 图片 ──
@app.get("/scenic_{n}.webp")
def scenic_img(n: int):
    return FileResponse(str(FRONTEND / f"scenic_{n}.webp"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("FAY_PORT", "8011"))
    uvicorn.run(app, host="0.0.0.0", port=port)
