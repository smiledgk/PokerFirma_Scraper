import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import csv
import os
import pandas as pd

# headers for a valid user agent
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}

""" Required Classes """

link_template = 'https://www.pokerfirma.com/tag/schenefeld/page'

class News_Entry:
    last_id = 0
    def __init__(self, title, link):
        self.title = title
        self.link = link
        self.id = News_Entry.last_id
        News_Entry.last_id += 1

class Player_Win:
    def __init__(self, name_or_alias, surname, winnings):
        self.full_name = (name_or_alias.strip() + surname.strip())
        self.winnings = winnings

""" Getting the CSV with all the News titles - Title + Link """
        
def get_all_page_news_entries(url,page_number):
    # This Function retrieves all of the news acticles for one selected page number
    page_entries = []
    url = f'{url}/{page_number}'
    class_to_look_for = 'entries clr' #custom class, derived from a page analysis
    try:
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.content, "html.parser")
        all_news_entries = soup.find_all(class_= class_to_look_for)
        if len(all_news_entries) == 1:
            a_tags = all_news_entries[0].find_all('a', href=True)
            for tag in a_tags:
                title = tag.get('title', 'No title available')
                link = tag['href']
                entry = News_Entry(title, link)
                page_entries.append(entry)
            return page_entries
        else:
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {url}: {e}")
        return []

def scan_pages(start_page=0, end_page=10, folder_path='poker_scrape_results'):
    # This function creates a CSV for each title/link pairs for all of the news entries for selected range of pages (0-25 by default)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    output_file = os.path.join(folder_path, f"news_entries_start_{start_page}_end_{end_page}.csv")
    news_entries = []
    for i in range(start_page, end_page + 1):
        page_entries = get_all_page_news_entries(link_template,i)
        news_entries.extend(page_entries)    
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'Link'])  # Write header row
        for entry in news_entries:
            writer.writerow([entry.title, entry.link])

""" Analysing the CSV """

# get all the news entries
def read_csv_file_news(filename='news_entries_start_0_end_24.csv', folder_path='poker_scrape_results'):
    
    file_path = os.path.join(folder_path, filename)
    news_entries = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            news_entry = {
                'title': row['Title'],
                'link': row['Link']
            }
            news_entries.append(news_entry)
    return news_entries

def parse_amount_with_euro(td_text):
    match = re.search(r'(?:€)?(\d+(?:\.\d+)?)', td_text)
    if match:
        amount_str = match.group(1)
        amount_str = amount_str.replace('.', '')
        return int(amount_str)
    else:
        return None

def get_all_tables(entries_to_analyse):
    for entry in entries_to_analyse:
        try:
            page = requests.get(entry['link'], headers=headers)
            soup = BeautifulSoup(page.content, "html.parser")
            class_to_look_for = 'entry-content clr'
            containers = soup.find_all(class_= class_to_look_for)
            if len(containers) == 1:
                tables = containers[0].find_all('table')
                return tables
            else:
                print(f"No or multiple containers found for {entry['link']}. Skipping.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {entry['link']}: {e}")
        except ValueError as e:
            print(f"ValueError: {e}")

def extract_winnings_from_tables(tables):
    player_wins = []
    for table in tables:
        for tbody in table.find_all('tbody'):
            for tr in tbody.find_all('tr'):
                if any('€' in td.get_text() for td in tr.find_all('td')):
                    name_or_alias = ''
                    surname = ''
                    winnings = 0
                    smallest_amount = float('inf')
                    smallest_td = None
                    for td in tr.find_all('td'):
                        td_text = td.get_text().strip()
                        if '.' in td_text and any(c.isalpha() for c in td_text):
                            surname = td_text
                        if all(c.isalpha() or c.isspace() or c == '.' for c in td_text) and len(td_text) > 3:
                            name_or_alias = name_or_alias + ' ' + td_text
                        if '€' in td_text:
                            amount = parse_amount_with_euro(td_text)
                            if amount is not None:
                                smallest_amount = amount
                                smallest_td = td
                    if (surname == '' and all(c.isspace() for c in name_or_alias)) or ('Pokerstars' in surname and all(c.isspace() for c in name_or_alias)):
                        splitted = name_or_alias.split()
                        if len(splitted) >= 2:
                            name_or_alias = splitted[0]
                            surname = splitted[1]
                        else:
                            name_or_alias = name_or_alias.strip()
                    if smallest_td is not None:
                        winnings = smallest_amount
                        player_win_entry = Player_Win(name_or_alias, surname, winnings)
                        player_wins.append(player_win_entry)
    return player_wins                              
    
