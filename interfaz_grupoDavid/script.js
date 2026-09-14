/* ============================================================
   SUPER CONTROL BROS — lógica MQTT (frontend)
   Basado en la Guía Actividad 3 Parcial 1 — Opción B (HTML + JS)
   ============================================================ */

// ---------- 1. CONFIGURACIÓN ----------
// ¡IMPORTANTE! Estos valores deben coincidir EXACTAMENTE con los que
// configures en el main.py de tu ESP32 (Paso 1 de la guía).
const GRUPO = "grupoDavid"; // <- identificador único de este grupo

const MQTT_BROKER = "broker.hivemq.com"; // solo el hostname, sin protocolo
const MQTT_PORT = 8884;                  // 8884 = WebSockets seguro (wss) en HiveMQ público

const TOPIC_ESTADO  = `clase/decoder/${GRUPO}/estado`;  // ESP32 -> Web (monitoreo)
const TOPIC_CONTROL = `clase/decoder/${GRUPO}/control`; // Web -> ESP32 (control)

// ID único por cliente para que no choque con otras pestañas/compañeros
const CLIENT_ID = "web_" + GRUPO + "_" + Math.random().toString(16).slice(2, 10);

// ---------- 2. ELEMENTOS DEL DOM ----------
const elEstado      = document.getElementById("estado");
const elDisplayNum  = document.getElementById("display_num");
const elDisplayBin  = document.getElementById("display_bin");
const elOrigen      = document.getElementById("origen");
const elTeclado     = document.getElementById("teclado");
const btnReconectar = document.getElementById("btnReconectar");

// ---------- 3. CLIENTE MQTT ----------
let client = null;

function conectar() {
  elEstado.textContent = "● Conectando...";
  elEstado.className = "indicador conectando";

  client = new Paho.MQTT.Client(MQTT_BROKER, MQTT_PORT, CLIENT_ID);

  client.onConnectionLost = onConnectionLost;
  client.onMessageArrived = onMessageArrived;

  client.connect({
    useSSL: true,   // obligatorio para el puerto 8884
    timeout: 10,
    onSuccess: onConnect,
    onFailure: onFailure,
  });
}

function onConnect() {
  elEstado.textContent = "● Conectado";
  elEstado.className = "indicador conectado";
  client.subscribe(TOPIC_ESTADO);
  console.log("MQTT listo — escuchando en:", TOPIC_ESTADO);
}

function onFailure(err) {
  elEstado.textContent = "● Error de conexión";
  elEstado.className = "indicador error";
  console.error("[MQTT] Falló la conexión:", err.errorMessage);
}

function onConnectionLost(responseObject) {
  if (responseObject.errorCode !== 0) {
    elEstado.textContent = "● Desconectado";
    elEstado.className = "indicador error";
    console.warn("[MQTT] Conexión perdida:", responseObject.errorMessage);
  }
}

// Llega un mensaje del ESP32. Formato esperado: "bits,decimal" ej: "1010,5"
function onMessageArrived(message) {
  try {
    const datos = message.payloadString.trim().split(",");
    if (datos.length !== 2) return;

    const [binario, decimalStr] = datos;

    // Validar antes de mostrar en el DOM (nunca confiar en datos externos)
    const esBinarioValido = /^[01]{4}$/.test(binario);
    const esDecimalValido = /^\d$/.test(decimalStr);
    if (!esBinarioValido || !esDecimalValido) {
      console.warn("[onMessageArrived] Payload con formato inesperado:", message.payloadString);
      return;
    }

    elDisplayNum.textContent = decimalStr;
    elDisplayBin.textContent = "Bits: [ " + binario.split("").join(" ") + " ]";
    elOrigen.textContent = "🎚️ Origen: DIP Switch (ESP32)";
  } catch (ex) {
    // Nunca dejar el catch vacío
    console.error("[onMessageArrived] Error:", ex);
  }
}

// ---------- 4. ENVIAR COMANDOS AL ESP32 ----------
function enviarComando(numero) {
  if (!client || !client.isConnected()) {
    alert("⚠️ Todavía no hay conexión MQTT. Espera un momento o presiona Reconectar.");
    return;
  }
  if (numero < 0 || numero > 9) return; // validar rango

  const mensaje = new Paho.MQTT.Message(String(numero));
  mensaje.destinationName = TOPIC_CONTROL;
  client.send(mensaje);

  elDisplayNum.textContent = numero;
  elOrigen.textContent = "🕹️ Origen: Teclado (Web)";
  console.log("Comando enviado:", numero);
}

// ---------- 5. GENERAR BOTONES 0-9 DINÁMICAMENTE ----------
for (let i = 0; i <= 9; i++) {
  const btn = document.createElement("button");
  btn.textContent = i;
  btn.className = "tecla";
  btn.addEventListener("click", () => enviarComando(i));
  elTeclado.appendChild(btn);
}

btnReconectar.addEventListener("click", conectar);

// ---------- 6. INICIAR ----------
conectar();
