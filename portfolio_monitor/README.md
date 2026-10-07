# Trading 212 持仓日报

每个交易日收盘后，Claude 会读取你 Trading 212 Stocks ISA 账户的持仓，以及 `watchlist.txt` 里的关注股票，联网查询相关新闻和行情后，直接在 Claude 里写出一份中文报告。

流程：Claude Code 定时任务（Routine）启动一个新会话 → 运行 `python -m portfolio_monitor` 读取持仓（只读）→ Claude 按 `REPORT.md` 的要求写报告。报告在 Claude App 或 claude.ai/code 的会话列表里查看。

> ⚠️ 报告只是参考，不构成投资建议。程序只读取数据，不会下单。

## 文件说明

- `watchlist.txt`：关注列表，每行一个股票代码。Trading 212 的 API 读不到 App 里的关注列表，所以需要手动维护这个文件。
- `REPORT.md`：给 Claude 的报告写作要求，包括结构、篇幅和注意事项。可以按需修改。
- `trading212.py`：Trading 212 API 客户端，只读，调用账户汇总和持仓两个接口。
- `snapshot.py`：整理持仓数据，计算仓位权重和收益率。

## 需要的配置

在 Claude Code 云端环境的设置里（会话标题栏的环境菜单 → Edit）：

1. **Network access**：把 `live.trading212.com` 加入 Allowed domains。
2. **环境变量**：添加 `T212_API_KEY` 和 `T212_API_SECRET`。
   - 在 Trading 212 App 的 **Settings → API (Beta)** 里生成。
   - 权限只勾选读取类，比如 Account data 和 Portfolio。

## 本地试跑

```bash
python -m portfolio_monitor --sample portfolio_monitor/samples/example.json   # 用示例数据
T212_API_KEY=... T212_API_SECRET=... python -m portfolio_monitor               # 用真实账户
```
