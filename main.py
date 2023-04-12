import os
import json
import machine
import network
import time
from simpleMQTT import MQTTClient
from neopixel import Neopixel
import rp2
import random
import _thread
import senko
import gc

gc.collect()
print(gc.mem_free())

#Clears old PIO programs from previous iterations of this program.
rp2.PIO(0).remove_program()

print("Loading secrets...")
f = open("secrets.json", 'r')
secrets = json.loads(f.read())

#secrets
ssid = secrets['ssid']
password = secrets['password']
mqtt_server = secrets['mqttserver']
mqtt_username = secrets['mqttusername']
mqtt_password = secrets['mqttpassword']
client_id = secrets['clientid']

#filesystem
settings = "settings.json"

class Light:
    def __init__(self, state_topic, command_topic, brightness=255, r=255, g=255, b=255, w=255, power=True, effect="", startLED=0, endLED=0):
        self.brightness = brightness
        self.r = r
        self.g = g
        self.b = b
        self.w = w
        self.power = power
        self.effect = effect
        self.startLED = startLED
        self.endLED = endLED
        self.state_topic = state_topic
        self.command_topic = command_topic
        
        
    def process_message(self, command_topic, message):
        if command_topic != self.command_topic and command_topic != b'masterbed/all/set':
            return
        
        msg_obj = json.loads(message)
        print(msg_obj)
        
        if('state' in msg_obj):
            self.power = msg_obj['state'] == 'ON'
        
        if('brightness' in msg_obj):
            self.brightness = int(msg_obj['brightness'])
            
        if('color' in msg_obj):
            self.r = int(msg_obj['color']['r'])
            self.g = int(msg_obj['color']['g'])
            self.b = int(msg_obj['color']['b'])
            self.w = int(msg_obj['color']['w'])
            
        if('effect' in msg_obj):
            self.effect = msg_obj['effect']
            
        if self.effect == 'none':
            self.effect = ''
        
    def update_strip(self, strip):        
        if self.power == False:
            strip[self.startLED:self.endLED: 1] = (0,0,0,0,0)
            return
        
        if self.effect == "":
            strip[self.startLED:self.endLED: 1] = (self.r, self.g, self.b, self.w, self.brightness)
            return
        
        if self.effect == "every2":
            strip[self.startLED:self.endLED: 1] = (0,0,0,0,0)
            strip[self.startLED:self.endLED: 2] = (self.r, self.g, self.b, self.w, self.brightness)
            return

        if self.effect == "every3":
            strip[self.startLED:self.endLED: 1] = (0,0,0,0,0)
            strip[self.startLED:self.endLED: 3] = (self.r, self.g, self.b, self.w, self.brightness)
            return
        
        if self.effect == "every4":
            strip[self.startLED:self.endLED: 1] = (0,0,0,0,0)
            strip[self.startLED:self.endLED: 4] = (self.r, self.g, self.b, self.w, self.brightness)
            return
    
    def dump_state(self):
        state = {
        "state": "ON" if self.power else "OFF",
        "brightness": self.brightness,
        "color_mode": "rgbw",
        "effect": self.effect,
        "color": {
            'r': self.r,
            'g': self.g,
            'b': self.b,
            'w': self.w
            }
        }
    
        return json.dumps(state)
    
    def print_state(self):
        print("Power :" + str(self.power))
        print("Brightness :" + str(self.brightness))
        print("RGBW :" + str([self.r, self.g, self.b, self.w]))
        print("Effect :" + self.effect)
        
    def serialize(self):
        return {
            'brightness': self.brightness,
            'r': self.r,
            'g': self.g,
            'b': self.b,
            'w': self.w,
            'power': self.power,
            'effect': self.effect
        }
        
    def deserialize(self, data):
        self.brightness = data["brightness"]
        self.r = data["r"]
        self.g = data["g"]
        self.b = data["b"]
        self.w = data["w"]
        self.power = data["power"]
        self.effect = data["effect"]
        
        

lightLeft = Light(startLED=240, endLED=360, state_topic = b'masterbed/left', command_topic = b'masterbed/left/set')
lightBottom = Light(startLED=120, endLED=240, state_topic = b'masterbed/bottom', command_topic = b'masterbed/bottom/set')
lightRight = Light(startLED=0, endLED=120, state_topic = b'masterbed/right', command_topic = b'masterbed/right/set')

lightAll = Light(state_topic = b'masterbed/all', command_topic = b'masterbed/all/set')

#neopixel
numpix = 360
strip = Neopixel(numpix, 0, 1, "GRBW")
 
#Load in light state from save
if settings in os.listdir():
    print("Restoring settings...")
    f = open(settings, 'r')
    settingData = json.loads(f.read())
        
    if len(settingData) == 3:
        lightLeft.deserialize(settingData[0])
        lightBottom.deserialize(settingData[1])
        lightRight.deserialize(settingData[2])

lightLeft.update_strip(strip)
lightBottom.update_strip(strip)
lightRight.update_strip(strip)
strip.show()

#status update
last_message = 0
message_interval = 5

def sub_cb(topic, msg):
  print((topic, msg))
  process_updates(topic, msg)

def connect_and_subscribe():
  global client_id, mqtt_server, topic_sub
  client = MQTTClient(client_id, mqtt_server, 1883, mqtt_username, mqtt_password)
  client.set_callback(sub_cb)
  client.connect()
  client.subscribe(lightLeft.command_topic)
  client.subscribe(lightBottom.command_topic)
  client.subscribe(lightRight.command_topic)
  client.subscribe(lightAll.command_topic)
  print('Connected to MQTT broker: ', mqtt_server)
  return client

def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  machine.reset()

def process_updates(topic, msg):

    if client == 0:
        return
    
    print(msg)
        
    lightLeft.process_message(topic, msg)
    lightBottom.process_message(topic, msg)
    lightRight.process_message(topic, msg)
    lightAll.process_message(topic, msg)
    
    lightLeft.update_strip(strip)
    lightBottom.update_strip(strip)
    lightRight.update_strip(strip)
    
    strip.show()
    
    publish_status()
    
    lightLeft.print_state()
    lightBottom.print_state()
    lightRight.print_state()
    
    write_settings()
    
def write_settings():
    f = open(settings, 'w')
    f.write(json.dumps((lightLeft.serialize(), lightBottom.serialize(), lightRight.serialize())))
    f.close()

    
def publish_status():
    client.publish(lightLeft.state_topic, lightLeft.dump_state())
    client.publish(lightBottom.state_topic, lightBottom.dump_state())
    client.publish(lightRight.state_topic, lightRight.dump_state())
    client.publish(lightAll.state_topic, lightAll.dump_state())
      
#connect to WLAN
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected() and wlan.status() >= 0:
    pass

print("Connected to Wifi")
print(wlan.ifconfig())


GITHUB_URL = "https://raw.githubusercontent.com/mpeddicord/bedroomled/master"
OTA = senko.Senko(None, None, url=GITHUB_URL, files=["main.py", "neopixel.py"])

if OTA.update():
    print("Updated to the latest version! Rebooting...")
    machine.reset()
    
#connect to mqtt
try:
    client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()
    
print("MQTT connected")

#main update loop
while True:
    try:
        client.check_msg()
        
        if (time.time() - last_message) > message_interval:
            last_message = time.time()
            publish_status()
            #if strip_effect in ['every2', 'every3','every4', '']:
            #    update_strips()
    
    except OSError as e:
        print(e)
        restart_and_reconnect()
        running_effect = False
        
    except KeyboardInterrupt as e:
        running_effect = False



