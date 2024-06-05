from typing import Dict
from bs4 import BeautifulSoup
import datetime
import json
import requests

url_to_check = "https://openai.com/pricing"
USER_QUERY = "What is the price of the GPT base models?"
SNAPSHOTS_JSON_FILE = "snapshots_data.json"

OPEN_AI_API_KEY = "YOUR_API_KEY"

def generate_prompt(user_query: str, html: str):
  return f"Your role is to answer questions based on the provided HTML. Your answers are concise. WE COUNT ON YOU!\n\n# Question\n{user_query}\n\n# HTML:\n" + html

def load_snapshots_json():
  with open(SNAPSHOTS_JSON_FILE, "r") as f:
    return json.load(f)


def save_snapshots_json(data: Dict):
  try:
    with open(SNAPSHOTS_JSON_FILE, "w") as f:
      json.dump(data, f, indent=4)
  except Exception as e:
    raise Exception(f"Error saving data to JSON file: {e}")

def get_snapshots(url):
  """
  This function takes a URL as input and returns a list of all its available snapshots from the Wayback Machine API.

  Args:
      url (str): The URL to query the Wayback Machine for.

  Returns:
      list: A list of dictionaries containing information about each snapshot, 
           including the timestamp and original URL (if available).

  Raises:
      Exception: If the Wayback Machine API request fails.
  """
  base_url = "https://web.archive.org/cdx/search/cdx?url="
  try:
    response = requests.get(base_url + url)
    response.raise_for_status()  # Raise exception for non-200 status codes
    snapshots = []
    for line in response.text.splitlines():
      # Each line in the response contains information about a snapshot
      fields = line.split(" ")
      # Format the timestamp into a human-readable string
      timestamp = fields[1].strip()
      try:
        timestamp_obj = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        formatted_timestamp = timestamp_obj.strftime("%b %dth, %Y | %I:%M %p")
      except ValueError:
        formatted_timestamp = timestamp  # Use original timestamp if parsing fails

      snapshot = {
          "timestamp": timestamp,
          "timestamp_formatted": formatted_timestamp,
          "original_url": fields[2]
      }
      snapshots.append(snapshot)
    return snapshots
  except requests.exceptions.RequestException as e:
    raise Exception(f"Error fetching snapshots from Wayback Machine: {e}")


def check_if_pages_diff(page1, page2):
  # save calls and execution time and snapshots don't differ
  # TODO implement
  pass


def get_snapshot_html(url, timestamp):
  """
  This function retrieves the HTML content of a specific snapshot and returns it.

  Args:
      url (str): The base URL of the snapshot.
      timestamp (str): The timestamp of the desired snapshot in Wayback Machine format (YYYYMMDDHHMMSS).

  Returns:
      str: The HTML content of the snapshot, or None if retrieval fails.

  Raises:
      Exception: If there's an error fetching the HTML or if robots.txt disallows access.
  """
  snapshot_url = f"http://web.archive.org/web/{timestamp}/{url}"  # Build snapshot URL

  # # Check robots.txt before fetching
  # if not is_robots_txt_allows(snapshot_url):
  #   raise Exception(f"Robots.txt disallows access to this snapshot: {snapshot_url}")

  try:
    response = requests.get(snapshot_url)
    response.raise_for_status()  # Raise exception for non-200 status codes
    return response.text
  except requests.exceptions.RequestException as e:
    raise Exception(f"Error fetching HTML for snapshot: {e}")


def process_snapshot(output_json_file: str, url: str, timestamp: str):
  try:
    # Extract date part from timestamp
    html = get_snapshot_html(url, timestamp.split()[0])
    clean_html = html_to_text(html)
    
    
    # TODO query if snapshots diff above some tresholds --> check_if_pages_diff()
    # query openai
    answer = query_openai(generate_prompt(USER_QUERY, clean_html))
    print(answer)
    return {'raw_html': html, 'clean_html': clean_html, 'llm_answer': answer}
  except Exception as e:
    print(f"Error retrieving HTML for {timestamp}: {e}")
  



def save_snapshots_to_json(url, output_json_file: str, snapshots_limit=99999):
  """
  This function retrieves all snapshots for a URL, saves their HTML content in a JSON file, 
  with timestamps as keys and HTML content as values.

  Args:
      url (str): The URL to query the Wayback Machine for.
      filename (str): The filename to save the JSON data to.

  Raises:
      Exception: If any errors occur during snapshot retrieval or JSON saving.
  """
  snapshots = get_snapshots(url)
  
  data = load_snapshots_json()

  snapshots_processed = 0
  for snapshot in snapshots:
    if snapshots_processed == snapshots_limit:
      break

    if snapshot in data:
      print(f'Already processed information for snapshot {snapshot}')

    data[snapshot] = process_snapshot(output_json_file, url, snapshot["timestamp"])
    save_snapshots_json(data)
    snapshots_processed += 1



def query_openai(prompt: str):
  # Endpoint for chat completions
  url = "https://api.openai.com/v1/chat/completions"

  # Define the request body
  data = {
      "model": "gpt-3.5-turbo",
      "messages": [
          {
              "role": "user",
              "content": prompt
          }
      ]
  }

  # Set the authorization header
  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {OPEN_AI_API_KEY}"
  }

  # Send the POST request
  response = requests.post(url, headers=headers, json=data)

  # Check for successful response
  if response.status_code != 200:
    print(f"Error: {response.status_code}")
    return None

  response_data = response.json()
  gpt_response = response_data["choices"][0]["message"]["content"]
  return gpt_response


def html_to_text(html: str):
    soup = BeautifulSoup(html, 'html.parser')

    for data in soup(['style', 'script', 'meta', 'link', 'noscript']):
        # Remove tags
        data.decompose()

    # Get and clean up plain text
    clean_html = soup.get_text()
    while "\n\n" in clean_html:
        clean_html = clean_html.replace("\n\n", "\n")

    return clean_html


# Example usage
save_snapshots_to_json(url_to_check, 'temp.json', snapshots_limit=2)




# get snapshots' URLS
# get URL's html
# clean HTML
# query if snapshots diff above some tresholds --> check_if_pages_diff()
# query openai
# store everything in a json
# check if already exists in json
# store if not, continue if so
