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
import calendar 
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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

    # Format the dates
    start_date = datetime.strptime(cal_start.get_date(), "%m/%d/%y").strftime("%Y-%m-%d")
    end_date = datetime.strptime(cal_end.get_date(), "%m/%d/%y").strftime("%Y-%m-%d")
    data_type = data_type_var.get()

    print("Data type:", data_type, "Type of data_type:", type(data_type))

    # Function to fetch data for a single city
    def fetch_city_data(city):
        if city and city in cities:
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
            return None

    # Fetch data for each city
    df_city1 = fetch_city_data(city1)
    df_city2 = fetch_city_data(city2)

    print("Type of df_city1:", type(df_city1), "Type of df_city2:", type(df_city2))

    if isinstance(data_type, str):
        if df_city1 is not None or df_city2 is not None:
            print(f"Final check - Data type: {data_type}, Type: {type(data_type)}")
            print(f"DF Check - df_city1: {type(df_city1)}, df_city2: {type(df_city2)}")
            process_and_plot_data(df_city1, df_city2, data_type, start_date, end_date, info_label)
        else:
            output_label.config(text="No data to display. Please select a city.")
    else:
        output_label.config(text="Error: data_type is not a string.")

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

def process_and_plot_data(df_city1, df_city2, data_type, start_date, end_date, info_label):
    global canvas_widget
    print(f"Inside process_and_plot_data - df_city1: {type(df_city1)}, df_city2: {type(df_city2)}, Data type: {data_type}, Type: {type(data_type)}")
    print("Processing data...")  # Debugging print statement
    
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Aggregation functions
    aggregation_funcs = {'temperature_2m': np.mean, 'snow_depth': np.mean, 'precipitation': np.sum}

    if data_type not in aggregation_funcs:
        print("Error: Invalid data type provided:", data_type)
        return

    aggregation_func = aggregation_funcs[data_type]

    # Destroy the existing canvas widget if it exists
    if canvas_widget is not None:
        canvas_widget.destroy()
    
    def format_period(date, period_label):
        if period_label == "Month":
            return calendar.month_name[date.month]
        elif period_label == "Year":
            return str(date.year)
        else:
            return date.strftime("%Y-%m-%d")
        
    def compute_time_period(df):
        time_diff = (df['date'].max() - df['date'].min()).days
        if time_diff <= 35:
            return 'D', "Day", "Daily"  # Daily
        elif time_diff <= 180:
            return 'W', "Week","Weekly" # Weekly
        elif time_diff <= 365:
            return 'M', "Month" , "Monthly" # Monthly
        else:
            return 'Y', "Year", "Yearly"  # Yearly
    # Create a figure and axis for the plot
    fig, ax = plt.subplots()

    # Function to plot data for a city
    def plot_city_data(df, city_name, plot_color, plot_type):
        if df is None:
            return

        # Convert 'date' column to datetime and sort
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values('date', inplace=True)

        # Filter data based on start and end dates
        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

        # Aggregate data
        df_agg = df.resample('D', on='date').agg({data_type: aggregation_func})
        
        if data_type == 'temperature_2m':
            ax.axhline(0, color='gray', linestyle='dotted', linewidth=1)

        if data_type == 'temperature_2m' and (df_city1 is None or df_city2 is None):
            # Resampling data for daily maximum and minimum
            daily_max = df.resample('D', on='date')['temperature_2m'].max()
            daily_min = df.resample('D', on='date')['temperature_2m'].min()

            # Plotting max and min temperature lines
            ax.plot(daily_max.index, daily_max.values, color='red', label='Max Temp', linestyle='--')
            ax.plot(daily_min.index, daily_min.values, color='blue', label='Min Temp', linestyle='--')

        # Plotting
        if plot_type == 'line':
            ax.plot(df_agg.index, df_agg[data_type], label=city_name, color=plot_color)
        elif plot_type == 'bar':
            ax.bar(df_agg.index, df_agg[data_type], label=city_name, color=plot_color)

    # Plot data for each city
    plot_city_data(df_city1, city_var.get(), 'black', chart_type_var.get())
    plot_city_data(df_city2, city2_var.get(), 'green', chart_type_var.get())

    # Set x-axis format
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))

    ax.set_xlabel('Date')
    ax.set_ylabel(f'{data_type.capitalize()}')

    plot_title = compute_time_period(df_city1)[2]
    
    title_city_part = city_var.get()
    if df_city2 is not None:
        title_city_part += f' and {city2_var.get()}'

    title_data_type_part = "Snow Depth"if data_type == "snow_depth" else "Temperature" if data_type == "temperature_2m" else data_type.capitalize()

    ax.set_title(f'{title_data_type_part} in {title_city_part} from {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
    ax.legend()
    fig.autofmt_xdate()  # Auto-format date labels
    

    print("Plotting data...")  # Debugging print statement
    

    def compute_city_stats(df, city_name, data_type, start_date, end_date):
        info_text = f"City: {city_name}\n"
            
        period_code, period_label, smtng_rndm = compute_time_period(df)
        df_agg = df.resample(period_code, on='date').mean()
        df_agg_sum = df.resample(period_code, on='date').sum()
            
        if data_type == 'temperature_2m':
            hottest_temp = df_agg[data_type].max()
            coldest_temp = df_agg[data_type].min()
            hottest_period = format_period(df_agg[data_type].idxmax(), period_label)
            coldest_period = format_period(df_agg[data_type].idxmin(), period_label)
            average_temp = df_agg[data_type].mean()

            info_text += f" Hottest {period_label}: {hottest_period} - Temperature: {hottest_temp:.2f}°C\n" \
                        f" Coldest {period_label}: {coldest_period} - Temperature: {coldest_temp:.2f}°C\n" \
                        f' Average Temperature in this period: {average_temp:.2f}°C\n'

        elif data_type == 'snow_depth':
            average_snow_depth = df_agg[data_type].mean()
            info_text += f'Average Snow Depth in this period: {average_snow_depth:.2f} cm\n'

        elif data_type == 'precipitation':
            total_precipitation = df_agg_sum[data_type].sum()
            info_text += f'Total Precipitation in this period: {total_precipitation:.2f} mm\n'

        return info_text

    info_texts = []
    if df_city1 is not None:
        info_texts.append(compute_city_stats(df_city1, city_var.get(), data_type, start_date, end_date))
    if df_city2 is not None:
        info_texts.append(compute_city_stats(df_city2, city2_var.get(), data_type, start_date, end_date))

    # Combine info texts
    combined_info_text = "\n".join(info_texts)
    info_label.configure(text=combined_info_text)

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