# Lab data pipeline

This project is for collecting data from the lab and uploading it to the lab's group dropbox.

## Installation  and setup
1.
```bash
git clone https://github.com/PV-Lab/labdata-pipeline.git
cd labdata-pipeline
pip install -r requirements.txt
```
2. `python3 run.py`
3. The program will ask for the Dropbox app key and the secret key.
4. You will then be asked to choose to generate a refresh token, where you will be redirected to dropbox which will request you to authorize the app to access your dropbox account for uploading and downloading the data to the group's dropbox folder.
5. You will then be asked to provide the chemicals inventory API key.

## Usage
1. `python3 run.py`
2. Follow the link http://localhost:8000.
