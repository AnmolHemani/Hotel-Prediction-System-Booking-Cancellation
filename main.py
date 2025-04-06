from flask import Flask, render_template, request
import mysql.connector
import matplotlib
matplotlib.use('Agg')  # Must be before importing pyplot
import matplotlib.pyplot as plt
import os
from io import BytesIO
import base64
import pandas as pd
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key_here'

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Jss@1313',
    'database': 'hotel_reservation'

}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

'''def create_chart_base64(fig):
    """Convert matplotlib figure to base64 encoded image"""
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    return base64.b64encode(buf.getbuffer()).decode('ascii')'''

def create_chart_base64(fig):
    """Convert matplotlib figure to base64 encoded image"""
    buf = BytesIO()
    try:
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('ascii')
    finally:
        plt.close(fig)
        buf.close()

@app.route('/')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get summary statistics
        cursor.execute("SELECT COUNT(*) as total_bookings, AVG(avg_price_per_room) as avg_price FROM hotel_reservations")
        stats = cursor.fetchone() or {'total_bookings': 0, 'avg_price': 0}
        
        # Get recent bookings
        cursor.execute("SELECT * FROM hotel_reservations ORDER BY arrival_date DESC LIMIT 10")
        recent_bookings = cursor.fetchall()
    except Exception as e:
        stats = {'total_bookings': 0, 'avg_price': 0}
        recent_bookings = []
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', 
                         stats=stats,
                         recent_bookings=recent_bookings)

@app.route('/group_by')
def group_by():
    group_by = request.args.get('group_by', 'room_type_reserved')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get available columns for grouping
    cursor.execute("SHOW COLUMNS FROM hotel_reservations")
    columns = [col['Field'] for col in cursor.fetchall()]
    
    # Validate group_by parameter
    if group_by not in columns:
        group_by = 'room_type_reserved'
    
    # Get grouped data
    query = f"""
        SELECT {group_by} AS group_name, COUNT(*) AS count 
        FROM hotel_reservations 
        GROUP BY {group_by}
        ORDER BY count DESC
    """
    cursor.execute(query)
    grouped_data = cursor.fetchall()
    
    # Create pie chart
    labels = [row['group_name'] for row in grouped_data]
    sizes = [row['count'] for row in grouped_data]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    plt.title(f'Bookings by {group_by.replace("_", " ").title()}')
    chart_base64 = create_chart_base64(fig)
    
    cursor.close()
    conn.close()
    
    return render_template('group_by.html',
                         grouped_data=grouped_data,
                         group_by=group_by,
                         columns=columns,
                         chart_base64=chart_base64)

@app.route('/top5')
def top5():
    sort_by = request.args.get('sort_by', 'avg_price_per_room')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get available numeric columns for sorting
        cursor.execute("SHOW COLUMNS FROM hotel_reservations")
        numeric_columns = [
            col['Field'] for col in cursor.fetchall() 
            if col['Type'].startswith(('int', 'decimal', 'float'))
        ]
        
        # Validate sort_by parameter
        if sort_by not in numeric_columns:
            sort_by = 'avg_price_per_room'
        
        # Get top 5 records - ensure Booking_ID is selected
        query = f"""
            SELECT Booking_ID, room_type_reserved, no_of_adults, 
                   no_of_children, arrival_date, avg_price_per_room, 
                   booking_status 
            FROM hotel_reservations 
            ORDER BY {sort_by} DESC 
            LIMIT 5
        """
        cursor.execute(query)
        top_records = cursor.fetchall()
        
        # Create bar chart
        labels = [f"Booking {row.get('Booking_ID', 'N/A')}" for row in top_records]
        values = [row.get(sort_by, 0) for row in top_records]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(labels, values, color='skyblue')
        plt.xticks(rotation=45)
        plt.title(f'Top 5 Bookings by {sort_by.replace("_", " ").title()}')
        plt.ylabel(sort_by.replace("_", " ").title())
        chart_base64 = create_chart_base64(fig)
        
    except Exception as e:
        top_records = []
        numeric_columns = []
        chart_base64 = ""
    
    cursor.close()
    conn.close()
    
    return render_template('top5.html',
                         top_records=top_records,
                         sort_by=sort_by,
                         numeric_columns=numeric_columns,
                         chart_base64=chart_base64)

@app.route('/visualizations')
def visualizations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Revenue by meal plan
        cursor.execute("""
            SELECT type_of_meal_plan, SUM(avg_price_per_room) AS revenue 
            FROM hotel_reservations 
            GROUP BY type_of_meal_plan
        """)
        meal_plan_data = cursor.fetchall()
        
        # Bookings by month
        cursor.execute("""
            SELECT DATE_FORMAT(arrival_date, '%Y-%m') AS month, 
                   COUNT(*) AS bookings 
            FROM hotel_reservations 
            GROUP BY month 
            ORDER BY month
        """)
        monthly_data = cursor.fetchall()
        
        # Meal plan chart
        fig1, ax1 = plt.subplots(figsize=(8, 6))
        ax1.bar([x['type_of_meal_plan'] for x in meal_plan_data], 
                [x['revenue'] for x in meal_plan_data])
        plt.title('Revenue by Meal Plan')
        plt.xlabel('Meal Plan')
        plt.ylabel('Revenue')
        meal_plan_chart = create_chart_base64(fig1)
        
        # Monthly bookings chart
        '''fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.plot([x['month'] for x in monthly_data], 
                 [x['bookings'] for x in monthly_data], 
                 marker='o')
        plt.title('Monthly Bookings Trend')
        plt.xlabel('Month')
        plt.ylabel('Number of Bookings')
        plt.xticks(rotation=45)
        monthly_chart = create_chart_base64(fig2)'''
        # Monthly bookings chart - Fixed Version
        try:
            if not monthly_data:
                raise ValueError("No monthly data available")
            
            # Debug print to check data
            print("Monthly Data Sample:", monthly_data[:3])  # Print first 3 entries
            
            months = [x['month'] for x in monthly_data]
            bookings = [x['bookings'] for x in monthly_data]
            
            # Create figure with larger size
            fig2, ax2 = plt.subplots(figsize=(12, 6))
            
            # Plot with styling
            ax2.plot(months, bookings, 
                    marker='o', 
                    linestyle='-', 
                    color='blue',
                    linewidth=2,
                    markersize=8)
            
            # Formatting
            plt.title('Monthly Bookings Trend', fontsize=14, pad=20)
            plt.xlabel('Month', fontsize=12)
            plt.ylabel('Number of Bookings', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            monthly_chart = create_chart_base64(fig2)
            print("Chart generated successfully")
            
        except Exception as e:
            print(f"Error generating chart: {str(e)}")
            monthly_chart = ""
        
    except Exception as e:
        meal_plan_chart = ""
        monthly_chart = ""
    finally:
        cursor.close()
        conn.close()
    
    return render_template('visualizations.html',
                         meal_plan_chart=meal_plan_chart,
                         monthly_chart=monthly_chart)

if __name__ == '__main__':
    app.run(debug=True)