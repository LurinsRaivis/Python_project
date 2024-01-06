#   Importējam vajadzīgās bibliotēkas
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

# Iestatām log failu
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# Ielādējam pilsētu datus no JSON faila
with open('cities.json', 'r') as file:
    cities = json.load(file) 

# Iestatām pieprasījumu kešatmiņu
cache_session = requests_cache.CachedSession('.cache', expire_after=-1) # Kešatmiņa tiek saglabāta .cache direktorijā
retry_session = retry(cache_session, retries=5, backoff_factor=0.2) # Pieprasījumi tiek atkārtoti 5 reizes, ja tie neizdodas
openmeteo = openmeteo_requests.Client(session=retry_session) # Pieprasījumi tiek veikti ar retry_session

# Iestatām pieprasījumu URL
url = "https://archive-api.open-meteo.com/v1/archive" 

# Iestatām izskatu
ctk.set_appearance_mode("System") 
ctk.set_default_color_theme("green")  

# Izveidojam logu
app = ctk.CTk()
app.title("Historical Weather Data Tool") 
app.attributes('-fullscreen', True) # Iestatām logu pilnekrāna režīmā

# Definējam globālos mainīgos
global canvas_widget, df
canvas_widget = None 
df = None

# Funkcija, kas ļauj lietotājam pārslēgties starp pilnekrāna un loga režīmu
def toggle_fullscreen():
    if app.attributes('-fullscreen'):
        app.attributes('-fullscreen', False)
    else:
        app.attributes('-fullscreen', True)

# Funkcija, kas ļauj lietotājam pārslēgties starp tumšo un gaišo režīmu
def toggle_appearance_mode():
    current_mode = ctk.get_appearance_mode()
    new_mode = "Light" if current_mode == "Dark" else "Dark"
    ctk.set_appearance_mode(new_mode)

# Funkcija, kas definē un inicializē globālos mainīgos
def initialize_variables():
    global city_var, city2_var, data_type_var, chart_type_var, data_types

    city_var = ctk.StringVar()
    city2_var = ctk.StringVar()
    data_type_var = ctk.StringVar()
    chart_type_var = ctk.StringVar(value="line")
    data_types = ['temperature_2m', 'snow_depth', 'precipitation']

# Funkcija, kas izveido pilsētu izvēles rāmīti
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

# Funkcija, kas izveido aplikācijas loga izkārtojumu
def setup_layout(app):
    top_frame = ctk.CTkFrame(app, fg_color='#aaaaaa')
    graph_frame = ctk.CTkFrame(app, width=1344)
    controls_frame = ctk.CTkFrame(app, width=576, fg_color='#aaaaaa')
    info_frame = ctk.CTkFrame(graph_frame, width=1344, height=100)
    city_selection_frame = create_city_selection_frame(controls_frame)
    
    top_frame.pack(side='top', fill='x')
    graph_frame.pack(side='left', fill='both', expand=True)
    controls_frame.pack(side='right', fill='both')
    info_frame.pack(side='top', fill='x')

    return top_frame, graph_frame, controls_frame, info_frame, city_selection_frame  

# Funkcija, kas izveido aplikācijas kontrolieru rāmīti (pogas, lauki, u.t.t.)
def controls(top_frame, controls_frame):
    global output_label, cal_start, cal_end, info_label

    app_title_label = ctk.CTkLabel(top_frame, text="Historical Weather Data Analysis Tool", font=("Helvetica", 24), text_color='black')
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
    
    output_label = ctk.CTkLabel(controls_frame, text="", text_color='red')
    output_label.pack(pady=10)
    
    quit_button = ctk.CTkButton(controls_frame, text="Quit", command=lambda: app.quit())
    quit_button.pack(side='bottom', pady=10)
    
    label_font = ctk.CTkFont(family="Helvetica", size=20)
    info_label = ctk.CTkLabel(info_frame, height=100, width=400, text="", font=label_font, anchor='center')
    info_label.pack(side='top', fill='x')

