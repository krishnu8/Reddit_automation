"""
Dashboard HTML templates — premium dark UI with glassmorphism.
"""

def get_base_css() -> str:
    return """
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
    --bg: #06060f; --surface: #0d0d1a; --card: #12121f;
    --border: rgba(99,102,241,0.15); --border-hover: rgba(99,102,241,0.35);
    --text: #e2e8f0; --text-muted: #64748b; --text-dim: #94a3b8;
    --accent: #818cf8; --accent2: #a78bfa; --accent3: #c084fc;
    --green: #4ade80; --red: #f87171; --yellow: #facc15; --blue: #60a5fa;
    --font: 'Inter', system-ui, sans-serif;
}
body { font-family: var(--font); background: var(--bg); color: var(--text); min-height: 100vh; }

.header {
    background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #1a1a2e 100%);
    padding: 20px 36px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
}
.header h1 { font-size: 20px; font-weight: 700;
    background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent3));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.header-controls { display: flex; gap: 14px; align-items: center; font-weight: 600; font-size: 13px; }

.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 5px; }
.dot.on { background: var(--green); box-shadow: 0 0 8px #4ade8088; }
.dot.off { background: var(--red); box-shadow: 0 0 8px #f8717188; }

.badge { padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
.badge-auto { background: rgba(99,102,241,0.2); color: var(--accent); border: 1px solid rgba(99,102,241,0.4); }
.badge-manual { background: rgba(250,204,21,0.15); color: var(--yellow); border: 1px solid rgba(250,204,21,0.3); }

.container { padding: 24px 36px; max-width: 1500px; margin: 0 auto; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 24px; }
.stat-card {
    background: linear-gradient(145deg, #1e1e2e, #16162a);
    border: 1px solid var(--border); border-radius: 12px; padding: 18px; text-align: center;
    transition: transform 0.2s, border-color 0.2s;
}
.stat-card:hover { transform: translateY(-2px); border-color: var(--border-hover); }
.stat-card .number { font-size: 32px; font-weight: 700;
    background: linear-gradient(90deg, var(--accent), var(--accent3));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.stat-card .label { font-size: 12px; color: var(--text-dim); margin-top: 4px;
    text-transform: uppercase; letter-spacing: 0.5px; }

.tabs { display: flex; gap: 0; margin-bottom: 20px; border-bottom: 2px solid var(--surface); overflow-x: auto; }
.tab { padding: 10px 20px; cursor: pointer; font-weight: 600; font-size: 13px;
    color: var(--text-muted); border-bottom: 2px solid transparent;
    margin-bottom: -2px; transition: all 0.2s; white-space: nowrap; }
.tab:hover { color: #a5b4fc; }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-content { display: none; }
.tab-content.active { display: block; }

table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; padding: 10px 12px; background: var(--surface); color: var(--text-dim);
    font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1; }
td { padding: 8px 12px; border-bottom: 1px solid #1a1a2a; vertical-align: middle; }
tr:hover { background: rgba(99,102,241,0.05); }

.table-wrap { background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; overflow: hidden; max-height: 550px; overflow-y: auto; }

.btn { padding: 5px 10px; border-radius: 8px; font-size: 11px; font-weight: 600;
    cursor: pointer; border: 1px solid var(--border); transition: all 0.2s;
    background: var(--surface); color: var(--text); text-decoration: none; display: inline-block; }
.btn:hover { border-color: var(--accent); background: rgba(99,102,241,0.1); }
.btn-green { background: rgba(74,222,128,0.15); color: var(--green); border-color: rgba(74,222,128,0.3); }
.btn-green:hover { background: rgba(74,222,128,0.25); }
.btn-red { background: rgba(248,113,113,0.15); color: var(--red); border-color: rgba(248,113,113,0.3); }
.btn-red:hover { background: rgba(248,113,113,0.25); }
.btn-blue { background: rgba(96,165,250,0.15); color: var(--blue); border-color: rgba(96,165,250,0.3); }
.btn-blue:hover { background: rgba(96,165,250,0.25); }
.btn-purple { background: rgba(167,139,250,0.15); color: var(--accent2); border-color: rgba(167,139,250,0.3); }
.btn-purple:hover { background: rgba(167,139,250,0.25); }
.btn-yellow { background: rgba(250,204,21,0.15); color: var(--yellow); border-color: rgba(250,204,21,0.3); }
.btn-yellow:hover { background: rgba(250,204,21,0.25); }

.action-group { display: flex; gap: 4px; flex-wrap: wrap; }

.log-box { background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; max-height: 400px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.log-entry { padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.log-time { color: var(--text-dim); margin-right: 8px; }
.log-ok { color: var(--green); } .log-err { color: var(--red); }
.log-warn { color: var(--yellow); } .log-info { color: var(--blue); }

.controls-bar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }

.quality-bar { width: 50px; height: 6px; border-radius: 3px; background: #1a1a2e; display: inline-block; vertical-align: middle; margin-left: 6px; }
.quality-fill { height: 100%; border-radius: 3px; }

.detail-row { font-size: 10px; color: var(--text-dim); margin-top: 2px; }

@media (max-width: 768px) {
    .container { padding: 12px; }
    .header { padding: 12px; }
    .stats { grid-template-columns: repeat(2, 1fr); }
}
"""


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_dashboard(
    leads: list[dict], stats: dict, conversations: list[dict],
    agent_running: bool, ollama_ok: bool, auto_send: bool,
    logs: list[dict], outreach_stats: dict,
) -> str:
    lead_rows = ""
    for lead in leads[:80]:
        q = lead.get("lead_quality", 0)
        qc = "var(--green)" if q >= 60 else "var(--yellow)" if q >= 40 else "var(--red)"
        status = lead.get("status", "")
        sb = {"new": "🆕", "analyzed": "🔍", "replied": "✅"}.get(status, "⏳")
        approved = lead.get("approved", 0)

        # Build action buttons based on status
        actions = []
        if status == "analyzed" and not approved:
            actions.append(f'<a class="btn btn-green" href="/api/leads/{lead["id"]}/approve">✓ Approve</a>')
            actions.append(f'<a class="btn btn-blue" href="/api/leads/{lead["id"]}/dm">📨 DM Now</a>')
        elif status == "analyzed" and approved:
            actions.append(f'<a class="btn btn-blue" href="/api/leads/{lead["id"]}/dm">📨 DM Now</a>')
            actions.append('<span style="color:var(--green);font-size:10px">✓ Approved</span>')
        elif status == "replied":
            actions.append(f'<a class="btn btn-yellow" href="/api/leads/{lead["id"]}/reinstate">🔄 Reinstate</a>')
        elif status == "new":
            actions.append('<span style="color:var(--text-dim);font-size:10px">⏳ Pending analysis</span>')

        action_html = '<div class="action-group">' + ''.join(actions) + '</div>'

        # Quality bar visual
        bar_color = "#4ade80" if q >= 60 else "#facc15" if q >= 40 else "#f87171"
        quality_html = f'<span style="color:{qc};font-weight:700">{q}</span><div class="quality-bar"><div class="quality-fill" style="width:{q}%;background:{bar_color}"></div></div>'

        # Extra details row
        biz = lead.get('business_intent', 'N/A')
        hiring = lead.get('hiring_probability', 'N/A')
        tech = lead.get('technical_complexity', 'N/A')
        budget = lead.get('budget_estimate', 'N/A')
        details = f'<div class="detail-row">💼 {_escape(str(biz))} · 🎯 Hiring: {_escape(str(hiring))} · 🔧 {_escape(str(tech))} · 💰 {_escape(str(budget))}</div>'

        title_text = _escape(lead.get('title', ''))[:50]
        username = _escape(lead.get('username', ''))
        subreddit = _escape(lead.get('subreddit', ''))
        urgency = _escape(lead.get('urgency', ''))
        project = _escape(lead.get('project_type', ''))
        post_url = lead.get('post_url', '#')

        lead_rows += f"""<tr>
            <td>{lead.get('id','')}</td>
            <td><a href="{post_url}" target="_blank" style="color:var(--blue)">{title_text}</a>{details}</td>
            <td>u/{username}</td>
            <td>r/{subreddit}</td>
            <td>{quality_html}</td>
            <td>{urgency}</td>
            <td>{project}</td>
            <td>{sb} {status}</td>
            <td>{action_html}</td>
        </tr>"""

    conv_rows = ""
    for conv in conversations[:30]:
        conv_rows += f"""<tr>
            <td>{conv.get('id','')}</td>
            <td>u/{_escape(conv.get('username',''))}</td>
            <td>{_escape(conv.get('project_details',''))[:35]}</td>
            <td>{conv.get('budget','N/A')}</td>
            <td>{conv.get('negotiation_stage','')}</td>
            <td>{conv.get('status','')}</td>
            <td>{conv.get('last_message_at','N/A')}</td>
            <td><a class="btn btn-blue" href="/api/conversations/{conv.get('id','')}/messages" target="_blank">View</a></td>
        </tr>"""

    log_entries = ""
    for log in logs[-40:]:
        lc = {"OK":"log-ok","ERR":"log-err","WARN":"log-warn"}.get(log.get("level",""), "log-info")
        log_entries += f'<div class="log-entry"><span class="log-time">{log.get("time","")}</span><span class="{lc}">{_escape(log.get("message",""))}</span></div>'

    total = sum(stats.values()) if stats else 0
    mode_badge = '<span class="badge badge-auto">Auto-Send</span>' if auto_send else '<span class="badge badge-manual">Manual</span>'
    o_total = outreach_stats.get("total", 0)
    o_ok = outreach_stats.get("successful", 0)
    o_fail = outreach_stats.get("failed", 0)

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Reddit AI Agent Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>{get_base_css()}</style>
</head><body>
<div class="header">
    <h1>🤖 Reddit AI Agent {mode_badge}</h1>
    <div class="header-controls">
        <span><span class="dot {'on' if ollama_ok else 'off'}"></span>Ollama {'✓' if ollama_ok else '✗'}</span>
        <span><span class="dot {'on' if agent_running else 'off'}"></span>Agent {'Running' if agent_running else 'Off'}</span>
    </div>
