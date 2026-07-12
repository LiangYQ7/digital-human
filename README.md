# 🏔️ 景区导览服务 AI 数字人

> 第十五届中国软件杯大赛 · A 组 · A5 赛题「景区导览服务 AI 数字人」参赛项目

## 📖 项目简介

基于 AI 数字人技术构建的智能景区导览系统，为游客提供多模态实时交互（语音 / 文本 / 口型同步），为景区管理方提供知识库管理、形象管理、游客感受度报告与数据大屏。

---

## 🧰 技术栈

| 层级 | 技术 |
|------|------|
| 渲染层 | [LiveTalking](https://github.com/lipku/LiveTalking) + MuseTalk（2D 图片驱动口型同步） |
| 大脑层 | [Fay](https://github.com/xszyou/Fay) + Qwen-VL 多模态大模型 + Chroma 向量库 |
| 管理后台 | FastAPI（后端）+ Vue3 + Element Plus + ECharts（前端） |
| 部署 | Docker Compose |

---

## 📂 目录结构

```
digital_human/
├── third_party/        # 开源依赖（LiveTalking / Fay，需自行 clone）
├── brain/              # 大脑层业务代码（基于 Fay 扩展）
├── render/             # 渲染层定制（数字人形象）
├── admin/              # 管理后台（backend + frontend）
├── frontend/           # 游客交互端（基于 LiveTalking web 扩展）
├── docs/               # 文档
└── scripts/            # 运维脚本
```

---

## 🚀 快速启动

### 环境要求

- Python ≥ 3.12
- Node.js ≥ 18
- Docker & Docker Compose（可选，用于容器化部署）
- 一个 [DashScope API Key](https://help.aliyun.com/zh/model-studio/getting-started/)（用于调用 Qwen 大模型）

### 启动步骤

```bash
# 1. 克隆本仓库
git clone https://github.com/<你的用户名>/<仓库名>.git
cd digital_human

# 2. 拉取第三方依赖（不入主 git 仓库）
mkdir -p third_party && cd third_party
git clone --depth 1 https://github.com/lipku/LiveTalking.git
git clone --depth 1 https://github.com/xszyou/Fay.git
cd ..

# 3. 复制环境配置并填入 API Key
cp .env.example .env
# 编辑 .env，将 DASHSCOPE_API_KEY 设为你的真实 Key

# 4. 启动服务
docker-compose up -d
# 或手动分别启动各服务（参考 docs/ 目录）
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 游客交互端 | http://localhost:8010 |
| 管理后台 | http://localhost:5173 |

---

## 🤝 如何参与贡献

我们欢迎任何形式的贡献！无论是修复 Bug、新增功能、改进文档，还是提出建议。

### 1. Fork 本仓库

点击 GitHub 页面右上角的 **Fork** 按钮，将仓库复制到你的账号下。

### 2. 克隆你的 Fork

```bash
git clone https://github.com/<你的用户名>/<仓库名>.git
cd digital_human
git remote add upstream https://github.com/<原始作者>/<仓库名>.git
```

### 3. 创建功能分支

```bash
git checkout -b feat/your-feature-name
```

分支命名建议：
- `feat/xxx` — 新功能
- `fix/xxx` — 修复 Bug
- `docs/xxx` — 文档改进
- `refactor/xxx` — 重构
- `chore/xxx` — 构建/工具链相关

### 4. 提交代码

```bash
git add .
git commit -m "feat: 简洁清晰地描述你的改动"
```

提交信息建议遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范。

### 5. 推送到你的 Fork 并创建 Pull Request

```bash
git push origin feat/your-feature-name
```

然后在 GitHub 上点击 **Compare & pull request**，描述你的改动内容和动机。

### 6. 等待审核

维护者会尽快 Review 你的 PR，可能会提出修改建议。讨论达成一致后即可合并。

---

## 🐛 报告 Issue

如果你发现了 Bug，或者有新功能建议，请 [提交 Issue](https://github.com/<你的用户名>/<仓库名>/issues/new)。

Issue 标题建议格式：
```
[BUG] 简洁描述问题
[FEAT] 简洁描述建议
[QUESTION] 你的问题
```

---

## 📋 开发规范

- **Python 代码**：遵循 [PEP 8](https://peps.python.org/pep-0008/) 风格
- **前端代码**：遵循项目内 ESLint / Prettier 配置
- **提交前**：确保已有测试通过
  ```bash
  cd brain && python -m pytest tests/ -v
  ```
- **提交信息**：使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式

---

## 🗺️ 开发路线图

- [x] 基础框架搭建
- [ ] 游客交互端完善
- [ ] 管理后台数据大屏
- [ ] 多景区支持
- [ ] Docker 一键部署脚本
- [ ] CI/CD 流水线

> 详细进度见 `docs/项目状态总结.md`

---

## 📄 许可证

本项目基于 **Apache License 2.0** 开源 — 详见 [LICENSE](LICENSE) 文件。

> 本项目依赖的第三方开源项目（LiveTalking、Fay）分别遵循其自身许可证。

---

## 📬 联系方式

- 项目 Issues：[点此提交](https://github.com/<你的用户名>/<仓库名>/issues)
- 软件杯大赛官网：http://www.cnsoftbei.com/

---

**如果这个项目对你有帮助，欢迎 ⭐ Star 支持！**
