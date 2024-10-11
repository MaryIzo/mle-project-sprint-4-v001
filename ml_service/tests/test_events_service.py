import requests

events_store_url = "http://127.0.0.1:8020"

headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

user_id = 1337055
items_for_put = [53404, 33311009, 178529, 35505245, 795836] # из файла recommendations.ipynb
params_to_get = {"user_id": user_id, "k": 3}

# params={"user_id": 1291248, "k": 3}

for item in items_for_put:

    params = {"user_id": user_id, "item_id": item}

    resp = requests.post(events_store_url + "/put", headers=headers, params=params)
    if resp.status_code == 200:
        result = resp.json()
    else:
        result = None
        print(f"status code: {resp.status_code}")


resp = requests.post(events_store_url + "/get", 
                     headers=headers, 
                     params=params_to_get).json()
print(resp)
assert resp['events'] == [795836, 35505245, 178529], 'Incorrect answer in events test'