# Funkcija, kas pieņem lietotāja ievadītos datus un izsauc funkciju, kas pieprasa datus no API
def fetch_data():
    global df_city1, df_city2
    city1 = city_var.get() # Pirmās pilsētas nosaukums, kas iegūts no lietotāja
    city2 = city2_var.get() # Otrās pilsētas nosaukums, kas iegūts no lietotāja

    logging.info(f"Fetching data for city1: {city1}" + (f" and city2: {city2}" if city2 else "")) # Ierakstām log failā, kuras pilsētas dati tiek pieprasīti

    start_date = datetime.strptime(cal_start.get_date(), "%m/%d/%y").strftime("%Y-%m-%d") # Sākuma datums, kas iegūts no lietotāja, pārveidots formātā, kas pieņemts API
    end_date = datetime.strptime(cal_end.get_date(), "%m/%d/%y").strftime("%Y-%m-%d")   # Beigu datums, kas iegūts no lietotāja, pārveidots formātā, kas pieņemts API
    data_type = data_type_var.get() # Datu tips, ko lietotājs vēlas iegūt

    #print("Data type:", data_type, "Type of data_type:", type(data_type))

    # Funkcija, kas pieprasa datus no API
    def fetch_city_data(city):
        
        if city and city in cities: # Pārbauda, vai pilsēta ir sarakstā (cities.json)
            latitude = cities[city]["latitude"] # Pilsētas koordinātes, kas iegūtas no cities.json
            longitude = cities[city]["longitude"] 
            params = {  # API pieprasījuma parametri
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": data_type
            }
            try: # Mēģina pieprasīt datus no API
                response = openmeteo.weather_api(url, params=params)[0] # Pieprasa datus no API
                hourly_data_values = response.Hourly().Variables(0).ValuesAsNumpy() # Iegūst datus no API
                return pd.DataFrame({ # Izveido DataFrame, kas satur datus, ar Pandas bibliotēkas palīdzību
                    "date": pd.date_range(  # Pievieno datuma kolonnu
                        start=pd.to_datetime(response.Hourly().Time(), unit="s"), # Pārveido UNIX timestamp uz datetime objektu
                        end=pd.to_datetime(response.Hourly().TimeEnd(), unit="s"),  
                        freq=pd.Timedelta(seconds=response.Hourly().Interval()), # Pievieno intervālu
                        inclusive="left" # Iekļauj sākuma datumu
                    ),
                    data_type: hourly_data_values # Pievieno datus
                })
            except Exception as e: # Ja pieprasījums neizdodas, izvada kļūdas paziņojumu
                output_label.configure(text=str(e)) # Izvada kļūdas paziņojumu
                logging.error(f"Error fetching data for {city}: {e}") # Ierakstām log failā, ja pieprasījums neizdodas
                return None
        else:
            return None

    df_city1 = fetch_city_data(city1) # Pieprasa datus no API
    df_city2 = fetch_city_data(city2) # Pieprasa datus no API

    #print("Type of df_city1:", type(df_city1), "Type of df_city2:", type(df_city2))

    if isinstance(data_type, str): # Pārbauda, vai datu tips ir teksts
        if df_city1 is not None or df_city2 is not None: # Pārbauda, vai ir iegūti dati
            process_and_plot_data(df_city1, df_city2, data_type, start_date, end_date, info_label) # Apstrādā un attēlo datus
        else:
            output_label.config(text="No data to display. Please select a city.") # Izvada paziņojumu, ja nav iegūti dati
    else:
        output_label.config(text="Error: data_type is not a string.") # Izvada paziņojumu, ja datu tips nav teksts

# Funkcija, kas ļauj lietotājam saglabāt datus CSV failā
def download_csv():
    global df
    if df is not None: # Pārbauda, vai ir iegūti dati
        city1_name = city_var.get()
        city2_name = city2_var.get()

        #if-else nosacījums, kas nosaka noklusējuma faila nosaukumu
        if city2_name:  
            default_filename = f"WeatherData_{city1_name}_and_{city2_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:  
            default_filename = f"WeatherData_{city1_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Funkcija, kas saglabā datus CSV failā
        filepath = asksaveasfilename(defaultextension='.csv', filetypes=[("CSV files", '*.csv')], title="Save file as", initialfile=default_filename)  
        
        #if-else nosacījums, kas nosaka, vai dati tika saglabāti vai nē
        if filepath:  
            df.to_csv(filepath, index=False)
            output_label.configure(text="File saved successfully.")
            logging.info(f"CSV file saved: {filepath}")
        else:
            logging.info("CSV file save operation was canceled.")
    else:
        output_label.configure(text="No data to save. Maybe try to fetch data first?")
        logging.warning("Attempted to save data, but no data was available.")

