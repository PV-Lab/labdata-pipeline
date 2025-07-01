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
import numpy as np
import requests

load_dotenv()

DROPBOX_APP_KEY = os.getenv('DROPBOX_APP_KEY')
DROPBOX_APP_SECRET = os.getenv('DROPBOX_APP_SECRET')
DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
CHEMICALS_API_KEY = os.getenv('CHEMICALS_API_KEY')

PARENT_PATH = '/Buonassisi-Group/Projects - Active/Labdata-pipeline/Tests'

dbx = dropbox.Dropbox(app_key=DROPBOX_APP_KEY,
                      app_secret=DROPBOX_APP_SECRET,
                      oauth2_refresh_token=DROPBOX_REFRESH_TOKEN)

# dbx = dropbox.Dropbox('sl.u.AF3e4ArKRb0b4Dpr25F6gDh70zQ9X3_wDPhb4RDzgbcJkxF8xOlIzPoBUKqiBqUN_M_xg7-765e8UFNA1N_kbI5N8VXmZWfb-xCYwjtD5Ee7Hzh6CtUSgr7EUdA6xBC7QKTNzjlBvNJyH8kf_pioCwHYWf2NZvLtJ21kirh8XjY5bg5QPMkIHoFHgn-Y278jhnLgUrW1bSumYkNygmK2y9Nwuc5oYcNqF6K--AiiNSjJH0PaerI6y1-keNIrW_L3YvrOJZ5LYNBtUOvgRGNTeHLzLlXjvAAErC6_7qCbdPWLpS7yXRS8B8tMrZcr80eVVRhSQA6yIst3On3_f5thwFEPdmYZh-xD1XcdvaIYCmB5XzZlfsCZtRk2Tzl7uQc3WeXf5yTSccMFaPvEKIhemiBksqbJeNx9v0FuxWPZkRbEjRC9Rw4AuRAVQ0vgdVsA504dfft_n-gQBurmhda6v0pmtdgU6gHr61cF2TUn2wXp8S98S11zvqOrCJge-OdIxIpHoa_7gDHhkmUoZ1Zr9tN7_Q3vbHSFcSQM4F4tF9FyoRfAbaQlq4Zrt7CKX5cVs7TW3Utgx-gKRapY4HHQIs8FCj6ZtPiGorCvYBrNkmV89igNrN_V2_k5JvB7DoUGwY3CmoX5mGKQKZB7F7-BPSHxITvlheMgKXfBfUiDEnoh7MjJ7lqMInVhyHEpP_7hyS7xV8XWOHyxWFgUUQPVYtPafCHufjzFptQAzskYAQjl2MiXWAlpp6FbVEPouNwOLZtyl_lWfRe4annbNF7EfwW7osvb3fRYOR4XyVay_z_7c2OKl72zyEq3xRHT0FJZ-R9qEsc7sn_T66PozW_mFho_FJe7_KbAO6a5hKbZYzGV5z6dLPE9pAp9dpnPbAEanHITDlhrhoVrEZMMqsV37NfZDOdoeaCT7rkU8hrYVdjYg2x9si3dke6tYEnoJhDdU1E9MqMoO_Izn25p8kNA0QWeTPKvUqwDnPUoIgB5N1ITZEO2Ot2N-Z6bAeX3f9nObM4qh-nbX68GsIgj7NRjvHGmWJSxExklRj-Ftl0UGxiJ2OajkKgv6VoeXwnGYfxiWfUM96Yg_AZVzAR-QrrfAW99Cm1_UPchtOjt7mpqcqnLH48LEX4n393MG2umRHWS3dBKoAd0kFfl8phtywxYvxWECnyPP0BgvirjFv8YUfYO6837wpKOlEY78DbsVyGsnWYWxpNbxcAQTGtdUKjN_xZgoNzdEqhxw1bUyKhHnDr14Z22DLiPwuafb9aIuA1UxZlJNbgkONrFkalA1M1og9lw')

