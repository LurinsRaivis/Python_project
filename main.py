from country_data import countries_neighbors

def play_game(start_country, target_country, country_data):
    current_country = start_country
    print(f"Your journey starts in {current_country}. Your goal is to reach {target_country}.")

    while current_country != target_country:
        print(f"You are now in {current_country}. Which neighboring country would you like to travel to?")
        for neighbor in country_data[current_country]:
            print(f" - {neighbor}")

        guess = input("Your guess: ").capitalize()
        if guess in country_data[current_country]:
            current_country = guess
            print(f"Traveling to {current_country}...")
        else:
            print("That's not a neighboring country. Try again.")

        if current_country == target_country:
            print(f"Congratulations! You have reached {target_country}.")

# Example usage
play_game("Germany", "Italy", countries_neighbors)

# Note: The input function will not work in this notebook environment.
# You should test this part of the code in your local Python environment.

