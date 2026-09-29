import time

import requests

BASE = 'http://127.0.0.1:5001'

def post(path, json_data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    r = requests.post(BASE + path, json=json_data, headers=headers, timeout=15)
    try:
        body = r.json()
    except Exception:
        body = r.text
    print(path, '→', r.status_code)
    print(body)
    return r

if __name__ == '__main__':
    ts = int(time.time())
    email = f'e2e+{ts}@example.com'
    print('Registering', email)
    try:
        r = post('/api/auth/register', {'name':'E2E User','email':email,'password':'E2Epass123!'})
    except Exception as e:
        print('REGISTER request failed:', e)
        raise SystemExit(1)

    token = None
    if r.status_code == 200:
        token = r.json().get('token')
        print('Got token')
    else:
        print('Register failed, trying login')
        r2 = post('/api/auth/login', {'email': email, 'password': 'E2Epass123!'})
        if r2.status_code == 200:
            token = r2.json().get('token')
            print('Logged in and got token')
        else:
            print('Register and login failed; aborting')
            raise SystemExit(1)

    # ai recommend
    post('/api/ai/recommend', {'profile':{'headline':'E2E test','skills':'py'}, 'goals':'get job'}, token=token)

    # analytics event
    post('/api/analytics/event', {'name':'e2e.test','metadata':{'ts':ts}}, token=token)

    print('E2E test complete')
