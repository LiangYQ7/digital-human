import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import avatar, dashboard, knowledge, report

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Scenic Admin")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(avatar.router)
app.include_router(dashboard.router)
app.include_router(knowledge.router)
app.include_router(report.router)


# ── LiveTalking 代理 ──
import httpx

LT_BASE = "http://127.0.0.1:8010"


@app.api_route("/lt/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def proxy_lt(request: Request, path: str):
    url = f"{LT_BASE}/{path}"
    qs = str(request.url.query)
    if qs:
        url += "?" + qs
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.request(request.method, url, headers=headers, content=body or None)
    return Response(content=r.content, status_code=r.status_code, headers=dict(r.headers))


@app.get("/api/health")
def health():
    return {"status": "ok"}


frontend = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend.exists():
    app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
