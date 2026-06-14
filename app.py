from flask import Flask, render_template, jsonify, request
import pymysql
from pymongo import MongoClient
from neo4j import GraphDatabase
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)

mqtt_client = mqtt.Client()
mqtt_client.connect("localhost", 1883, 60)
mqtt_client.loop_start()

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

@app.route("/api/temperature_avg")
def temperature_avg():
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("""
        SELECT room, ROUND(AVG(value), 1)
        FROM (SELECT room, value FROM temperature ORDER BY recorded_at DESC LIMIT 20) recent
        GROUP BY room
    """)
    rows = cursor.fetchall()
    db.close()
    return jsonify([{"room": r[0], "avg": r[1]} for r in rows])

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

@app.route("/api/light_status")
def light_status():
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("SELECT room, status FROM light_status")
    rows = cursor.fetchall()
    db.close()
    return jsonify([{"room": r[0], "status": r[1]} for r in rows])

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
    motion_docs = mongo_db["motion_events"].find({"detected": True}).sort("_id", -1).limit(3)
    for d in motion_docs:
        logs.append({
            "type": "motion",
            "message": f"Motion detected in {d['room']}",
            "raw": {"room": d["room"], "detected": d["detected"]}
        })
    door_docs = mongo_db["door_events"].find({"status": "open"}).sort("_id", -1).limit(3)
    for d in door_docs:
        logs.append({
            "type": "door",
            "message": f"{d['door']} was opened",
            "raw": {"door": d["door"], "status": d["status"]}
        })
    return jsonify(logs[:5])

@app.route("/api/fan_status")
def fan_status():
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("SELECT room, value FROM gas ORDER BY id DESC LIMIT 1")
    r = cursor.fetchone()
    db.close()
    if r and r[1] > 0.5:
        return jsonify({"active": True, "room": r[0]})
    return jsonify({"active": False})

@app.route("/api/control/light", methods=["POST"])
def control_light():
    data = request.json
    room = data["room"]
    action = data["action"]
    status = "on" if action == "turn_on" else "off"
    db = get_mysql()
    cursor = db.cursor()
    cursor.execute("UPDATE light_status SET status = %s WHERE room = %s", (status, room))
    db.commit()
    db.close()
    mqtt_client.publish("home/control/light", json.dumps({"room": room, "action": action}))
    return jsonify({"status": status, "room": room})

if __name__ == "__main__":
    app.run(debug=True)
