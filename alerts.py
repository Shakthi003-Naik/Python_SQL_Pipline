"""
alerts.py — Format and dispatch anomaly alerts.

Currently outputs to:
  - Console (stdout)
  - Log file  (logs/pipeline.log)

Easy to extend: add email (smtplib), Slack webhook,
or Teams webhook by adding a new dispatch function below.
"""

import logging

logger = logging.getLogger(__name__)

# ANSI colour codes for console output
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"
_BOLD   = "\033[1m"


def _format_alert(anomaly: dict) -> str:
    direction = "ABOVE" if (
        anomaly.get("zscore") is not None and anomaly["zscore"] > 0
    ) else "BELOW"

    lines = [
        f"{_BOLD}{_RED}⚠  ANOMALY DETECTED — {anomaly['symbol']}{_RESET}",
        f"   Date        : {anomaly['trade_date']}",
        f"   Close price : ${anomaly['close_price']:,.4f}  ({direction} baseline)",
        f"   Z-score     : {anomaly['zscore']}  (threshold ±{_get_threshold()})",
        f"   IQR flag    : {'Yes' if anomaly['iqr_flag'] else 'No'}",
        f"   Baseline    : mean={anomaly['baseline_mean']}  std={anomaly['baseline_std']}",
        f"   Method      : {anomaly['anomaly_type']}",
    ]
    return "\n".join(lines)


def _get_threshold() -> float:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return float(os.getenv("ANOMALY_ZSCORE_THRESHOLD", 3.0))


def dispatch(anomalies: list[dict]) -> None:
    """
    Send alerts for each detected anomaly.
    Add extra channels (email, Slack) here as needed.
    """
    if not anomalies:
        logger.info("No anomalies to alert on.")
        return

    for anomaly in anomalies:
        # ── Console output ─────────────────────────────
        alert_text = _format_alert(anomaly)
        print(alert_text)

        # ── Structured log entry ───────────────────────
        logger.warning(
            "ANOMALY | symbol=%s | date=%s | close=%.4f | zscore=%s | type=%s",
            anomaly["symbol"],
            anomaly["trade_date"],
            anomaly["close_price"],
            anomaly.get("zscore"),
            anomaly["anomaly_type"],
        )

    print(f"\n{_CYAN}Total alerts dispatched: {len(anomalies)}{_RESET}\n")


# ── Extension point: Email ────────────────────────────────
# Uncomment and configure to enable email alerts.
#
# import smtplib
# from email.mime.text import MIMEText
#
# def send_email_alert(anomaly: dict) -> None:
#     msg = MIMEText(_format_alert(anomaly))
#     msg["Subject"] = f"[Pipeline Alert] {anomaly['symbol']} anomaly detected"
#     msg["From"]    = os.getenv("ALERT_FROM_EMAIL")
#     msg["To"]      = os.getenv("ALERT_TO_EMAIL")
#     with smtplib.SMTP(os.getenv("SMTP_HOST"), 587) as server:
#         server.starttls()
#         server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
#         server.send_message(msg)


# ── Extension point: Slack Webhook ───────────────────────
# import requests
#
# def send_slack_alert(anomaly: dict) -> None:
#     webhook_url = os.getenv("SLACK_WEBHOOK_URL")
#     payload = {"text": f":warning: *{anomaly['symbol']}* anomaly on {anomaly['trade_date']}"}
#     requests.post(webhook_url, json=payload, timeout=5)
