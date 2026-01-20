import pandas as pd
import requests

url = 'https://en.wikipedia.org/wiki/Simpson%27s_paradox'

# Define a header that mimics a real browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Fetch the page content
response = requests.get(url, headers=headers)

# Pass the HTML text to pandas
sim = pd.read_html(response.text)

# Look at the first table found
print(len(sim))