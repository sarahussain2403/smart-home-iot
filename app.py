from flask import Flask, render_template, jsonify
import pymysql
from pymongo import MongoClient
from neo4j import GraphDatabase

app = Flask(__name__)

def get_mysql():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="sara",
        database="smarthome"
    )

mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["smarthome"]

neo4j_driver = GraphDatabase.driver(
    "neo4j://127.0.0.1:7687",
    auth=("neo4j", "password")
)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/temperature")
def temperature():
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("SELECT room, value, recorded_at FROM temperature ORDER BY recorded_at DESC LIMIT 1")
    rows = cursor.fetchall()
    db.close()
    return jsonify([{"room": r[0], "value": r[1], "time": str(r[2])} for r in rows])

@app.route("/api/temperature_history")
def temperature_history():
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("SELECT room, value, recorded_at FROM temperature ORDER BY recorded_at DESC LIMIT 5")
    rows = cursor.fetchall()
    db.close()
    return jsonify([{"room": r[0], "value": r[1], "time": str(r[2])} for r in rows])

@app.route("/api/gas")
def gas():
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("SELECT room, value FROM gas ORDER BY id DESC LIMIT 1")
    r = cursor.fetchone()
    db.close()
    if not r:
        return jsonify([])
    return jsonify([{"room": r[0], "value": r[1], "status": "danger" if r[1] > 0.5 else "safe"}])

@app.route("/api/light")
def light():
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("SELECT room, lux FROM light ORDER BY id DESC LIMIT 1")
    rows = cursor.fetchall()
    db.close()
    return jsonify([{"room": r[0], "lux": r[1]} for r in rows])

@app.route("/api/motion")
def motion():
    docs = mongo_db["motion_events"].find().sort("_id", -1).limit(1)
    return jsonify([{"room": d["room"], "detected": d["detected"]} for d in docs])

@app.route("/api/door")
def door():
    docs = mongo_db["door_events"].find().sort("_id", -1).limit(1)
    return jsonify([{"door": d["door"], "status": d["status"]} for d in docs])

@app.route("/api/devices")
def devices():
    with neo4j_driver.session() as session:
        result = session.run("MATCH (a)-[r]->(b) RETURN a.name, r.action, b.name LIMIT 1")
        return jsonify([{"from": row["a.name"], "action": row["r.action"], "to": row["b.name"]} for row in result])

@app.route("/api/alerts")
def alerts():
    alerts = []
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("SELECT room, value FROM gas ORDER BY id DESC LIMIT 1")
    gas = cursor.fetchone()
    cursor.execute("SELECT room, value FROM temperature ORDER BY recorded_at DESC LIMIT 1")
    temp = cursor.fetchone()
    db.close()
    if gas and gas[1] > 0.5:
        alerts.append(f"Gas danger detected in {gas[0]}")
    if temp and temp[1] > 33:
        alerts.append(f"High temperature in {temp[0]}: {temp[1]}C")
    return jsonify(alerts)

@app.route("/api/incidents")
def incidents():
    logs = []

    # Gas danger from MongoDB
    gas_docs = mongo_db["motion_events"].find({"detected": True}).sort("_id", -1).limit(3)
    for d in gas_docs:
        logs.append({
            "type": "motion",
            "message": f"Motion detected in {d['room']}",
            "raw": {"room": d["room"], "detected": d["detected"]}
        })

    # Door open events from MongoDB
    door_docs = mongo_db["door_events"].find({"status": "open"}).sort("_id", -1).limit(3)
    for d in door_docs:
        logs.append({
            "type": "door",
            "message": f"{d['door']} was opened",
            "raw": {"door": d["door"], "status": d["status"]}
        })

    return jsonify(logs[:5])

if __name__ == "__main__":
    app.run(debug=True)