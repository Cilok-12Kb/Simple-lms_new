import requests

URL = "http://localhost:8000/api/courses/"

for i in range(1, 70):
    r = requests.get(URL)
    print(f"Request {i:3d}: HTTP {r.status_code}")
    if r.status_code == 429:
        print(f"  → THROTTLED! {r.json()}")