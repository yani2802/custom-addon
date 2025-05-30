import requests
import threading

url = "http://127.0.0.1:5000"

def update_inventory():
    data = {"barcode": "56730920", "quantity": -1}  # Reduce stock by 1
    response = requests.post(url, json=data)
    print(f"Response: {response.status_code} - {response.text}")

# Creating multiple threads to simulate concurrent users
threads = []
for _ in range(10):  # Simulating 10 users at once
    t = threading.Thread(target=update_inventory)
    t.start()
    threads.append(t)

# Wait for all threads to finish
for t in threads:
    t.join()
