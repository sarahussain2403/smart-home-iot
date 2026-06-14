import paho.mqtt.client as mqtt
import time
import json
import random

client = mqtt.Client()
client.connect("localhost", 1883, 60)

print("Publisher started. Sending data every 5 seconds.")
print("Press Ctrl+C to stop")
print(" ")

device_events = [
    {"from": "smartphone", "to": "smart_bulb", "action": "turn_on"},
    {"from": "smartphone", "to": "AC", "action": "turn_off"},
    {"from": "tablet", "to": "smart_door", "action": "lock"},
    {"from": "thermostat", "to": "AC", "action": "set_temperature"},
    {"from": "motion_sensor", "to": "smart_bulb", "action": "turn_on"},
    {"from": "smartphone", "to": "smart_tv", "action": "turn_on"},
]

while True:
    temp_data = {
        "room": random.choice(["living_room", "bedroom", "kitchen"]),
        "value": round(random.uniform(18, 35), 1)
    }
    client.publish("sensor/temp", json.dumps(temp_data))
    print("Sent temperature:", temp_data)

    motion_data = {
        "room": random.choice(["hallway", "living_room", "garden"]),
        "detected": random.choice([True, False])
    }
    client.publish("sensor/motion", json.dumps(motion_data))
    print("Sent motion:", motion_data)

    gas_data = {
        "room": random.choice(["kitchen", "garage"]),
        "value": round(random.uniform(0.0, 1.0), 2),
        "status": "danger" if random.random() > 0.8 else "safe"
    }
    client.publish("sensor/gas", json.dumps(gas_data))
    print("Sent gas:", gas_data)

    light_data = {
        "room": random.choice(["living_room", "bedroom", "kitchen"]),
        "lux": random.randint(50, 1000)
    }
    client.publish("sensor/light", json.dumps(light_data))
    print("Sent light:", light_data)

    door_data = {
        "door": random.choice(["main_door", "back_door"]),
        "status": random.choice(["open", "closed"])
    }
    client.publish("sensor/door", json.dumps(door_data))
    print("Sent door:", door_data)

    device_data = random.choice(device_events)
    client.publish("home/devices", json.dumps(device_data))
    print("Sent device event:", device_data)

    time.sleep(5)
