from machine import Pin
from time import sleep

# ==========================================
# ENTRADAS DEL DIP SWITCH
# ==========================================
# Según el circuito de la imagen:
# DIP 1 -> GPIO 32
# DIP 2 -> GPIO 33
# DIP 3 -> GPIO 25
# DIP 4 -> GPIO 26
#
# Solo se usan 4 bits. Si tu circuito trae un 5to switch en GPIO 27,
# queda cableado pero sin usar en este código (no afecta nada).

dip = [
    Pin(32, Pin.IN, Pin.PULL_DOWN),
    Pin(33, Pin.IN, Pin.PULL_DOWN),
    Pin(25, Pin.IN, Pin.PULL_DOWN),
    Pin(26, Pin.IN, Pin.PULL_DOWN),
]


# ==========================================
# DISPLAY DE 7 SEGMENTOS
# ==========================================
# Segmentos: a, b, c, d, e, f, g
#
# Ajusta estos GPIO si el orden de los
# cables de tu display es diferente.

a = Pin(23, Pin.OUT)
b = Pin(22, Pin.OUT)
c = Pin(21, Pin.OUT)
d = Pin(19, Pin.OUT)
e = Pin(18, Pin.OUT)
f = Pin(5, Pin.OUT)
g = Pin(17, Pin.OUT)

segmentos = [a, b, c, d, e, f, g]


# ==========================================
# NUMEROS DEL DISPLAY
# ==========================================
# 1 = segmento encendido
# 0 = segmento apagado
#
# NOTA: se agregaron los patrones del 6 al 9 (antes solo llegaba
# hasta el 5) porque el control remoto de la interfaz web puede
# pedir cualquier dígito 0-9, y sin esto el ESP32 se caía
# (IndexError) al recibir un 6, 7, 8 o 9 desde la web.

numeros = [
    # a b c d e f g
    [1, 1, 1, 1, 1, 1, 0],  # 0
    [0, 1, 1, 0, 0, 0, 0],  # 1
    [1, 1, 0, 1, 1, 0, 1],  # 2
    [1, 1, 1, 1, 0, 0, 1],  # 3
    [0, 1, 1, 0, 0, 1, 1],  # 4
    [1, 0, 1, 1, 0, 1, 1],  # 5
    [1, 0, 1, 1, 1, 1, 1],  # 6  <- nuevo
    [1, 1, 1, 0, 0, 0, 0],  # 7  <- nuevo
    [1, 1, 1, 1, 1, 1, 1],  # 8  <- nuevo
    [1, 1, 1, 1, 0, 1, 1],  # 9  <- nuevo
]


# ==========================================
# FUNCION PARA MOSTRAR UN NUMERO
# ==========================================

def mostrar_numero(numero):

    for i in range(7):
        segmentos[i].value(numeros[numero][i])


# ==========================================
# RED Y MQTT  (Paso 1 de la guía)
# ==========================================
WIFI_SSID   = "Wokwi-GUEST"
WIFI_PASS   = ""
MQTT_BROKER = "broker.hivemq.com"   # solo el hostname, sin "://"

# Debe coincidir EXACTAMENTE con los tópicos del frontend (script.js)
GRUPO = "grupoDavid"
TOPIC_ESTADO  = "clase/decoder/" + GRUPO + "/estado"   # ESP32 -> Web (monitoreo)
TOPIC_CONTROL = "clase/decoder/" + GRUPO + "/control"  # Web -> ESP32 (control)


def conectar_wifi():
    import network, time
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)

    inicio = time.ticks_ms()
    while not wlan.isconnected():
        # Sin este timeout el simulador se congela indefinidamente
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
        # No dejar el except vacío: imprimir siempre el error
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

    # 1. Revisar si llegó un comando remoto (no bloqueante)
    client.check_msg()

    # 2. Leer cada entrada del DIP (tu lógica original, intacta)
    contador = 0
    for interruptor in dip:
        if interruptor.value() == 1:
            contador += 1

    # 3. Actualizar display y publicar SOLO cuando cambia el DIP.
    #    (si actualizáramos en cada vuelta del while, un comando remoto
    #    se borraría solo 0.1s después de presionarlo, porque el
    #    conteo de switches lo pisaría de nuevo)
    if contador != ultimo_valor:
        mostrar_numero(contador)
        print("Entradas activadas:", contador)

        bits_str = "".join([str(pin.value()) for pin in dip])
        payload = bits_str + "," + str(contador)
        client.publish(TOPIC_ESTADO, payload.encode())
        print("Publicado:", payload)

        ultimo_valor = contador

    sleep(0.1)
