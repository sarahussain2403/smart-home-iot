import paho.mqtt.client as mqtt
import json
import pymysql
from pymongo import MongoClient
from neo4j import GraphDatabase

# ---------------- MYSQL ----------------
db = pymysql.connect(
    host="localhost",
    user="root",
    password="sara",
    database="smarthome"
)
cursor = db.cursor()
print("Connected to MySQL!")

# ---------------- MONGODB ----------------
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["smarthome"]

motion_collection = mongo_db["motion_events"]
door_collection = mongo_db["door_events"]

print("Connected to MongoDB!")

# ---------------- NEO4J ----------------
neo4j_driver = GraphDatabase.driver(
    "neo4j://127.0.0.1:7687",
    auth=("neo4j", "password")
)
print("Connected to Neo4j!")


# ---------------- NEO4J FUNCTION ----------------
def save_device_to_neo4j(from_device, to_device, action):
    try:
        with neo4j_driver.session() as session:
            session.run("""
                MERGE (a:Device {name: $from_device})
                MERGE (b:Device {name: $to_device})
                MERGE (a)-[:CONTROLS {action: $action}]->(b)
            """, from_device=from_device, to_device=to_device, action=action)

        print("DEVICE saved → Neo4j")

    except Exception as e:
        print("Neo4j error:", e)


# ---------------- MQTT CONNECT ----------------
def on_connect(client, userdata, flags, rc):
    print("Connected to Mosquitto!")

    client.subscribe("sensor/#")
    client.subscribe("home/devices")

    print("Subscribed to all sensor topics!")


# ---------------- MQTT MESSAGE HANDLER ----------------
def on_message(client, userdata, msg):

    topic = msg.topic.strip()   # 🔥 IMPORTANT FIX
    data = json.loads(msg.payload.decode())

    print("\n--- MESSAGE RECEIVED ---")
    print("TOPIC:", topic)
    print("DATA:", data)

    try:

        # 🌡 TEMPERATURE → MySQL
        if "temp" in topic:
            cursor.execute(
                "INSERT INTO temperature (room, value) VALUES (%s, %s)",
                (data["room"], data["value"])
            )
            db.commit()
            print("TEMP saved → MySQL")

        # 💨 GAS → MySQL
        elif "gas" in topic:
            cursor.execute(
                "INSERT INTO gas (room, value, status) VALUES (%s, %s, %s)",
                (data["room"], data["value"], data["status"])
            )
            db.commit()
            print("GAS saved → MySQL")

        # 💡 LIGHT → MySQL
        elif "light" in topic:
            cursor.execute(
                "INSERT INTO light (room, lux) VALUES (%s, %s)",
                (data["room"], data["lux"])
            )
            db.commit()
            print("LIGHT saved → MySQL")

        # 🕵️ MOTION → MongoDB
        elif "motion" in topic:
            motion_collection.insert_one(data)
            print("MOTION saved → MongoDB")

        # 🚪 DOOR → MongoDB
        elif "door" in topic:
            door_collection.insert_one(data)
            print("DOOR saved → MongoDB")

        # 📱 DEVICE → Neo4j
        elif "devices" in topic:
            save_device_to_neo4j(
                data["from"],
                data["to"],
                data["action"]
            )

    except Exception as e:
        print("ERROR processing message:", e)

    print("---")


# ---------------- MQTT CLIENT ----------------
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

client.loop_forever()