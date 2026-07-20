"""CosyVoice TTS 克隆服务。监听 8091 端口。
环境变量 DASHSCOPE_API_KEY 可切换为云端合成（快，~1-2s），否则走本地 CPU 推理（慢，~15-30s）。
"""
import os, re, sys, json, tempfile, uuid, shutil, base64
from pathlib import Path
from dotenv import load_dotenv
# 加载项目根目录 .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)
from fastapi import FastAPI, UploadFile, File, Form, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uvicorn

class TTSReq(BaseModel):
    text: str
    voice: str = "__default__"

# 云端合成开关：配了 DASHSCOPE_API_KEY 就走云端（快），否则本地 CPU（慢）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
_CLOUD_AVAILABLE = bool(DASHSCOPE_API_KEY)
if _CLOUD_AVAILABLE:
    print(f"[CosyVoice] 云端合成已启用 (API Key: ...{DASHSCOPE_API_KEY[-4:]})", flush=True)
else:
    print("[CosyVoice] 云端合成未配置（设置 DASHSCOPE_API_KEY 环境变量可加速）", flush=True)

COSY_DIR = Path(r"D:\Code\Vs code\digital_human\third_party\CosyVoice")
sys.path = [p for p in sys.path if 'matcha' not in p.lower()]
sys.path.insert(0, str(COSY_DIR))
sys.path.insert(0, str(COSY_DIR / "third_party" / "Matcha-TTS"))
import site; site.ENABLE_USER_SITE = False

from cosyvoice.cli.cosyvoice import CosyVoice

MODEL_PATH = r"D:\CosyVoice_models\models\iic--CosyVoice-300M\snapshots\master"
CLONE_DIR = Path(__file__).resolve().parent / "_clones"
CLONE_DIR.mkdir(exist_ok=True)

app = FastAPI(title="CosyVoice TTS")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
model: CosyVoice = None

# 云端音色 ID 缓存
_cloud_voice_ids: dict[str, str] = {}


