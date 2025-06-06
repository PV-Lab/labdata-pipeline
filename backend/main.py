from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import dropbox
import dropbox.files
import csv
from datetime import datetime
import pandas as pd
from io import StringIO

load_dotenv()

DROPBOX_APP_KEY = os.getenv('DROPBOX_APP_KEY')
DROPBOX_APP_SECRET = os.getenv('DROPBOX_APP_SECRET')
DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')

dbx = dropbox.Dropbox(app_key=DROPBOX_APP_KEY,
                      app_secret=DROPBOX_APP_SECRET,
                      oauth2_refresh_token=DROPBOX_REFRESH_TOKEN)

app = FastAPI()

items = []

class Parent(BaseModel):
    name: str
    barcode: str
    solvent_name: str
    salt_name: str

#### helper functions ###
def upload_file(local_file_path, dropbox_file_path):
    with open(local_file_path, 'rb') as f:
        dbx.files_upload(f.read(), dropbox_file_path, mode=dropbox.files.WriteMode('overwrite'))

def upload_csv_buffer(csv_buffer, dropbox_file_path):
    dbx.files_upload(csv_buffer.getvalue().encode('utf-8'), dropbox_file_path, mode=dropbox.files.WriteMode('overwrite'))

@app.get('/')
def index():
    return {"hello": "world"}

# Creates and uploads the parent metadata to dropbox
@app.post('/create/parent')
def create_parent(parent: Parent):
    data = [{'Barcode': parent.barcode,
            'Name': parent.name,
            'Date': datetime.now().date(),
            'Salt': parent.salt_name,
            'Solvent': parent.solvent_name,
            }]
    csv_buffer = StringIO()
    fieldnames = list(data[0].keys())
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    try:
        upload_csv_buffer(csv_buffer, f'/parent_vials/{data[0]['Date']}_{parent.barcode}.csv')
        return {'message': 'Uploaded successfully'}
    except:
        return {'message': 'Upload failed'}

# Downloads the parent metadata from dropbox
@app.get('/parent/{parent_barcode}', response_model=Parent)
def get_parent(parent_barcode: int):
    options = dropbox.files.SearchOptions(path='/parent_vials')
    result = dbx.files_search_v2(query=str(parent_barcode), options=options)
    if len(result.matches) == 0:
        raise HTTPException(status_code=404, detail=f'parent vial with barcode {parent_barcode} does not exist')
    if len(result.matches) > 1:
        raise HTTPException(status_code=400, detail=f'There are multiple vials with the barcode {parent_barcode}')
    match = result.matches[0]
    path = match.metadata.get_metadata().path_display
    metadata, response = dbx.files_download(path)
    csv_data = response.content.decode('utf-8')
    df = pd.read_csv(StringIO(csv_data))
    return Parent(name = df.iloc[0]['Name'], barcode = parent_barcode, solvent_name= df.iloc[0]['Solvent'], salt_name=df.iloc[0]['Salt'])
