$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LocalDir = Join-Path $ProjectDir "local"
$DashboardPath = Join-Path $LocalDir "网站后台.html"
$GeneratedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

$html = @'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <title>网站后台（本地私有）</title>
  <style>
    :root {
      --bg: #f5f7fa;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #54616f;
      --line: #cfd8e3;
      --primary: #1565c0;
      --primary-ink: #ffffff;
      --success: #2e7d32;
      --warning: #fbc02d;
      --warning-ink: #212121;
      --danger: #c62828;
      --soft-blue: #e8f1fb;
      --soft-green: #eaf5ec;
      --soft-yellow: #fff8d8;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "DejaVu Sans", Arial, "Microsoft YaHei", sans-serif;
      font-size: 17px;
      line-height: 1.55;
    }

    header {
      background: #0f172a;
      color: #ffffff;
      padding: 28px 32px;
    }

    header h1 {
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0;
    }

    header p {
      margin: 0;
      color: #dbeafe;
      max-width: 980px;
    }

    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 22px;
    }

    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 0 0 18px;
      padding: 18px;
    }

    h2 {
      margin: 0 0 12px;
      font-size: 22px;
      letter-spacing: 0;
    }

    h3 {
      margin: 18px 0 8px;
      font-size: 18px;
      letter-spacing: 0;
    }

    p {
      margin: 0 0 12px;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 14px 0 0;
    }

    a.button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
      padding: 8px 13px;
      border-radius: 6px;
      background: var(--primary);
      color: var(--primary-ink);
      font-weight: 700;
      text-decoration: none;
      border: 1px solid #0d47a1;
    }

    a.button.secondary {
      background: #e0e0e0;
      color: #212121;
      border-color: #b0bec5;
      font-weight: 600;
    }

    a.button.warning {
      background: var(--warning);
      color: var(--warning-ink);
      border-color: #a87400;
    }

    a.button:hover,
    a.button:focus {
      outline: 3px solid #90caf9;
      outline-offset: 2px;
      text-decoration: underline;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0 0;
      background: #ffffff;
    }

    th,
    td {
      border: 1px solid var(--line);
      padding: 10px 12px;
      vertical-align: top;
      text-align: left;
    }

    th {
      background: #eef2f7;
      font-weight: 700;
    }

    .status {
      display: inline-block;
      border-radius: 999px;
      padding: 3px 10px;
      font-weight: 700;
      white-space: nowrap;
    }

    .ok {
      background: var(--soft-green);
      color: var(--success);
      border: 1px solid #b7dfbd;
    }

    .pending {
      background: var(--soft-yellow);
      color: #684f00;
      border: 1px solid #e7cf71;
    }

    .blocked {
      background: #fdecea;
      color: var(--danger);
      border: 1px solid #f3b5af;
    }

    .note {
      background: var(--soft-blue);
      border-left: 5px solid var(--primary);
      padding: 12px 14px;
      margin: 12px 0 0;
    }

    .muted {
      color: var(--muted);
    }

    code {
      background: #edf2f7;
      color: #1f2933;
      border-radius: 4px;
      padding: 1px 5px;
      font-family: Consolas, "DejaVu Sans Mono", monospace;
      font-size: 0.95em;
    }

    footer {
      color: var(--muted);
      font-size: 15px;
      padding: 4px 0 22px;
    }

    @media (max-width: 760px) {
      header {
        padding: 22px 18px;
      }

      main {
        padding: 14px;
      }

      table,
      thead,
      tbody,
      th,
      td,
      tr {
        display: block;
      }

      thead {
        display: none;
      }

      tr {
        border: 1px solid var(--line);
        margin-bottom: 10px;
      }

      td {
        border: 0;
        border-bottom: 1px solid var(--line);
      }

      td:last-child {
        border-bottom: 0;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>网站后台（本地私有）</h1>
    <p>这个页面由本机脚本生成在 <code>local/网站后台.html</code>，只用于管理入口和状态查看，不发布到 GitHub Pages。</p>
  </header>

  <main>
    <section>
      <h2>当前结论</h2>
      <table>
        <thead>
          <tr>
            <th>模块</th>
            <th>状态</th>
            <th>所以现在能看什么</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>论文/Scholar 自动更新</td>
            <td><span class="status ok">已接入</span></td>
            <td>通过 GitHub Actions 查看每次同步日志、更新摘要和邮件发送状态。</td>
          </tr>
          <tr>
            <td>报告邮箱配置</td>
            <td><span class="status ok">私密配置</span></td>
            <td>收件邮箱应放在 GitHub Actions secret <code>SCHOLARLY_REPORT_EMAIL_TO</code>，不写进公开仓库。</td>
          </tr>
          <tr>
            <td>访客人数</td>
            <td><span class="status pending">未启用</span></td>
            <td>当前不会显示假访客数；匿名汇总访问量风险低，但 tracking cookie、指纹或用户 ID 仍需要合规说明。</td>
          </tr>
          <tr>
            <td>访客地理位置</td>
            <td><span class="status blocked">暂不采集</span></td>
            <td>地理位置属于更高风险数据；暂时不采集国家/地区、城市、精确坐标或 IP 推断位置。</td>
          </tr>
        </tbody>
      </table>
      <div class="toolbar">
        <a class="button" href="https://github.com/FanCheng5640/fancheng5640.github.io/actions/workflows/sync_orcid_publications.yml" target="_blank" rel="noopener">打开更新日志</a>
        <a class="button secondary" href="https://github.com/FanCheng5640/fancheng5640.github.io/graphs/traffic" target="_blank" rel="noopener">打开 GitHub Traffic</a>
        <a class="button secondary" href="https://github.com/FanCheng5640/fancheng5640.github.io/settings/secrets/actions" target="_blank" rel="noopener">打开 Secrets 设置</a>
      </div>
    </section>

    <section>
      <h2>更新日志</h2>
      <table>
        <thead>
          <tr>
            <th>要查的内容</th>
            <th>入口</th>
            <th>判断口径</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>ORCID / Google Scholar 同步</td>
            <td><a href="https://github.com/FanCheng5640/fancheng5640.github.io/actions/workflows/sync_orcid_publications.yml" target="_blank" rel="noopener">sync_orcid_publications.yml</a></td>
            <td>看最近一次 workflow 是否成功；如果缺少邮箱或 SMTP secret，Actions summary 会直接写明。</td>
          </tr>
          <tr>
            <td>GitHub Pages 发布</td>
            <td><a href="https://github.com/FanCheng5640/fancheng5640.github.io/deployments/github-pages" target="_blank" rel="noopener">GitHub Pages deployments</a></td>
            <td>看最新部署是否成功，以及部署时间是否晚于最后一次网页修改。</td>
          </tr>
          <tr>
            <td>本地预览日志</td>
            <td><code>tmp/local-preview.log</code></td>
            <td>本机预览失败时先看这里；这个日志在本地，不会发布。</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h2>访客统计</h2>
      <p class="note">当前策略：暂时不接入 analytics。后台只记录法律风险口径，不显示人数、时间分布或地理位置的估算值。GitHub Traffic 只能作为仓库/页面访问线索，不等同于完整的网站访客后台。</p>
      <table>
        <thead>
          <tr>
            <th>统计项</th>
            <th>当前状态</th>
            <th>法律风险口径</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>按时间统计访客人数</td>
            <td><span class="status pending">暂不启用</span></td>
            <td>只做匿名汇总访问量时风险较低；如果用 cookie、fingerprint、用户 ID 或第三方 analytics，需要告知用途并按适用地区处理同意或退出机制。</td>
          </tr>
          <tr>
            <td>访问来源和热门页面</td>
            <td><span class="status pending">只看有限入口</span></td>
            <td>GitHub Traffic 可看最近访问趋势；不把它当作完整访客画像，不做跨站追踪或个人级路径分析。</td>
          </tr>
          <tr>
            <td>访客地理位置</td>
            <td><span class="status blocked">未采集</span></td>
            <td>地理位置在 GDPR 语境下属于可能识别个人的数据；美国部分州法也把精确地理位置作为更敏感的数据类别。当前不采集国家/地区、城市、精确坐标，也不保存明文 IP。</td>
          </tr>
          <tr>
            <td>未来若确实要启用</td>
            <td><span class="status pending">先评估</span></td>
            <td>优先选择 cookie-free、IP 匿名化、只输出聚合数据的方案；公开网页同步增加 Privacy note，说明统计目的、数据类型、保留时间和退出方式。</td>
          </tr>
        </tbody>
      </table>
      <div class="toolbar">
        <a class="button secondary" href="https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository" target="_blank" rel="noopener">GitHub Traffic 文档</a>
        <a class="button secondary" href="https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng" target="_blank" rel="noopener">GDPR 数据定义</a>
        <a class="button secondary" href="https://ico.org.uk/for-the-public/online/cookies/" target="_blank" rel="noopener">ICO Cookies 说明</a>
        <a class="button secondary" href="https://docs.github.com/en/actions/concepts/security/secrets" target="_blank" rel="noopener">GitHub Secrets 文档</a>
      </div>
    </section>

    <section>
      <h2>私密设置</h2>
      <table>
        <thead>
          <tr>
            <th>设置</th>
            <th>放在哪里</th>
            <th>公开风险</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>更新报告收件邮箱</td>
            <td>GitHub Actions secret：<code>SCHOLARLY_REPORT_EMAIL_TO</code></td>
            <td>不应写进 workflow、网页或仓库文件。</td>
          </tr>
          <tr>
            <td>SMTP 发信配置</td>
            <td><code>SMTP_HOST</code>、<code>SMTP_PORT</code>、<code>SMTP_USERNAME</code>、<code>SMTP_PASSWORD</code></td>
            <td>全部必须放在 secrets。</td>
          </tr>
          <tr>
            <td>analytics tracking ID</td>
            <td>若以后启用，再放到 Jekyll 配置或 GitHub variable</td>
            <td>tracking ID 通常不是密码，但会公开在网页源码里；隐私说明必须同步。</td>
          </tr>
        </tbody>
      </table>
      <div class="toolbar">
        <a class="button warning" href="https://github.com/FanCheng5640/fancheng5640.github.io/settings/secrets/actions" target="_blank" rel="noopener">编辑 Actions Secrets</a>
        <a class="button secondary" href="更新报告邮箱设置说明.txt">打开本地邮箱说明</a>
      </div>
    </section>

    <footer>
      生成时间：__GENERATED_AT__。本页面由 <code>scripts/open_admin_dashboard.ps1</code> 生成；如果页面内容旧，重新双击 <code>打开网站后台.bat</code>。
    </footer>
  </main>
</body>
</html>
'@

$html = $html.Replace("__GENERATED_AT__", $GeneratedAt)
Set-Content -LiteralPath $DashboardPath -Value $html -Encoding UTF8

Start-Process -FilePath $DashboardPath
