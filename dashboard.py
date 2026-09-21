import os
import time
from functools import wraps

import httpx
from flask import Flask, flash, redirect, render_template, request, session, url_for

from config import BOT_TOKEN, DASHBOARD_PASSWORD, FLASK_SECRET_KEY
import storage

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
BROADCAST_DELAY = 0.05


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "كلمة المرور غير صحيحة"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    subscribers = storage.get_all_subscribers()
    return render_template("dashboard.html", subscribers=subscribers, count=len(subscribers))


@app.route("/broadcast", methods=["POST"])
@login_required
def broadcast():
    text = request.form.get("message", "").strip()
    if not text:
        flash("الرسالة فارغة، لم يتم الإرسال.")
        return redirect(url_for("dashboard"))

    subscriber_ids = storage.get_all_subscriber_ids()
    sent, failed = 0, 0

    with httpx.Client(timeout=10) as client:
        for chat_id in subscriber_ids:
            try:
                resp = client.post(
                    f"{TELEGRAM_API}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                )
                if resp.status_code == 200:
                    sent += 1
                else:
                    failed += 1
                    if resp.json().get("error_code") == 403:
                        storage.remove_subscriber(chat_id)
            except httpx.HTTPError:
                failed += 1
            time.sleep(BROADCAST_DELAY)

    flash(f"تم الإرسال إلى {sent} مشترك، وفشل الإرسال إلى {failed}.")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
