# Harvard-Artifacts-Collection-Data-Engineering-Analytics-App
An end-to-end data engineering and analytics application built using the Harvard Art Museums API.   This project demonstrates real-world ETL pipelines, SQL analytics, and interactive data visualization using Streamlit.

---

## 🚀 Project Overview

The application allows users to:
- Collect artifact data dynamically from the Harvard Art Museums API
- Perform ETL (Extract, Transform, Load) operations
- Store structured data into SQL databases
- Run analytical SQL queries
- Visualize query results using interactive dashboards

The project simulates a real-world data pipeline used in analytics and data engineering roles.

---

## 🧱 Architecture

**API → ETL → SQL → Analytics → Visualization**

- **API Source:** Harvard Art Museums API  
- **ETL:** Python (Requests, Pandas)  
- **Database:** MySQL / TiDB Cloud  
- **Backend Logic:** Python  
- **Frontend:** Streamlit  
- **Visualization:** Plotly  

---

## ⚙️ Features

### 🔑 API Integration
- Secure API key configuration
- Pagination handling
- Rate-limited data collection

### 🔄 ETL Pipeline
- Extracts artifact metadata, media details, and color data
- Transforms nested JSON into relational tables
- Batch inserts into SQL for performance optimization

### 🗄️ SQL Database Design
- `artifactmetadata`
- `artifactmedia`
- `artifactcolors`
- Proper foreign key relationships

### 📊 SQL Analytics Dashboard
- 20 predefined analytical SQL queries
- Dynamic query execution
- Tabular results with auto-generated visualizations

### 📈 Visualization
- Interactive bar charts using Plotly
- Real-time analytics based on SQL query outputs

---

## 🛠️ Tech Stack

- Python
- Streamlit
- Pandas
- Requests
- MySQL / TiDB Cloud
- Plotly
- Harvard Art Museums API

---

## 📌 Sample Insights
- Artifact distribution by culture and century
- Media and image availability analysis
- Color usage patterns across artifacts
- Department-wise artifact counts

---

## 🧪 How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
