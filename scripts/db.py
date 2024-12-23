#!/usr/bin/env python
import os
import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine
from dotenv import load_dotenv

class ECommerceDashboard:
    def __init__(self):
        load_dotenv()
        self.db_url = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
        self.engine = create_engine(self.db_url)
    
    def get_data_from_db(self, query):
        with self.engine.connect() as connection:
            return pd.read_sql(query, connection)
    
    def create_sidebar_filters(self):
        st.sidebar.header("Filter Options")
        self.aggregation_type = st.sidebar.selectbox(
            "Select Aggregation Type", ["Daily", "Weekly", "Monthly", "Yearly"]
        )
        self.start_date = st.sidebar.date_input(
            "Start Date", value=pd.to_datetime('2010-12-01')
        )
        self.end_date = st.sidebar.date_input(
            "End Date", value=pd.to_datetime('2011-12-09')
        )
    
    def construct_total_sales_query(self):
        if self.aggregation_type == "Daily":
            return f"""
                SELECT DATE(invoice_date) AS label, SUM(total_price) AS total_sales
                FROM invoice_details id
                JOIN invoices i ON id.invoice_number = i.invoice_number
                WHERE invoice_date BETWEEN '{self.start_date}' AND '{self.end_date}'
                GROUP BY label;
            """
        elif self.aggregation_type == "Weekly":
            return f"""
                SELECT YEARWEEK(invoice_date, 1) AS label, SUM(total_price) AS total_sales
                FROM invoice_details id
                JOIN invoices i ON id.invoice_number = i.invoice_number
                WHERE invoice_date BETWEEN '{self.start_date}' AND '{self.end_date}'
                GROUP BY label;
            """
        elif self.aggregation_type == "Monthly":
            return f"""
                SELECT MONTH(invoice_date) AS label, SUM(total_price) AS total_sales
                FROM invoice_details id
                JOIN invoices i ON id.invoice_number = i.invoice_number
                WHERE invoice_date BETWEEN '{self.start_date}' AND '{self.end_date}'
                GROUP BY label;
            """
        elif self.aggregation_type == "Yearly":
            return f"""
                SELECT YEAR(invoice_date) AS label, SUM(total_price) AS total_sales
                FROM invoice_details id
                JOIN invoices i ON id.invoice_number = i.invoice_number
                WHERE invoice_date BETWEEN '{self.start_date}' AND '{self.end_date}'
                GROUP BY label;
            """
    
    def display_total_sales(self):
        total_sales_query = self.construct_total_sales_query()
        total_sales_data = self.get_data_from_db(total_sales_query)
        
        st.header(f"Total Sales ({self.aggregation_type} Aggregation)")
        
        if not total_sales_data.empty:
            fig = px.pie(
                total_sales_data, 
                names='label', 
                values='total_sales', 
                title=f"Total Sales by {self.aggregation_type}"
            )
            st.plotly_chart(fig)
        else:
            st.write("No data available for the selected period.")
    
    def display_kpis(self):
        queries = {
            "total_sales": "SELECT SUM(total_price) AS total_sales FROM invoice_details;",
            "num_transactions": "SELECT COUNT(DISTINCT invoice_number) AS num_transactions FROM invoices;",
            "average_order_value": """
                SELECT SUM(total_price) / COUNT(DISTINCT invoice_number) AS average_order_value 
                FROM invoice_details;
            """
        }
        total_sales = self.get_data_from_db(queries["total_sales"]).iloc[0, 0]
        num_transactions = self.get_data_from_db(queries["num_transactions"]).iloc[0, 0]
        average_order_value = self.get_data_from_db(queries["average_order_value"]).iloc[0, 0]
        
        st.metric("Total Sales", f"${total_sales:,.2f}")
        st.metric("Number of Transactions", f"{num_transactions:,}")
        st.metric("Average Order Value (AOV)", f"${average_order_value:,.2f}")
    
    def display_customer_segmentation(self):
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
        customer_segmentation = self.get_data_from_db(segmentation_query)
        st.markdown("## Customer Segmentation")
        st.dataframe(customer_segmentation)
        
        segment_counts = customer_segmentation["segment"].value_counts().reset_index()
        segment_counts.columns = ["Segment", "Count"]
        
        fig = px.pie(
            segment_counts, 
            values='Count', 
            names='Segment', 
            title="Customer Segmentation Breakdown",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig)
    
    def display_customer_engagement(self):
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
        customer_engagement = self.get_data_from_db(customer_engagement_query)
        st.subheader("Customer Engagement")
        st.dataframe(customer_engagement)
        
        fig = px.bar(
            customer_engagement, 
            x="customer_id", 
            y="total_spent", 
            color="country", 
            title="Customer Spending by Country"
        )
        st.plotly_chart(fig)
    
    def run(self):
        st.title("E-Commerce Dashboard")
        self.create_sidebar_filters()
        self.display_total_sales()
        self.display_kpis()
        self.display_customer_segmentation()
        self.display_customer_engagement()

# Run the Streamlit app
if __name__ == "__main__":
    dashboard = ECommerceDashboard()
    dashboard.run()