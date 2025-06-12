from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

### Import inventory
try:
    INVENTORY = pd.read_excel('backend/current_inventory.xlsx')
except:
    raise HTTPException(status_code=400, detail={'detail': 'Inventory not found'})

FIELDNAMES = ["Date", "Executer", "Salt name",
                  "Chemical formula", "Salt Molecular Weight in g/mol", "Mass of salt added in the vial in g",
                  "Barcode on the salt", "Name of the solvent", "Concentration of the solvent (%)",
                  "Solvent Type", "Barcode on the solvent", "Vol of solvent added (ml)", "Desired molarity",
                  "Ambient temperature (C)", "Ambient humidity (%)", "Stir Time (min)", "Barcode of Vial"]

PROPERTIES_TO_FIELDMAMES = {'general': {'executer': "Executer", 'barcode': "Barcode of Vial",},
                            'salts': {'name': "Salt name", 'barcode': "Barcode on the salt", "chemical_formula": "Chemical formula",
                                    "molar_mass": "Salt Molecular Weight in g/mol", "mass": "Mass of salt added in the vial in g"},
                            'solvents': {'barcode': "Barcode on the solvent", 'name': "Name of the solvent", 'concentation': "Concentration of the solvent (%)",
                                         'vol_added': "Vol of solvent added (ml)", 'desired_molarity': "Desired molarity",
                                         'ambient_temp': "Ambient temperature (C)", 'ambient_humidity': "Ambient humidity (%)",
                                         'stir_time': "Stir Time (min)"}
                            }

class Parent_vial(BaseModel):
    executer: str
    barcode: str
    solvents: dict
    salts: dict


class Salt(BaseModel):
    barcode: str
    name: str
    chemical_formula: str
    molar_mass: float
    mass: float

class Solvent(BaseModel):
    barcode: str
    name: str
    vol_added: float
    desired_molarity: float
    ambient_temp: float
    ambient_humidity: float
    stir_time: float



#### helper functions ###
def upload_file(local_file_path, dropbox_file_path):
    with open(local_file_path, 'rb') as f:
        dbx.files_upload(f.read(), dropbox_file_path, mode=dropbox.files.WriteMode('overwrite'))

def upload_csv_buffer(csv_buffer, dropbox_file_path):
    dbx.files_upload(csv_buffer.getvalue().encode('utf-8'), dropbox_file_path, mode=dropbox.files.WriteMode('overwrite'))

@app.get('/get_salt/{salt_barcode}')
def get_salt(salt_barcode: str):
    row = INVENTORY[INVENTORY['Inventory Bar Code'] == salt_barcode]
    if not row.empty:
        row_dict = row.iloc[0].fillna('').to_dict()
        return {'name': row_dict['Chemical Description'], 'chem_form': row_dict['Chemical Formula']}
    else:
        raise HTTPException(status_code=400, detail={'detail': 'Salt barcode not found'})


@app.get('/get_solvent/{solvent_barcode}')
def get_solvent(solvent_barcode: str):
    row = INVENTORY[INVENTORY['Inventory Bar Code'] == solvent_barcode]
    if not row.empty:
        row_dict = row.iloc[0].fillna('').to_dict()
        return {'name': row_dict['Chemical Description'], 'concentration': row_dict['Concentration']}
    else:
        raise HTTPException(status_code=400, detail={'detail': 'Salt barcode not found'})

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.get('/create', response_class=HTMLResponse)
async def create(request: Request):
    return templates.TemplateResponse('create_new.html', {'request': request})

# Creates and uploads the parent metadata to dropbox
@app.post('/create/parent')
def create_parent(parent: Parent_vial):
    data = [{'Date': datetime.now().date(),
             "Barcode of Vial": parent.barcode,
            'Executer': parent.executer,
            },]

    for attribute, fieldname in PROPERTIES_TO_FIELDMAMES['general'].items():
        data[0][fieldname] = parent.__getattribute__(attribute)

    for salt_no in parent.salts:
        if int(salt_no) > len(data):
            data.append({})
        salt = parent.salts[salt_no]
        salt_index = int(salt_no)-1
        row = data[salt_index]
        for property, fieldname in PROPERTIES_TO_FIELDMAMES['salts'].items():
            row[fieldname] = salt[property]

    for solvent_no in parent.solvents:
        if int(solvent_no) > len(data):
            data.append({})
        solvent_index = int(solvent_no)-1
        solvent = parent.solvents[solvent_no]
        row = data[solvent_index]
        for property, fieldname in PROPERTIES_TO_FIELDMAMES['solvents'].items():
            row[fieldname] = solvent[property]

    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    try:
        upload_csv_buffer(csv_buffer, f'/parent_vials/{data[0]['Date']}_{parent.barcode}.csv')
        return {'message': 'Uploaded successfully'}
    except:
        return {'message': 'Upload failed'}

# Downloads the parent metadata from dropbox
@app.get('/parent')
def get_parent(parent_barcode: str):
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
    output = {}
    salts = {}
    solvents = {}
    for attribute, fieldname in PROPERTIES_TO_FIELDMAMES['general'].items():
        output[attribute] = df.iloc[0][fieldname]
    no_salts = df["Salt name"].count()
    for i in range(no_salts):
        salts[i+1] = {}
        for attribute, fieldname in PROPERTIES_TO_FIELDMAMES['salts'].items():
            salts[i+1][attribute] = df.iloc[i][fieldname]
    no_solvents = df["Name of the solvent"].count()
    for i in range(no_solvents):
        solvents[i+1] = {}
        for attribute, fieldname in PROPERTIES_TO_FIELDMAMES['solvents'].items():
            solvents[i+1][attribute] = df.iloc[i][fieldname]

    output['salts'] = salts
    output['solvents'] = solvents
    return output

@app.get('/salt/{salt_barcode}')
def get_salt(salt_barcode: str):
    pass
