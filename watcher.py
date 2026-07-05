import requests
import time
import os
import json

# --- Config: pulled from environment variables (set these in Render's dashboard) ---

COOKIE_STRING = os.environ["COOKIE_STRING"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "15"))

CHECK_URL = "https://www.coursehero.com/api/v1/tutor/next-question/"

# categorySubjects can be overridden via env var if you change your tutoring subjects
CATEGORY_SUBJECTS = os.environ.get(
    "CATEGORY_SUBJECTS",
    "8,308,13,14,15,61,138,257,820,46,62,86,105,229,624,743,894,969,124575053",
)

PAYLOAD = {
    "categorySubjects": CATEGORY_SUBJECTS,
    "excludeSkippedQuestions": True,
    "trackEndOfQuestionQueue": False,
}

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.coursehero.com/qa/expert/dashboard/",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
    ),
}


def load_cookies(cookie_string):
    """Parse a raw 'name=value; name2=value2' Cookie header into a cookie jar."""
    jar = requests.cookies.RequestsCookieJar()
    for part in cookie_string.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        jar.set(name.strip(), value.strip(), domain="www.coursehero.com", path="/")
    return jar


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print("Telegram send failed:", e, flush=True)


def looks_like_login_page(text):
    return "Email address" in text and "Log In" in text and "Forgot password" in text


def main():
    session = requests.Session()
    session.cookies = load_cookies(COOKIE_STRING)

    print(f"Watching CourseHero every {POLL_INTERVAL}s...", flush=True)
    send_telegram("✅ CourseHero watcher started on Render.")

    notified = False
    warned_expired = False

    while True:
        try:
            resp = session.post(CHECK_URL, headers=HEADERS, json=PAYLOAD, timeout=15)
            text = resp.text

            if looks_like_login_page(text):
                if not warned_expired:
                    send_telegram(
                        "⚠️ CourseHero session expired. Update COOKIE_STRING in "
                        "Render's environment variables with a fresh value."
                    )
                    warned_expired = True
                time.sleep(POLL_INTERVAL)
                continue
            warned_expired = False

            try:
                data = resp.json()
            except ValueError:
                data = None

            has_question = isinstance(data, list) and len(data) > 0

            if has_question and not notified:
                send_telegram("🔔 New CourseHero question available! Go accept it before it expires.")
                notified = True
            elif not has_question:
                notified = False

        except Exception as e:
            print("Check failed:", e, flush=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
