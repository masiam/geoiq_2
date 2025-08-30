from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import json
import time
from datetime import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres-service'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'flaskdb'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return None

def log_request(method, path, status_code, duration):
    """Log request in JSON format"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2),
        "level": "INFO"
    }
    logger.info(json.dumps(log_entry))

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time
    log_request(
        request.method,
        request.path,
        response.status_code,
        duration
    )
    return response

@app.route('/serviceup', methods=['GET'])
def service_health():
    return jsonify({
        "status": 200,
        "message": "success"
    }), 200

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({
            "error": "Database connection failed",
            "status": 500
        }), 500
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            
            if user:
                return jsonify({
                    "id": user['id'],
                    "name": user['name']
                }), 200
            else:
                return jsonify({
                    "error": f"User with id {user_id} not found",
                    "status": 404
                }), 404
                
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        return jsonify({
            "error": "Database query failed",
            "status": 500
        }), 500
    finally:
        conn.close()

@app.route('/user', methods=['GET'])
def get_user_by_query():
    user_id = request.args.get('id')
    if not user_id:
        return jsonify({
            "error": "Missing id parameter",
            "status": 400
        }), 400
    
    try:
        user_id = int(user_id)
        return get_user_by_id(user_id)
    except ValueError:
        return jsonify({
            "error": "Invalid id parameter",
            "status": 400
        }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
