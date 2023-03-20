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

#subscription and publish topics
state_topic = b'masterbed/rgbw1'
command_topic = b'masterbed/rgbw1/set'

#light state
strip_brightness = 255
strip_r = 255
strip_g = 255
strip_b = 255
strip_w = 255
strip_power = True
strip_effect = ""
strip_left = True
strip_center = True
strip_right = True

effect_thread = ""
running_effect = False
thread_finished = False

#neopixel
numpix = 360
strip = Neopixel(numpix, 0, 1, "GRBW")

def update_strip():
    global running_effect, thread_finished, effect_thread, strip, strip_r, strip_g, strip_b, strip_w, strip_brightness   
    
    #signal the thread to end and wait for it to finish
    if running_effect:
        thread_finished = False
        running_effect = False
        while thread_finished == False:
            pass
        
    if strip_power == False:
        color = (0, 0, 0, 0)
        brightness = 0
        strip.fill(color, brightness)
        strip.show()
        return
    
    if strip_effect == "":
        color = (strip_r, strip_g, strip_b, strip_w)
        brightness = strip_brightness
        strip.fill(color, brightness)
        update_sides()
        strip.show()
        return
    
    if strip_effect == "every2":
        color = (strip_r, strip_g, strip_b, strip_w)
        brightness = strip_brightness
        strip.fill(color, brightness)
        strip[::2] = (0,0,0,0)
        update_sides()
        strip.show()
        return

    if strip_effect == "every3":
        color = (strip_r, strip_g, strip_b, strip_w)
        brightness = strip_brightness
        strip.fill(color, brightness)
        strip[::3] = (0,0,0,0)
        strip[1::3] = (0,0,0,0)
        update_sides()
        strip.show()
        return
    
    if strip_effect == "every4":
        color = (strip_r, strip_g, strip_b, strip_w)
        brightness = strip_brightness
        strip.fill(color, brightness)
        strip[::4] = (0,0,0,0)
        strip[1::4] = (0,0,0,0)
        strip[2::4] = (0,0,0,0)
        update_sides()
        strip.show()
        return
        
    if strip_effect == "hueshift":
        running_effect = True
        effect_thread = _thread.start_new_thread(update_hueshift, ())
            
    if strip_effect == "whitefairy":
        running_effect = True
        effect_thread = _thread.start_new_thread(update_whitefairy, ())
        
    if strip_effect == "colorfairy":
        running_effect = True
        effect_thread = _thread.start_new_thread(update_colorfairy, ())
        
        
def update_sides():
    if not strip_right:
        strip[:120:1]  = (0,0,0,0)
    if not strip_center:
        strip[121:240:1]  = (0,0,0,0)
    if not strip_left:
        strip[241:360:1]  = (0,0,0,0)
    
def update_hueshift():
    global strip, numpix, running_effect, thread_finished, strip_brightness
    
    strip.fill((0,0,0,0))
    
    hue = 0
    while running_effect:
        color = strip.colorHSV(hue, 255, 150)
        strip.fill(color, strip_brightness)
        strip.show()
        
        hue += 150
        
    thread_finished = True
    return
    
