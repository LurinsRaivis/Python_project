import requests
import pandas as pd

# Function to fetch historical weather data
def fetch_historical_weather(latitude, longitude, start_date, end_date, variables):
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": variables,
        "timezone": "auto"  # Automatically determines the timezone
    }

    response = requests.get(base_url, params=params)
    return response.json()

# Example usage
latitude = 56.946  # Latitude for Riga, Latvia
longitude = 24.1059  # Longitude for Riga, Latvia
start_date = "2000-01-01"
end_date = "2009-12-31"
variables = "temperature_2m"  # You can specify other variables as needed

weather_data = fetch_historical_weather(latitude, longitude, start_date, end_date, variables)

# Converting the data to a Pandas DataFrame for analysis
if 'data' in weather_data:
    hourly_data = weather_data['data']
    hourly_dataframe = pd.DataFrame(hourly_data)
    print(hourly_dataframe)
else:
    print("No data available for the given parameters.")
