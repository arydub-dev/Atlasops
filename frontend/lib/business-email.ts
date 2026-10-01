const PERSONAL_DOMAINS = new Set(["gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "yahoo.co.in", "ymail.com", "rocketmail.com", "outlook.com", "hotmail.com", "hotmail.co.uk", "live.com", "msn.com", "icloud.com", "me.com", "mac.com", "aol.com", "proton.me", "protonmail.com", "pm.me", "hey.com", "mail.com", "gmx.com", "gmx.de", "gmx.net", "tutanota.com", "tuta.com", "tutamail.com", "fastmail.com", "zoho.com", "yandex.com", "yandex.ru", "mail.ru", "qq.com", "163.com", "126.com", "rediffmail.com", "mailinator.com", "guerrillamail.com", "10minutemail.com", "temp-mail.org"]);
export function isBusinessEmail(email: string): boolean {
 const domain = email.trim().toLowerCase().split("@").pop()?.replace(/\.$/, "") || "";
 return email.includes("@") && domain.includes(".") && !Array.from(PERSONAL_DOMAINS).some(item => domain === item || domain.endsWith(`.${item}`));
}
