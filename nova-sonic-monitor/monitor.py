#!/usr/bin/env python3
"""
Nova Sonic Service Monitor
监控服务状态并发送邮件告警
"""

import subprocess
import smtplib
import json
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error
import ssl

# 配置文件路径
CONFIG_FILE = Path(__file__).parent / "config.json"
STATE_FILE = Path(__file__).parent / "state.json"

def load_config():
    """加载配置"""
    if not CONFIG_FILE.exists():
        print(f"错误: 配置文件不存在 {CONFIG_FILE}")
        print("请复制 config.example.json 为 config.json 并填写配置")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return json.load(f)

def load_state():
    """加载状态（用于避免重复告警）"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_alert": None, "consecutive_failures": 0, "is_down": False}

def save_state(state):
    """保存状态"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def check_systemd_service(service_name="nova-sonic"):
    """检查 systemd 服务状态"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True, text=True, timeout=10
        )
        is_active = result.stdout.strip() == "active"
        return {
            "check": "systemd_service",
            "name": service_name,
            "status": "ok" if is_active else "fail",
            "message": f"服务状态: {result.stdout.strip()}"
        }
    except Exception as e:
        return {
            "check": "systemd_service",
            "name": service_name,
            "status": "fail",
            "message": f"检查失败: {str(e)}"
        }

def check_local_port(port=8100, host="127.0.0.1"):
    """检查本地端口"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        is_open = result == 0
        return {
            "check": "local_port",
            "port": port,
            "status": "ok" if is_open else "fail",
            "message": f"端口 {port} {'开放' if is_open else '未开放'}"
        }
    except Exception as e:
        return {
            "check": "local_port",
            "port": port,
            "status": "fail",
            "message": f"检查失败: {str(e)}"
        }

def check_external_url(url, timeout=15):
    """检查外部 URL 可达性"""
    try:
        # 创建 SSL context
        ctx = ssl.create_default_context()

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Nova-Sonic-Monitor/1.0"}
        )

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            status_code = response.getcode()
            # 2xx 和 3xx 都算成功
            is_ok = 200 <= status_code < 400
            return {
                "check": "external_url",
                "url": url,
                "status": "ok" if is_ok else "fail",
                "http_code": status_code,
                "message": f"HTTP {status_code}"
            }
    except urllib.error.HTTPError as e:
        return {
            "check": "external_url",
            "url": url,
            "status": "fail",
            "http_code": e.code,
            "message": f"HTTP {e.code}: {e.reason}"
        }
    except urllib.error.URLError as e:
        return {
            "check": "external_url",
            "url": url,
            "status": "fail",
            "http_code": None,
            "message": f"连接失败: {str(e.reason)}"
        }
    except Exception as e:
        return {
            "check": "external_url",
            "url": url,
            "status": "fail",
            "http_code": None,
            "message": f"检查失败: {str(e)}"
        }

def send_email(config, subject, body):
    """发送邮件告警"""
    smtp_config = config["smtp"]

    msg = MIMEMultipart()
    msg["From"] = smtp_config["sender"]
    msg["To"] = ", ".join(smtp_config["recipients"])
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        if smtp_config.get("use_ssl", False):
            server = smtplib.SMTP_SSL(smtp_config["server"], smtp_config["port"])
        else:
            server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
            server.starttls()

        server.login(smtp_config["username"], smtp_config["password"])
        server.sendmail(
            smtp_config["sender"],
            smtp_config["recipients"],
            msg.as_string()
        )
        server.quit()
        print(f"[{datetime.now()}] 邮件发送成功")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] 邮件发送失败: {str(e)}")
        return False

def run_checks(config):
    """运行所有检查"""
    results = []

    # 1. 检查 systemd 服务
    results.append(check_systemd_service(config.get("service_name", "nova-sonic")))

    # 2. 检查本地端口
    results.append(check_local_port(config.get("local_port", 8100)))

    # 3. 检查外部 URL
    if config.get("external_url"):
        results.append(check_external_url(config["external_url"]))

    return results

def format_alert_message(results, is_recovery=False):
    """格式化告警消息"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if is_recovery:
        lines = [
            "=" * 50,
            "✅ Nova Sonic 服务已恢复",
            "=" * 50,
            f"时间: {now}",
            "",
            "检查结果:",
        ]
    else:
        lines = [
            "=" * 50,
            "🚨 Nova Sonic 服务异常告警",
            "=" * 50,
            f"时间: {now}",
            "",
            "检查结果:",
        ]

    for r in results:
        status_icon = "✅" if r["status"] == "ok" else "❌"
        lines.append(f"  {status_icon} [{r['check']}] {r['message']}")

    lines.extend([
        "",
        "服务器: nova-sonic.teague.live",
        "=" * 50,
    ])

    return "\n".join(lines)

def main():
    config = load_config()
    state = load_state()

    # 运行检查
    results = run_checks(config)

    # 判断是否有失败
    has_failure = any(r["status"] == "fail" for r in results)

    # 打印结果
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now}] 检查结果:")
    for r in results:
        status_icon = "✅" if r["status"] == "ok" else "❌"
        print(f"  {status_icon} [{r['check']}] {r['message']}")

    # 告警逻辑
    alert_threshold = config.get("alert_threshold", 2)  # 连续失败多少次才告警

    if has_failure:
        state["consecutive_failures"] += 1
        print(f"  ⚠️  连续失败次数: {state['consecutive_failures']}")

        # 达到阈值且之前不是 down 状态，发送告警
        if state["consecutive_failures"] >= alert_threshold and not state["is_down"]:
            print("  📧 发送故障告警邮件...")
            subject = "🚨 [告警] Nova Sonic 服务异常"
            body = format_alert_message(results, is_recovery=False)
            if send_email(config, subject, body):
                state["is_down"] = True
                state["last_alert"] = now
    else:
        # 如果之前是 down 状态，现在恢复了，发送恢复通知
        if state["is_down"]:
            print("  📧 发送恢复通知邮件...")
            subject = "✅ [恢复] Nova Sonic 服务已恢复"
            body = format_alert_message(results, is_recovery=True)
            send_email(config, subject, body)

        state["consecutive_failures"] = 0
        state["is_down"] = False

    save_state(state)

    # 返回状态码
    sys.exit(1 if has_failure else 0)

if __name__ == "__main__":
    main()
