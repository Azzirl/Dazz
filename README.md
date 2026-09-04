# ⚡ EMS Control Center & Microgrid SCADA

[![CI/CD Status](https://img.shields.io/badge/CI%2FCD-Passing-success?style=flat-square&logo=github)](#)
[![Python 3.9](https://img.shields.io/badge/Python-3.9-blue.svg?style=flat-square&logo=python)](#)
[![Streamlit](https://img.shields.io/badge/Streamlit-Ready-FF4B4B.svg?style=flat-square&logo=streamlit)](#)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?style=flat-square&logo=docker)](#)

Plataforma integral de gestión de energía (Energy Management System) y análisis dinámico para sistemas de generación distribuida (BESS + PV). 

## 📐 Arquitectura del Sistema
El proyecto está construido bajo una arquitectura modular y escalable lista para producción:
*   **`core/`**: Motor matemático puro para despachos de Peak Shaving y análisis de transitorios electromagnéticos (EMT).
*   **`ui/`**: Componentización de vistas (Dashboard, diagramas unifilares dinámicos, análisis transitorio).
*   **`utils/`**: Herramientas de exportación técnica a AutoCAD (.DXF), código de verificación MATLAB (.m) y memorias técnicas (.DOCX).
*   **`tests/`**: Pruebas unitarias automatizadas mediante `pytest` e Integración Continua (GitHub Actions).

## 📋 Cumplimiento Normativo
Los algoritmos de control de potencia activa y reactiva (Volt/VAR) están diseñados respetando los límites de operación continua:
*   **IEEE 2800**: Capacidad de soporte dinámico de red frente a huecos de tensión e inyección de reactivos para recuperación de fallas[cite: 1].
*   **ARCONEL-001/24 y CREG-0060**: Operación continua para rangos de voltaje de **0.90 p.u. a 1.05 p.u.** y rangos de frecuencia de **58.8 Hz a 61.2 Hz**[cite: 1].

## 🚀 Despliegue Local
1. Clonar el repositorio:
   `git clone https://github.com/TuUsuario/Dazz.git`
2. Instalar dependencias:
   `pip install -r requirements.txt`
3. Ejecutar la aplicación:
   `streamlit run App.py`

## 🐳 Despliegue con Docker
Construcción y ejecución nativa en contenedores para servidores (AWS, DigitalOcean, Google Cloud):
```bash
docker build -t ems-control-center .
docker run -p 8501:8501 ems-control-center