#Funkcija, kas apstrādā un attēlo datus
def process_and_plot_data(df_city1, df_city2, data_type, start_date, end_date, info_label):
    global canvas_widget # Definējam globālo mainīgo canvas_widget, kas satur grafika rāmīti
    global df # Definējam globālo mainīgo df, kas satur datus

    #print(f"Inside process_and_plot_data - df_city1: {type(df_city1)}, df_city2: {type(df_city2)}, Data type: {data_type}, Type: {type(data_type)}")
    #print("Processing data...") 

    # If-elif-else nosacījums, kas pārveido kolonnu nosaukumus, lai lietotājs labāk saprastu excel failu
    if df_city1 is not None and df_city2 is not None:
        df = pd.merge(df_city1, df_city2, on='date', suffixes=(f'_{city_var.get()}', f'_{city2_var.get()}')) # Apvieno divus DataFrame, ja ir iegūti dati abām pilsētām
    elif df_city1 is not None:
        df = df_city1.rename(columns={col: f'{col}_{city_var.get()}' for col in df_city1.columns if col != 'date'})
    elif df_city2 is not None:
        df = df_city2.rename(columns={col: f'{col}_{city2_var.get()}' for col in df_city2.columns if col != 'date'})
    else:
        df = None
    
    # Pārveido sākuma un beigu datumus datetime objektos
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Definējam funkcijas, kas aprēķina vidējo temperatūru, sniega biezumu un nokrišņu daudzumu
    aggregation_funcs = {'temperature_2m': 'mean', 'snow_depth': 'mean', 'precipitation': 'sum'}

    # Definējam funkciju, kas aprēķina vidējo temperatūru, sniega biezumu un nokrišņu daudzumu
    aggregation_func = aggregation_funcs[data_type]

    # Ja jau ir izveidots grafika rāmītis, to izdzēš (lai varētu attēlot jaunus datus)
    if canvas_widget is not None:
        canvas_widget.destroy()
    
    # Funkcija, kas formatē laika periodu
    def format_period(date, period_label):
        if period_label == "Month": # Pārveido mēneša numuru par mēneša nosaukumu
            return calendar.month_name[date.month]
        elif period_label == "Year": # Pārveido gadu par gadas skaitli
            return str(date.year)
        else:
            return date.strftime("%Y-%m-%d") 

    # Funkcija, kas aprēķina laika periodu   
    def compute_time_period(df):
        time_diff = (df['date'].max() - df['date'].min()).days # Aprēķina laika periodu, ko lietotājs izvēlējās
        if time_diff <= 35: # Ja laika periods ir mazāks par 35 dienām, tad dati tiek attēloti dienās
            return 'D', "Day", "Daily"  
        elif time_diff <= 180: # Ja laika periods ir mazāks par 180 dienām, tad dati tiek attēloti nedēļās
            return 'W', "Week","Weekly" 
        elif time_diff <= 365: # Ja laika periods ir mazāks par 365 dienām, tad dati tiek attēloti mēnešos
            return 'M', "Month" , "Monthly" 
        else: # Ja laika periods ir lielāks par 365 dienām, tad dati tiek attēloti gados
            return 'Y', "Year", "Yearly"  

    fig, ax = plt.subplots() # Izveidojam grafika rāmīti

    # Funkcija, kas attēlo datus
    def plot_city_data(df, city_name, plot_color, plot_type):
        
        if df is None: # Pārbauda, vai ir iegūti dati
            return

        df['date'] = pd.to_datetime(df['date']) # Pārveido datumu kolonnu datetime objektos
        df.sort_values('date', inplace=True) # Sakārto datus pēc datuma

        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))] # Izvēlas datus, kas atrodas starp sākuma un beigu datumu

        df_agg = df.resample('D', on='date').agg({data_type: aggregation_func}) # Apvieno datus pēc dienām
        
        if data_type == 'temperature_2m': # Ja dati ir temperatūras dati, tad tiek pievienota līnija, kas atbilst 0°C
            ax.axhline(0, color='gray', linestyle='dotted', linewidth=1)

        # if nosacījums, kas pārbauda, vai dati ir par temperatūras un ir izvēlēta tikai viena pilsēta
        if data_type == 'temperature_2m' and (df_city1 is None or df_city2 is None): 
            daily_max = df.resample('D', on='date')['temperature_2m'].max() # Aprēķina maksimālo temperatūru
            daily_min = df.resample('D', on='date')['temperature_2m'].min() # Aprēķina minimālo temperatūru

            ax.plot(daily_max.index, daily_max.values, color='red', label='Max Temp', linestyle='--') # Attēlo maksimālo temperatūru
            ax.plot(daily_min.index, daily_min.values, color='blue', label='Min Temp', linestyle='--') # Attēlo minimālo temperatūru

        # if-elif nosacījums, kas pārbauda, vai ir izvēlēt līnijas vai stabiņu grafiks
        if plot_type == 'line': 
            ax.plot(df_agg.index, df_agg[data_type], label=city_name, color=plot_color) # Attēlo līniju
        elif plot_type == 'bar':
            ax.bar(df_agg.index, df_agg[data_type], label=city_name, color=plot_color) # Attēlo stabiņu

    plot_city_data(df_city1, city_var.get(), 'black', chart_type_var.get()) # Attēlo pirmās pilsētas datus
    plot_city_data(df_city2, city2_var.get(), 'green', chart_type_var.get()) # Attēlo otrās pilsētas datus
    
    period_label = compute_time_period(df_city1)[1] # Mainīgajam period_label piešķiram laika periodu
    period_code = compute_time_period(df_city1)[0] # Mainīgajam period_code piešķiram laika perioda "kodu"
    
    if period_label in ["Day", "Week", "Month", "Year"]: # Ja laika periods ir dienās, nedēļās, mēnešos vai gados, tad tiek attēlotas vertikālas līnijas, kas atbilst laika periodam

        dates_range = pd.date_range(start=start_date, end=end_date, freq=period_code) # Izveido datu diapazonu
        for date in dates_range:
            ax.axvline(date, color='grey', linestyle='dotted', alpha=0.5)

    ax.xaxis.set_major_locator(mdates.AutoDateLocator()) # Funkcija, kas automātiski izvēlas datu intervālu, un pārveido x asi, lai tā būtu lasāmāka
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator())) # Funkcija, kas izēlās labākos datus, ko norādīt x asī

    ax.set_xlabel('Date') # Pievieno x ass nosaukumu

    # if-elif-else nosacījums, kas nosaka y ass nosaukumu
    if data_type == 'temperature_2m':
        ax.set_ylabel('Temperature (°C)')
    elif data_type == 'snow_depth':
        ax.set_ylabel('Snow Depth (cm)')    
    else:    
        ax.set_ylabel('Precipitation (mm)')

    # Mainīgais, kas palīdz izveidot skaistāku grafika nosaukumu
    title_city_part = city_var.get() 
    if df_city2 is not None:
        title_city_part += f' and {city2_var.get()}'

    title_data_type_part = "Snow Depth"if data_type == "snow_depth" else "Temperature" if data_type == "temperature_2m" else data_type.capitalize() 
    ax.set_title(f'{title_data_type_part} in {title_city_part} from {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}') # Tiek izveidots grafika nosaukums
    
    ax.legend() # Tiek pievienota grafika leģenda
    fig.autofmt_xdate() # Funkcija, kas automātiski formatē datumu nosaukumus uz x ass, lai izskatītos labāk
    
    #print("Plotting data...") 
    
    # Funkcija, kas izrēķina dažādu statistiku par laikapstākļiem dotajā periodā
    def compute_city_stats(df, city_name, data_type, start_date, end_date):
        info_text = f"City: {city_name}\n"
            
        period_code, period_label, smtng_rndm = compute_time_period(df) # Jauneim mainīgajiem tiek dotas vērtības no compute_time_period funkcijas
        df_agg = df.resample(period_code, on='date').mean() # Funkcija kas paŗveido dataframe, un izrēķina vidējo vērtību dotajā periodā
        df_agg_sum = df.resample(period_code, on='date').sum() # Funkcija kas paŗveido dataframe, un izrēķina kopējo vērtību dotajā periodā
            
        if data_type == 'temperature_2m':
            hottest_temp = df_agg[data_type].max() # Mainīgais, kas satur maksimālo datu tipa vērtību noteiktā paeriodā
            coldest_temp = df_agg[data_type].min() # Mainīgais, kas satur minimālo datu tipa vērtību noteiktā paeriodā
            hottest_period = format_period(df_agg[data_type].idxmax(), period_label) # Mainīgais, kas satur laika periodu, kurā ir maksimālā datu tipa vērtība
            coldest_period = format_period(df_agg[data_type].idxmin(), period_label) # Mainīgais, kas satur laika periodu, kurā ir minimālā datu tipa vērtība
            average_temp = df_agg[data_type].mean() # Mainīgais, kas satur vidējo datu tipa vērtību noteiktā paeriodā

            # Teksts, kas tiek pievienots info_label un satur dažādu statistiku par laikapstākļiem dotajā periodā
            info_text += f" Hottest {period_label}: {hottest_period} - Average Temperature: {hottest_temp:.2f}°C\n" \
                        f" Coldest {period_label}: {coldest_period} - Average Temperature: {coldest_temp:.2f}°C\n" \
                        f' Average Temperature in this period: {average_temp:.2f}°C\n'

        elif data_type == 'snow_depth': # Ja dati ir par sniega biezumu, tad tiek aprēķināta vidējā sniega biezuma vērtība
            average_snow_depth = df_agg[data_type].mean()
            info_text += f'Average Snow Depth in this period: {average_snow_depth:.2f} cm\n'

        elif data_type == 'precipitation': # Ja dati ir par nokrišņu daudzumu, tad tiek aprēķināts kopējais nokrišņu daudzums
            total_precipitation = df_agg_sum[data_type].sum()
            info_text += f'Total Precipitation in this period: {total_precipitation:.2f} mm\n'

        return info_text # Funkcija atgriež tekstu, kas satur dažādu statistiku par laikapstākļiem dotajā periodā

    info_texts = [] # Mainīgais, kas satur tekstu, kas tiek pievienots info_label un satur dažādu statistiku par laikapstākļiem dotajā periodā
    
    if df_city1 is not None: # Ja ir iegūti dati par pirmo pilsētu, tad tiek izsaukta funkcija, kas aprēķina dažādu statistiku par laikapstākļiem dotajā periodā
        info_texts.append(compute_city_stats(df_city1, city_var.get(), data_type, start_date, end_date))
    if df_city2 is not None: 
        info_texts.append(compute_city_stats(df_city2, city2_var.get(), data_type, start_date, end_date))

    combined_info_text = "\n".join(info_texts) # Apvieno tekstu, kas satur dažādu statistiku par laikapstākļiem dotajā periodā
    info_label.configure(text=combined_info_text) # Pievieno šo tekstu aplikācijas logam

    canvas = FigureCanvasTkAgg(fig, master=graph_frame) # Canvas mainīgais, satur grafika rāmīti, kas tiks ievietots graph_frame rāmītī
    canvas_widget = canvas.get_tk_widget() # Mainīgajam canvas_widget piešķiram grafika rāmīti
    canvas_widget.pack(side='bottom', fill='both', expand=True) # Šim mainīgajam tiek definēta atrašanās vieta un izmērs
    canvas.draw() # Attēlo grafiku

    #print("Data plotted.")  

# Funkcija, kas tiek izsaukta, kad lietotājs aizver aplikāciju
def on_close():
    app.quit() # Aizver aplikāciju
    app.destroy() # Izdzēš aplikācijas logu
    logging.info("Application closed") # Ierakstām log failā, ka aplikācija ir aizvērta

initialize_variables() # Definējam globālos mainīgos
top_frame, graph_frame, controls_frame, info_frame, city_selection_frame  = setup_layout(app) # Izveidojam aplikācijas loga izkārtojumu
controls(top_frame, controls_frame) # Izveidojam aplikācijas kontrolieru rāmīti
app.protocol("WM_DELETE_WINDOW", on_close) # Izsauc funkciju, kas tiek izsaukta, kad lietotājs aizver aplikāciju
app.mainloop() # Izsauc aplikāciju