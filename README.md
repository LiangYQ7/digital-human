# 景区导览服务 AI 数字人

> 第十五届中国软件杯大赛 · A 组 · A5 赛题「景区导览服务 AI 数字人」参赛项目

## 项目简介

基于 AI 数字人技术构建的智能景区导览系统，为游客提供多模态实时交互（语音/文本/口型同步），为景区管理方提供知识库管理、形象管理、游客感受度报告与数据大屏。

## 技术栈

| 层级 | 技术 |
|------|------|
| 渲染层 | [LiveTalking](https://github.com/lipku/LiveTalking) + MuseTalk（2D 图片驱动口型同步）|
| 大脑层 | [Fay](https://github.com/xszyou/Fay) + Qwen-VL 多模态大模型 + Chroma 向量库 |
| 管理后台 | FastAPI（后端）+ Vue3 + Element Plus + ECharts（前端）|
| 部署 | Docker Compose |

## 目录结构

```
digital_human/
├── third_party/        # 开源依赖（LiveTalking / Fay）
├── brain/              # 大脑层业务代码（基于 Fay 扩展）
├── render/             # 渲染层定制（数字人形象）
├── admin/              # 管理后台（backend + frontend）
├── frontend/           # 游客交互端（基于 LiveTalking web 扩展）
├── docs/               # 文档（含 superpowers 规划与部署手册）
└── scripts/            # 运维脚本
```

## 启动指引

> 完整部署见 `docs/部署手册.md`（开发中）

```bash
# 0. 拉取第三方依赖（Fay + LiveTalking，不入主 git 仓库）
mkdir -p third_party && cd third_party
git clone --depth 1 https://github.com/lipku/LiveTalking.git
git clone --depth 1 https://github.com/xszyou/Fay.git
cd ..

# 1. 复制环境配置并填入 API Key
cp .env.example .env

# 2. （开发模式）分别启动各服务
docker-compose up -d        # 或用 scripts/start_all.ps1
```

- 游客交互端：http://localhost:8010
- 管理后台：http://localhost:5173

## 开发进度

按 superpowers 方法论推进，当前进度见 `docs/superpowers/plans/`。
