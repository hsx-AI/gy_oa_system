import imaplib
import email
import re
from email.header import decode_header


EMAIL_ACCOUNT = "hsx@hec-china.com"
AUTH_CODE = "pX#41bF$u2JFdn#S"   # 不是网页登录密码
IMAP_SERVER = "imap.qiye.163.com"
IMAP_PORT = 993


def decode_mime_words(text):
    """解码邮件主题、发件人等 MIME 编码内容"""
    if not text:
        return ""
    result = []
    for part, charset in decode_header(text):
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="ignore"))
            except Exception:
                result.append(part.decode("utf-8", errors="ignore"))
        else:
            result.append(part)
    return "".join(result)


def extract_flags(fetch_response):
    """从 FETCH 返回中提取 FLAGS"""
    flags_text = ""
    for item in fetch_response:
        if isinstance(item, tuple):
            raw = item[0]
        else:
            raw = item

        if isinstance(raw, bytes):
            s = raw.decode("utf-8", errors="ignore")
            if "FLAGS" in s:
                flags_text += s + " "

    match = re.search(r"FLAGS \((.*?)\)", flags_text)
    if match:
        return match.group(1)
    return ""


def fetch_mail_info(imap, mail_id):
    """读取邮件的主题、发件人、日期和 FLAGS"""
    status, data = imap.fetch(
        mail_id,
        "(FLAGS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])"
    )

    if status != "OK":
        return None

    flags = extract_flags(data)

    header_bytes = b""
    for item in data:
        if isinstance(item, tuple):
            header_bytes += item[1]

    msg = email.message_from_bytes(header_bytes)

    subject = decode_mime_words(msg.get("Subject"))
    sender = decode_mime_words(msg.get("From"))
    date = msg.get("Date", "")

    return {
        "id": mail_id.decode() if isinstance(mail_id, bytes) else str(mail_id),
        "subject": subject,
        "from": sender,
        "date": date,
        "flags": flags
    }


def print_mail_list(imap, mail_ids, title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    if not mail_ids:
        print("没有查到邮件")
        return

    for mail_id in mail_ids:
        info = fetch_mail_info(imap, mail_id)
        if not info:
            continue

        print(f"ID: {info['id']}")
        print(f"主题: {info['subject']}")
        print(f"发件人: {info['from']}")
        print(f"日期: {info['date']}")
        print(f"FLAGS: {info['flags']}")
        print("-" * 80)


def safe_search(imap, *criteria):
    """安全搜索，避免某些 KEYWORD 不支持时报错中断"""
    try:
        status, data = imap.search(None, *criteria)
        if status == "OK" and data and data[0]:
            return data[0].split()
        return []
    except Exception as e:
        print(f"搜索条件 {criteria} 失败: {e}")
        return []


def main():
    imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    imap.login(EMAIL_ACCOUNT, AUTH_CODE)

    # 先只测试收件箱
    imap.select("INBOX", readonly=True)

    # 1. 测试标准红旗/星标标记
    flagged_ids = safe_search(imap, "FLAGGED")
    print_mail_list(imap, flagged_ids, "一、IMAP 标准 FLAGGED / 红旗 / 星标 邮件")

    # 2. 测试一些可能的待办关键词
    # 注意：这些只是候选，是否存在取决于 163 是否同步
    candidate_keywords = [
        "TODO",
        "$TODO",
        "$Todo",
        "$todo",
        "ToDo",
        "$Important",
        "$Label1",
        "$label1"
    ]

    for kw in candidate_keywords:
        ids = safe_search(imap, "KEYWORD", kw)
        if ids:
            print_mail_list(imap, ids, f"二、查到 KEYWORD = {kw} 的邮件")

    # 3. 打印最近 30 封邮件的 FLAGS
    # 你可以手动把其中一封设为“待办”，然后看 FLAGS 是否发生变化
    all_ids = safe_search(imap, "ALL")
    recent_ids = all_ids[-30:] if len(all_ids) > 30 else all_ids

    print_mail_list(imap, recent_ids, "三、最近 30 封邮件的 FLAGS，用于人工观察待办标记")

    imap.logout()


if __name__ == "__main__":
    main()