account = dbx.users_get_current_account()
team_namespace_id = account.root_info.root_namespace_id
dbx = dbx.with_path_root(dropbox.common.PathRoot.namespace_id(team_namespace_id))

app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

### Import inventory
try:
    INVENTORY = pd.read_excel('backend/current_inventory.xlsx')
except:
    raise HTTPException(status_code=400, detail={'detail': 'Inventory not found'})

FIELDNAMES = ["Date", "Executer", "Barcode on the salt", "Salt name",
                  "Chemical formula", "Salt Molecular Weight in g/mol", "Mass of salt added in the vial in g",
                  "Ambient temperature in glovebox (C)", "Ambient humidity in glovebox (%)",
                  "Salt receipt date",  "Barcode on the solvent", "Name of the solvent", "Concentration of the solvent (%)",
                  "Vol of solvent added (ml)", "Desired molarity",
                  "Ambient temperature (C)", "Ambient humidity (%)", "Stir Time (min)", "Solvent receipt date",
                  "Barcode of Vial",
                  ]

PROPERTIES_TO_FIELDMAMES = {'general': {'executer': "Executer", 'barcode': "Barcode of Vial", 'date': "Date"},
                            'salts': {'name': "Salt name", 'barcode': "Barcode on the salt", "chemical_formula": "Chemical formula",
                                    "molar_mass": "Salt Molecular Weight in g/mol", "mass": "Mass of salt added in the vial in g",
                                    'ambient_temp': "Ambient temperature in glovebox (C)", 'ambient_humidity': "Ambient humidity in glovebox (%)",
                                    'receipt_date': 'Salt receipt date'},
                            'solvents': {'barcode': "Barcode on the solvent", 'name': "Name of the solvent", 'concentration': "Concentration of the solvent (%)",
                                         'vol_added': "Vol of solvent added (ml)", 'desired_molarity': "Desired molarity",
                                         'ambient_temp': "Ambient temperature (C)", 'ambient_humidity': "Ambient humidity (%)",
                                         'stir_time': "Stir Time (min)", 'receipt_date': 'Solvent receipt date'}
                            }

CHILD_FIELDNAMES = ["Date", "Executer", "Barcode on holder", "Parent 1 barcode", "Parent 2 barcode", "Ambient temperature (C)", "Ambient humidity (%)"]

CHILD_PROPERTIES_TO_FIELDNAMES = {'date': "Date", 'executer': "Executer", 'barcode': "Barcode on holder", 'parent_1': "Parent 1 barcode",
                                  'parent_2': "Parent 2 barcode", 'ambient_temp': "Ambient temperature (C)", 'ambient_humidity': "Ambient humidity (%)"}

class Parent_vial(BaseModel):
    date: str
    executer: str
    barcode: str
    solvents: list
    salts: list


class Salt(BaseModel):
    barcode: str
    name: str
    chemical_formula: str
    molar_mass: float
    mass: float
    ambient_temp: float

class Solvent(BaseModel):
    barcode: str
    name: str
    vol_added: float
    desired_molarity: float
    ambient_temp: float
    ambient_humidity: float
    stir_time: float

class Child(BaseModel):
    barcode: str
    executer: str
    date: str
    parent_1: str
    parent_2: str
    ambient_temp: float
    ambient_humidity: float



#### helper functions ###
def upload_file(local_file_path, dropbox_file_path):
    with open(local_file_path, 'rb') as f:
        dbx.files_upload(f.read(), PARENT_PATH + dropbox_file_path, mode=dropbox.files.WriteMode('overwrite'))

def upload_csv_buffer(csv_buffer, dropbox_file_path):
    return dbx.files_upload(csv_buffer.getvalue().encode('utf-8'), PARENT_PATH + dropbox_file_path, mode=dropbox.files.WriteMode('overwrite'))

def delete_file(file_path):
    dbx.files_delete_v2(file_path)

