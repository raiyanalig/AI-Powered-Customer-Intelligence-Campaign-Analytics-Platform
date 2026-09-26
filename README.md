# AI Retail Analytics Copilot

An AI-powered retail analytics application for exploring customer behaviour, sales performance, campaign results, and business metrics through an interactive Streamlit dashboard.

It also includes an AI Analyst that lets users ask business questions in plain English and get validated SQL queries, results, insights, and recommendations.

## 🚀 Live Demo

[Launch AI Retail Analytics Copilot](https://ai-powered-customer-intelligence-campaign-analytics-platform-h.streamlit.app/)

## 📌 What this project does

Retail teams often have large amounts of customer and transaction data but need SQL knowledge to get useful answers.

This project brings common analytics into one application:

* Business dashboard with KPIs and charts
* Customer 360 view
* RFM customer segmentation
* Campaign funnel and performance analysis
* Customer retention analysis
* SQL performance comparison
* Natural language AI Analyst
* Read-only SQL validation for safer AI queries

## 🧩 Main Features

### Dashboard

Provides a quick view of:

* Total revenue
* Orders
* Customers
* Average order value
* Monthly trends
* Revenue by category
* Campaign performance
* Retention

### Customer 360

Shows customer-level information such as:

* Total orders
* Total spend
* Average order value
* Last purchase
* RFM score
* Customer segment
* Loyalty tier

### RFM Analysis

Customers are grouped using:

* **Recency** — how recently they purchased
* **Frequency** — how often they purchased
* **Monetary** — how much they spent

The application uses five score buckets for each dimension and assigns segments such as Champions, Loyal Customers, New Customers, Potential Loyalists, At Risk, and Lost Customers.

### Campaign Analytics

Tracks campaign performance across the funnel:

```text
Sent → Opened → Clicked → Converted
```

It also shows:

* Conversion rate
* Attributed revenue
* ROI
* Campaign rankings
* Channel performance

### SQL Performance Lab

The application demonstrates SQL optimization using real PostgreSQL execution plans.

Examples include:

* Function-based date filtering vs index-friendly range filtering
* Correlated subqueries vs JOIN + GROUP BY
* Index usage
* Query plan comparison

### AI Analyst

Users can ask questions such as:

> Which product category generated the highest revenue?

The system then:

```text
User Question
      ↓
DeepSeek LLM
      ↓
Generated SQL
      ↓
SQL Validation
      ↓
PostgreSQL
      ↓
Query Result
      ↓
Business Insight
      ↓
Recommendation
```

The generated SQL is shown to the user so the result remains understandable and traceable.

## 🏗️ Architecture

```mermaid
flowchart TD

    U[Business User] --> UI[Streamlit UI]

    UI --> A[Analytics Engine]
    UI --> AI[AI Analyst]
    UI --> DB[Database Layer]

    A --> PG[(PostgreSQL)]
    DB --> PG

    AI --> LLM[DeepSeek LLM]
    LLM --> AI

    AI --> V[SQL Validation]
    V --> PG

    PG --> AI
    AI --> UI

    GD[Data Generator] --> PG
```

## 🤖 AI Analyst Workflow

```mermaid
flowchart LR

    Q[Business Question]
    L[DeepSeek LLM]
    S[Generated SQL]
    V[SQL Validation]
    DB[(PostgreSQL)]
    R[Query Result]
    I[Insight + Recommendation]

    Q --> L
    L --> S
    S --> V
    V --> DB
    DB --> R
    R --> L
    L --> I
```

## 🗄️ Database

The application uses PostgreSQL with the following main tables:

```text
customers
orders
campaigns
campaign_events
```

### Schema

```mermaid
erDiagram

    CUSTOMERS {
        int customer_id PK
        string name
        string city
        date signup_date
        string loyalty_tier
    }

    ORDERS {
        int order_id PK
        int customer_id FK
        date order_date
        decimal amount
        string product_category
        string payment_method
    }

    CAMPAIGNS {
        int campaign_id PK
        string campaign_name
        string channel
        decimal budget
        date start_date
        date end_date
    }

    CAMPAIGN_EVENTS {
        int event_id PK
        int campaign_id FK
        int customer_id FK
        string event_type
        date event_date
    }

    CUSTOMERS ||--o{ ORDERS : places
    CUSTOMERS ||--o{ CAMPAIGN_EVENTS : receives
    CAMPAIGNS ||--o{ CAMPAIGN_EVENTS : generates
```

## 📊 Dataset

The project uses a reproducible synthetic dataset containing:

| Data            | Records |
| --------------- | ------: |
| Customers       |  20,000 |
| Orders          | 150,000 |
| Campaigns       |     100 |
| Campaign Events | 300,000 |

The data is generated using `generate_data.py` and loaded into PostgreSQL.

## 🔐 Security

The AI Analyst includes basic safeguards before executing generated SQL:

* Only `SELECT` and `WITH` queries are accepted
* Multiple SQL statements are rejected
* Dangerous SQL keywords are blocked
* System catalog access is restricted
* Query results have a configurable row limit
* API keys and database credentials are stored through environment variables or Streamlit Secrets
* `.env` is excluded from Git

For stronger production isolation, the application can use a PostgreSQL role with read-only permissions.

## 🛠️ Technology Stack

**Language**

* Python

**Application**

* Streamlit

**Database**

* PostgreSQL
* SQLAlchemy
* Psycopg 3

**Data & Analytics**

* Pandas
* NumPy
* SQL

**Visualization**

* Plotly

**AI**

* DeepSeek API
* OpenAI-compatible SDK

**Deployment**

* Streamlit Community Cloud
* Neon PostgreSQL

**Version Control**

* Git
* GitHub

## 📁 Project Structure

```text
ai-retail-analytics/
│
├── app.py                # Streamlit application
├── database.py           # Database engine, schema and queries
├── generate_data.py      # Synthetic data generation and loading
├── analytics.py          # SQL analytics, RFM and retention
├── ai_analyst.py         # NL → SQL, validation and insights
│
├── screenshots/          # Application screenshots
│   ├── dashboard.png
│   ├── rfm-analysis.png
│   ├── campaign-analytics.png
│   └── ai-analyst.png
│
├── requirements.txt
├── runtime.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🖥️ Screenshots

### Dashboard

<img width="2872" height="1312" alt="Screenshot 2026-09-26 224559" src="https://github.com/user-attachments/assets/0118a266-0abd-4143-8ea1-6914a35fbc98" />


### RFM Analysis

<img width="2840" height="1338" alt="Screenshot 2026-09-26 224724" src="https://github.com/user-attachments/assets/dda5c4c1-5bc1-438a-b8b9-2043f7ca5452" />


### Campaign Analytics

<img width="2872" height="1366" alt="Screenshot 2026-09-26 230719" src="https://github.com/user-attachments/assets/9acffa14-28ed-43f2-b8b4-4bcdaec31ce2" />


### AI Analyst

<img width="2832" height="1340" alt="Screenshot 2026-09-26 224651" src="https://github.com/user-attachments/assets/cad49190-06d0-4335-a13c-3f59af3e512d" />


## ⚙️ Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/raiyanalig/AI-Powered-Customer-Intelligence-Campaign-Analytics-Platform.git

cd AI-Powered-Customer-Intelligence-Campaign-Analytics-Platform
```

### 2. Create a virtual environment

#### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
DATABASE_URL="postgresql+psycopg://user:password@host/db?sslmode=require"

DEEPSEEK_API_KEY="your_api_key"

DEEPSEEK_BASE_URL="https://api.deepseek.com"

DEEPSEEK_MODEL="deepseek-chat"

AI_ROW_LIMIT="200"
```

### 5. Generate the dataset

```bash
python generate_data.py --reset
```

### 6. Start the application

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## ☁️ Deployment

The application is deployed using:

```text
GitHub
   ↓
Streamlit Community Cloud
   ↓
Streamlit Application
   ↓
Neon PostgreSQL
   ↓
DeepSeek API
```

For deployment:

1. Create a managed PostgreSQL database.
2. Set `DATABASE_URL` to the cloud database.
3. Run `python generate_data.py --reset` to load the dataset.
4. Push the project to GitHub.
5. Deploy `app.py` through Streamlit Community Cloud.
6. Add the required values through Streamlit Secrets.

## 📈 Analytics Covered

The application currently includes analytics such as:

* Total revenue
* Monthly revenue
* Total orders
* Average order value
* Total customers
* Active customers
* Returning customers
* Top customers
* Revenue by category
* Campaign performance
* Campaign conversion rate
* RFM segmentation
* Monthly retention
* Customers at risk

## 🎯 Why I Built This

I built this project to combine data analytics with application development and GenAI.

The goal was not only to create charts but to build a complete workflow where a business user can explore data, ask questions in natural language, and get understandable answers from the underlying database.

## 🔮 Future Improvements

* Analysis history and saved reports
* More reliable NL-to-SQL using a semantic layer
* Cohort-based retention analysis
* Churn prediction
* Read-only PostgreSQL role with stronger isolation
* Automated testing for analytics and SQL validation
* Scheduled data refresh

## 👤 Author

**Raiyan Ali**

B.Tech Computer Science Engineering
Lovely Professional University

GitHub: [@raiyanalig](https://github.com/raiyanalig)

---

⭐ Built with Python, PostgreSQL, Streamlit and Generative AI.
