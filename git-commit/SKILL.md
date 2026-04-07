---
name: go-commit
description: "Git 提交助手：执行 git add -u 暂存变更，分析 diff 内容，自动生成 Conventional Commits 规范的中文提交信息并执行 git commit。当用户要求提交代码、生成 commit message、执行 git commit、暂存并提交、或者说'提交一下'、'commit'、'帮我提交'时触发此技能。即使用户没有明确提到 Conventional Commits，只要涉及 git 提交相关操作都应使用此技能。"
---

# Go Commit — Git 智能提交助手

一个自动化的 git 提交工作流：暂存已跟踪文件的变更、分析 diff、生成规范的中文 commit message、执行提交。

## 为什么需要这个技能

好的提交信息是项目可维护性的基石。它让 `git log` 变成可读的变更日志，让 `git bisect` 真正有用，让代码审查者在打开 diff 之前就能理解意图。这个技能确保每次提交都达到这个标准，同时节省你思考措辞的时间。

## 工作流程

按以下步骤执行，每一步都有其存在的理由：

### 第一步：检查工作区状态

```bash
git status
git diff --stat
```

先看全局。如果工作区是干净的，直接告诉用户"没有需要提交的变更"并结束。如果有未跟踪的新文件（untracked），提醒用户这些文件不会被 `git add -u` 包含，询问是否需要手动添加。

### 第二步：暂存变更

```bash
git add -u
```

这只会暂存**已跟踪文件**的修改和删除。暂存后立即检查实际暂存了什么：

```bash
git diff --staged --stat
```

### 第三步：分析变更内容

```bash
git diff --staged
```

这是最关键的一步——你需要**理解**代码变更的逻辑意义，而不是机械地翻译 diff 内容。

**判断是否需要拆分提交：**

如果暂存区同时包含逻辑上不相关的变更（例如：一个 bug 修复 + 一个新功能，或者业务代码改动 + 依赖升级），应该建议用户拆分为多次提交。拆分的依据：

- 功能 vs 重构
- 后端 vs 前端
- 格式调整 vs 逻辑变更
- 测试 vs 生产代码
- 依赖升级 vs 行为变更

如果需要拆分，告诉用户具体的拆分建议，并指导使用 `git reset HEAD <file>` 或 `git add -p` 来精细控制暂存内容。每次只提交一个逻辑单元。

### 第四步：安全检查

在提交前扫描暂存内容，检查以下敏感信息：

- API 密钥、Token、Secret（如 `sk-`、`ghp_`、`AKIA`、`Bearer` 等前缀）
- 密码字段（`password =`、`passwd`、`secret`）
- 私钥文件内容（`-----BEGIN RSA PRIVATE KEY-----`）
- 硬编码的内网 IP 或数据库连接串
- 遗留的调试代码（`fmt.Println("debug`、`log.Debug`、`TODO: remove`）

运行辅助脚本（如果可用）：
```bash
python scripts/security_check.py
```

如果检测到可疑内容，**立即暂停**，向用户列出可疑行并要求确认后再继续。安全永远优先于便利。

### 第五步：生成 Commit Message

根据 diff 分析结果，生成符合以下规范的中文提交信息。

#### 格式规范

```
<type>(<scope>): <subject>

<body>
```

#### Type（类型）

只能从以下选取，选择最能描述变更本质的类型：

| Type       | 含义                                     |
|------------|------------------------------------------|
| `feat`     | 新功能                                   |
| `fix`      | 修补 bug                                |
| `docs`     | 文档修改                                 |
| `style`    | 代码格式修改（不影响运行的变动）         |
| `refactor` | 重构（非新功能，非 bug 修复的代码变动）  |
| `perf`     | 性能优化                                 |
| `test`     | 增加或修改测试                           |
| `chore`    | 构建过程或辅助工具的变动                 |

#### Scope（范围）

可选。填写受影响的模块名、包名或文件名。例如：`auth`、`router`、`config`、`Makefile`。

#### Subject（标题）

- 使用中文，简洁明了
- **不超过 50 个字符**
- 结尾**不加**句号
- 用祈使语气描述"做了什么"
- 涉及文件重命名或移动时，须在标题或正文第一行标注路径（如 `mv pkg/old -> pkg/new`）

#### Body（正文）

- 使用中文
- 解释**为什么**要做这个修改，以及**改了什么**
- 每行不超过 72 个字符
- 如果是破坏性改动（Breaking Change），必须在正文中用 `BREAKING CHANGE:` 开头的段落特别注明

#### 示例

**示例 1：新功能**
```
feat(auth): 添加 JWT Token 刷新机制

用户反馈长时间操作时 token 过期导致数据丢失。
新增 /auth/refresh 接口，支持在 token 过期前 5 分钟
自动续期，避免用户操作中断。
```

**示例 2：Bug 修复**
```
fix(handler): 修复并发请求下的 map 竞态问题

线上偶现 panic，排查发现 sessionMap 在并发读写时
未加锁保护。改用 sync.RWMutex 保证并发安全。
```

**示例 3：重构**
```
refactor(service): 将用户服务拆分为独立模块

随着业务增长，user_service.go 已超过 1200 行，
职责混杂。按领域拆分为 user_profile.go、
user_auth.go、user_preference.go 三个文件，
各自职责清晰，便于后续维护和测试。
```

**示例 4：破坏性改动**
```
feat(api): 统一错误响应格式为 RFC 7807

BREAKING CHANGE: 所有 API 错误响应结构变更，
原 {"code": 400, "msg": "..."} 改为
{"type": "...", "title": "...", "status": 400}，
客户端需同步更新错误处理逻辑。
```

### 第六步：执行提交

将生成的 commit message 展示给用户确认，然后执行：

```bash
git commit -m "<type>(<scope>): <subject>

<body>"
```

对于多行 commit message，使用如下方式：

```bash
git commit -m "<第一行 subject>" -m "<body 内容>"
```

或者先写入临时文件再提交：

```bash
cat > /tmp/commit_msg.txt << 'EOF'
<完整的 commit message>
EOF
git commit -F /tmp/commit_msg.txt
rm /tmp/commit_msg.txt
```

### 第七步：确认提交结果

```bash
git log --oneline -1
git show --stat HEAD
```

向用户展示：
- Commit hash（短格式）
- 提交信息摘要
- 变更文件列表

## 边界情况处理

- **暂存区为空**：提示用户没有可提交的变更
- **merge 冲突未解决**：提示用户先解决冲突
- **不在 git 仓库中**：提示用户当前目录不是 git 仓库
- **用户要求修改生成的 message**：尊重用户意见，按要求调整后再提交
- **变更量极大（超过 500 行 diff）**：强烈建议拆分提交，除非用户明确表示这是一个原子性变更
