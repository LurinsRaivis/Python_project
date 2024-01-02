import tkinter as tk
import tkinter.ttk as ttk
from tkcalendar import Calendar
from datetime import datetime
import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import openmeteo_requests
import requests_cache
from retry_requests import retry

# Load city data from JSON
with open('cities.json', 'r') as file:
    cities = json.load(file)

# Function to fetch data and create a graph
def fetch_data():
    city = city_var.get()
    if city in cities:
        latitude = cities[city]["latitude"]
        longitude = cities[city]["longitude"]
    else:
        output_label.config(text="City not found.")
        return

    # Format the dates
    start_date = datetime.strptime(cal_start.get_date(), "%m/%d/%y").strftime("%Y-%m-%d")
    end_date = datetime.strptime(cal_end.get_date(), "%m/%d/%y").strftime("%Y-%m-%d")
    data_type = data_type_var.get()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": data_type
    }

    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Process hourly data
        hourly = response.Hourly()
        hourly_data_values = hourly.Variables(0).ValuesAsNumpy()

        # Create DataFrame for easier processing
        hourly_data = pd.DataFrame({
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s"),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s"),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            data_type: hourly_data_values
        })

        process_and_plot_data(hourly_data, data_type)

    except Exception as e:
        output_label.config(text=str(e))

def process_and_plot_data(df, data_type):
    # Determine time difference
    time_diff = df['date'].max() - df['date'].min()

    if time_diff.days <= 30:
        # Daily averages
        df['date'] = df['date'].dt.date
        plot_title = "Daily Average"
    elif time_diff.days <= 365:
        # Monthly averages
        df['date'] = df['date'].dt.to_period('M')
        plot_title = "Monthly Average"
    else:
        # Yearly averages
        df['date'] = df['date'].dt.to_period('Y')
        plot_title = "Yearly Average"

    # Aggregate data
    df_agg = df.groupby('date').mean()

    # Plotting
    fig, ax = plt.subplots()
    df_agg[data_type].plot(kind='line', ax=ax)
    ax.set_xlabel('Date')
    ax.set_ylabel(data_type)
    ax.set_title(f'{plot_title} {data_type.capitalize()}')

    # Embedding the plot in the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=app)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack()
    canvas.draw()

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

url = "https://archive-api.open-meteo.com/v1/archive"

# Set up the main application window
app = tk.Tk()
app.title("Historical Weather Data Tool")

# Dropdown for city selection
city_var = tk.StringVar()
city_choice = ttk.Combobox(app, textvariable=city_var, values=list(cities.keys()), state='readonly')
city_choice.pack()

# Calendar for start date selection
cal_start = Calendar(app, selectmode='day')
cal_start.pack(padx=10, pady=10)

# Calendar for end date selection
cal_end = Calendar(app, selectmode='day')
cal_end.pack(padx=10, pady=10)

# Dropdown for data type selection
data_types = ['temperature_2m', 'snow_depth', 'precipitation']
data_type_var = tk.StringVar()
data_type_choice = ttk.Combobox(app, textvariable=data_type_var, values=data_types, state='readonly')
data_type_choice.pack()

# Button to fetch data
fetch_button = tk.Button(app, text="Fetch Data", command=fetch_data)
fetch_button.pack()

# Output label
output_label = tk.Label(app, text="")
output_label.pack()

# Run the application
app.mainloop()
