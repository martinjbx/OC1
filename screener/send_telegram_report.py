#!/usr/bin/env python3
"""
Generate and send Telegram report from JSON screener output.
Called by GitHub Actions after the screener runs.
Usage: python send_telegram_report.py
Env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import json
import os
import requests
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "dashboard" / "data"


def load_json(filename):
    path = DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def format_report(minervini, structure, exit_alerts):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = []

    lines.append(f"📊 *Daily Screener — {today}*")
    lines.append("")

    # ── Minervini candidates ──────────────────────────
    top = minervini.get("top_candidates", [])
    all_8 = [c for c in top if c.get("all_criteria_met")]
    seven_plus = [c for c in top if not c.get("all_criteria_met") and c.get("criteria_passed", 0) >= 7]

    lines.append(f"*Minervini SEPA* ({minervini.get('total_scanned', 0)} scanned)")
    if all_8:
        lines.append(f"✅ *All 8 criteria ({len(all_8)}):*")
        for c in all_8[:10]:
            lines.append(f"  `{c['ticker']}` ${c['price']} | RS {c['rs_rating']} | {c['pct_from_high']:+.1f}% from high")
    if seven_plus:
        lines.append(f"🔶 *7/8 criteria ({len(seven_plus)}):*")
        for c in seven_plus[:8]:
            lines.append(f"  `{c['ticker']}` ${c['price']} | RS {c['rs_rating']}")
    if not all_8 and not seven_plus:
        lines.append("  No candidates today")

    lines.append("")

    # ── Structure signals ─────────────────────────────
    sigs = structure.get("signals", [])
    if sigs:
        lines.append(f"*Structure (SMMA)* — {len(sigs)} signal(s)")
        for s in sigs[:6]:
            vs = "📈" if s.get("volume_surge") else ""
            lines.append(f"  `{s['ticker']}` ${s['price']:.2f} RSI {s.get('rsi', 0):.0f} {vs}")
    else:
        lines.append("*Structure (SMMA)* — No signals")

    lines.append("")

    # ── Exit alerts ───────────────────────────────────
    strong = exit_alerts.get("strong_exits", [])
    weak   = exit_alerts.get("weak_exits", [])
    below  = exit_alerts.get("below_ma50_lingering", [])
    watchlist_size = exit_alerts.get("watchlist_size", 0)

    lines.append(f"*Exit Monitor* (watchlist: {watchlist_size})")
    if strong:
        lines.append(f"🔴 *SELL signals ({len(strong)}) — crossed MA50 on high volume:*")
        for r in strong:
            pnl = f" | P&L {r['pnl_pct']:+.1f}%" if r.get("pnl_pct") is not None else ""
            lines.append(f"  `{r['ticker']}` ${r['current_price']} | {r['pct_vs_ma50']:+.1f}% vs MA50 | vol {r['vol_ratio']}×{pnl}")
    if weak:
        lines.append(f"🟡 *Caution ({len(weak)}) — crossed MA50, normal volume:*")
        for r in weak[:5]:
            lines.append(f"  `{r['ticker']}` ${r['current_price']} | {r['pct_vs_ma50']:+.1f}% vs MA50")
    if below:
        lines.append(f"🟠 *Monitoring below MA50 ({len(below)}):*")
        for r in below[:5]:
            lines.append(f"  `{r['ticker']}` {r['pct_vs_ma50']:+.1f}% vs MA50")
    if not strong and not weak and not below:
        lines.append("  ✅ All positions holding above MA50")

    # ── Take-profit alerts ────────────────────────────
    climactic = exit_alerts.get("climactic_sells", [])
    partial   = exit_alerts.get("partial_profits", [])
    extended  = exit_alerts.get("extended_watch", [])

    if climactic or partial or extended:
        lines.append("")
        lines.append("*Take-Profit Alerts*")
        if climactic:
            lines.append(f"🚀 *Climactic — sell into strength ({len(climactic)}):*")
            for r in climactic:
                lines.append(f"  `{r['ticker']}` ${r['current_price']} | +{r['pct_above_ma50']:.1f}% vs MA50 | {r['wide_up_days']} wide up days")
        if partial:
            lines.append(f"💰 *Take partial profits ({len(partial)}):*")
            for r in partial:
                gain = f" | gain {r['gain_pct']:+.1f}%" if r.get('gain_pct') is not None else ""
                lines.append(f"  `{r['ticker']}` ${r['current_price']} | +{r['pct_above_ma50']:.1f}% vs MA50{gain}")
        if extended:
            lines.append(f"⚠️ *Extended, watch closely ({len(extended)}):*")
            for r in extended[:5]:
                lines.append(f"  `{r['ticker']}` +{r['pct_above_ma50']:.1f}% vs MA50")

    return "\n".join(lines)


def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Telegram max message length is 4096
    if len(text) > 4000:
        text = text[:3990] + "\n…_(truncated)_"
    r = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }, timeout=15)
    return r.status_code, r.json()


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        raise SystemExit(1)

    minervini  = load_json("minervini_latest.json")
    structure  = load_json("structure_latest.json")
    exit_alerts = load_json("exit_alerts.json")

    report = format_report(minervini, structure, exit_alerts)
    print("=== TELEGRAM REPORT ===")
    print(report)
    print("=======================")

    status, resp = send_telegram(token, chat_id, report)
    if status == 200 and resp.get("ok"):
        print("✅ Telegram message sent")
    else:
        print(f"❌ Send failed: {status} — {resp}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
