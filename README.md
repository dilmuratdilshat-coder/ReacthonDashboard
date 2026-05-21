# Yer-Tai Enrichment Plant Dashboard (ReacthonDashboard)

This repository contains the **Yer-Tai Monitoring Dashboard**, designed and built for the **Chemicthon 2026** hackathon. It offers a live, high-fidelity monitoring interface for a copper enrichment plant, integrating technical metrics, equipment states, water intake logs, Z-score anomalies, and background dynamic auto-refresh.

## 🚀 Live Streamlit Cloud Deployment

This app is optimized for Streamlit Cloud!

* **Main App Entry Point:** `final_version/copper_dashboard/app.py`
* **Python Requirements:** Automatically resolved from the root `requirements.txt`

---

## 📂 Project Structure

* **`final_version/copper_dashboard/app.py`:** The production-grade Streamlit entry point.
* **`final_version/copper_dashboard/config.yaml`:** Operational threshold configuration parameters.
* **`final_version/copper_dashboard/data_service.py`:** Backend calculations, shift timeline manager, and live data auto-reload thread.
* **`final_version/copper_dashboard/components/`:** Custom HTML/CSS layouts for the dashboard tabs.
* **`final_version/copper_dashboard/utils/`:** Math packages (Z-Score & Moving Average) and custom Plotly charts.
* **`streamlit_app.py`:** A simplified prototype/mock demonstration.

---

## 💻 Running Locally

Double-click the **`run_dashboard.bat`** file inside the root folder on Windows. It will verify Python, set up a local virtual environment, install requirements, and open the app automatically.
