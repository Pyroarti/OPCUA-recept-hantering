import requests

url = 'https://localhost:8001/sv/001.1/api/v1/Manufacturing/ManufacturingPickingLists'

headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers, verify=False) # Ändra sedan till verify=path till certifikat

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
