import customtkinter as ctk
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
from tkinter.filedialog import asksaveasfilename
import logging
import tkinter.font as tkFont 

logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

with open('cities.json', 'r') as file:
    cities = json.load(file)

cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

url = "https://archive-api.open-meteo.com/v1/archive"

ctk.set_appearance_mode("System") 
ctk.set_default_color_theme("green")  

app = ctk.CTk()
app.title("Historical Weather Data Tool")
app.attributes('-fullscreen', True)

global canvas_widget, df
canvas_widget = None
df = None

def toggle_fullscreen():
    if app.attributes('-fullscreen'):
        app.attributes('-fullscreen', False)
    else:
        app.attributes('-fullscreen', True)

def toggle_appearance_mode():
    current_mode = ctk.get_appearance_mode()
    new_mode = "Light" if current_mode == "Dark" else "Dark"
    ctk.set_appearance_mode(new_mode)

def initialize_variables():
    global city_var, city2_var, data_type_var, chart_type_var, data_types

    city_var = ctk.StringVar()
    city2_var = ctk.StringVar()
    data_type_var = ctk.StringVar()
    chart_type_var = ctk.StringVar(value="line")
    data_types = ['temperature_2m', 'snow_depth', 'precipitation']

def create_city_selection_frame(parent):
    city_selection_frame = ctk.CTkFrame(parent, fg_color='#aaaaaa')
    city_selection_frame.pack(fill='x', pady=10)

    city1_choice = ctk.CTkComboBox(city_selection_frame, values=list(cities.keys()), variable=city_var, state='readonly')
    city1_choice.pack(pady=10)

    city2_choice = ctk.CTkComboBox(city_selection_frame, values=list(cities.keys()), variable=city2_var, state='readonly')
    city2_choice.pack(side='left', padx=10, pady=10)

    def clear_city2_selection():
        city2_var.set("") 

    clear_city2_button = ctk.CTkButton(city_selection_frame, text="Clear", command=clear_city2_selection)
    clear_city2_button.pack(side='right', padx=10, pady=10)

    return city_selection_frame

def setup_layout(app):
    # Create frames for layout
    top_frame = ctk.CTkFrame(app, fg_color='#aaaaaa')
    graph_frame = ctk.CTkFrame(app, width=1344)
    controls_frame = ctk.CTkFrame(app, width=576, fg_color='#aaaaaa')
    info_frame = ctk.CTkFrame(graph_frame, width=1344, height=100)
    city_selection_frame = create_city_selection_frame(controls_frame)
    
    # Position the frames
    top_frame.pack(side='top', fill='x')
    graph_frame.pack(side='left', fill='both', expand=True)
    controls_frame.pack(side='right', fill='both')
    info_frame.pack(side='top', fill='x')

    return top_frame, graph_frame, controls_frame, info_frame, city_selection_frame  # Return the created frames

def controls(top_frame, controls_frame):
    global output_label, cal_start, cal_end, info_label

    app_title_label = ctk.CTkLabel(top_frame, text="Weather Analysis Tool", font=("Helvetica", 24), text_color='black')
    app_title_label.pack(side='top', pady=10)
    
    cal_start = Calendar(controls_frame, selectmode='day')
    cal_start.pack(pady=10)
    
    cal_end = Calendar(controls_frame, selectmode='day')
    cal_end.pack(pady=10)
    
    data_type_choice = ctk.CTkComboBox(controls_frame, values=data_types, variable=data_type_var, state='readonly')
    data_type_choice.pack(pady=10)
    
    line_chart_rb = ctk.CTkRadioButton(controls_frame, text="Line Chart", variable=chart_type_var, value="line", text_color='black')
    bar_chart_rb = ctk.CTkRadioButton(controls_frame, text="Bar Chart", variable=chart_type_var, value="bar", text_color='black')
    line_chart_rb.pack(pady=5)
    bar_chart_rb.pack(pady=5)
    
    fetch_button = ctk.CTkButton(controls_frame, text="Fetch Data", command=lambda: fetch_data())
    fetch_button.pack(pady=10)
    
    download_button = ctk.CTkButton(controls_frame, text="Download CSV", command=lambda: download_csv())
    download_button.pack(pady=10)
    
    toggle_appearance_button = ctk.CTkButton(controls_frame, text="Toggle Appearance", command=toggle_appearance_mode)
    toggle_appearance_button.pack(pady=10)
    
    exit_fullscreen_button = ctk.CTkButton(controls_frame, text="Windowed/Fullscreen", command=toggle_fullscreen)
    exit_fullscreen_button.pack(pady=10)
    
    output_label = ctk.CTkLabel(controls_frame, text="")
    output_label.pack(pady=10)
    
    quit_button = ctk.CTkButton(controls_frame, text="Quit", command=lambda: app.quit())
    quit_button.pack(side='bottom', pady=10)
    
    label_font = ctk.CTkFont(family="Helvetica", size=20)
    info_label = ctk.CTkLabel(info_frame, height=100, width=400, text="", font=label_font, anchor='center')
    info_label.pack(side='top', fill='x')

