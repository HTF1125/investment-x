import requests
import json

app_url = "http://127.0.0.1:8000"


def test_dashboard_pdf():
    print("Logging in...")
    r = requests.post(
        f"{app_url}/api/auth/login",
        data={"username": "admin@example.com", "password": "admin"},
    )
    if r.status_code != 200:
        print("Login failed, skipping test.")
        return
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    print("Testing PDF Export...")
    r = requests.post(
        f"{app_url}/api/custom/pdf",
        json={"items": [], "theme": "light"},
        headers=headers,
    )
    print(f"PDF Status: {r.status_code}")
    if r.status_code == 200:
        with open("test_dashboard.pdf", "wb") as f:
            f.write(r.content)
        print("Saved test_dashboard.pdf")

    print("Testing HTML Export...")
    r = requests.post(
        f"{app_url}/api/custom/html",
        json={"items": [], "theme": "dark"},
        headers=headers,
    )
    print(f"HTML Status: {r.status_code}")
    if r.status_code == 200:
        with open("test_dashboard.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print("Saved test_dashboard.html")


if __name__ == "__main__":
    test_dashboard_pdf()
