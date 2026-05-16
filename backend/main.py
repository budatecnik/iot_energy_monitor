from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from modelos import Base, Lectura

import paho.mqtt.client as mqtt
import json

from datetime import datetime
from zoneinfo import ZoneInfo

# ---------------- CREAR TABLAS ----------------

Base.metadata.create_all(bind=engine)

app = FastAPI()

# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DATOS EN MEMORIA ----------------

datos_actuales = {
    "temperatura": "--",
    "humedad": "--",
    "luz": "--",
    "timestamp": "--"
}

# ---------------- DB ----------------

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()

# ---------------- MQTT ----------------

BROKER = "192.168.1.6"
TOPIC = "iot/esp32/datos"

def on_connect(client, userdata, flags, rc):

    print(f"✅ MQTT conectado (Código: {rc})")

    client.subscribe(TOPIC)

def on_message(client, userdata, msg):

    global datos_actuales

    try:

        payload = msg.payload.decode()

        datos = json.loads(payload)

        datos_actuales = datos

        db = SessionLocal()

        try:

            nueva_lectura = Lectura(
                temperatura=datos.get("temperatura"),
                humedad=datos.get("humedad"),
                luz=datos.get("luz"),
                timestamp=datos.get("timestamp")
            )

            db.add(nueva_lectura)

            db.commit()

            print(
                f"💾 Guardado -> "
                f"T:{datos.get('temperatura')} "
                f"H:{datos.get('humedad')}"
            )

        finally:

            db.close()

    except Exception as e:

        print(f"❌ Error MQTT: {e}")

# ---------------- MQTT CLIENT ----------------

mqtt_client = mqtt.Client()

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

@app.on_event("startup")
def startup_event():

    try:

        mqtt_client.connect(BROKER, 1883, 60)

        mqtt_client.loop_start()

    except Exception as e:

        print(f"⚠️ Error conectando MQTT: {e}")

@app.on_event("shutdown")
def shutdown_event():

    mqtt_client.loop_stop()

    mqtt_client.disconnect()

# ---------------- API ----------------

@app.get("/datos-actuales")
def obtener_actuales():

    return datos_actuales

# ---------------- HORA ARGENTINA ----------------

@app.get("/hora")
def obtener_hora():

    ahora = datetime.now(
        ZoneInfo("America/Argentina/Buenos_Aires")
    )

    return {
        "hora": ahora.strftime("%H:%M:%S")
    }

# ---------------- HISTORIAL ----------------

@app.get("/historial")
def historial(db: Session = Depends(get_db)):

    lecturas = (
        db.query(Lectura)
        .order_by(Lectura.id.desc())
        .limit(20)
        .all()
    )

    return [

        {
            "temperatura": l.temperatura,
            "humedad": l.humedad,
            "timestamp": l.timestamp.split(" ")[1]
            if l.timestamp else "--"
        }

        for l in reversed(lecturas)

    ]

# ---------------- DASHBOARD ----------------

