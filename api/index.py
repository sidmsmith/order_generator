# api/index.py
from flask import Flask, request, jsonify, send_from_directory
import json
import os
import requests
from requests.auth import HTTPBasicAuth
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# === SECURE CONFIG (from Vercel Environment Variables) ===
AUTH_HOST = "salep-auth.sce.manh.com"
API_HOST = "salep.sce.manh.com"
USERNAME_BASE = "sdtadmin@"
PASSWORD = os.getenv("MANHATTAN_PASSWORD")
CLIENT_ID = "omnicomponent.1.0.0"
CLIENT_SECRET = os.getenv("MANHATTAN_SECRET")

# Critical: Fail fast if secrets missing
if not PASSWORD or not CLIENT_SECRET:
    raise Exception("Missing MANHATTAN_PASSWORD or MANHATTAN_SECRET environment variables")

# === HELPERS ===
def get_manhattan_token(org):
    url = f"https://{AUTH_HOST}/oauth/token"
    username = f"{USERNAME_BASE}{org.lower()}"
    data = {
        "grant_type": "password",
        "username": username,
        "password": PASSWORD
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth = HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    try:
        r = requests.post(url, data=data, headers=headers, auth=auth, timeout=60, verify=False)
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception as e:
        print(f"[AUTH] Error: {e}")
    return None

def log_api_call(endpoint, method, url, headers=None, payload=None, response=None, status_code=None):
    """Detailed logging for API calls"""
    print("=" * 80)
    print(f"[API_CALL] {method} {endpoint}")
    print("=" * 80)
    print(f"[API_CALL] URL: {url}")
    if headers:
        # Redact authorization token
        log_headers = headers.copy()
        if 'Authorization' in log_headers:
            log_headers['Authorization'] = 'Bearer [REDACTED]'
        print(f"[API_CALL] Headers: {json.dumps(log_headers, indent=2)}")
    if payload:
        print(f"[API_CALL] Payload: {json.dumps(payload, indent=2)}")
    if status_code:
        print(f"[API_CALL] Response Status: {status_code}")
    if response:
        # Limit response logging to first 2000 chars to avoid huge logs
        response_str = json.dumps(response, indent=2) if isinstance(response, dict) else str(response)
        if len(response_str) > 2000:
            response_str = response_str[:2000] + "... [TRUNCATED]"
        print(f"[API_CALL] Response: {response_str}")
    print("=" * 80)

# === API ROUTES ===
@app.route('/api/app_opened', methods=['POST'])
def app_opened():
    print("[APP] Order Generator opened")
    return jsonify({"success": True})

@app.route('/api/auth', methods=['POST'])
def auth():
    org = request.json.get('org', '').strip()
    if not org:
        return jsonify({"success": False, "error": "ORG required"})
    
    print(f"[AUTH] Authenticating for ORG: {org}")
    token = get_manhattan_token(org)
    if token:
        print(f"[AUTH] Success for ORG: {org}")
        return jsonify({"success": True, "token": token})
    
    print(f"[AUTH] Failed for ORG: {org}")
    return jsonify({"success": False, "error": "Auth failed"})

@app.route('/api/find_order', methods=['POST'])
def find_order():
    """Find an order by OrderId using the extended order API"""
    data = request.json
    org = data.get('org', '').strip()
    token = data.get('token', '').strip()
    orderNumber = data.get('orderNumber', '').strip()
    
    if not org or not token:
        return jsonify({"success": False, "error": "ORG and token required"})
    
    if not orderNumber:
        return jsonify({"success": False, "error": "Order number required"})
    
    # Build the URL with orderId as path parameter
    # Extract FacilityId from ORG: {ORG}-DM1 (e.g., SS-DEMO -> SS-DEMO-DM1)
    facility_id = f"{org.upper()}-DM1"
    url = f"https://{API_HOST}/dcorder/api/dcorder/order/orderId/{orderNumber}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "FacilityId": facility_id,
        "selectedOrganization": org.upper(),
        "selectedLocation": facility_id
    }
    
    log_api_call("find_order", "GET", url, headers=headers)
    
    try:
        r = requests.get(url, headers=headers, timeout=60, verify=False)
        
        log_api_call("find_order", "GET", url, response=r.text, status_code=r.status_code)
        
        if r.status_code not in (200, 201):
            error_msg = f"API {r.status_code}: {r.text[:500]}"
            print(f"[FIND_ORDER] Error: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"Invalid Order - {error_msg}"
            })
        
        # Parse response
        try:
            response_data = r.json()
        except json.JSONDecodeError:
            print(f"[FIND_ORDER] Invalid JSON response: {r.text[:500]}")
            return jsonify({
                "success": False,
                "error": "Invalid Order - Invalid response format"
            })
        
        # The extended order API should return the order directly
        # Check if response contains order data
        orderData = None
        
        if isinstance(response_data, dict):
            # If the response itself is an order object
            if "OrderId" in response_data:
                orderData = response_data
            # Or if it's wrapped in a data field
            elif "data" in response_data:
                orderData = response_data["data"]
            elif "Data" in response_data:
                orderData = response_data["Data"]
            else:
                # Assume the whole response is the order
                orderData = response_data
        
        if not orderData:
            print(f"[FIND_ORDER] No order data found in response")
            return jsonify({
                "success": False,
                "error": "Invalid Order - Order not found or no data returned"
            })
        
        print(f"[FIND_ORDER] Successfully found order: {orderNumber}")
        return jsonify({
            "success": True,
            "orderData": orderData,
            "orderNumber": orderNumber
        })
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"[FIND_ORDER] {error_msg}")
        log_api_call("find_order", "GET", url, response={"error": error_msg}, status_code=500)
        return jsonify({
            "success": False,
            "error": f"Error finding order: {str(e)}"
        })

