import urllib.request
import json
try:
    req = urllib.request.Request("http://127.0.0.1:8080/api/indicadores")
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        with open("/home/admin/drone_acuatico/test_api_resp.json", "w") as f:
            json.dump(data, f, indent=2)
except Exception as e:
    with open("/home/admin/drone_acuatico/test_api_resp.json", "w") as f:
        f.write(str(e))