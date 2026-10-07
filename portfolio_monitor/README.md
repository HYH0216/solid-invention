# Trading 212 持仓日报

每个交易日美股收盘后，自动读取 Trading 212 Stocks ISA 账户的持仓，交给 Claude 分析（会联网查相关新闻），再把中文简报推送到你手机上的 Telegram。

流程：GitHub Actions 定时运行 → 调用 Trading 212 API（只读）→ 调用 Claude API 分析 → 通过 Telegram 机器人发给你。

> ⚠️ 报告只是参考，不构成投资建议。程序只读取数据，不会下单。

## 一、先把仓库设为私有

报告里有你的持仓金额，上一次的持仓快照也会存在 GitHub Actions 的缓存里。公开仓库的缓存和运行记录别人有办法看到，所以请先到仓库的 **Settings → General → Danger Zone → Change visibility** 改成 **Private**，或者把代码放到一个新的私有仓库里。

## 二、准备 4 样东西

### 1. Trading 212 API 密钥

在 Trading 212 App 里打开 **Settings → API (Beta)**，生成一对 API Key 和 API Secret。

- 权限**只勾选读取类**：Account data、Portfolio。不要勾选下单相关的权限。
- Secret 只显示一次，请马上复制保存。

### 2. Claude API 密钥

在 <https://console.anthropic.com> 注册账号、充值少量额度，然后创建一个 API Key。每天一份报告（包含几次网络搜索）的费用大约是几美分到二十几美分。

### 3. Telegram 机器人

1. 在 Telegram 里搜索 **@BotFather**，发送 `/newbot`，按提示起个名字，拿到 **bot token**（格式类似 `123456:ABC-DEF...`）。
2. 打开你新建的机器人，随便给它发一条消息（比如 "hi"）。
3. 在电脑上运行下面的命令，拿到你的 **chat id**：

   ```bash
   pip install -r requirements.txt
   TELEGRAM_BOT_TOKEN=你的token python -m portfolio_monitor --find-chat-id
   ```

   如果不想在本地运行，也可以在浏览器打开 `https://api.telegram.org/bot你的token/getUpdates`，找到 `"chat":{"id":数字` 里的那个数字。

### 4. （可选）你的投资偏好

用几句话写下你的情况，Claude 会据此调整建议，例如：

> 长期投资，期限 10 年以上；能接受较大波动；希望单只个股不超过 15%；每月定投 500 英镑。

## 三、在 GitHub 上配置

打开仓库的 **Settings → Secrets and variables → Actions**：

| 类型 | 名称 | 内容 |
| --- | --- | --- |
| Secret | `T212_API_KEY` | Trading 212 API Key |
| Secret | `T212_API_SECRET` | Trading 212 API Secret |
| Secret | `ANTHROPIC_API_KEY` | Claude API Key |
| Secret | `TELEGRAM_BOT_TOKEN` | 机器人 token |
| Secret | `TELEGRAM_CHAT_ID` | 你的 chat id |
| Variable（可选） | `INVESTOR_PROFILE` | 你的投资偏好 |

另外，定时任务只会在默认分支（`main`）上运行，所以需要先把这些代码合并到 `main`。

## 四、测试和运行

- **手动跑一次**：进入仓库的 **Actions → Portfolio report → Run workflow**，一两分钟后 Telegram 应该就会收到报告。
- **自动运行**：周一到周五 UTC 21:30，也就是英国夏令时 22:30、冬令时 21:30。GitHub 的定时任务偶尔会延迟几分钟到十几分钟。
- **出错时**：如果拉取数据或分析失败，机器人会发一条"报告生成失败"的消息，详细原因可以在 Actions 的运行记录里查看。

想改推送时间的话，修改 `.github/workflows/portfolio-report.yml` 里的 `cron` 一行即可（时间是 UTC）。

## 本地运行

```bash
pip install -r requirements.txt

# 用示例数据试跑，只打印报告、不推送（需要 ANTHROPIC_API_KEY）
python -m portfolio_monitor --dry-run --sample portfolio_monitor/samples/example.json

# 用真实账户数据跑完整流程
export T212_API_KEY=... T212_API_SECRET=... ANTHROPIC_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
python -m portfolio_monitor
```

## 文件说明

- `trading212.py`：Trading 212 API 客户端，只读，包括账户汇总和持仓两个接口。
- `snapshot.py`：整理持仓数据，计算仓位权重和收益率，并和上一次的快照对比。
- `analyst.py`：调用 Claude 生成中文报告；分析要求写在 `SYSTEM_PROMPT` 里，可以按需修改。
- `telegram.py`：发送 Telegram 消息，超过 4096 字时自动拆分。