def get_winnings_report(number_of_entries=0, folder_path='poker_scrape_results'):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    selected_entries = entries
    if number_of_entries != 0:
        selected_entries = entries[:number_of_entries]
    output_file = os.path.join(folder_path, f"winnings_for_last_{len(selected_entries)}_news.csv")     
    all_tables = get_all_tables(selected_entries)
    player_wins = extract_winnings_from_tables(all_tables)
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Full Name', 'Winnings'])  # Write header row
        for win in player_wins:
            writer.writerow([win.full_name, win.winnings])

""" Helper Functions For Clearing Data """

def remove_after_second_whitespace(input_string):
    parts = input_string.split(maxsplit=2)
    return ' '.join(parts[:2])

def separate_short_surname(input_string):
    result = []
    previous_char = ''
    count_letters = 0
    
    for char in input_string:
        if char.isalpha():
            count_letters += 1
            if count_letters >= 3 and char.isupper() and previous_char.isalpha() and not previous_char.isupper():
                result.append(' ')
        result.append(char)
        previous_char = char
    
    return ''.join(result).strip()

def create_first_name_and_initial(full_name):
    parts = full_name.split()
    if len(parts) >= 2:
        first_name = parts[0].lower().capitalize()
        initial = parts[1][0]  # Take the first character of the surname
        return f"{first_name} {initial}."
    else:
        return full_name
    
def adjust_name(full_name):
    parts = full_name.split()
    if len(parts) >= 2:
        first_name = parts[0].lower().capitalize()
        last_name = parts[1].lower().capitalize()
        return f"{first_name} {last_name}"
    else:
        return full_name
    
def clean_winners_input(winners):
    winners = winners[winners['Full Name'].notna() & (winners['Full Name'].str.strip() != '')]
    winners['Full Name'] = winners['Full Name'].apply(remove_after_second_whitespace).apply(separate_short_surname)
    winners['First Name And Initial'] = winners['Full Name'].apply(create_first_name_and_initial)
    winners.to_csv('players/cleared_winners', index=False)   
    
# Getting user input
def get_integer_input(prompt):
    while True:
        try:
            user_input = input(prompt)
            user_input = int(user_input)  # Try to convert the input to an integer
            if user_input < 50:
                return user_input  # If successful and less than 50, return the integer value
            else:
                print("Input must be less than 50. Pages below are not supported. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a valid page number.")

# Check the Player in the Database
def check_the_player(player):
    filtered = winners_by_money[winners_by_money['First Name And Initial'].str.contains(player, case=False)]
    return filtered

# Execution

user_input_pages = 25

# Scanning all the pages for an input
user_input_pages = get_integer_input("'Enter how many pages to scan? (note - meaningful results seem to be to the page 25 at 15.07.2024 stand) '")
scan_pages(0,user_input_pages) # this function returns a csv output
entries = read_csv_file_news(f"news_entries_start_0_end_{user_input_pages - 1}.csv") #this reads a CSV out into an array

# get a list of all the winners with cashes
file_path = os.path.join('poker_scrape_results', f"winnings_for_last_{user_input_pages * 20}_news.csv")
winners = pd.read_csv(file_path)
winners = winners[winners['Full Name'].notna() & (winners['Full Name'].str.strip() != '')]
winners['Full Name'] = winners['Full Name'].apply(remove_after_second_whitespace).apply(separate_short_surname)
winners['First Name And Initial'] = winners['Full Name'].apply(create_first_name_and_initial)
winners.to_csv('players/cleared_winners', index=False)   
cleared_winners = pd.read_csv('players/cleared_winners')
cleared_winners_unique = cleared_winners.drop_duplicates(subset=['First Name And Initial', 'Winnings'])

# Get Winnings, Cashes and Full Name columns
summarized_winners = cleared_winners_unique.groupby('First Name And Initial').agg({
    'Winnings': 'sum',
    'Full Name': 'first'
}).reset_index()
summarized_winners['Occurrences'] = cleared_winners_unique.groupby('First Name And Initial').size().values
summarized_winners['Full Name'] = summarized_winners['Full Name'].apply(adjust_name)

# Group the winners by their number of cashes and winnings
winners_by_number_of_cashes = summarized_winners.sort_values(by='Occurrences', ascending=False)
winners_by_number_of_cashes.to_csv('players/sorted_players/winners_by_number_of_cashes', index=False)
winners_by_money = summarized_winners.sort_values(by='Winnings', ascending=False)
winners_by_money.to_csv('players/sorted_players/winners_by_money', index=False)

# Checking for a player in the database
input_player = input('Enter a player: ')
check_the_player(input_player)


