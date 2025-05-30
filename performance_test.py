import requests
import time

url = "http://127.0.0.1:5000/get_product?barcode=56730920"

# Run test 10 times
for i in range(10):
    start = time.time()
    response = requests.get(url)
    end = time.time()
    
    print(f"Test {i+1}: Response Time: {end - start:.4f} seconds")
