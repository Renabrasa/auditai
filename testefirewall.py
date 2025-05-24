import requests

headers = {
    "Authorization": "Bearer tgp_v1_T-MXgORSpaf-k-VtfjYX2rPh_B8-0XFMxw_igPS2Mvw",
    "Content-Type": "application/json"
}

data = {
    "model": "mistralai/Mixtral-8x7B-Instruct-v0.1"
,
    "messages": [{"role": "user", "content": "Diga olá"}],
    "temperature": 0.7,
    "max_tokens": 50
}

r = requests.post("https://api.together.xyz/inference", headers=headers, json=data)
print("Status:", r.status_code)
print("Resposta:", r.text)
