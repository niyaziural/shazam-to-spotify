# Creates a Spotify Playlist from a Shazam Chart CSV file
# Author: Niyazi Ural
# Date: 23.03.2023

import requests, base64, json, webbrowser, csv
from urllib.parse import urlencode, quote
from csv_handler import song_dict, playlist_name


api_url = "https://api.spotify.com/v1/"
auth_url = "https://accounts.spotify.com/api/token"
redirect_uri = "https://open.spotify.com/collection/playlists"
client_id = "your_client_id"
client_secret = "your_client_secret"
tokens = {}

# Prepare an URL to enter into a browser so user can give permission to the app
def generate_user_permission_url():
    header = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "playlist-modify-public playlist-modify-private playlist-read-collaborative playlist-read-private"
    }
    query_string = urlencode(header)
    auth_code_url = "https://accounts.spotify.com/authorize?"
    webbrowser.open(auth_code_url + query_string)
    code = input("Enter the 'code' from the browser URL: ")
    return code


# Basic base64 encoder
def encode_to_base64(text):
    # Encode text to ascii byte code - turn that bytes to base64 - decode base64 codes as ascii
    return base64.b64encode(text.encode("ascii")).decode("ascii")


# Save tokens to a file
def save_tokens(file_name, response):
    with open(file_name, "w") as file_to_save:
        tokens["access_token"] = response["access_token"]
        tokens["refresh_token"] = response["refresh_token"]
        file_to_save.write(f"access_token,refresh_token\n{tokens['access_token']},{tokens['refresh_token']}")


# Generate tokens for an user following the OAuth 2 architecture
def generate_access_and_refresh_tokens():
    code = generate_user_permission_url()
    base64_auth_info = encode_to_base64(f"{client_id}:{client_secret}")
    header = {
        "Authorization": "Basic " + base64_auth_info,
        "Content-Type":"application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }
    response = requests.post(auth_url, headers=header, data=data)
    # Check if returned response is not a bad request of any kind
    if response.status_code < 400:
        save_tokens("tokens.txt", response.json())
        return True
    # Return false to indicate we got a bad request from server
    return False
# Get the current user's id from the server
def get_user_id():
    endpoint = "me"
    header = {
        "Authorization": "Bearer " + tokens["access_token"],
        "Content-Type": "application/json"
    }
    response = requests.get(api_url + endpoint, headers=header)
    if response.status_code < 400:
        user_id = response.json()["id"]
        return user_id
    # If we got a bad request from server return a dummy
    return "bad_request"

# Create new playlist and get playlist id
def create_new_playlist(user_id):
    endpoint = f"users/{user_id}/playlists"
    header = create_regular_header()
    data = {
        "name":playlist_name
    }
    response = requests.post(api_url + endpoint, headers=header, data=json.dumps(data))
    if response.status_code < 400:
        playlist_id = response.json()["id"]
        return playlist_id
    return "bad_request"


# Create a default header to use for regular API requests
def create_regular_header():
    header = {
        "Authorization": "Bearer " + tokens["access_token"],
        "Content-Type": "application/json"
    }
    return header
    

# Clean the given string from Shazam to be able to search them more precisely on the API
def clean_string(s):
    unwanted_characters = [",", "(", ")", "[", "]", "feat. ", "'"]
    for character in unwanted_characters:
        s = s.replace(character, "")
    return s


# Send a search request to the API
def search(artist, title):    
    endpoint = "search"
    # Clean artist and track names a bit
    artist = artist.replace(" & ", " ")
    artist = quote(artist)
    title = clean_string(title)
    query = f"?q={artist}%20{title}&type=track&limit=1"
    response = requests.get(api_url + endpoint + query, headers=create_regular_header())
    return response


# Extract song uris from the response objects that came from search results and put these
# URIs in a list so we can bulk post the list with one API request into a playlist
def create_song_uris():
    uris = []
    counter = 1
    for row in song_dict:
        response = search(row["Artist"], row["Title"])
        response_json = response.json()
        if response.status_code < 400 and len(response_json["tracks"]["items"]) > 0:
            uri = response_json["tracks"]["items"][0]["uri"]
            uris.append(uri)
            artist_name = response_json["tracks"]["items"][0]["artists"][0]["name"]
            track_name = response_json["tracks"]["items"][0]["name"]
            print(f"{counter}-Adding {artist_name} - {track_name}...")
        else:
            print(f"{counter}-Can't find {row['Artist']} - {row['Title']} in Spotify...")
        counter += 1
    return uris


# Add tracks to certain playlist
def add_songs_to_playlist(playlist_id):
    endpoint = f"playlists/{playlist_id}/tracks"
    header = create_regular_header()
    uris = create_song_uris()
    i = 0
    # Make a post request with max 100 items at once as explained in the API docs
    while i < len(uris): 
        data = {
            "uris":uris[i:i+100]
        }
        response = requests.post(api_url + endpoint, headers=header, data=json.dumps(data))
        if response.status_code < 400:
            print("Songs added to the playlist successfully!")
        i += 100


# Get tokens into the memory if they are already saved in a file
def get_tokens_from_file(fileName):
    try:
        with open(fileName, encoding="utf-8-sig") as tokens_file:
            tokens_dict = csv.DictReader(tokens_file)
            tokens_from_file = next(tokens_dict)
            if tokens_from_file.get("access_token", "Not Found") == "Not Found":
                return False
            tokens["access_token"] = tokens_from_file["access_token"]
            tokens["refresh_token"] = tokens_from_file["refresh_token"]
        return True
    except StopIteration:
        return False


# Make a dummy call to the API to check tokens' validation (expired or not)
def is_tokens_working():
    response = search("dummy", "dummy")
    return response.status_code < 400


def main():
    # Try to get tokens from the file if not try to generate new ones. if got tokens either way test them to see if they're working
    if not get_tokens_from_file("tokens.txt") or not is_tokens_working():
        if not generate_access_and_refresh_tokens():
            print("Cannot create or validate tokens. Check your client_id and client_secret! Exiting...")
            return
    
    user_id = get_user_id()
    if user_id != "bad_request":
        playlist_id = create_new_playlist(user_id)
        if playlist_id != "bad_request":
            add_songs_to_playlist(playlist_id)

main()
