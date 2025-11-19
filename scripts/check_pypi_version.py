"""Check the latest version on PyPI."""
import urllib.request
import json

url = 'https://pypi.org/pypi/toontools/json'
try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
        print(f"Latest version on PyPI: {data['info']['version']}")
        print(f"Package URL: https://pypi.org/project/toontools/{data['info']['version']}/")
except Exception as e:
    print(f"Error checking PyPI: {e}")

