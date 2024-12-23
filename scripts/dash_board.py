#!/usr/bin/env python
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import plotly.express as px
import matplotlib.pyplot as plt
# Load environment variables
load_dotenv()

# Create the database connection URL
db_url = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)

# Function to execute a SQL query and return a DataFrame
def get_data_from_db(query):
    with engine.connect() as connection:
        result = pd.read_sql(query, connection)
    return result

# Streamlit App
st.title("E-Commerce Dashboard")


# Sidebar filter options
st.sidebar.header("Filter Options")
aggregation_type = st.sidebar.selectbox("Select Aggregation Type", ["Daily", "Weekly", "Monthly", "Yearly"])

# Date range filter
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime('2010-12-01'))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime('2011-12-09'))

# Query construction based on aggregation type
if aggregation_type == "Daily":
    total_sales_query = f"""
        SELECT DATE(invoice_date) AS label, SUM(total_price) AS total_sales
        FROM invoice_details id
        JOIN invoices i ON id.invoice_number = i.invoice_number
        WHERE invoice_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY label;
    """
elif aggregation_type == "Weekly":
    total_sales_query = f"""
        SELECT YEARWEEK(invoice_date, 1) AS label, SUM(total_price) AS total_sales
        FROM invoice_details id
        JOIN invoices i ON id.invoice_number = i.invoice_number
        WHERE invoice_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY label;
    """
elif aggregation_type == "Monthly":
    total_sales_query = f"""
        SELECT MONTH(invoice_date) AS label, SUM(total_price) AS total_sales
        FROM invoice_details id
        JOIN invoices i ON id.invoice_number = i.invoice_number
        WHERE invoice_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY label;
    """
elif aggregation_type == "Yearly":
    total_sales_query = f"""
        SELECT YEAR(invoice_date) AS label, SUM(total_price) AS total_sales
        FROM invoice_details id
        JOIN invoices i ON id.invoice_number = i.invoice_number
        WHERE invoice_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY label;
    """


total_sales_data = get_data_from_db(total_sales_query)

# Display the filtered data in a pie chart
st.header(f"Total Sales ({aggregation_type} Aggregation)")

if not total_sales_data.empty:
    # Using Plotly Express for pie chart
    fig = px.pie(total_sales_data, names='label', values='total_sales', title=f'Total Sales by {aggregation_type}')
    
    # Display the pie chart in Streamlit
    st.plotly_chart(fig)
else:
    st.write("No data available for the selected period.")

# Queries
total_sales_query = "SELECT SUM(total_price) AS total_sales FROM invoice_details;"
num_transactions_query = "SELECT COUNT(DISTINCT invoice_number) AS num_transactions FROM invoices;"
average_order_value_query = """
    SELECT SUM(total_price) / COUNT(DISTINCT invoice_number) AS average_order_value 
    FROM invoice_details;
"""

customer_engagement_query = """
    SELECT 
        c.customer_id,
        c.country,
        SUM(id.total_price) AS total_spent,
        COUNT(DISTINCT i.invoice_number) AS purchase_count,
        CAST(MAX(i.invoice_date) AS DATE) AS last_purchase_date
    FROM customers c
    JOIN invoices i ON c.customer_id = i.customer_id
    JOIN invoice_details id ON i.invoice_number = id.invoice_number
    GROUP BY c.customer_id, c.country;
"""
# customer Segmentation Query
segmentation_query = """
 SELECT 
    c.customer_id,
    c.country,
    CASE 
        WHEN DATEDIFF('2011-12-09', CAST(MAX(i.invoice_date) AS DATE)) <= 30 
             AND COUNT(DISTINCT i.invoice_number) > 5 
             AND SUM(id.total_price) > 1000 THEN 'Loyal'
        WHEN DATEDIFF('2011-12-09', CAST(MAX(i.invoice_date) AS DATE)) > 60 
             AND SUM(id.total_price) > 500 THEN 'At-Risk'
        WHEN DATEDIFF('2011-12-09', CAST(MAX(i.invoice_date) AS DATE)) <= 60 
             AND SUM(id.total_price) BETWEEN 500 AND 1000 THEN 'Potential'
        ELSE 'Low-Value'
    END AS segment
FROM customers c
JOIN invoices i ON c.customer_id = i.customer_id
JOIN invoice_details id ON i.invoice_number = id.invoice_number
GROUP BY c.customer_id, c.country;
"""

# Fetch data
total_sales = get_data_from_db(total_sales_query).iloc[0, 0]
num_transactions = get_data_from_db(num_transactions_query).iloc[0, 0]
average_order_value = get_data_from_db(average_order_value_query).iloc[0, 0]
customer_engagement = get_data_from_db(customer_engagement_query)
customer_segmentation = get_data_from_db(segmentation_query)


# Add segmentation labels
segment_counts = customer_segmentation['segment'].value_counts().reset_index()
segment_counts.columns = ['Segment', 'Count'] 

# Display KPIs in Streamlit
st.metric("Total Sales", f"${total_sales:,.2f}")
st.metric("Number of Transactions", f"{num_transactions:,}")
st.metric("Average Order Value (AOV)", f"${average_order_value:,.2f}")

st.markdown("## Customer Segmentation")
st.dataframe(customer_segmentation)

segment_counts = customer_segmentation["segment"].value_counts().reset_index()
segment_counts.columns = ["segment", "count"]
fig = px.pie(
    segment_counts, 
    values='count', 
    names='segment', 
    title="Customer Segmentation Breakdown",
    color_discrete_sequence=px.colors.qualitative.Set3
)

st.plotly_chart(fig)



# Display Customer Engagement Table
st.subheader("Customer Engagement")
st.dataframe(customer_engagement)



fig = px.bar(customer_engagement, x="customer_id", y="total_spent", color="country", title="Customer Spending by Country")
st.plotly_chart(fig)