def fetch_data():
    global df_city1, df_city2
    city1 = city_var.get()
    city2 = city2_var.get()

    logging.info(f"Fetching data for city1: {city1}" + (f" and city2: {city2}" if city2 else ""))

    # Function to fetch data for a single city
    def fetch_city_data(city):
        if city in cities:
            latitude = cities[city]["latitude"]
            longitude = cities[city]["longitude"]
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": data_type
            }
            try:
                response = openmeteo.weather_api(url, params=params)[0]
                hourly_data_values = response.Hourly().Variables(0).ValuesAsNumpy()
                return pd.DataFrame({
                    "date": pd.date_range(
                        start=pd.to_datetime(response.Hourly().Time(), unit="s"),
                        end=pd.to_datetime(response.Hourly().TimeEnd(), unit="s"),
                        freq=pd.Timedelta(seconds=response.Hourly().Interval()),
                        inclusive="left"
                    ),
                    data_type: hourly_data_values
                })
            except Exception as e:
                output_label.configure(text=str(e))
                logging.error(f"Error fetching data for {city}: {e}")
                return None
        else:
            output_label.configure(text=f"City {city} not found.")
            return None

    # Format the dates
    start_date = datetime.strptime(cal_start.get_date(), "%m/%d/%y").strftime("%Y-%m-%d")
    end_date = datetime.strptime(cal_end.get_date(), "%m/%d/%y").strftime("%Y-%m-%d")
    data_type = data_type_var.get()

    df_city1 = fetch_city_data(city1)
    df_city2 = fetch_city_data(city2) if city2 else None

    if df_city1 is not None:
        process_and_plot_data(df_city1, df_city2, data_type, start_date, end_date)



def download_csv():
    global df
    if df is not None:
        filepath = asksaveasfilename(defaultextension='.csv',
                                     filetypes=[("CSV files", '*.csv')],
                                     title="Save file as")
        if filepath:  # If the user does not cancel the dialog
            df.to_csv(filepath, index=False)
            output_label.config(text="File saved successfully.")
            logging.info(f"CSV file saved: {filepath}")
        else:
            logging.info("CSV file save operation was canceled.")
    else:
        output_label.config(text="No data to save.")
        logging.warning("Attempted to save data, but no data was available.")

