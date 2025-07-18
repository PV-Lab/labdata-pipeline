# Lab data pipeline

This project is for collecting data from the lab and uploading it to the lab's group dropbox.

## Installation
```bash
git clone https://github.com/PV-Lab/labdata-pipeline.git
cd labdata-pipeline
pip install -r requirements.txt
```

## Usage
1. `python3 run.py`
2. If it is the first time running this program on your laptop, the program will ask for the Dropbox APP key and the secret key.
3. You will then be asked to choose to generate a refresh token, where you will be redirected to dropbox which will request you to authorize the app to access your dropbox account for uploading and downloading the data to the group's dropbox folder.
4. You will then be asked to provide the chemicals inventory API key.