@app.route('/api/validate_items', methods=['POST'])
def validate_items():
    """Validate items using item-master search API"""
    data = request.json
    org = data.get('org', '').strip()
    token = data.get('token', '').strip()
    query = data.get('query', '').strip()
    
    if not org or not token:
        return jsonify({"success": False, "error": "ORG and token required"})
    
    if not query:
        return jsonify({"success": False, "error": "Query required"})
    
    # Extract FacilityId from ORG
    facility_id = f"{org.upper()}-DM1"
    url = f"https://{API_HOST}/item-master/api/item-master/item/search"
    
    # Try POST with JSON body first (as user mentioned it works in Postman)
    payload = {"Query": query}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "FacilityId": facility_id,
        "selectedOrganization": org.upper(),
        "selectedLocation": facility_id
    }
    
    # Log the raw JSON payload being sent
    import json as json_module
    payload_json = json_module.dumps(payload, indent=2)
    print(f"[VALIDATE_ITEMS] Raw JSON Payload:")
    print(payload_json)
    
    log_api_call("validate_items", "POST", url, headers=headers, payload=payload)
    
    try:
        # Try POST with JSON body (as user mentioned it works in Postman)
        r = requests.post(url, json=payload, headers=headers, timeout=60, verify=False)
        
        log_api_call("validate_items", "POST", url, response=r.text, status_code=r.status_code)
        
        if r.status_code not in (200, 201):
            error_msg = f"API {r.status_code}: {r.text[:500]}"
            print(f"[VALIDATE_ITEMS] Error: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"Validation failed - {error_msg}"
            })
        
        try:
            response_data = r.json()
        except json.JSONDecodeError:
            return jsonify({
                "success": False,
                "error": "Invalid response format"
            })
        
        # Extract data array
        data_list = response_data.get("data") or response_data.get("Data") or []
        if not isinstance(data_list, list):
            data_list = []
        
        print(f"[VALIDATE_ITEMS] Found {len(data_list)} valid items")
        return jsonify({
            "success": True,
            "data": data_list,
            "Data": data_list,
            "count": len(data_list)
        })
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"[VALIDATE_ITEMS] {error_msg}")
        return jsonify({
            "success": False,
            "error": f"Error validating items: {str(e)}"
        })

@app.route('/api/create_order', methods=['POST'])
def create_order():
    """Create a new order using the order save API"""
    data = request.json
    org = data.get('org', '').strip()
    token = data.get('token', '').strip()
    orderData = data.get('orderData')
    
    if not org or not token:
        return jsonify({"success": False, "error": "ORG and token required"})
    
    if not orderData:
        return jsonify({"success": False, "error": "Order data required"})
    
    # Extract FacilityId from ORG: {ORG}-DM1 (e.g., SS-DEMO -> SS-DEMO-DM1)
    facility_id = f"{org.upper()}-DM1"
    url = f"https://{API_HOST}/dcorder/api/dcorder/order"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "FacilityId": facility_id,
        "selectedOrganization": org.upper(),
        "selectedLocation": facility_id
    }
    
    log_api_call("create_order", "POST", url, headers=headers, payload=orderData)
    
    try:
        r = requests.post(url, json=orderData, headers=headers, timeout=60, verify=False)
        
        log_api_call("create_order", "POST", url, response=r.text, status_code=r.status_code)
        
        if r.status_code not in (200, 201):
            error_msg = f"API {r.status_code}: {r.text[:500]}"
            print(f"[CREATE_ORDER] Error: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"Create failed - {error_msg}"
            })
        
        # Parse response
        try:
            response_data = r.json()
        except json.JSONDecodeError:
            # Some APIs return empty body on success
            if r.status_code in (200, 201):
                print(f"[CREATE_ORDER] Success (no JSON response)")
                return jsonify({
                    "success": True,
                    "message": "Order created successfully"
                })
            else:
                print(f"[CREATE_ORDER] Invalid JSON response: {r.text[:500]}")
                return jsonify({
                    "success": False,
                    "error": "Invalid response format"
                })
        
        # Extract order ID from response if available
        orderId = None
        if isinstance(response_data, dict):
            orderId = response_data.get("OrderId") or response_data.get("orderId") or response_data.get("data", {}).get("OrderId")
        
        print(f"[CREATE_ORDER] Successfully created order")
        if orderId:
            print(f"[CREATE_ORDER] New Order ID: {orderId}")
        
        return jsonify({
            "success": True,
            "orderId": orderId,
            "response": response_data,
            "message": "Order created successfully"
        })
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"[CREATE_ORDER] {error_msg}")
        log_api_call("create_order", "POST", url, response={"error": error_msg}, status_code=500)
        return jsonify({
            "success": False,
            "error": f"Error creating order: {str(e)}"
        })

