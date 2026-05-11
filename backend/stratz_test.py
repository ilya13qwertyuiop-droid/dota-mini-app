import os
import requests

STRATZ_API_TOKEN = os.getenv("STRATZ_API_TOKEN")
assert STRATZ_API_TOKEN, "No STRATZ_API_TOKEN in env"

headers = {
    "Authorization": f"Bearer {STRATZ_API_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "STRATZ_API",
    "Accept": "application/json",
}

query = """
query TestConstants {
  constants {
    heroes {
      id
      name
    }
  }
}
"""

resp = requests.post(
    "https://api.stratz.com/graphql",
    headers=headers,
    json={"query": query, "variables": {}},
    timeout=15,
)

print("status:", resp.status_code)
print("body snippet:", resp.text[:300])

with open("stratz_403.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("saved to stratz_403.html")

