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
                  "Chemical formula", "Salt Molecular Weight in g/mol", "Desired molarity", "Mass of salt added in the vial in g",
                  "Ambient temperature in glovebox (C)", "Ambient humidity in glovebox (%)",
                  "Salt receipt date",  "Barcode on the solvent", "Name of the solvent", "Concentration of the solvent (%)",
                  "Vol of solvent added (ml)",
                  "Ambient temperature (C)", "Ambient humidity (%)", "Stir Time (min)", "Solvent receipt date",
                  "Barcode of Vial", "Total volume (ml)",
                  ]

PROPERTIES_TO_FIELDMAMES = {'general': {'executer': "Executer", 'barcode': "Barcode of Vial", 'date': "Date", 'total_volume': "Total volume (ml)",},
                            'salts': {'name': "Salt name", 'barcode': "Barcode on the salt", "chemical_formula": "Chemical formula",
                                    "molar_mass": "Salt Molecular Weight in g/mol", "mass": "Mass of salt added in the vial in g",
                                    'ambient_temp': "Ambient temperature in glovebox (C)", 'ambient_humidity': "Ambient humidity in glovebox (%)",
                                    'receipt_date': 'Salt receipt date', 'desired_molarity': "Desired molarity"},
                            'solvents': {'barcode': "Barcode on the solvent", 'name': "Name of the solvent", 'concentration': "Concentration of the solvent (%)",
                                         'vol_added': "Vol of solvent added (ml)",
                                         'ambient_temp': "Ambient temperature (C)", 'ambient_humidity': "Ambient humidity (%)",
                                         'stir_time': "Stir Time (min)", 'receipt_date': 'Solvent receipt date'}
                            }

CHILD_FIELDNAMES = ["Date", "Executer", "Barcode on holder", "Parents", "Ambient temperature (C)", "Ambient humidity (%)"]

CHILD_PROPERTIES_TO_FIELDNAMES = {'date': "Date", 'executer': "Executer", 'barcode': "Barcode on holder",
                                  'ambient_temp': "Ambient temperature (C)", 'ambient_humidity': "Ambient humidity (%)"}

PLATE_FIELDNAMES = ["Date", "Executer", "Sample plate barcode", "Precursor vial barcode", "Washed", "Washed in", 'Ozone treatment', 'Ozone treatment time (min)', 'Sample type', 'Dropcast volume (ml)', 'Dropcasting temperature (C)', "Dropcast Ambient temp (C)", "Dropcast Ambient humidity (%)", 'Dropcast drying temp (C)', 'Dropcast drying time (min)', "Spuncoat spin speed (RPM)", 'Spuncoat volume (ml)', "Annealing temp (C)", "Annealing time (min)", "Ambient temp at anneal (C)", "Ambient Humidity at anneal (%)",]

PLATE_PROPERTIES_TO_FIELDNAMES = {'general': {'date': "Date", 'barcode': "Sample plate barcode", 'executer': "Executer", 'precursor': "Precursor vial barcode"},
                                  'props':{"anneal_ambient_humidity": "Ambient Humidity at anneal (%)", "anneal_ambient_temp": "Ambient temp at anneal (C)", "annealing_temp": "Annealing temp (C)", "annealing_time": "Annealing time (min)", "ozone": "Ozone treatment", "ozone_time": "Ozone treatment time (min)", "sample_type": "Sample type", "spuncoat_spin_speed": "Spuncoat spin speed (RPM)", "spuncoat_volume": "Spuncoat volume (ml)", "dropcast_ambient_humidity": "Dropcast Ambient humidity (%)", "dropcast_ambient_temp": "Dropcast Ambient temp (C)", "dropcast_drying_temp": "Dropcast drying temp (C)", "dropcast_drying_time": "Dropcast drying time (min)", "dropcast_temp": "Dropcasting temperature (C)", "dropcast_volume": "Dropcast volume (ml)", "washed": "Washed", "washed_in": "Washed in"}
}


class Parent_vial(BaseModel):
    date: str
    executer: str
    barcode: str
    solvents: list
    salts: list
    total_volume: int

class Child(BaseModel):
    barcode: str
    executer: str
    date: str
    parents: list
    ambient_temp: float
    ambient_humidity: float

class Plate(BaseModel):
    executer: str
    date: str
    barcode: str
    precursor: str
    props: dict


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

#### Parent vials #####
#######################

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.get('/create', response_class=HTMLResponse)
async def create(request: Request):
    return templates.TemplateResponse('create_new.html', {'request': request, 'date': datetime.now().date()})

@app.get('/edit', response_class=HTMLResponse)
async def edit(request: Request):
    return templates.TemplateResponse('edit.html', {'request': request})

# Creates and uploads the parent metadata to dropbox
def save_parent(parent):
    data = [{},]

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

#### Child vials #####
######################

@app.get('/create-child', response_class=HTMLResponse)
async def create_child(request: Request):
    return templates.TemplateResponse('create_child.html', {'request': request, 'date': datetime.now().date()})

@app.post('/create/child')
def save_child(child: Child):
    data = [{}]
    for attribute, fieldname in CHILD_PROPERTIES_TO_FIELDNAMES.items():
        data[0][fieldname] = child.__getattribute__(attribute)

    for i, parent in enumerate(child.parents):
        if i > len(data) - 1:
            data.append({})
        data[i]['Parents'] = parent

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
async def get_child(request: Request, barcode: str):
    df, path = download(barcode, '/child_vials')
    output = {}
    output['parents'] = []
    for attribute, fieldname in CHILD_PROPERTIES_TO_FIELDNAMES.items():
        output[attribute] = df.iloc[0][fieldname]
    no_parents = df['Parents'].count()
    for i in range(no_parents):
        output['parents'].append(df.iloc[i]['Parents'])
    return templates.TemplateResponse('view_child.html', {'request': request} | output)

@app.get('/search/child', response_class=HTMLResponse)
async def search_child(request: Request):
    return templates.TemplateResponse('search_child.html', {'request': request})

#### Sample plates #####
########################

@app.get('/create-plate', response_class=HTMLResponse)
async def create_plate(request: Request):
    return templates.TemplateResponse('create_plate.html', {'request': request, 'date': datetime.now().date()})

@app.post('/plate')
async def save_plate(plate: Plate):
    data = [{},]
    for attribute, fieldname in PLATE_PROPERTIES_TO_FIELDNAMES['general'].items():
        data[0][fieldname] = plate.__getattribute__(attribute)
    for attribute, value in plate.props.items():
        fieldname = PLATE_PROPERTIES_TO_FIELDNAMES['props'][attribute]
        data[0][fieldname] = value

    # get fieldnames with that are only available in the given data
    fieldnames = [fieldname for fieldname in PLATE_FIELDNAMES if fieldname in data[0]]

    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    try:
        upload_csv_buffer(csv_buffer, f'/sample_plates/{data[0]["Date"]}_{plate.barcode}.csv')
        return {'detail': 'Uploaded successfully'}
    except Exception as e:
        return {'detail': 'Upload failed', 'error': e}