def process_and_plot_data(df, data_type, info_label, start_date, end_date):
    global canvas_widget

    print("Processing data...")  # Debugging print statement

    # Destroy the existing canvas widget if it exists
    if canvas_widget is not None:
        canvas_widget.destroy()

    # Determine time difference
    time_diff = (df['date'].max() - df['date'].min()).days

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

    aggregation_func = {'temperature_2m': np.mean, 'snow_depth': np.mean, 'precipitation': np.sum}[data_type]

    # Aggregate data based on the time period and data type
    if data_type == 'precipitation':
        aggregation_func = np.sum  # Sum up precipitation values
    else:
        aggregation_func = np.mean  # Calculate mean for other data types

    print("Plotting data...")  # Debugging print statement
    
    # Create a figure and axis for the plot
    fig, ax = plt.subplots() 

    # Determine the aggregation method based on time_diff
    if time_diff <= 35:
        df_agg = df.groupby(df['date'].dt.date).agg({data_type: aggregation_func})
        plot_title = "Daily"
    elif time_diff <= 180:
        df_agg = df.groupby(df['date'].dt.to_period('W').dt.start_time).agg({data_type: aggregation_func})
        plot_title = "Weekly"
    elif time_diff <= 365:
        df_agg = df.groupby(df['date'].dt.to_period('M').dt.start_time).agg({data_type: aggregation_func})
        plot_title = "Monthly"
    else:
        df_agg = df.groupby(df['date'].dt.to_period('Y').dt.start_time).agg({data_type: aggregation_func})
        plot_title = "Yearly"

    # Plotting
    if data_type == 'temperature_2m' and time_diff <= 35 and chart_type_var.get() == "line":
        # Calculate daily max and min temperatures
        daily_max = df.resample('D', on='date').max()
        daily_min = df.resample('D', on='date').min()

        # Plot average, max, and min temperatures
        df_agg[data_type].plot(kind='line', ax=ax, label='Average Temperature')
        daily_max[data_type].plot(kind='line', ax=ax, color='red', label='Max Temperature')
        daily_min[data_type].plot(kind='line', ax=ax, color='blue', label='Min Temperature')

        # Add a horizontal line at 0°C (freezing point)
        ax.axhline(0, color='grey', linestyle='dotted', linewidth=1)

        # Add legend
        ax.legend()

    elif chart_type_var.get() == "line": df_agg[data_type].plot(kind='line', ax=ax)
    elif chart_type_var.get() == "bar":  df_agg[data_type].plot(kind='bar', ax=ax)
    
    ax.set_xlabel('Date')

    if data_type == 'temperature_2m':
        ax.set_ylabel('Temperature (°C)')
        ax.axhline(0, color='grey', linestyle='dotted', linewidth=1)
    elif data_type == 'snow_depth': 
        ax.set_ylabel('Snow Depth (cm)')
    elif data_type == 'precipitation':
        ax.set_ylabel('Precipitation (mm)')
    
    if data_type == 'temperature_2m':
        ax.set_title(f'{plot_title} average temperature in {city_var.get()} ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})')
    else:
        ax.set_title(f'{plot_title} average {data_type.capitalize()} in {city_var.get()} ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})')

    # Setting x-axis ticks and labels
    ax.xaxis.set_major_locator(plt.MaxNLocator(min(len(df_agg.index), 20)))
    plt.xticks(rotation=45)

    # Update info_label with additional information
    if data_type == 'temperature_2m':
        if time_diff <= 35:  # Daily
            df_agg = df.resample('D', on='date').mean()
            period_format = "%Y-%m-%d"
            period_label = "Day"
        elif time_diff <= 180:  # Weekly
            df_agg = df.resample('W', on='date').mean()
            period_format = "Week of %Y-%m-%d"
            period_label = "Week"
        elif time_diff <= 365:  # Monthly
            df_agg = df.resample('M', on='date').mean()
            period_format = "%Y-%m"
            period_label = "Month"
        else:  # Yearly
            df_agg = df.resample('Y', on='date').mean()
            period_format = "%Y"
            period_label = "Year"

        # Find hottest and coldest periods
        hottest_temp = df_agg[data_type].max()
        coldest_temp = df_agg[data_type].min()
        hottest_period = df_agg[data_type].idxmax().strftime(period_format)
        coldest_period = df_agg[data_type].idxmin().strftime(period_format)
        # Find average temperature
        average_temp = df[data_type].mean()

        # Update info_label
        info_text =     f"Hottest {period_label}: {hottest_period} - Average temperature was {hottest_temp:.2f}°C\n" \
                        f" Coldest {period_label}: {coldest_period} - Average temperature was {coldest_temp:.2f}°C\n" \
                        f'Average temperature in period {start_date} - {end_date} was {average_temp:.2f}°C'
    elif data_type == 'snow_depth':
        # Calculate the average snow depth
        average_snow_depth = df[data_type].mean()
        info_text = f'Average snow depth in period {start_date} - {end_date} was {average_snow_depth:.2f} cm'
    elif data_type == 'precipitation':
        # Calculate the total precipitation
        total_precipitation = df[data_type].sum()
        info_text = f'Total precipitation in period {start_date} - {end_date} was {total_precipitation:.2f} mm'
    
    info_label.configure(text=info_text)
    # Embedding the plot in the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(side='bottom', fill='both', expand=True)
    canvas.draw()

    print("Data plotted.")  # Debugging print statement

def on_close():
    # Terminate the Tkinter application
    app.quit()
    app.destroy()
    logging.info("Application closed")

initialize_variables()
top_frame, graph_frame, controls_frame, info_frame, city_selection_frame  = setup_layout(app)
controls(top_frame, controls_frame)
app.protocol("WM_DELETE_WINDOW", on_close)
app.mainloop()