from machine import Pin
from time import sleep

# ==========================================
# ENTRADAS DEL DIP SWITCH
# ==========================================
# Según el circuito de la imagen:
# DIP 1 -> GPIO 32  (bit mas significativo, peso 8)
# DIP 2 -> GPIO 33  (peso 4)
# DIP 3 -> GPIO 25  (peso 2)
# DIP 4 -> GPIO 26  (bit menos significativo, peso 1)
#
# Solo se usan 4 bits. Si tu circuito trae un 5to switch en GPIO 27,
# queda cableado pero sin usar en este código (no afecta nada).
#
# Si al probarlo ves que el orden queda "al revés" (ej. mueves el
# switch 1 y cambia como si fuera el de menor peso), solo invierte
# esta lista: dip = list(reversed(dip))

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
# 4 bits reales = valores de 0 a 15, por eso la tabla llega hasta
# el 15 (10-15 se muestran en hexadecimal: A, b, C, d, E, F).
# Sin esto, un valor binario como 1111 (=15) tumbaba el ESP32
# (IndexError) al no existir esa posición en la tabla.

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
    [1, 1, 1, 1, 0, 1, 1],  # 9
    [1, 1, 1, 0, 1, 1, 1],  # 10 -> A
    [0, 0, 1, 1, 1, 1, 1],  # 11 -> b
    [1, 0, 0, 1, 1, 1, 0],  # 12 -> C
    [0, 1, 1, 1, 1, 0, 1],  # 13 -> d
    [1, 0, 0, 1, 1, 1, 1],  # 14 -> E
    [1, 0, 0, 0, 1, 1, 1],  # 15 -> F
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


from umqtt.simple import MQTTClient


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

    # 2. Leer el DIP como número BINARIO real (no como conteo).
    #    bits_str queda como "1010", "0001", etc. (DIP1..DIP4)
    bits_str = "".join([str(pin.value()) for pin in dip])
    valor_dip = int(bits_str, 2)   # "1010" -> 10  (binario -> decimal)

    # 3. Actualizar display y publicar SOLO cuando cambia el DIP.
    #    (si actualizáramos en cada vuelta del while, un comando remoto
    #    se borraría solo 0.1s después de presionarlo, porque la
    #    lectura del DIP lo pisaría de nuevo)
    if valor_dip != ultimo_valor:
        mostrar_numero(valor_dip)
        print("DIP:", bits_str, "-> valor binario:", valor_dip)

        payload = bits_str + "," + str(valor_dip)
        client.publish(TOPIC_ESTADO, payload.encode())
        print("Publicado:", payload)

        ultimo_valor = valor_dip

    sleep(0.1)
