# Agent Skill 全链路发布 SOP

> 本文档定义了将一个本地 `SKILL.md` 文件发布到全网（NPM + PyPI + GitHub）的标准操作流程。
> 设计为 Human-in-the-Loop：人类完成账号注册和认证，AI Agent 完成全部构建、打包和发布。

---

## 术语

| 术语 | 含义 |
|------|------|
| SKILL.md | 符合 Agent Skills 开放标准的 Markdown 文件，YAML frontmatter 含 `name` 和 `description` |
| Skills CLI | Vercel 开源的 `skills` 命令行工具，通过 `npx skills add` 调用 |
| 包名 | NPM/PyPI 上的注册名称（如 `hashmind-skill`），用于搜索发现 |
| GitHub 路径 | `owner/repo` 格式，Skills CLI 实际通过 git clone 拉取，**不走 NPM registry** |

---

## Phase 0 — 人类一次性准备（约 15 分钟）

以下账号和凭证只需注册一次，后续所有 Skill 发布复用。

### 0.1 注册账号

| 平台 | 注册地址 | 用途 |
|------|---------|------|
| GitHub | https://github.com/signup | 代码托管 + Skills CLI 分发源 |
| npmjs.com | https://www.npmjs.com/signup | NPM 包注册（搜索发现入口） |
| pypi.org | https://pypi.org/account/register/ | PyPI 包注册（Python 生态分发） |

### 0.2 创建 Token

#### GitHub CLI 认证

```bash
gh auth login
```

按提示完成浏览器 OAuth 认证。验证：

```bash
gh auth status
# ✓ Logged in to github.com account xxx
```

#### NPM Token

1. 登录 https://www.npmjs.com → 头像 → Access Tokens → Generate New Token
2. 选 **Granular Access Token**
3. **Packages and scopes** → 选 **Read and write**（必须，否则无法发布）
4. 其他保持默认 → Generate token
5. 复制 token（`npm_` 开头）

> **踩坑记录**：Packages 权限设为 "No access" 会导致 `E403 Forbidden`。

#### PyPI Token

1. 登录 https://pypi.org → Account settings → API tokens → Add API token
2. Scope 选 **Entire account**（首次发布新包必须用 account-wide token）
3. 复制 token（`pypi-` 开头）

### 0.3 提供给 Agent 的清单

将以下信息提供给 AI Agent：

```
1. GitHub 用户名: ___
2. NPM Token: npm_xxx
3. PyPI Token: pypi-xxx
4. SSH Key 路径（如有多个）: ~/.ssh/id_xxx
5. SKILL.md 文件路径: /path/to/SKILL.md
6. 期望的包名: xxx-skill（用于 NPM/PyPI 注册名）
```

> **安全提醒**：Token 在对话中暴露后，建议发布完成后立即轮换（删旧建新），
> GitHub Secrets 中的值同步更新即可。

---

## Phase 1 — Agent 自动构建（约 5 分钟）

> 以下所有步骤由 AI Agent 自动执行，人类无需介入。

### 1.1 检查包名可用性

```bash
# NPM
npm view {包名} 2>&1  # 期望 E404

# PyPI
curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/{包名}/json  # 期望 404
```

如果被占用，与人类协商替代名称后再继续。

### 1.2 创建 Monorepo 目录结构

```
{包名}/
├── package.json              # NPM 元数据 + 搜索关键词
├── pyproject.toml            # PyPI 构建配置
├── .claude-plugin/
│   └── plugin.json           # Claude Code 插件元数据
├── skills/
│   └── {skill-name}/
│       └── SKILL.md          # ★ 唯一源文件（从用户路径复制）
├── {python_包名}/
│   ├── __init__.py           # 版本号
│   ├── cli.py                # pip 安装后的 CLI 入口
│   └── SKILL.md              # → symlink 到 skills/{name}/SKILL.md
├── MANIFEST.in               # 确保 sdist 包含 .md 文件
├── README.md                 # 安装说明（含所有渠道命令）
├── LICENSE                   # MIT
├── .gitignore
└── .github/
    └── workflows/
        └── publish.yml       # Release tag → 自动发布 NPM + PyPI
```

