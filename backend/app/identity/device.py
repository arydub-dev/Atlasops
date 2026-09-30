"""Parse coarse device / browser labels from User-Agent strings."""
from __future__ import annotations


def device_label_from_ua(user_agent: str | None) -> str:
    if not user_agent:
        return "Unknown device"
    ua = user_agent.lower()

    if "ipad" in ua:
        device = "iPad"
    elif "iphone" in ua:
        device = "iPhone"
    elif "android" in ua and "mobile" in ua:
        device = "Android phone"
    elif "android" in ua:
        device = "Android tablet"
    elif "macintosh" in ua or "mac os" in ua:
        device = "Mac"
    elif "windows" in ua:
        device = "Windows PC"
    elif "linux" in ua:
        device = "Linux"
    else:
        device = "Device"

    if "edg/" in ua or "edgios" in ua:
        browser = "Edge"
    elif "chrome" in ua and "chromium" not in ua and "edg" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    else:
        browser = "Browser"

    return f"{browser} on {device}"
