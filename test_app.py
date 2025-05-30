from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "Flask server is working!",
        "status": "success"
    })

@app.route('/test')
def test():
    return jsonify({
        "message": "Test endpoint working",
        "endpoints": ["/", "/test", "/scan/nfc"]
    })

@app.route('/scan/nfc', methods=['POST'])
def scan_nfc():
    return jsonify({
        "message": "NFC scan endpoint working!",
        "status": "success"
    })

if __name__ == '__main__':
    print("Starting test Flask server...")
    app.run(debug=True, host='127.0.0.1', port=5000)
