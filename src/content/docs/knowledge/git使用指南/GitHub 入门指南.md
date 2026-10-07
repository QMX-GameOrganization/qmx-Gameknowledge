---
title: git入门
description: git？
---

<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/61618570/1790167285212-04004be1-dafb-4480-a419-c20be067277c.png)

> 目标：看完这份指南，你应该能完成一套最常用的流程：注册 GitHub、创建仓库、把电脑上的代码上传到 GitHub、拉取别人的更新、创建分支并提交 Pull Request。
>
> 本文默认使用 Windows 电脑。命令中的英文、空格和标点请尽量原样输入。
>

## 0. 先说清楚：Git 和 GitHub 是什么
可以把它们想成两个东西：

+ **Git**：安装在自己电脑上的版本管理工具，负责记录文件的每次修改。
+ **GitHub**：放在网上的代码仓库平台，负责保存和分享 Git 仓库，也方便多人协作。

一个简单类比：

+ Git 像“游戏存档系统”，可以回到以前的存档。
+ GitHub 像“云端存档 + 分享平台”，同学可以看到你的项目，也可以一起修改。

常见词语先记住这几个：

| 词语 | 通俗解释 |
| --- | --- |
| 仓库（Repository / Repo） | 一个项目的文件夹，以及它的版本记录 |
| 提交（Commit） | 给当前修改拍一张有说明的“快照” |
| 推送（Push） | 把本地的提交上传到 GitHub |
| 拉取（Pull） | 把 GitHub 上的新内容下载并合并到本地 |
| 分支（Branch） | 从主线分出来的一条独立工作线 |
| 合并（Merge） | 把一个分支的修改并入另一个分支 |
| Pull Request（合并请求，简称 PR） | 请求项目负责人检查并合并你的修改 |
| Fork（复刻） | 把别人的公开仓库复制到自己的 GitHub 账号下 |