### 1.3 关键文件内容规范

#### package.json

```json
{
  "name": "{包名}",
  "version": "1.0.0",
  "description": "{SKILL.md 的 description}",
  "keywords": ["agent-skills", "claude", "cursor", "windsurf", "opencode", "ai"],
  "files": ["skills/", "README.md", "LICENSE"],
  "license": "MIT",
  "homepage": "{项目主页}",
  "repository": {
    "type": "git",
    "url": "https://github.com/{owner}/{包名}"
  }
}
```

#### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "{包名}"
version = "1.0.0"
description = "{SKILL.md 的 description}"
readme = "README.md"
license = "MIT"
requires-python = ">=3.8"
keywords = ["agent-skills", "claude", "ai"]

[project.scripts]
{包名} = "{python_包名}.cli:main"

[tool.setuptools]
packages = ["{python_包名}"]

[tool.setuptools.package-data]
{python_包名} = ["SKILL.md"]
```

> **注意**：`license` 用字符串格式 `license = "MIT"`，
> 不要用 table 格式 `license = {text = "MIT"}`（setuptools 77+ 已弃用）。

#### .github/workflows/publish.yml

```yaml
name: Publish to NPM & PyPI
on:
  release:
    types: [published]

jobs:
  publish-npm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20.x'
          registry-url: 'https://registry.npmjs.org'
      - run: npm publish --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

  publish-pypi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

### 1.4 Python CLI 模板 (cli.py)

```python
"""CLI to install {skill-name} SKILL.md into agent skill directories."""
import argparse, shutil, sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Install SKILL.md")
    parser.add_argument("--global", "-g", dest="global_install", action="store_true",
                        help="Install to ~/.claude/skills/ and ~/.agents/skills/")
    parser.add_argument("--output", "-o", type=Path, help="Custom output directory")
    args = parser.parse_args()

    source = Path(__file__).resolve().parent / "SKILL.md"
    if not source.exists():
        print(f"Error: SKILL.md not found at {source}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        targets = [args.output]
    elif args.global_install:
        home = Path.home()
        targets = [
            home / ".claude" / "skills" / "{skill-name}",
            home / ".agents" / "skills" / "{skill-name}",
        ]
    else:
        targets = [Path.cwd()]

    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target / "SKILL.md")
        print(f"Installed SKILL.md -> {target / 'SKILL.md'}")
```

---

## Phase 2 — Agent 自动发布（约 3 分钟）

### 2.1 创建 GitHub 仓库并推送

```bash
cd {包目录}
git init && git add -A
git commit -m "feat: initial release — {skill-name} agent skill"
gh repo create {owner}/{包名} --public --source=. --remote=origin \
  --description "{description}" --push
```

> **SSH Key 踩坑**：如果 GitHub 账号用专用 SSH key，push 需指定：
> ```bash
> GIT_SSH_COMMAND="ssh -i {ssh_key_path} -o IdentitiesOnly=yes" git push -u origin main
> ```

### 2.2 发布到 NPM

```bash
echo '//registry.npmjs.org/:_authToken={npm_token}' > .npmrc
npm publish --access public
rm -f .npmrc   # 发布后立即删除，避免 token 泄露
```

### 2.3 发布到 PyPI

```bash
pip install build twine
python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD="{pypi_token}" twine upload dist/*
```

> **中国镜像踩坑**：如果用户 pip 配置了阿里云/清华等镜像源，新包同步需要数小时。
> 验证时用 `pip install {包名} -i https://pypi.org/simple/` 绕过。

### 2.4 设置 GitHub Secrets（CI/CD 用）

```bash
gh secret set NPM_TOKEN --body "{npm_token}" --repo {owner}/{包名}
gh secret set PYPI_TOKEN --body "{pypi_token}" --repo {owner}/{包名}
```

### 2.5 验证清单

```bash
# 1. NPM 包存在
npm view {包名}

# 2. PyPI 包存在
curl -s https://pypi.org/pypi/{包名}/json | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d['info']['name'], d['info']['version'])"

# 3. pip install 可用
pip install {包名} -i https://pypi.org/simple/
{包名} --global

# 4. npx skills add 可用
npx skills add {owner}/{包名}

# 5. GitHub Secrets 已设
gh secret list --repo {owner}/{包名}
```

