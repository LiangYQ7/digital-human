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


# ── Whisper 模型常驻内存（ponytail: 每次请求加载 → 启动时加载一次）──
import whisper as _whisper
import threading as _threading
import soundfile as sf
import numpy as np
from scipy import signal

_whisper_model = None
_whisper_lock = _threading.Lock()

# 景区领域词汇（注入 Whisper decoder 做语言模型偏置）
_DOMAIN_PROMPT = (
    "灵山胜境景区智能导览。"
    "灵山大佛 梵宫 拈花湾 五印坛城 九龙灌浴 天下第一掌 "
    "曼飞龙塔 阿育王柱 百子戏弥勒 灵山博物馆 灵山花海 "
    "门票价格 开放时间 占地面积 历史背景 游览路线 交通指南 "
    "半日游 一日游 景点介绍 怎么去 好玩吗 有多高 几点开始"
)

# 领域术语纠错映射（同音/近音词 → 正确术语）
# ponytail: 小映射表兜底，不引入重纠错模型
_ASR_CORRECTIONS: list[tuple[str, list[str]]] = [
    # 景区名称
    ("灵山胜境", ["灵山圣境", "林山胜境", "迎山盛进", "迎山圣境", "灵山胜景", "灵山盛境", "凌山胜境", "铃山胜境"]),
    ("灵山大佛", ["林山大佛", "凌山大佛"]),
    ("拈花湾",   ["年花湾", "莲花湾", "拈花弯", "年花弯"]),
    ("梵宫",     ["凡宫", "繁宫"]),
    ("五印坛城", ["五英坛城", "无印坛城"]),
    ("九龙灌浴", ["九龙冠玉", "九龙关玉"]),
    ("天下第一掌", ["天下第一张"]),
    ("曼飞龙塔", ["满飞龙塔", "慢飞龙塔"]),
    ("阿育王柱", ["阿玉王柱", "啊育王柱"]),
    ("百子戏弥勒", ["百子西弥勒"]),
    ("灵山博物馆", ["林山博物馆"]),
    ("灵山花海", ["林山花海"]),
    # 常见术语
    ("景区",     ["警区", "景气"]),
    ("占地面积", ["战地面积", "占地棉机", "战地棉机"]),
    ("门票",     ["门漂", "门飘"]),
    ("游览",     ["有览", "游缆"]),
    ("开放时间", ["开房时间"]),
    ("导览",     ["岛览", "倒览"]),
    ("历史",     ["利史", "力士"]),
    ("建筑",     ["建住", "见筑"]),
    ("佛教",     ["佛脚", "佛交"]),
    ("佛像",     ["佛相", "佛象"]),
]

# 展开为 {错别: 正确} 查找表
_ASR_CORRECTION_MAP: dict[str, str] = {}
for _correct, _wrongs in _ASR_CORRECTIONS:
    for _w in _wrongs:
        _ASR_CORRECTION_MAP[_w] = _correct


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        print("[ASR] 加载 whisper-base 模型...", flush=True)
        _whisper_model = _whisper.load_model("base")
        print("[ASR] 模型就绪", flush=True)
    return _whisper_model


def _correct_asr(text: str) -> str:
    """用领域术语表纠正 ASR 同音错别字。"""
    for wrong, correct in _ASR_CORRECTION_MAP.items():
        if wrong in text:
            text = text.replace(wrong, correct)
    return text


