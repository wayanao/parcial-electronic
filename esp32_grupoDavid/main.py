from machine import Pin
from time import sleep

# ==========================================
# ENTRADAS DEL DIP SWITCH (patron binario de 4 bits)
# ==========================================
# Se lee como DIP1 DIP2 DIP3 DIP4 (de izquierda a derecha),
# igual que se escribe un binario normal. Ej: 0001 -> DIP4
# encendido -> valor 1.
# DIP 1 -> GPIO 32  (bit 3, valor 8)  <- MSB
# DIP 2 -> GPIO 33  (bit 2, valor 4)
# DIP 3 -> GPIO 25  (bit 1, valor 2)
# DIP 4 -> GPIO 26  (bit 0, valor 1)  <- LSB

dip = [
    Pin(32, Pin.IN, Pin.PULL_DOWN),
    Pin(33, Pin.IN, Pin.PULL_DOWN),
    Pin(25, Pin.IN, Pin.PULL_DOWN),
    Pin(26, Pin.IN, Pin.PULL_DOWN)
]

# ==========================================
# DISPLAY DE 7 SEGMENTOS
# ==========================================
a = Pin(23, Pin.OUT)
b = Pin(22, Pin.OUT)
c = Pin(21, Pin.OUT)
d = Pin(19, Pin.OUT)
e = Pin(18, Pin.OUT)
f = Pin(5, Pin.OUT)
g = Pin(17, Pin.OUT)

segmentos = [a, b, c, d, e, f, g]

# ==========================================
# NUMEROS DEL DISPLAY (solo decimal 0-9)
# ==========================================
numeros = [
    # a b c d e f g
    [1, 1, 1, 1, 1, 1, 0],  # 0
    [0, 1, 1, 0, 0, 0, 0],  # 1
    [1, 1, 0, 1, 1, 0, 1],  # 2
    [1, 1, 1, 1, 0, 0, 1],  # 3
    [0, 1, 1, 0, 0, 1, 1],  # 4
    [1, 0, 1, 1, 0, 1, 1],  # 5
    [1, 0, 1, 1, 1, 1, 1],  # 6
    [1, 1, 1, 0, 0, 0, 0],  # 7
    [1, 1, 1, 1, 1, 1, 1],  # 8
    [1, 1, 1, 1, 0, 1, 1]   # 9
]

def mostrar_numero(numero):
    for i in range(7):
        segmentos[i].value(numeros[numero][i])

# ==========================================
# RED Y MQTT
# ==========================================
WIFI_SSID   = "Wokwi-GUEST"
WIFI_PASS   = ""
MQTT_BROKER = "broker.hivemq.com"

GRUPO = "grupoDavid"
TOPIC_ESTADO  = "clase/decoder/" + GRUPO + "/estado"
TOPIC_CONTROL = "clase/decoder/" + GRUPO + "/control"

def conectar_wifi():
    import network, time
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)

    inicio = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), inicio) > 10000:
            raise OSError("WiFi timeout - verifique la red en Wokwi")
        time.sleep_ms(300)
        print("   Esperando IP...")

    print("WiFi OK - IP:", wlan.ifconfig()[0])
    return wlan

from umqtt import MQTTClient

def al_recibir_del_frontend(topic, msg):
    try:
        numero_remoto = int(msg.decode())
        if 0 <= numero_remoto <= 9:
            mostrar_numero(numero_remoto)
            print("Comando remoto recibido:", numero_remoto)
        else:
            print("Valor fuera de rango:", numero_remoto)
    except ValueError:
        print("Mensaje no numérico recibido:", msg)

conectar_wifi()

client = MQTTClient("esp32_" + GRUPO, MQTT_BROKER)
client.set_callback(al_recibir_del_frontend)
client.connect()
client.subscribe(TOPIC_CONTROL)
print("MQTT listo - escuchando en:", TOPIC_CONTROL)

# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================
ultimo_valor = -1

while True:
    client.check_msg()

    valor = 0
    for i, interruptor in enumerate(dip):
        if interruptor.value() == 1:
            valor += (1 << (3 - i))

    if valor != ultimo_valor:
        # El display fisico solo tiene 0-9; si el binario da 10-15,
        # se deja en 9 para no romper la tabla.
        mostrar_numero(min(valor, 9))
        print("Valor binario (DIP1..DIP4):", valor)

        bits_str = "".join([str(pin.value()) for pin in dip])
        payload = bits_str + "," + str(valor)
        client.publish(TOPIC_ESTADO, payload.encode())
        print("Publicado:", payload)

        ultimo_valor = valor

    sleep(0.1)