async def _register_cloud_voice(voice: str) -> str | None:
    """注册 clone 音色到 DashScope，返回 voice_id。"""
    if voice in _cloud_voice_ids:
        return _cloud_voice_ids[voice]
    cd = CLONE_DIR / voice
    if not (cd / "ref.wav").exists():
        return None
    ref_b64 = base64.b64encode((cd / "ref.wav").read_bytes()).decode()
    ref_txt = (cd / "ref_text.txt").read_text(encoding="utf-8") if (cd / "ref_text.txt").exists() else ""
    payload = {
        "model": "voice-enrollment",
        "input": {
            "action": "create_voice",
            "target_model": "cosyvoice-v3.5-flash",
            "prefix": re.sub(r'[^a-zA-Z0-9]', '', voice)[:10],
            "url": f"data:audio/wav;base64,{ref_b64}",
        },
    }
    if ref_txt:
        payload["input"]["reference_text"] = ref_txt
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(
                "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization",
                headers={"Authorization": f"Bearer {DASHSCOPE_API_KEY}"},
                json=payload,
            )
            if r.status_code == 200:
                vid = r.json().get("output", {}).get("voice_id")
                if vid:
                    _cloud_voice_ids[voice] = vid
                    print(f"[CLOUD-TTS] 注册音色 {voice} → {vid}", flush=True)
                    return vid
            print(f"[CLOUD-TTS] 注册 {voice}: {r.status_code} {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"[CLOUD-TTS] 注册 {voice} 异常: {e}", flush=True)
    return None


async def _cloud_tts(text: str, voice: str) -> bytes | None:
    """通过 DashScope SpeechSynthesizer API 合成语音，返回 WAV 数据。"""
    voice_id = voice
    cd = CLONE_DIR / voice
    if (cd / "ref.wav").exists():
        vid = await _register_cloud_voice(voice)
        if vid:
            voice_id = vid
        else:
            print(f"[CLOUD-TTS] {voice}: 注册失败，回退本地", flush=True)
            return None

    payload = {
        "model": "cosyvoice-v3.5-flash",
        "input": {
            "text": text,
            "voice": voice_id,
            "format": "wav",
            "sample_rate": 24000,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(
                "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer",
                headers={"Authorization": f"Bearer {DASHSCOPE_API_KEY}"},
                json=payload,
            )
            if r.status_code == 200:
                data = r.json()
                audio_url = data.get("output", {}).get("audio", {}).get("url", "")
                if audio_url:
                    r2 = await c.get(audio_url, timeout=30.0)
                    if r2.status_code == 200:
                        print(f"[CLOUD-TTS] {voice}: 成功 ({len(r2.content)} bytes)", flush=True)
                        return r2.content
                print(f"[CLOUD-TTS] {voice}: 无音频URL — {r.text[:200]}", flush=True)
            else:
                print(f"[CLOUD-TTS] {voice}: {r.status_code} {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"[CLOUD-TTS] {voice}: 请求异常 {e}", flush=True)
    return None

def get_model():
    global model
    if model is None:
        print("[CosyVoice] 加载模型中...", flush=True)
        model = CosyVoice(str(MODEL_PATH))
        print("[CosyVoice] 加载完成", flush=True)
    return model

@app.get("/")
def root():
    return {"service": "CosyVoice TTS", "model": "CosyVoice-300M"}

@app.get("/v1/audio/voices")
@app.get("/voice/list")
def list_voices():
    uploaded = []
    if CLONE_DIR.exists():
        for d in CLONE_DIR.iterdir():
            if not d.is_dir() or not list(d.glob("*.wav")):
                continue
            ref = (d / "ref_text.txt").read_text(encoding="utf-8").strip() if (d / "ref_text.txt").exists() else ""
            desc = (d / "description.txt").read_text(encoding="utf-8").strip() if (d / "description.txt").exists() else ""
            uploaded.append({"name": d.name, "ref_text": ref, "speaker_description": desc})
    return {"voices": [], "uploaded_voices": uploaded}

@app.post("/v1/audio/voices")
async def clone_voice_lt(audio_sample: UploadFile = File(...), name: str = Form(""), ref_text: str = Form(""), consent: str = Form(""), speaker_description: str = Form("")):
    """兼容 LiveTalking TTS 页面的上传克隆接口。"""
    return await _do_clone(audio_sample, ref_text, name, speaker_description)


@app.delete("/v1/audio/voices/{name}")
@app.delete("/voice/{name}")
def delete_voice(name: str):
    """删除克隆音色。"""
    import shutil
    d = CLONE_DIR / name
    if d.exists() and d.is_dir():
        shutil.rmtree(d)
        return {"status": "ok", "message": f"音色 {name} 已删除"}
    return {"status": "error", "message": f"音色 {name} 未找到"}


@app.post("/voice/clone")
async def clone_voice(file: UploadFile = File(...), ref_text: str = Form(""), name: str = Form("")):
    return await _do_clone(file, ref_text, name)

async def _do_clone(f: UploadFile, ref_text: str, name: str, description: str = ""):
    clone_id = name or f"voice_{uuid.uuid4().hex[:8]}"
    d = CLONE_DIR / clone_id; d.mkdir(parents=True, exist_ok=True)
    (d / "ref.wav").write_bytes(await f.read())
    (d / "ref_text.txt").write_text(ref_text, encoding="utf-8")
    if description:
        (d / "description.txt").write_text(description, encoding="utf-8")
    return {"status": "ok", "name": clone_id}

@app.post("/v1/audio/speech")
async def speech_api(req: dict = Body(...)):
    """兼容 LiveTalking TTS 页面的语音合成接口。"""
    voice = req.get("voice", "__default__")
    text = req.get("input", "")
    if not text:
        return {"status": "error", "message": "text is required"}

    # 云端合成（快）
    if _CLOUD_AVAILABLE:
        audio = await _cloud_tts(text, voice)
        if audio:
            return Response(content=audio, media_type="audio/wav",
                            headers={"Content-Disposition": "attachment; filename=tts.wav"})
        print("[WARN] 云端合成失败，回退本地推理", flush=True)

    # 本地 CPU 推理（慢）
    m = get_model()
    cd = CLONE_DIR / voice
    if (cd / "ref.wav").exists():
        ref_txt = (cd / "ref_text.txt").read_text(encoding="utf-8") if (cd / "ref_text.txt").exists() else ""
        gen = m.inference_zero_shot(text, ref_txt, str(cd / "ref.wav"))
    else:
        gen = m.inference_sft(text, spk_id=voice)

    import soundfile as sf
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        for r in gen:
            sf.write(tmp.name, r['tts_speech'].cpu().numpy().flatten(), 22050)
            break
        with open(tmp.name, "rb") as f:
            return Response(content=f.read(), media_type="audio/wav",
                            headers={"Content-Disposition": "attachment; filename=tts.wav"})
    finally:
        try: os.unlink(tmp.name)
        except: pass

@app.post("/tts")
async def synthesize(req: TTSReq):
    # 云端合成
    if _CLOUD_AVAILABLE:
        audio = await _cloud_tts(req.text, req.voice)
        if audio:
            return Response(content=audio, media_type="audio/wav",
                            headers={"Content-Disposition": "attachment; filename=tts.wav"})

    m = get_model()
    if req.voice == "__default__":
        gen = m.inference_sft(req.text, spk_id="中文女")
    else:
        cd = CLONE_DIR / req.voice
        if not (cd / "ref.wav").exists():
            return {"status": "error", "message": f"音色 {req.voice} 未找到"}
        ref_txt = (cd / "ref_text.txt").read_text(encoding="utf-8") if (cd / "ref_text.txt").exists() else ""
        gen = m.inference_zero_shot(req.text, ref_txt, str(cd / "ref.wav"))

    import soundfile as sf
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        for r in gen:
            sf.write(tmp.name, r['tts_speech'].cpu().numpy().flatten(), 22050)
            break
        with open(tmp.name, "rb") as f:
            return Response(content=f.read(), media_type="audio/wav",
                            headers={"Content-Disposition": "attachment; filename=tts.wav"})
    finally:
        try: os.unlink(tmp.name)
        except: pass

if __name__ == "__main__":
    get_model()
    uvicorn.run(app, host="0.0.0.0", port=8091)
