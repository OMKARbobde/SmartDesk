import os
import requests


def main():
    base_url = "http://127.0.0.1:8000"
    password = os.environ.get("SMARTDESK_TEST_AI_PASSWORD")
    if not password:
        print("SMARTDESK_TEST_AI_PASSWORD is not set in the environment.")
        return

    session = requests.Session()

    # Get Django admin login page
    login_url = base_url + "/admin/login/"
    login_page = session.get(login_url)

    csrf_token = session.cookies.get("csrftoken")

    if not csrf_token:
        print("CSRF cookie not found!")
        return

    # Get admin credentials securely
    username = input("Enter Django username: ")

    # Login to Django
    login_response = session.post(
        login_url,
        data={
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": csrf_token,
            "next": "/admin/"
        },
        headers={
            "Referer": login_url,
            "X-CSRFToken": csrf_token
        }
    )

    # Verify login
    if "/admin/login/" in login_response.url:
        print("Login failed! Check your credentials.")
        return

    print("Django login successful!")

    # Call AI analysis API
    api_url = base_url + "/api/ai/analyze/1/"

    csrf_token = session.cookies.get("csrftoken")

    response = session.post(
        api_url,
        headers={
            "X-CSRFToken": csrf_token,
            "Referer": base_url + "/"
        }
    )

    print("\nStatus Code:", response.status_code)
    print("Response:", response.text)


if __name__ == "__main__":
    main()
