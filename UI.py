from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/trigger', methods=['POST'])
def trigger_operations():
    data = request.json
    # Process the data and trigger backend operations
    # Example: call get_ontap_details function
    ontap_details = get_ontap_details(data['vm_details'], data['datastore_details'])
    return jsonify(ontap_details)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)