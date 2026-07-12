# Surge Proxy List

将 [TopChina/proxy-list](https://github.com/TopChina/proxy-list) 提供的 Clash
订阅自动转换为 Surge 托管配置。

## Surge 订阅地址

```text
https://raw.githubusercontent.com/SAPToddZhang/surge-proxy-list/main/surge.conf
```

在 Surge 中选择“从 URL 下载配置”，粘贴上面的地址即可。仓库中的 GitHub
Actions 会在每小时第 17 分钟检查一次上游；只在转换结果变化时提交新的
`surge.conf`。

GitHub 的定时任务可能因平台负载延迟几分钟，因此这是“约每小时”更新，
不是精确到秒的调度。如果想立即刷新，可以在仓库的 Actions 页面手动运行
`Update Surge profile`。

## 本地转换

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python convert.py
```

当前转换器支持 Clash 的 HTTP/HTTPS 和 SOCKS5/SOCKS5-TLS 节点，并把
`select`、`url-test` 分组及 `MATCH` 终结规则映射成 Surge 格式。遇到未知
协议时任务会明确失败，避免生成看似正常但缺少节点的配置。
