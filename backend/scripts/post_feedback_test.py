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
    payload = {
        'name': 'UI Tester',
        'email': 'tester@example.com',
        'feedbackType': 'general',
        'rating': '5',
        'subject': 'Great app',
        'message': 'Testing feedback endpoint',
        'features': ['AI Recommendations','Dashboard'],
        'allowContact': False
    }
    post('/api/feedback', payload)