@app.get("/", response_class=HTMLResponse)
def dashboard():

    return """

<!DOCTYPE html>

<html>

<head>

    <title>🌿 Smart Garden Dashboard</title>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>

        body {

            background: #0d1117;
            color: #c9d1d9;

            font-family: 'Segoe UI', sans-serif;

            margin: 0;
            padding: 20px;
        }

        .container {

            max-width: 1100px;
            margin: auto;
        }

        h1 {

            color: #58a6ff;
            text-align: center;

            margin-bottom: 10px;
        }

        #hora {

            text-align: center;

            color: #8b949e;

            margin-bottom: 30px;

            font-size: 1.1em;
        }

        .grid {

            display: flex;

            justify-content: space-around;

            flex-wrap: wrap;

            gap: 20px;

            margin-bottom: 30px;
        }

        .card {

            background: #161b22;

            border: 1px solid #30363d;

            border-radius: 14px;

            padding: 20px;

            width: 220px;

            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }

        .label {

            color: #8b949e;

            text-transform: uppercase;

            font-size: 0.8em;
        }

        .valor {

            display: block;

            margin-top: 10px;

            font-size: 2em;

            font-weight: bold;

            color: #39d353;
        }

        #grafico-container {

            background: #161b22;

            border: 1px solid #30363d;

            border-radius: 14px;

            padding: 20px;
        }

        #grafico {

            height: 400px !important;
        }

    </style>

</head>

<body>

    <div class="container">

        <h1>🌿 Smart Garden Dashboard</h1>

        <div id="hora">

            🇦🇷 Hora Argentina: --:--:--

        </div>

        <div class="grid">

            <div class="card">

                <span class="label">Temperatura</span>

                <span id="temp" class="valor">--</span>

            </div>

            <div class="card">

                <span class="label">Humedad</span>

                <span id="hum" class="valor">--</span>

            </div>

            <div class="card">

                <span class="label">Estado Luz</span>

                <span id="luz" class="valor">--</span>

            </div>

        </div>

        <div id="grafico-container">

            <canvas id="grafico"></canvas>

        </div>

    </div>

<script>

    let chart;

    // ---------------- RELOJ ARGENTINA ----------------

    async function actualizarHora() {

        try {

            const res =
                await fetch('/hora');

            const data =
                await res.json();

            document.getElementById('hora').innerText =
                "🇦🇷 Hora Argentina: " + data.hora;

        } catch (e) {

            console.error("Error hora:", e);
        }
    }

    setInterval(actualizarHora, 1000);

    actualizarHora();

    // ---------------- DASHBOARD ----------------

    async function actualizar() {

        try {

            // DATOS ACTUALES

            const resAct =
                await fetch('/datos-actuales');

            const data =
                await resAct.json();

            document.getElementById('temp').innerText =
                data.temperatura + "°C";

            document.getElementById('hum').innerText =
                data.humedad + "%";

            document.getElementById('luz').innerText =
                data.luz ? "💡 Iluminado" : "🌑 Oscuro";

            // HISTORIAL

            const resHist =
                await fetch('/historial');

            const hist =
                await resHist.json();

            const labels =
                hist.map(d => d.timestamp);

            const temps =
                hist.map(d => d.temperatura);

            const hums =
                hist.map(d => d.humedad);

            // ACTUALIZAR GRÁFICO

            if (chart) {

                chart.data.labels.length = 0;

                labels.forEach(l =>
                    chart.data.labels.push(l)
                );

                chart.data.datasets[0].data.length = 0;

                temps.forEach(t =>
                    chart.data.datasets[0].data.push(t)
                );

                chart.data.datasets[1].data.length = 0;

                hums.forEach(h =>
                    chart.data.datasets[1].data.push(h)
                );

                chart.update();

            } else {

                const ctx =
                    document.getElementById('grafico')
                    .getContext('2d');

                chart = new Chart(ctx, {

                    type: 'line',

                    data: {

                        labels: labels,

                        datasets: [

                            {
                                label: 'Temperatura °C',

                                yAxisID: 'y',

                                data: temps,

                                borderColor: '#ff7b72',

                                backgroundColor: '#ff7b7233',

                                fill: true,

                                tension: 0.3
                            },

                            {
                                label: 'Humedad %',

                                yAxisID: 'y1',

                                data: hums,

                                borderColor: '#79c0ff',

                                backgroundColor: '#79c0ff33',

                                fill: true,

                                tension: 0.3
                            }

                        ]
                    },

                    options: {

                        responsive: true,

                        maintainAspectRatio: true,

                        animation: false,

                        normalized: true,

                        interaction: {

                            intersect: false,

                            mode: 'index'
                        },

                        scales: {

                            y: {

                                type: 'linear',

                                position: 'left',

                                min: 15,

                                max: 35,

                                grid: {
                                    color: '#30363d'
                                },

                                ticks: {
                                    color: '#ff7b72'
                                },

                                title: {

                                    display: true,

                                    text: 'Temperatura °C',

                                    color: '#ff7b72'
                                }
                            },

                            y1: {

                                type: 'linear',

                                position: 'right',

                                min: 0,

                                max: 100,

                                grid: {
                                    drawOnChartArea: false
                                },

                                ticks: {
                                    color: '#79c0ff'
                                },

                                title: {

                                    display: true,

                                    text: 'Humedad %',

                                    color: '#79c0ff'
                                }
                            },

                            x: {

                                grid: {
                                    display: false
                                },

                                ticks: {
                                    color: '#8b949e'
                                }
                            }
                        },

                        plugins: {

                            legend: {

                                labels: {
                                    color: '#c9d1d9'
                                }
                            }
                        },

                        elements: {

                            line: {
                                borderWidth: 3
                            },

                            point: {
                                radius: 0
                            }
                        }
                    }
                });
            }

        } catch (e) {

            console.error(
                "❌ Error actualizando dashboard:",
                e
            );
        }
    }

    // ---------------- LOOP SUAVE ----------------

    async function loop() {

        await actualizar();

        setTimeout(loop, 3000);
    }

    loop();

</script>

</body>

</html>

"""