## 1. 注册并设置 GitHub 账号
1. 打开 [https://github.com](https://github.com)，点击 **Sign up** 注册。
2. 使用常用邮箱，并完成邮箱验证。
3. 用户名建议简单、长期使用，尽量不要包含真实身份证号、手机号等隐私信息。
4. 登录后，点右上角头像进入 **Settings**，检查个人资料和头像。
5. 建议开启双重验证（2FA）。账号一旦被盗，公开仓库和私有仓库都可能受到影响。

### 用户名和仓库名怎么取
+ 用户名最好与个人学习方向相关，例如 `hj-bigData`。
+ 仓库名使用英文、数字和连字符更稳妥，例如 `Tsc-c-notes`。
+ README、代码和提交说明可以写中文；项目文件名尽量使用英文，避免不同电脑之间出现编码或路径问题。

## 2. 安装电脑上的 Git
### Windows 安装
1. 打开 [Git 官网下载页](https://git-scm.com/download/win) 下载并安装 Git for Windows。
2. 安装时大部分选项保持默认即可。
3. 安装完成后，在项目文件夹空白处右键，应该能看到 **Open Git Bash here**；也可以使用 PowerShell。

检查是否安装成功：

```bash
git --version
```

能看到类似 `git version 2.x.x` 的结果，就说明安装成功。

### 第一次使用前配置身份
这些信息会写入每次提交，用来说明“是谁提交的”。邮箱建议使用 GitHub 账号中已经验证过的邮箱；如果在意隐私，可以在 GitHub 的邮箱设置里使用 `noreply` 地址。

```bash
git config --global user.name "你的姓名或昵称"
git config --global user.email "你的邮箱"
```

检查配置：

```bash
git config --global --list
```

注意：这里的 `user.name` 不是 GitHub 用户名，也不是登录密码，只是提交记录中显示的作者名。

## 3. 认证：为什么 Push 时要登录
GitHub 已经不支持直接用账号密码进行 Git 操作。常用的认证方式有两种：

+ **HTTPS + Personal Access Token（PAT）**：配置比较直观，适合刚开始学习。
+ **SSH Key**：配置一次后比较方便，适合长期使用。

### 推荐方式：HTTPS + Token
1. 在 GitHub 右上角头像中进入 **Settings**。
2. 进入 **Developer settings -> Personal access tokens -> Tokens (classic)**，点击 **Generate new token**。
3. 设置过期时间，按照需要勾选权限。只推送自己仓库的代码时，通常需要 `repo` 权限；能用细粒度 Token 时，优先只给目标仓库需要的权限。
4. 生成后立即复制 Token。它只会完整显示一次，**不要发给任何人，也不要提交到代码仓库**。
5. 命令行要求输入密码时，粘贴 Token（粘贴时屏幕通常不会显示字符），然后回车。

Token 就像临时钥匙：如果怀疑泄露，立即到 GitHub 设置中撤销并重新生成。

### 可选方式：SSH Key
在 Git Bash 中生成密钥：

```bash
ssh-keygen -t ed25519 -C "你的邮箱"
```

一路按回车可以使用默认路径；如果提示设置密码，建议设置一个自己记得住的密码。

查看公钥内容：

```bash
cat ~/.ssh/id_ed25519.pub
```

复制输出的整行内容，在 GitHub 中进入 **Settings -> SSH and GPG keys -> New SSH key** 粘贴保存。测试连接：

```bash
ssh -T git@github.com
```

如果出现欢迎信息，说明 SSH 配置成功。

## 4. 在 GitHub 网页上创建第一个仓库
1. 登录 GitHub，点击右上角的 **+ -> New repository**。
2. 填写仓库名，例如 `my-first-repo`。
3. 选择 **Public**（公开）或 **Private**（私有）。
+ Public：任何人都能看，适合开源学习项目和作品集。
+ Private：只有你和授权成员能看，适合课程作业、未完成项目或包含敏感内容的项目。
4. 建议勾选 **Add a README file**，这样仓库创建后就有项目说明。
5. `.gitignore` 用来告诉 Git 忽略哪些文件。Python、Node.js 等项目可以选择对应模板。
6. 点击 **Create repository**。

### 任何仓库里都不应直接提交什么
+ 密码、Token、API Key、数据库连接字符串
+ 身份证号、手机号、住址等个人隐私
+ 未经允许上传的课程资料、商业资料或他人代码
+ 通常不需要版本管理的大体积压缩包、编译产物和系统缓存

私有仓库也不是密码箱：仓库成员、误配置的权限、Fork、下载到本地的副本或备份，都可能让内容扩散。因此，密码和密钥在公开仓库、私有仓库中都不应提交。

编译产物和缓存一般应写入 `.gitignore`，让仓库只保存源代码和必要的配置模板。如果确实需要发布安装包或构建结果，可以使用 GitHub Releases、Packages 或专门的制品存储，而不是把它们混在源代码提交里。

即使后来删除了文件，敏感信息也可能仍然存在于 Git 历史中。误传密钥时，第一时间撤销密钥，再处理仓库历史。

## 5. 把电脑上的项目上传到 GitHub：完整流程
下面以新建一个本地文件夹为例。先在电脑上创建项目目录，并在里面放一个 `README.md` 或代码文件。

### 第一步：进入项目文件夹
PowerShell 示例：

```powershell
cd "D:\学习\my-first-repo"
```

路径中有空格或中文时，使用引号包住整个路径。

### 第二步：让这个文件夹成为 Git 仓库
```bash
git init
```

这条命令会创建一个隐藏的 `.git` 文件夹，用来保存版本记录。不要手动删除它，也不要把它上传到网盘后随意改动。

### 第三步：查看当前状态
```bash
git status
```

这是最值得养成的习惯。它会告诉你有哪些文件还没有被 Git 跟踪、哪些文件已经修改、当前在哪个分支。

### 第四步：把文件放入暂存区
添加所有当前目录下的文件：

```bash
git add .
```

或者只添加某个文件：

```bash
git add README.md
```

暂存区可以理解为“这次准备提交的文件清单”。不确定时，先运行 `git status` 检查清单。

### 第五步：创建一次提交
```bash
git commit -m "完成第一次提交"
```

提交说明要让别人看懂你做了什么，例如：

```bash
git commit -m "新增实验一代码"
git commit -m "修复登录页面样式问题"
git commit -m "补充项目运行说明"
```

提交应该小而清楚。不要把一周的所有改动混成一个“终于写完了”的提交。

### 第六步：把本地仓库连接到 GitHub
打开 GitHub 仓库页面，点击 **Code**，复制 HTTPS 或 SSH 地址，然后执行其中一种：

HTTPS：

```bash
git remote add origin https://github.com/你的用户名/你的仓库名.git
```

SSH：

```bash
git remote add origin git@github.com:你的用户名/你的仓库名.git
```

检查是否添加成功：

```bash
git remote -v
```

`origin` 只是远程仓库的默认昵称，不是固定要求，但大家通常都这样命名。

### 第七步：推送到 GitHub
先把本地当前分支命名为 `main`，再推送：

```bash
git branch -M main
git push -u origin main
```

刷新 GitHub 网页，就能看到本地文件了。之后再次推送通常只需要：

```bash
git push
```

> 如果你是在 GitHub 网页上已经创建了 README，而本地又执行了 `git init`，两边可能各自有第一次提交，第一次推送会提示历史不一致。初学时更简单的做法是：先在 GitHub 创建一个空仓库（不要勾选 README），本地完成 `git init` 后再连接远程；或者先拉取远程再合并，见下方“常见报错”。
>

## 6. 从 GitHub 下载项目到电脑：Clone
如果仓库已经在 GitHub 上，使用 **Code -> Local -> HTTPS/SSH** 复制地址，然后执行：

```bash
git clone https://github.com/用户名/仓库名.git
```

或者：

```bash
git clone git@github.com:用户名/仓库名.git
```

进入新下载的文件夹：

```bash
cd 仓库名
```

`clone` 只需要第一次使用。以后同步别人已经推送的新内容，使用：

```bash
git pull
```

## 7. 日常单人开发：一个常用工作循环
如果项目已经和 GitHub 仓库连接，平时可以按照下面的顺序工作：

### 1）先同步远程仓库
开始修改前，先把 GitHub 上可能出现的新内容下载到本地：

```bash
git pull
```

如果这是刚创建的本地项目，还没有连接 GitHub，可以暂时跳过这一步。

### 2）修改代码并测试
完成一个小功能或修复一个问题后，先运行程序或测试，确认基本功能正常。

### 3）查看自己修改了什么
```bash
git status
git diff
```

+ `git status`：查看哪些文件被修改了；
+ `git diff`：查看具体修改内容。

### 4）选择要提交的文件
```bash
git add 文件名
```

如果确认当前目录下的所有修改都应该提交，也可以使用：

```bash
git add .
```

### 5）创建本地提交
```bash
git commit -m "说明本次修改"
```

提交相当于给当前代码保存一个有说明的版本快照。例如：

```bash
git commit -m "修复登录按钮无法点击的问题"
```

### 6）上传到 GitHub
```bash
git push
```

`commit` 只是保存到自己电脑上，`push` 才是把提交上传到 GitHub。

因此，一个完整的日常流程通常是：

```latex
拉取更新 -> 修改代码 -> 测试 -> 查看修改 -> add -> commit -> push
```

> 如果电脑上的项目还没有连接远程仓库，或者项目只是自己本地练习，就不需要执行 `git pull` 和 `git push`。
>

查看提交记录：

```bash
git log --oneline --decorate --graph --all
```

## 8. 分支：写新功能时不要直接改主线
主分支通常叫 `main`，可以把它看作比较稳定的版本。开发新功能或修复问题时，建议新建分支：

```bash
git switch -c feature-login
```

在这个分支上修改、提交、推送：

```bash
git add .
git commit -m "新增登录功能"
git push -u origin feature-login
```

切回主分支：

```bash
git switch main
```

查看所有分支：

```bash
git branch -a
```

不再需要的本地分支可以删除：

```bash
git branch -d feature-login
```

## 9. Pull Request（合并请求）：和同学协作的标准流程
假设你在一个小组项目中完成了一个功能：

1. 从最新的 `main` 创建自己的分支。
2. 在自己的分支上修改代码，并多次小提交。
3. 把分支推送到 GitHub。
4. 打开仓库页面，点击 **Compare & pull request**，创建 Pull Request。
5. 在 PR 描述中写清楚：改了什么、为什么改、如何测试、是否有截图或待处理问题。
6. 邀请同学或老师 Review。看到建议后，在原分支继续修改并 `push`，PR 会自动更新。
7. 检查通过后，由项目负责人点击 **Merge pull request**。
8. 合并后同步本地主分支：

```bash
git switch main
git pull
```

不要直接复制粘贴同学的代码覆盖自己的文件。通过分支和 PR 协作，修改有记录，也更容易发现问题。

## 10. Fork（复刻）：给别人的开源项目贡献代码
如果你没有某个仓库的直接写权限：

1. 打开对方仓库，点击右上角 **Fork**，把仓库复刻到自己的 GitHub 账号下。
2. Clone 自己账号下的仓库。
3. 创建功能分支并完成修改。
4. Push 到自己账号下的仓库。
5. 在 GitHub 上向原仓库创建 Pull Request。

这就是很多开源项目接受贡献的基本流程。提交 PR 前先阅读项目的 `README`、`CONTRIBUTING` 和行为准则。

## 11. `.gitignore`：不提交不必要的文件
在项目根目录创建 `.gitignore`，把不需要上传的文件写进去。例如一个 Python 项目可以写：

```plain
__pycache__/
*.pyc
.venv/
.env
.idea/
```

其中 `.env` 常常保存本地密钥或配置，不能上传。不同语言可以从 [github/gitignore](https://github.com/github/gitignore) 选择模板。

注意：`.gitignore` 只对“还没有被 Git 跟踪”的文件生效。如果某个密钥已经提交过，单纯把它写进 `.gitignore` 并不能让它从历史中消失，仍然要先撤销密钥。

## 12. 常见问题与处理方法
### 1）`git is not recognized`
Git 没安装，或者安装后终端没有重新打开。重新安装 Git for Windows，关闭当前终端并打开新的 PowerShell/Git Bash，再运行 `git --version`。

### 2）`Permission denied` 或 `Authentication failed`
先确认远程地址是否正确：

```bash
git remote -v
```

HTTPS 方式不要输入 GitHub 登录密码，应输入 Personal Access Token。SSH 方式检查公钥是否已经添加到 GitHub，并测试：

```bash
ssh -T git@github.com
```

### 3）`rejected because the remote contains work`
说明远程仓库有本地没有的提交，先拉取再推送：

```bash
git pull --rebase origin main
git push
```

如果出现冲突，打开 Git 标记出来的文件，保留正确内容后执行：

```bash
git add 冲突文件名
git rebase --continue
git push
```

不确定如何处理时，不要直接使用 `git push --force`。强制推送可能覆盖别人的提交。

### 4）不小心修改了文件，还没提交，想撤销
先查看状态。撤销某个文件尚未暂存的修改：

```bash
git restore 文件名
```

这会丢掉该文件未提交的修改，执行前确认里面没有需要保留的内容。

取消某个文件的暂存，但保留文件修改：

```bash
git restore --staged 文件名
```

### 5）提交说明写错了
只想修改最近一次提交说明，且还没有推送：

```bash
git commit --amend -m "新的提交说明"
```

如果已经推送，尽量新增一个提交修正，不要随意改写公共分支历史。

### 6）把不该提交的文件推上去了
如果是密码或 Token：

1. 立刻在对应平台撤销或更换它；
2. 把文件加入 `.gitignore`；
3. 从当前版本移除并提交；
4. 如果敏感信息曾经进入 Git 历史，继续清理历史，并通知可能受影响的人。

如果只是普通的大文件或缓存，先停止继续推送，确认是否需要从 Git 历史中清理，再处理。

## 13. 一个可以直接背下来的命令清单
```bash
# 第一次配置
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"

# 新项目上传
git init
git status
git add .
git commit -m "第一次提交"
git branch -M main
git remote add origin 仓库地址
git push -u origin main

# 日常同步
git pull
git status
git add .
git commit -m "说明修改"
git push

# 分支协作
git switch -c feature-name
git push -u origin feature-name
git switch main
git pull
```

## 14. 推荐的学习顺序
不要试图一次记住所有命令，可以按这个顺序练习：

1. 注册 GitHub，创建一个公开仓库，写好 README。
2. 在本地创建一个小项目，完成 `init -> add -> commit -> push`。
3. 换一台电脑或换一个文件夹，练习 `clone -> pull`。
4. 修改 README，练习 `status -> diff -> commit -> push`。
5. 创建分支并提交一个 Pull Request。
6. 找一个允许新手贡献的开源项目，先从修改错别字、补充文档开始。

建议每一步都自己敲一遍命令。Git 的命令不需要死记，遇到问题时先看 `git status`，再查对应报错，通常比盲目重试更快。

## 结语
GitHub 不只是“交作业的网站”，它更像是你的学习作品集和团队协作记录。把项目说明写清楚，把提交拆小，把密钥保护好，慢慢养成规范习惯，之后做课程项目、参加竞赛、找实习都会用得上。

当你忘记某条命令时，可以先执行：

```bash
git help <命令名>
```

例如：

```bash
git help commit
```

也可以查看 [GitHub Docs](https://docs.github.com/zh) 和 [Git 官方文档](https://git-scm.com/doc)。

