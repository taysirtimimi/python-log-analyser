import requests

def get_location(ip):
    response = requests.get(
        "https://ipinfo.io/" + ip + "/json",
        timeout=10
    )

    if response.status_code == 200:
        return response.json()

    return None