---

## Phase 3 — 后续更新流程

当 SKILL.md 内容更新时：

### 人类操作（30 秒）

告诉 Agent："更新 SKILL.md 到 x.y.z 版本"，并提供新的 SKILL.md 文件（或描述变更）。

### Agent 自动执行

```bash
# 1. 替换 SKILL.md
cp {新文件路径} skills/{skill-name}/SKILL.md

# 2. 同步更新版本号（四处）
# - package.json: "version": "x.y.z"
# - pyproject.toml: version = "x.y.z"
# - {python_包名}/__init__.py: __version__ = "x.y.z"
# - .claude-plugin/plugin.json: "version": "x.y.z"

# 3. 提交并推送
git add -A && git commit -m "feat: update SKILL.md to vx.y.z"
git push

# 4. 创建 GitHub Release（触发 CI/CD 自动发布到 NPM + PyPI）
gh release create vx.y.z --title "vx.y.z" --notes "Update SKILL.md"
```

CI/CD 流水线自动完成 NPM + PyPI 双渠道发布，无需人工介入。

---

## 踩坑记录（实战总结）

| # | 问题 | 现象 | 解决 |
|---|------|------|------|
| 1 | NPM token 权限不足 | `E403 Forbidden` | Packages and scopes 必须选 **Read and write** |
| 2 | `npx skills add` 用包名 | `Failed to clone repository` | 用 GitHub 路径 `owner/repo`，不是 npm 包名 |
| 3 | pip 镜像未同步 | `No matching distribution found` | 加 `-i https://pypi.org/simple/` 或等几小时 |
| 4 | Claude Code `/plugin install` | `Marketplace not found` | 不存在此命令；`npx skills add` 已自动安装到 `.claude/skills/` |
| 5 | pyproject.toml license 格式 | setuptools deprecation warning | 用 `license = "MIT"` 而非 `license = {text = "MIT"}` |
| 6 | GitHub push SSH key | `Permission denied` | 多 key 场景需 `GIT_SSH_COMMAND` 指定正确 key |
| 7 | Python symlink 在 wheel 中 | 可能在 Windows 失败 | setuptools `python -m build` 会自动 dereference symlink |

---

## 分发渠道覆盖矩阵

| 安装命令 | 数据源 | 覆盖的 AI Agent |
|---------|--------|----------------|
| `npx skills add {owner}/{repo}` | GitHub repo | Claude Code, Cursor, Windsurf, Cline, OpenCode, Codex, Gemini CLI, Amp, GitHub Copilot, Kimi Code CLI 等 40+ |
| `pip install {包名}` + CLI | PyPI | Python 环境中的任意 Agent |
| `curl -sL {url} -o ~/SKILL.md` | 自有服务器 | 所有 Agent（手动） |
| npmjs.com 搜索 `{包名}` | NPM registry | 搜索发现入口（不直接用于安装） |

---

## 快速参考：文件与变量清单

发布一个新 Skill 时，Agent 需要人类提供的变量：

| 变量 | 示例 | 用途 |
|------|------|------|
| `{skill-name}` | `hashmind` | SKILL.md frontmatter 的 name 字段 |
| `{包名}` | `hashmind-skill` | NPM/PyPI 注册名 |
| `{python_包名}` | `hashmind_skill` | Python 模块名（下划线） |
| `{owner}` | `wentorai` | GitHub 用户名/组织名 |
| `{description}` | `HashMind SYNAPSE protocol...` | 包描述 |
| `{npm_token}` | `npm_xxx` | NPM 发布凭证 |
| `{pypi_token}` | `pypi-xxx` | PyPI 发布凭证 |
| `{ssh_key_path}` | `~/.ssh/id_ed25519_xxx` | GitHub SSH key（可选） |
| `{skill_md_path}` | `/path/to/SKILL.md` | 源文件路径 |
| `{homepage}` | `https://hashmind.space` | 项目主页 URL |

---

*基于 2026-03-08 实际发布 hashmind-skill 的完整经验编写。*
*参考实现：https://github.com/wentorai/hashmind-skill*
