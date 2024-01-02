from flask import Flask, render_template, request, jsonify
import random
import requests

# Assuming you have a module named 'country_data' with a dictionary 'countries_neighbors'
from country_data import countries_neighbors

app = Flask(__name__)

@app.route('/')
def index():
    # Render an HTML page with a map
    return render_template('index.html')

@app.route('/guess', methods=['POST'])
def guess():
    data = request.json
    country = data['country']
    # Process the guess and determine if it's a neighboring country
    # For now, let's just return the guessed country
    response = {
        'country': country,
        'result': 'success'  # You will have your game logic determine the actual result
    }
    return jsonify(response)

@app.route('/random-countries')
def random_countries():
    all_countries = get_all_countries()
    if all_countries:
        start_country = random.choice(all_countries)
        end_country = random.choice([country for country in all_countries if country != start_country])
        return jsonify({
            'start_country': start_country,
            'target_country': end_country
        })
    else:
        return jsonify({'error': 'Unable to fetch countries'}), 500

@app.route('/check-neighbor', methods=['POST'])
def check_neighbor():
    data = request.json
    print(f"Data received: {data}")  # Debug print
    country_code1 = get_country_code(data['current_country'])
    country_code2 = get_country_code(data['guess'])
    print(f"Country codes: {country_code1}, {country_code2}")  # Debug print

    if country_code1 and country_code2:
        is_neighbor = check_if_neighbor(country_code1, country_code2)
        return jsonify({'is_neighbor': is_neighbor})
    else:
        return jsonify({'error': 'Country not found'}), 404

def get_country_code(country_name):
    try:
        response = requests.get(f"https://restcountries.com/v2/name/{country_name}")
        if response.status_code == 200:
            countries = response.json()
            if countries:
                return countries[0]['alpha3Code']
    except Exception as e:
        print(f"Error getting country code: {e}")
    return None

def check_if_neighbor(country_code1, country_code2):
    response = requests.get(f"https://restcountries.com/v2/alpha/{country_code1}")
    if response.status_code == 200:
        return country_code2 in response.json().get('borders', [])
    return False

def check_borders(country_code):
    response = requests.get(f"https://restcountries.com/v2/alpha/{country_code}")
    if response.status_code == 200:
        country_data = response.json()
        print(f"Borders of {country_data['name']}: {country_data.get('borders', [])}")
    else:
        print(f"Error: {response.status_code}")

# Replace 'DE' with the ISO code of a country you want to check
check_borders('VAT')  #------ FOR TEST

def get_all_countries():
    # Fetch all countries from the REST Countries API
    response = requests.get("https://restcountries.com/v2/all")
    if response.status_code == 200:
        countries = response.json()
        return [country['name'] for country in countries]
    else:
        return []

# Fetch and print the list of all countries
all_countries_list = get_all_countries()

if __name__ == '__main__':
    app.run(debug=True)
