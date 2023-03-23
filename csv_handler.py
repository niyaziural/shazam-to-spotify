import csv
from urllib.parse import quote
from tkinter import Tk
from tkinter.filedialog import askopenfilename

file_name = askopenfilename()

# Extract the playlist name from the first row of the CSV file
playlist_name = ""
with open(file_name, encoding="utf-8-sig") as csvFile:
    playlist_name = next(csvFile)
    next(csvFile)
    csv_tmp_file = csvFile.readlines()
# Get entries from the CSV file into the memory as a dictionary
song_dict = csv.DictReader(csv_tmp_file)