</div>
<div class="container">
    <div class="controls-bar">
        <a class="btn btn-green" href="/api/toggle-auto-send">{'🔴 Disable' if auto_send else '🟢 Enable'} Auto-Send</a>
        <a class="btn" href="/api/trigger-scan">🔍 Trigger Scan</a>
        <a class="btn btn-blue" href="/api/send-approved">📨 Send Approved</a>
        <a class="btn btn-red" href="/api/{'pause' if agent_running else 'resume'}-agent">{'⏸️ Pause' if agent_running else '▶️ Resume'}</a>
    </div>
    <div class="stats">
        <div class="stat-card"><div class="number">{total}</div><div class="label">Total Leads</div></div>
        <div class="stat-card"><div class="number">{stats.get('new',0)}</div><div class="label">New</div></div>
        <div class="stat-card"><div class="number">{stats.get('analyzed',0)}</div><div class="label">Analyzed</div></div>
        <div class="stat-card"><div class="number">{stats.get('replied',0)}</div><div class="label">Messaged</div></div>
        <div class="stat-card"><div class="number">{len(conversations)}</div><div class="label">Conversations</div></div>
        <div class="stat-card"><div class="number">{o_ok}/{o_total}</div><div class="label">Outreach OK</div></div>
    </div>
    <div class="tabs">
        <div class="tab active" onclick="switchTab('leads')">📋 Leads ({total})</div>
        <div class="tab" onclick="switchTab('conversations')">💬 Conversations ({len(conversations)})</div>
        <div class="tab" onclick="switchTab('logs')">📜 Live Logs</div>
    </div>
    <div id="tab-leads" class="tab-content active"><div class="table-wrap"><table>
        <thead><tr><th>ID</th><th>Title & Details</th><th>User</th><th>Source</th><th>Quality</th><th>Urgency</th><th>Type</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>{lead_rows or '<tr><td colspan="9" style="text-align:center;color:var(--text-muted);padding:40px">No leads yet — agent is scanning…</td></tr>'}</tbody>
    </table></div></div>
    <div id="tab-conversations" class="tab-content"><div class="table-wrap"><table>
        <thead><tr><th>ID</th><th>User</th><th>Project</th><th>Budget</th><th>Stage</th><th>Status</th><th>Last Msg</th><th>View</th></tr></thead>
        <tbody>{conv_rows or '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:40px">No conversations yet</td></tr>'}</tbody>
    </table></div></div>
    <div id="tab-logs" class="tab-content"><div class="log-box">{log_entries or '<div class="log-entry log-info">Waiting for agent activity…</div>'}</div></div>
</div>
<script>
function switchTab(n){{document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));
document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
document.getElementById('tab-'+n).classList.add('active');event.target.classList.add('active');}}
setTimeout(()=>location.reload(),30000);
</script></body></html>"""
