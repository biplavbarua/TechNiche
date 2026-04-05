import requests
import json
import time

url = "http://localhost:8000/api/analyze"
payload = {"idea": "I want to publish a book about a boy wizard."}
headers = {"Content-Type": "application/json"}

print("Waiting for server to be ready...")
for i in range(10):
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print("SUCCESS! API returned 200 OK")
            print("Response:", json.dumps(response.json(), indent=2)[:200], "...")
            break
        else:
            print(f"Server returned status code: {response.status_code}")
            print("Response:", response.text)
            break
    except Exception as e:
        print(f"Connection failed ({i+1}/10): {e}")
        time.sleep(2)
else:
    print("Failed to connect after 10 attempts.")