@app.post("/asr")
async def speech_to_text(file: UploadFile = File(...)):
    """语音转文字。支持 WAV/MP3 等常见格式。"""
    ext = (file.filename or "wav").split(".")[-1]
    tmp = tempfile.NamedTemporaryFile(suffix="." + ext, delete=False)
    try:
        tmp.write(await file.read())
        tmp.close()

        audio, sr = sf.read(tmp.name, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != 16000:
            target_len = int(len(audio) * 16000 / sr)
            audio = signal.resample(audio, target_len)
        peak = abs(audio).max()
        if peak > 0:
            audio = audio / peak * 0.95

        model = _get_whisper()
        with _whisper_lock:
            result = model.transcribe(
                audio, language="zh", fp16=False,
                initial_prompt=_DOMAIN_PROMPT,
                temperature=0,
            )
        text = result["text"].strip()
        try:
            import zhconv
            text = zhconv.convert(text, 'zh-cn')
        except Exception: pass
        text = _correct_asr(text)
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
import httpx, json as _json, asyncio

LT_BASE = "http://127.0.0.1:8010"
COSY_BASE = "http://127.0.0.1:8091"
DEFAULT_EDGE_VOICE = "zh-CN-XiaoxiaoNeural"  # cosyvoice:* refaudio 统一替换为此


async def _cosyvoice_speak_bg(clone: str, sid: str, text: str):
    """后台异步：CosyVoice 合成 → /humanaudio 推送。"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as _c:
            r = await _c.post(f"{COSY_BASE}/v1/audio/speech",
                              json={"input": text, "voice": clone})
            if r.status_code != 200:
                print(f"[COSY-BG] TTS failed ({clone}): {r.status_code}", flush=True)
                return
            files = {"file": ("tts.wav", r.content, "audio/wav")}
            r2 = await _c.post(f"{LT_BASE}/humanaudio",
                               data={"sessionid": sid}, files=files)
            print(f"[COSY-BG] {clone} → /humanaudio: {r2.status_code}", flush=True)
    except Exception as e:
        print(f"[COSY-BG] ERROR {clone}: {e}", flush=True)


def _strip_cosyvoice_refaudio(body: bytes) -> bytes:
    """把 body 中 refaudio 的 cosyvoice:* 替换为默认 edge-tts 音色。"""
    try:
        data = _json.loads(body)
        ra = data.get("refaudio", "")
        if isinstance(ra, str) and ra.startswith("cosyvoice:"):
            data["refaudio"] = DEFAULT_EDGE_VOICE
            return _json.dumps(data).encode("utf-8")
    except Exception:
        pass
    return body


def _inject_active_avatar(body: bytes) -> bytes:
    """从 brain/config/active_avatar.json 读取 avatar_id，
    注入到 /offer 请求体中（如果请求没有显式传 avatar）。"""
    try:
        data = _json.loads(body)
        if not data.get("avatar"):
            cfg_path = os.path.join(
                os.path.dirname(__file__), "config", "active_avatar.json"
            )
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = _json.load(f)
                aid = cfg.get("avatar_id", "")
                if aid:
                    data["avatar"] = aid
                    return _json.dumps(data).encode("utf-8")
    except Exception:
        pass
    return body


@app.api_route("/lt/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def proxy_lt(request: Request, path: str):
    body = await request.body()

    # ── /offer：防止 cosyvoice:* 进入 LiveTalking session 的 REF_FILE ──
    if path == "offer" and request.method == "POST":
        body = _strip_cosyvoice_refaudio(body)
        # 注入 active_avatar.json 中的 avatar_id，让用户端也跟随切换
        body = _inject_active_avatar(body)

    # ── /human：cosyvoice 音色走后台异步 CosyVoice → /humanaudio ──
    if path == "human" and request.method == "POST":
        try:
            data = _json.loads(body)
            ref = data.get("tts", {}).get("ref_file", "")
            if ref.startswith("cosyvoice:"):
                clone = ref.replace("cosyvoice:", "")
                sid = data.get("sessionid", "")
                text = data.get("text", "")
                asyncio.create_task(_cosyvoice_speak_bg(clone, sid, text))
                print(f"[PROXY-COSY] {clone} enqueued (bg)", flush=True)
                return Response(content='{"code":0,"message":"ok"}', status_code=200)
        except Exception as e:
            print(f"[PROXY-COSY] ERROR: {e}", flush=True)
            # fall through to normal proxy

    url = f"{LT_BASE}/{path}"
    qs = str(request.url.query)
    if qs: url += "?" + qs
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    async with httpx.AsyncClient(timeout=30.0) as c:
        try:
            r = await c.request(request.method, url, headers=headers, content=body or None)
            print(f"[PROXY] {request.method} {url} → {r.status_code}", flush=True)
            return Response(content=r.content, status_code=r.status_code, headers=dict(r.headers))
        except Exception as e:
            print(f"[PROXY] ERROR {request.method} {url}: {e}", flush=True)
            return Response(content=str(e), status_code=502)


# ── TTS 代理（解决跨域问题）──
TTS_BASE = "http://127.0.0.1:8091"


@app.api_route("/tts/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def proxy_tts(request: Request, path: str):
    url = f"{TTS_BASE}/{path}"
    qs = str(request.url.query)
    if qs:
        url += "?" + qs
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    async with httpx.AsyncClient(timeout=120.0) as c:
        try:
            r = await c.request(request.method, url, headers=headers, content=body or None)
            print(f"[PROXY-TTS] {request.method} {url} → {r.status_code}", flush=True)
            return Response(content=r.content, status_code=r.status_code, headers=dict(r.headers))
        except Exception as e:
            print(f"[PROXY-TTS] ERROR {request.method} {url}: {e}", flush=True)
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
