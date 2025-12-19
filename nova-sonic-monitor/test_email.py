#!/usr/bin/env python3
"""测试邮件发送功能"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

CONFIG_FILE = Path(__file__).parent / "config.json"

def main():
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    smtp_config = config["smtp"]

    msg = MIMEMultipart()
    msg["From"] = smtp_config["sender"]
    msg["To"] = ", ".join(smtp_config["recipients"])
    msg["Subject"] = "✅ [测试] Nova Sonic 监控邮件测试"

    body = f"""
==================================================
Nova Sonic 监控系统 - 邮件测试
==================================================

这是一封测试邮件，用于验证告警系统是否正常工作。

时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
服务器: nova-sonic.teague.live

如果你收到这封邮件，说明邮件告警配置正确！

==================================================
"""

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        print("正在连接 SMTP 服务器...")
        if smtp_config.get("use_ssl", False):
            server = smtplib.SMTP_SSL(smtp_config["server"], smtp_config["port"])
        else:
            server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
            server.starttls()

        print("正在登录...")
        server.login(smtp_config["username"], smtp_config["password"])

        print("正在发送邮件...")
        server.sendmail(
            smtp_config["sender"],
            smtp_config["recipients"],
            msg.as_string()
        )
        server.quit()
        print("✅ 测试邮件发送成功！请检查收件箱。")
    except Exception as e:
        print(f"❌ 邮件发送失败: {str(e)}")

if __name__ == "__main__":
    main()