@app.route('/api/bulk_import_orders', methods=['POST'])
def bulk_import_orders():
    """Bulk import multiple orders using bulkImport API"""
    data = request.json
    org = data.get('org', '').strip()
    token = data.get('token', '').strip()
    ordersData = data.get('ordersData')  # Array of orders
    
    if not org or not token:
        return jsonify({"success": False, "error": "ORG and token required"})
    
    if not ordersData or not isinstance(ordersData, list):
        return jsonify({"success": False, "error": "Orders data array required"})
    
    # Extract FacilityId from ORG
    facility_id = f"{org.upper()}-DM1"
    url = f"https://{API_HOST}/dcorder/api/dcorder/order/bulkImport"
    payload = {"Data": ordersData}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "FacilityId": facility_id,
        "selectedOrganization": org.upper(),
        "selectedLocation": facility_id
    }
    
    log_api_call("bulk_import_orders", "POST", url, headers=headers, payload=payload)
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60, verify=False)
        
        log_api_call("bulk_import_orders", "POST", url, response=r.text, status_code=r.status_code)
        
        if r.status_code not in (200, 201):
            error_msg = f"API {r.status_code}: {r.text[:500]}"
            print(f"[BULK_IMPORT] Error: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"Bulk import failed - {error_msg}"
            })
        
        try:
            response_data = r.json()
        except json.JSONDecodeError:
            if r.status_code in (200, 201):
                return jsonify({
                    "success": True,
                    "message": "Orders imported successfully"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Invalid response format"
                })
        
        print(f"[BULK_IMPORT] Successfully imported {len(ordersData)} orders")
        return jsonify({
            "success": True,
            "response": response_data,
            "message": f"Successfully imported {len(ordersData)} orders"
        })
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"[BULK_IMPORT] {error_msg}")
        return jsonify({
            "success": False,
            "error": f"Error importing orders: {str(e)}"
        })

@app.route('/api/search_uoms', methods=['POST'])
def search_uoms():
    """Search for unit of measures"""
    data = request.json
    org = data.get('org', '').strip()
    token = data.get('token', '').strip()
    
    if not org or not token:
        return jsonify({"success": False, "error": "ORG and token required"})
    
    # Extract FacilityId from ORG
    facility_id = f"{org.upper()}-DM1"
    url = f"https://{API_HOST}/item-master/api/item-master/unitOfMeasure/search"
    payload = {
        "Query": "",
        "Size": 200,
        "Template": {
            "UnitOfMeasureId": None,
            "UomCode": None,
            "Description": None
        }
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "FacilityId": facility_id,
        "selectedOrganization": org.upper(),
        "selectedLocation": facility_id
    }
    
    log_api_call("search_uoms", "POST", url, headers=headers, payload=payload)
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60, verify=False)
        
        log_api_call("search_uoms", "POST", url, response=r.text, status_code=r.status_code)
        
        if r.status_code not in (200, 201):
            error_msg = f"API {r.status_code}: {r.text[:500]}"
            print(f"[SEARCH_UOMS] Error: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"Search failed - {error_msg}"
            })
        
        try:
            response_data = r.json()
        except json.JSONDecodeError:
            return jsonify({
                "success": False,
                "error": "Invalid response format"
            })
        
        # Extract data array
        data_list = response_data.get("data") or response_data.get("Data") or []
        if not isinstance(data_list, list):
            data_list = []
        
        print(f"[SEARCH_UOMS] Found {len(data_list)} UOMs")
        return jsonify({
            "success": True,
            "data": data_list,
            "Data": data_list,
            "count": len(data_list)
        })
        
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"[SEARCH_UOMS] {error_msg}")
        return jsonify({
            "success": False,
            "error": f"Error searching UOMs: {str(e)}"
        })

# === FALLBACK: Serve index.html for SPA ===
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.dirname(os.path.dirname(__file__)), 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