def change_to_native_types(object):
    if isinstance(object, np.int_):
        return int(object)
    if isinstance(object, np.float64):
        return float(object)
    return object

### API endpoints ###
@app.get('/get_salt/{salt_barcode}')
def get_salt(salt_barcode: str):
    """
    Returns information about a salt
    """
    params = {'AuthKey': CHEMICALS_API_KEY,
              'barcode': salt_barcode}
    response = requests.get('https://onsite-prd-app1.mit.edu/ehsa/public/ApiInterface/GetChemicalInventoryData',
                          params=params)
    try:
        result = response.json()
        cas = result['Table'][0]['cas_num']
        name = result['Table'][0]['chemical_description']
        chem_form = result['Table'][0]['chemical_formula']
        molar_mass = ''
        if cas:
            cid = requests.get(f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas}/cids/JSON').json()["IdentifierList"]["CID"][0]
            response = requests.get(f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularWeight,MolecularFormula/JSON').json()
            molar_mass = response["PropertyTable"]["Properties"][0]["MolecularWeight"]
            if not chem_form:
                chem_form = response["PropertyTable"]["Properties"][0]["MolecularFormula"]
        return {'name': name, 'chem_form': chem_form, 'molar_mass': molar_mass, 'receipt_date': result['Table'][0]['receipt_date'][:10]}

    except Exception as e:
        raise HTTPException(status_code=400, detail='Salt barcode not found')



@app.get('/get_solvent/{solvent_barcode}')
def get_solvent(solvent_barcode: str):
    params = {'AuthKey': CHEMICALS_API_KEY,
              'barcode': solvent_barcode}
    response = requests.get('https://onsite-prd-app1.mit.edu/ehsa/public/ApiInterface/GetChemicalInventoryData',
                          params=params)
    try:
        result = response.json()
        return {'name': result['Table'][0]['chemical_description'], 'concentration': result['Table'][0]['concentration'],
                'receipt_date': result['Table'][0]['receipt_date'][:10]}
    except:
        raise HTTPException(status_code=400, detail='Solvent barcode not found')

## Webpages
@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.get('/create', response_class=HTMLResponse)
async def create(request: Request):
    return templates.TemplateResponse('create_new.html', {'request': request, 'date': datetime.now().date()})

@app.get('/edit', response_class=HTMLResponse)
async def edit(request: Request):
    return templates.TemplateResponse('edit.html', {'request': request})

@app.get('/create-child', response_class=HTMLResponse)
async def create_child(request: Request):
    return templates.TemplateResponse('create_child.html', {'request': request, 'date': datetime.now().date()})

# Creates and uploads the parent metadata to dropbox
def save_parent(parent):
    data = [{'Date': parent.date,
             "Barcode of Vial": str(parent.barcode),
            'Executer': parent.executer,
            },]

    # for each general attribute, add the data to the fieldname
    for attribute, fieldname in PROPERTIES_TO_FIELDMAMES['general'].items():
        data[0][fieldname] = parent.__getattribute__(attribute)

    # for each salt attribute, add the data to the fieldname
    for i, salt in enumerate(parent.salts):
        if i > len(data) -1:
            data.append({})
        row = data[i]
        for property, fieldname in PROPERTIES_TO_FIELDMAMES['salts'].items():
            row[fieldname] = salt[property]

    # for each solvent attribute, add the data to the fieldname
    for i, solvent in enumerate(parent.solvents):
        if i > len(data) -1:
            data.append({})
        row = data[i]
        for property, fieldname in PROPERTIES_TO_FIELDMAMES['solvents'].items():
            row[fieldname] = solvent[property]

    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    try:
        upload_csv_buffer(csv_buffer, f'/parent_vials/{data[0]["Date"]}_{parent.barcode}.csv')
        return {'detail': 'Uploaded successfully'}
    except Exception as e:
        return {'detail': 'Upload failed', 'error': e}

@app.post('/create/parent')
async def create_parent(parent: Parent_vial):
    try:
        matches = search_parent_barcode(parent.barcode)
    except Exception as e:
        return {'detail': 'Upload failed', 'error': e}
    if len(matches) == 1:
        raise HTTPException(status_code=400, detail=f'There exists a vial with this barcode {parent.barcode}')
    return save_parent(parent)

@app.post('/edit/parent')
async def edit_parent(parent: Parent_vial):
    matches = search_parent_barcode(parent.barcode)
    if len(matches) == 0:
        raise HTTPException(status_code=404, detail=f'parent vial with barcode {parent.barcode} does not exist')
    if len(matches) > 1:
        raise HTTPException(status_code=400, detail=f'There are multiple vials with the barcode {parent.barcode}')
    print(parent)
    return save_parent(parent)



def search_parent_barcode(parent_barcode, parent_folder='/parent_vials'):
    options = dropbox.files.SearchOptions(path=PARENT_PATH + parent_folder)
    result = dbx.files_search_v2(query=str(parent_barcode), options=options)
    return result.matches

def download(parent_barcode, parent_folder='/parent_vials'):
    """
    Downloads the file with the given barcode,
    Returns the data frame and the file path
    """
    matches = search_parent_barcode(parent_barcode, parent_folder)
    if len(matches) == 0:
        raise HTTPException(status_code=404, detail=f'Vial with barcode {parent_barcode} does not exist')
    if len(matches) > 1:
        raise HTTPException(status_code=400, detail=f'There are multiple vials with the barcode {parent_barcode}')
    match = matches[0]
    path = match.metadata.get_metadata().path_display
    metadata, response = dbx.files_download(path)
    csv_data = response.content.decode('utf-8')
    df = pd.read_csv(StringIO(csv_data), dtype=str)
    return df, path


# Downloads the parent metadata from dropbox
@app.get('/parent', response_class=HTMLResponse)
async def get_parent(request: Request, parent_barcode: str):
    df, path = download(parent_barcode)
    output = {}
    salts = []
    solvents = []
    for attribute, fieldname in PROPERTIES_TO_FIELDMAMES['general'].items():
        output[attribute] = df.iloc[0][fieldname]
    no_salts = df["Salt name"].count()
    for i in range(no_salts):
        salt = {}
        for attribute, fieldname in PROPERTIES_TO_FIELDMAMES['salts'].items():
            salt[attribute] = df.iloc[i][fieldname]
        salts.append(salt)
    no_solvents = df["Name of the solvent"].count()
    for i in range(no_solvents):
        solvent = {}
        for attribute, fieldname in PROPERTIES_TO_FIELDMAMES['solvents'].items():
            solvent[attribute] =df.iloc[i][fieldname]
        solvents.append(solvent)

    output['salts'] = salts
    output['solvents'] = solvents
    return templates.TemplateResponse('edit_vial.html', {'request': request} | output)

@app.post('/create/child')
def save_child(child: Child):
    data = [{}]
    for attribute, fieldname in CHILD_PROPERTIES_TO_FIELDNAMES.items():
        data[0][fieldname] = child.__getattribute__(attribute)

    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=CHILD_FIELDNAMES)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    try:
        upload_csv_buffer(csv_buffer, f'/child_vials/{data[0]["Date"]}_{child.barcode}.csv')
        return {'detail': 'Uploaded successfully'}
    except Exception as e:
        return {'detail': 'Upload failed', 'error': e}

@app.get('/view/child', response_class=HTMLResponse)
async def get_parent(request: Request, barcode: str):
    df, path = download(barcode, '/child_vials')
    output = {}
    for attribute, fieldname in CHILD_PROPERTIES_TO_FIELDNAMES.items():
        output[attribute] = df.iloc[0][fieldname]
    return templates.TemplateResponse('view_child.html', {'request': request} | output)

@app.get('/search/child', response_class=HTMLResponse)
async def search_child(request: Request):
    return templates.TemplateResponse('search_child.html', {'request': request})