def update_whitefairy():
    global strip, numpix, running_effect, thread_finished, strip_brightness
    
    strip.fill((0,0,0,0))
    strip.brightness(strip_brightness)
    strip[::numpix//4] = (255,255,255,255)
    
    while running_effect:
        strip.rotate_right(1)
        strip.show()
        
    thread_finished = True
    return
        
def update_colorfairy():
    global strip, numpix, running_effect, thread_finished
    
    seperation = numpix // 4;
    
    strip.fill((0,0,0,0))
    strip.brightness(strip_brightness)
    strip[0] = (255,0,0,0)
    strip[seperation] = (0,255,0,0)
    strip[seperation*2] = (0,0,255,0)
    strip[seperation*3] = (0,0,0,255)
    
    while running_effect:
        strip.rotate_right(1)
        strip.show()
        
    thread_finished = True
    return

#Load in light state from save
if settings in os.listdir():
    print("Restoring settings...")
    f = open(settings, 'r')
    settingData = json.loads(f.read())
    strip_brightness = settingData["brightness"]
    strip_r = settingData["r"]
    strip_g = settingData["g"]
    strip_b = settingData["b"]
    strip_w = settingData["w"]
    strip_power = settingData["power"]
    strip_effect = settingData["effect"]
    if 'left' in settingData:
       strip_left = settingData["left"]
    if 'center' in settingData:
       strip_center = settingData["center"]
    if 'right' in settingData:
       strip_right = settingData["right"]
    
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
  client.subscribe(command_topic)
  print('Connected to MQTT broker: ', mqtt_server)
  return client

def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  machine.reset()

def process_updates(topic, msg):
    global strip_power, strip_brightness, strip_r, strip_g, strip_b, strip_w, strip_effect
    
    if client == 0:
        return
    
    if topic == command_topic:
        msg_obj = json.loads(msg)
        print(msg_obj)
        
        if('state' in msg_obj):
            strip_power = msg_obj['state'] == 'ON'
        
        if('brightness' in msg_obj):
            strip_brightness = int(msg_obj['brightness'])
            
        if('color' in msg_obj):
            strip_r = int(msg_obj['color']['r'])
            strip_g = int(msg_obj['color']['g'])
            strip_b = int(msg_obj['color']['b'])
            strip_w = int(msg_obj['color']['w'])
            
        if('effect' in msg_obj):
            if msg_obj['effect'] in ['leftflip', 'centerflip','rightflip']:
                if msg_obj['effect'] is 'leftflip':
                   strip_left != strip_left
                if msg_obj['effect'] is 'centerflip':
                   strip_center != strip_center
                if msg_obj['effect'] is 'rightflip':
                   strip_right != strip_right
            else:
                strip_effect = msg_obj['effect']
            
        if strip_effect == 'none':
            strip_effect = ''
            
    update_strip()
    publish_status()
    write_settings()
    
def write_settings():
    f = open(settings, 'w')
    
    f.write(json.dumps({
        'brightness': strip_brightness,
        'r': strip_r,
        'g': strip_g,
        'b': strip_b,
        'w': strip_w,
        'power': strip_power,
        'effect': strip_effect,
        'left': strip_left,
        'center': strip_center,
        'right': strip_right,
        
        }))
    
    f.close()

    
def publish_status():
    
    state = {
        "state": "ON" if strip_power else "OFF",
        "brightness": strip_brightness,
        "color_mode": "rgbw",
        "effect": strip_effect,
        "color": {
            'r': strip_r,
            'g': strip_g,
            'b': strip_b,
            'w': strip_w
            }
        }
    
    client.publish(state_topic, json.dumps(state))
    
    print("Power :" + str(strip_power))
    print("Brightness :" + str(strip_brightness))
    print("RGBW :" + str([strip_r, strip_g, strip_b, strip_w]))
    print("Effect :" + strip_effect)
    print("Left :" + str(strip_left))
    print("Center :" + str(strip_center))
    print("Right :" + str(strip_right))

    
#connect to WLAN
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected() and wlan.status() >= 0:
    pass

print("Connected to Wifi")
print(wlan.ifconfig())


GITHUB_URL = "https://raw.githubusercontent.com/mpeddicord/bedroomled/master"
OTA = senko.Senko(None, None, url=GITHUB_URL, files=["main.py"])

if OTA.update():
    print("Updated to the latest version! Rebooting...")
    machine.reset()
    
#connect to mqtt
try:
    client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()
    
print("MQTT connected")
update_strip()

#main update loop
while True:
    try:
        client.check_msg()
        
        if (time.time() - last_message) > message_interval:
            last_message = time.time()
            publish_status();
            if strip_effect in ['every2', 'every3','every4', '']:
                update_strip()
    
    except OSError as e:
        restart_and_reconnect()
        running_effect = False
        
    except KeyboardInterrupt as e:
        running_effect = False







