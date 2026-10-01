"""Company-email policy; not proof of company ownership or verified identity."""
from fastapi import HTTPException

PERSONAL_EMAIL_DOMAINS = frozenset(['gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.co.uk', 'yahoo.co.in', 'ymail.com', 'rocketmail.com', 'outlook.com', 'hotmail.com', 'hotmail.co.uk', 'live.com', 'msn.com', 'icloud.com', 'me.com', 'mac.com', 'aol.com', 'proton.me', 'protonmail.com', 'pm.me', 'hey.com', 'mail.com', 'gmx.com', 'gmx.de', 'gmx.net', 'tutanota.com', 'tuta.com', 'tutamail.com', 'fastmail.com', 'zoho.com', 'yandex.com', 'yandex.ru', 'mail.ru', 'qq.com', '163.com', '126.com', 'rediffmail.com', 'mailinator.com', 'guerrillamail.com', '10minutemail.com', 'temp-mail.org'])
MESSAGE = "Use your company email address, such as you@company.com. Personal and disposable email providers are not accepted for signup."


def require_business_email(email: str) -> None:
    domain = email.strip().lower().rsplit("@", 1)[-1].rstrip(".")
    if "@" not in email or "." not in domain or any(domain == item or domain.endswith("." + item) for item in PERSONAL_EMAIL_DOMAINS):
        raise HTTPException(status_code=400, detail=MESSAGE)
