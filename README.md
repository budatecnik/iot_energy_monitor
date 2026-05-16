# IoT Energy Monitor

Scalable IoT monitoring system using ESP32, MQTT, FastAPI and Docker.

## Overview

This project collects environmental and electrical data from ESP32 devices and sends it through MQTT to a FastAPI backend for storage and visualization.

The system is designed with a modular and scalable architecture for future cloud and edge deployments.

---

## Features

- Temperature monitoring
- Humidity monitoring
- Light state detection
- MQTT communication
- FastAPI backend
- SQLite database
- Real-time dashboard
- Historical data visualization

---

## Architecture

ESP32 → MQTT Broker → FastAPI Backend → SQLite → Dashboard

---

## Technologies Used

- ESP32
- Python
- FastAPI
- MQTT
- SQLite
- Linux
- Docker (in progress)
- Chart.js

---

## Project Structure

``` id="tree1"
iot_energy_monitor/
│
├── backend/
├── esp32/
├── dashboard/
├── docker/
├── README.md
└── docker-compose.yml
