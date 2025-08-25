import os
import csv
from datetime import datetime
from io import StringIO
import urllib
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import dropbox
import dropbox.files
import pandas as pd
import requests


## get API keys
load_dotenv()
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")
CHEMICALS_API_KEY = os.getenv("CHEMICALS_API_KEY")

PARENT_PATH = "/Buonassisi-Group/Projects - Active/Chemical Tracing"

### Load the dropbox account
dbx = dropbox.Dropbox(
    app_key=DROPBOX_APP_KEY,
    app_secret=DROPBOX_APP_SECRET,
    oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
)
account = dbx.users_get_current_account()
team_namespace_id = account.root_info.root_namespace_id
dbx = dbx.with_path_root(dropbox.common.PathRoot.namespace_id(team_namespace_id))

## create the app
app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

PROFILE_FIELDNAMES = [
    "Name",
    "Parent vial directories",
    "Child vial directories",
    "Sample plate directories",
]

PROFILE_PROPERTIES_TO_FIELDNAMES = {
    "name": "Name",
    "parent": "Parent vial directories",
    "child": "Child vial directories",
    "sample": "Sample plate directories",
}

## Models


class ParentVial(BaseModel):
    """
    model for the parent vial JSON input
    """

    date: str
    executer: str
    barcode: str
    solvents: list
    salts: list
    total_volume: float
    directory: str
    notes: str
    molarity: float


class Child(BaseModel):
    """
    model for the Child vial JSON input
    """

    barcode: str
    executer: str
    date: str
    parents: list
    ambient_temp: float
    ambient_humidity: float
    directory: str
    notes: str


class Plate(BaseModel):
    """
    Model for the Plate JSON input
    """

    executer: str
    date: str
    barcode: str
    precursor: str
    props: dict
    directory: str
    notes: str
    other_treatment: str


class Profile(BaseModel):
    """
    Model for the profile JSON input
    """

    name: str
    parent: list
    child: list
    sample: list


#### Dropbox helper functions ###
def get_initials(full_name):
    """
    Returns the initials of a name
    """
    return ".".join([name[0] for name in full_name.split(" ")])


def upload_file(local_file_path, dropbox_file_path):
    """
    Uploads local file to the given dropbox file path
    """
    with open(local_file_path, "rb") as f:
        dbx.files_upload(
            f.read(),
            PARENT_PATH + dropbox_file_path,
            mode=dropbox.files.WriteMode("overwrite"),
        )


def search_keyword(keyword, parent_folder="/Parent vials"):
    """
    Returns all matches to the given keyword in the given parent forlder
    """
    path = PARENT_PATH + parent_folder
    options = dropbox.files.SearchOptions(path=path)
    result = dbx.files_search_v2(query=str(keyword), options=options)
    return result.matches


def download(name, parent_folder="/Parent vials"):
    """
    Downloads the file with the given barcode,
    Returns the data frame and the file path
    """
    matches = search_keyword(name, parent_folder)
    if len(matches) == 0:
        raise HTTPException(
            status_code=404, detail=f"Vial with barcode {name} does not exist"
        )
    if len(matches) > 1:
        raise HTTPException(
            status_code=400, detail=f"There are multiple vials with the barcode {name}"
        )
    match = matches[0]
    path = match.metadata.get_metadata().path_display
    metadata, response = dbx.files_download(path)
    csv_data = response.content.decode("utf-8")
    df = pd.read_csv(StringIO(csv_data), dtype=str)
    return df, path


def check_if_exists(keyword, parent_folder):
    """
    Check if there exists a file with the given keyword in the given folder
    Return true if it exists
    """
    return len(search_keyword(keyword, parent_folder)) != 0


def upload_csv_buffer(csv_buffer, dropbox_file_path):
    """
    Uploads a csv buffer to the given dropbox file path + the parent path
    """
    return dbx.files_upload(
        csv_buffer.getvalue().encode("utf-8"),
        PARENT_PATH + dropbox_file_path,
        mode=dropbox.files.WriteMode("overwrite"),
    )


def upload_csv_buffer_to_path(csv_buffer, dropbox_file_path):
    """
    Uploads a csv buffer to the given dropbox file path + the parent path
    """
    return dbx.files_upload(
        csv_buffer.getvalue().encode("utf-8"),
        dropbox_file_path,
        mode=dropbox.files.WriteMode("overwrite"),
    )


def delete_file(file_path):
    """
    Deletes a files at the given dropbox file path
    """
    dbx.files_delete_v2(file_path)


def all_file_names(directory):
    """
    Returns all file names in the given directory sorted in alphabetical order
    """
    path = PARENT_PATH + directory
    entries = []
    try:
        result = dbx.files_list_folder(path)
        entries.extend(result.entries)

        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)

        file_names = [
            entry.name[:-4]
            for entry in entries
            if isinstance(entry, dropbox.files.FileMetadata)
        ]
        return sorted(file_names)

    except dropbox.exceptions.ApiError as err:
        print("API error:", err)
        return []


### Salt and solvent API endpoints ###
@app.get("/salt/{salt_barcode}")
def get_salt(salt_barcode: str):
    """
    Returns information about a salt from the EHS inventory and the pubchem database
    """
    params = {"AuthKey": CHEMICALS_API_KEY, "barcode": salt_barcode}
    try:
        response = requests.get(
            "https://onsite-prd-app1.mit.edu/ehsa/public/ApiInterface/GetChemicalInventoryData",
            params=params,
            timeout=5,
        )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=400, detail="Request timeout")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=400, detail="Connection error")

    try:
        result = response.json()
        cas = result["Table"][0]["cas_num"]
        name = result["Table"][0]["chemical_description"]
        chem_form = result["Table"][0]["chemical_formula"]
        molar_mass = ""
        if cas:
            try:
                pub_result = requests.get(
                    f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas}/cids/JSON",
                    timeout=5,
                ).json()
            except requests.exceptions.Timeout:
                pub_result = {"Fault": "Timeout"}
            if "Fault" in pub_result and name != "":
                encoded_name = urllib.parse.quote(name.lower())
                try:
                    pub_result = requests.get(
                        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/cids/JSON",
                        timeout=5,
                    ).json()
                except requests.exceptions.Timeout:
                    pub_result = {"Fault": "Timeout"}
            if "Fault" not in pub_result:
                cid = pub_result["IdentifierList"]["CID"][0]
                try:
                    response = requests.get(
                        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularWeight,MolecularFormula/JSON",
                        timeout=5,
                    ).json()
                except requests.exceptions.Timeout:
                    pub_result = {"Fault": "Timeout"}
                if "Fault" not in response:
                    molar_mass = response["PropertyTable"]["Properties"][0][
                        "MolecularWeight"
                    ]
                    if not chem_form:
                        chem_form = response["PropertyTable"]["Properties"][0][
                            "MolecularFormula"
                        ]
        return {
            "name": name,
            "chem_form": chem_form,
            "molar_mass": molar_mass,
            "receipt_date": result["Table"][0]["receipt_date"][:10],
        }

    except json.JSONDecodeError:
        error = response.text
        if error == 'Invalid Key':
            raise HTTPException(status_code=500, detail='Chemical Inventory API Key is invalid')
        raise HTTPException(status_code=400, detail=error)


@app.get("/solvent/{solvent_barcode}")
def get_solvent(solvent_barcode: str):
    """
    Returns the solvent information from the EHS database
    """
    params = {"AuthKey": CHEMICALS_API_KEY, "barcode": solvent_barcode}
    try:
        response = requests.get(
            "https://onsite-prd-app1.mit.edu/ehsa/public/ApiInterface/GetChemicalInventoryData",
            params=params,
            timeout=5,
        )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=400, detail="Request timeout")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=400, detail="Connection error")
    try:
        result = response.json()
        return {
            "name": result["Table"][0]["chemical_description"],
            "concentration": result["Table"][0]["concentration"],
            "receipt_date": result["Table"][0]["receipt_date"][:10],
        }
    except json.JSONDecodeError:
        error = response.text
        if error == 'Invalid Key':
            raise HTTPException(status_code=500, detail='Chemical Inventory API Key is invalid')
        raise HTTPException(status_code=400, detail=error)


### Homepage ####


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Renders the homepage
    """
    return templates.TemplateResponse("index.html", {"request": request})


#### Parent vials #####
#######################

### Fieldnames for generated csv files and the respective properties for parent vial
FIELDNAMES = [
    "Date",
    "Executer",
    "Barcode of Vial",
    "Desired molarity",
    "Total volume (ml)",
    "Barcode on the salt",
    "Salt name",
    "Chemical formula",
    "Salt Molecular Weight in g/mol",
    "Stoichiometric ratio",
    "Mass of salt added in the vial in g",
    "Ambient temperature in glovebox (C)",
    "Ambient humidity in glovebox (%)",
    "Salt receipt date",
    "Barcode on the solvent",
    "Name of the solvent",
    "Concentration of the solvent (%)",
    "Vol of solvent added (ml)",
    "Ambient temperature (C)",
    "Ambient humidity (%)",
    "Stir Time (min)",
    "Solvent receipt date",
    "Notes",
    "Save copy to",
]

PROPERTIES_TO_FIELDMAMES = {
    "general": {
        "executer": "Executer",
        "barcode": "Barcode of Vial",
        "date": "Date",
        "total_volume": "Total volume (ml)",
        "directory": "Save copy to",
        "notes": "Notes",
        "molarity": "Desired molarity",
    },
    "salts": {
        "name": "Salt name",
        "barcode": "Barcode on the salt",
        "ratio": "Stoichiometric ratio",
        "chemical_formula": "Chemical formula",
        "molar_mass": "Salt Molecular Weight in g/mol",
        "mass": "Mass of salt added in the vial in g",
        "ambient_temp": "Ambient temperature in glovebox (C)",
        "ambient_humidity": "Ambient humidity in glovebox (%)",
        "receipt_date": "Salt receipt date",
    },
    "solvents": {
        "barcode": "Barcode on the solvent",
        "name": "Name of the solvent",
        "concentration": "Concentration of the solvent (%)",
        "vol_added": "Vol of solvent added (ml)",
        "ambient_temp": "Ambient temperature (C)",
        "ambient_humidity": "Ambient humidity (%)",
        "stir_time": "Stir Time (min)",
        "receipt_date": "Solvent receipt date",
    },
}


@app.get("/create/parent", response_class=HTMLResponse)
async def create_new_parent(request: Request):
    """
    Renders the page which allows the user to enter the parent vial metadata
    """
    return templates.TemplateResponse(
        "create_parent.html",
        {
            "request": request,
            "date": datetime.now().date(),
            "profiles": list_all_profiles(),
        },
    )


@app.get("/search/parent", response_class=HTMLResponse)
async def search_parent(request: Request):
    """
    Renders the page which allows the user to search for the parent using barcode
    """
    return templates.TemplateResponse("search_parent.html", {"request": request})


# Creates and uploads the parent metadata to dropbox
def save_parent(parent: ParentVial):
    """
    Saves the given parent vial metadata to dropbox
    """
    data = [
        {},
    ]

    # for each general attribute, add the data to the fieldname
    for attribute, fieldname in PROPERTIES_TO_FIELDMAMES["general"].items():
        data[0][fieldname] = parent.__getattribute__(attribute)

    # for each salt attribute, add the data to the fieldname
    for i, salt in enumerate(parent.salts):
        if i > len(data) - 1:
            data.append({})
        row = data[i]
        for attribute, fieldname in PROPERTIES_TO_FIELDMAMES["salts"].items():
            row[fieldname] = salt[attribute]

    # for each solvent attribute, add the data to the fieldname
    for i, solvent in enumerate(parent.solvents):
        if i > len(data) - 1:
            data.append({})
        row = data[i]
        for attribute, fieldname in PROPERTIES_TO_FIELDMAMES["solvents"].items():
            row[fieldname] = solvent[attribute]

    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    try:
        upload_csv_buffer(
            csv_buffer, f'/Parent vials/{data[0]["Date"]}_{parent.barcode}.csv'
        )
        upload_csv_buffer_to_path(
            csv_buffer, f'{parent.directory}/{data[0]["Date"]}_{parent.barcode}.csv'
        )
        return {"detail": "Uploaded successfully"}
    except Exception as e:
        return {"detail": "Upload failed", "error": e}


@app.post("/create/parent")
async def create_parent(parent: ParentVial):
    """
    Creates a new parent vial and saves the metadata to dropbox
    """
    try:
        matches = search_keyword(parent.barcode)
    except Exception as e:
        return {"detail": "Upload failed", "error": e}
    if len(matches) == 1:
        raise HTTPException(
            status_code=400,
            detail=f"There exists a vial with this barcode {parent.barcode}",
        )
    return save_parent(parent)


@app.post("/edit/parent")
async def edit_parent(parent: ParentVial):
    """
    Edits the given parent vial metadata and save the information to dropbox
    """
    matches = search_keyword(parent.barcode)
    if len(matches) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"parent vial with barcode {parent.barcode} does not exist",
        )
    if len(matches) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"There are multiple vials with the barcode {parent.barcode}",
        )
    print(parent)
    return save_parent(parent)


# Downloads the parent metadata from dropbox
@app.get("/parent", response_class=HTMLResponse)
async def get_parent(request: Request, barcode: str):
    """
    Renders the page which allows the user to edit and view parent vial information
    """
    df, path = download(barcode)
    output = {}
    salts = []
    solvents = []
    for attribute, fieldname in PROPERTIES_TO_FIELDMAMES["general"].items():
        output[attribute] = df.loc[0, fieldname] if not pd.isna(df.loc[0, fieldname]) else ''
    no_salts = df["Salt name"].count()
    for i in range(no_salts):
        salt = {}
        for attribute, fieldname in PROPERTIES_TO_FIELDMAMES["salts"].items():
            salt[attribute] = df.iloc[i][fieldname]
        salts.append(salt)
    no_solvents = df["Name of the solvent"].count()
    for i in range(no_solvents):
        solvent = {}
        for attribute, fieldname in PROPERTIES_TO_FIELDMAMES["solvents"].items():
            solvent[attribute] = df.iloc[i][fieldname]
        solvents.append(solvent)

    output["salts"] = salts
    output["solvents"] = solvents
    return templates.TemplateResponse("edit_vial.html", {"request": request} | output)


#### Child vials #####
######################

## Fieldnames for generated csv and respective JS

CHILD_FIELDNAMES = [
    "Date",
    "Executer",
    "Barcode on holder",
    "Parents",
    "Ambient temperature (C)",
    "Ambient humidity (%)",
    "Notes",
    "Save copy to",
]

CHILD_PROPERTIES_TO_FIELDNAMES = {
    "date": "Date",
    "executer": "Executer",
    "barcode": "Barcode on holder",
    "ambient_temp": "Ambient temperature (C)",
    "ambient_humidity": "Ambient humidity (%)",
    "directory": "Save copy to",
    "notes": "Notes",
}


@app.get("/create/child", response_class=HTMLResponse)
async def create_child(request: Request):
    """
    Renders the page which allows the user to enter the child vial metadata
    """
    return templates.TemplateResponse(
        "create_child.html",
        {
            "request": request,
            "date": datetime.now().date(),
            "profiles": list_all_profiles(),
        },
    )


@app.post("/create/child")
def save_child(child: Child):
    """
    Uploads the child metadata to dropbox
    """
    if check_if_exists(child.barcode, "/Child vials"):
        return {"detail": f"Child vial with barcode {child.barcode} already exists"}
    data = [{}]
    for attribute, fieldname in CHILD_PROPERTIES_TO_FIELDNAMES.items():
        data[0][fieldname] = child.__getattribute__(attribute)

    for i, parent in enumerate(child.parents):
        if i > len(data) - 1:
            data.append({})
        data[i]["Parents"] = parent

    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=CHILD_FIELDNAMES)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    try:
        upload_csv_buffer(
            csv_buffer, f'/Child vials/{data[0]["Date"]}_{child.barcode}.csv'
        )
        upload_csv_buffer_to_path(
            csv_buffer, f'{child.directory}/{data[0]["Date"]}_{child.barcode}'
        )
        return {"detail": "Uploaded successfully"}
    except Exception as e:
        return {"detail": "Upload failed", "error": e}


@app.get("/search/child", response_class=HTMLResponse)
async def search_child(request: Request):
    """
    Renders the plate which allows the user to search the child vial metadata by child
    vial barcode
    """
    return templates.TemplateResponse("search_child.html", {"request": request})


@app.get("/child", response_class=HTMLResponse)
async def get_child(request: Request, barcode: str):
    """
    Renders the page which allows the user to view the child vial metadata
    given the barcode
    """
    df, path = download(barcode, "/Child vials")
    output = {}
    output["parents"] = []
    for attribute, fieldname in CHILD_PROPERTIES_TO_FIELDNAMES.items():
        output[attribute] = df.loc[0, fieldname] if not pd.isna(df.loc[0, fieldname]) else ''
    no_parents = df["Parents"].count()
    for i in range(no_parents):
        output["parents"].append(df.iloc[i]["Parents"])
    return templates.TemplateResponse("view_child.html", {"request": request} | output)


#### Sample plates #####
########################

### fieldnames for csv and the respective

PLATE_FIELDNAMES = [
    "Date",
    "Executer",
    "Sample plate barcode",
    "Precursor vial barcode",
    "Washed",
    "Washed in",
    "Ozone treatment",
    "Ozone treatment time (min)",
    "Additional treatment notes",
    "Sample type",
    "Dropcast droplet volume (μl)",
    "Dropcasting temperature (C)",
    "Dropcast Ambient temp (C)",
    "Dropcast Ambient humidity (%)",
    "Dropcast drying temp (C)",
    "Dropcast drying time (min)",
    "Spuncoat droplet volume (μl)",
    "Spuncoat spin speed (RPM)",
    "Spuncoat spin acceleration",
    "Spuncoat spin time",
    "Spuncoat ambient temp (C)",
    "Spuncoat ambient humidity (%)",
    "Annealing temp (C)",
    "Annealing time (min)",
    "Ambient temp at anneal (C)",
    "Ambient Humidity at anneal (%)",
    "Notes",
    "Save copy to",
]

PLATE_PROPERTIES_TO_FIELDNAMES = {
    "general": {
        "date": "Date",
        "barcode": "Sample plate barcode",
        "executer": "Executer",
        "precursor": "Precursor vial barcode",
        "directory": "Save copy to",
        "other_treatment": "Additional treatment notes",
        "notes": "Notes",
    },
    "props": {
        "anneal_ambient_humidity": "Ambient Humidity at anneal (%)",
        "anneal_ambient_temp": "Ambient temp at anneal (C)",
        "annealing_temp": "Annealing temp (C)",
        "annealing_time": "Annealing time (min)",
        "ozone": "Ozone treatment",
        "ozone_time": "Ozone treatment time (min)",
        "sample_type": "Sample type",
        "spuncoat_spin_speed": "Spuncoat spin speed (RPM)",
        "spuncoat_droplet_volume": "Spuncoat droplet volume (μl)",
        "spuncoat_spin_acceleration": "Spuncoat spin acceleration",
        "spuncoat_spin_time": "Spuncoat spin time",
        "spuncoat_ambient_temp": "Spuncoat ambient temp (C)",
        "spuncoat_ambient_humidity": "Spuncoat ambient humidity (%)",
        "dropcast_ambient_humidity": "Dropcast Ambient humidity (%)",
        "dropcast_ambient_temp": "Dropcast Ambient temp (C)",
        "dropcast_drying_temp": "Dropcast drying temp (C)",
        "dropcast_drying_time": "Dropcast drying time (min)",
        "dropcast_temp": "Dropcasting temperature (C)",
        "dropcast_droplet_volume": "Dropcast droplet volume (μl)",
        "washed": "Washed",
        "washed_in": "Washed in",
    },
}


@app.get("/create/plate", response_class=HTMLResponse)
async def create_plate(request: Request):
    """
    Renders the page which allows the user to enter the sample plate metadata
    """
    return templates.TemplateResponse(
        "create_plate.html",
        {
            "request": request,
            "date": datetime.now().date(),
            "profiles": list_all_profiles(),
        },
    )


@app.post("/plate")
async def save_plate(plate: Plate):
    """
    Uploads the plate metadata to dropbox
    """
    if check_if_exists(plate.barcode, "/Sample plates"):
        return {"detail": f"Sample plate with barcode {plate.barcode} already exists"}
    data = [
        {},
    ]
    for attribute, fieldname in PLATE_PROPERTIES_TO_FIELDNAMES["general"].items():
        data[0][fieldname] = plate.__getattribute__(attribute)
    for attribute, value in plate.props.items():
        fieldname = PLATE_PROPERTIES_TO_FIELDNAMES["props"][attribute]
        data[0][fieldname] = value

    sample_types = {"Dropcast": "dc", "Spuncoat": "sc"}
    sample_type = sample_types[plate.props["sample_type"]]

    ## find precursors and copy
    initials = get_initials(plate.executer)
    precursor = plate.precursor
    child_matches = search_keyword(precursor, "/Child vials")
    new_plate_folder = (
        plate.directory + f"/{plate.date}-{initials}-{plate.barcode}-{sample_type}"
    )

    ### Check if the precursor was a child vial or not

    # if the parent was a child vial, copy from the child vials directiry
    if len(child_matches) == 1:
        df, path = download(precursor, "/Child vials")
        child_file_name = path.split("/")[-1]
        dbx.files_copy_v2(
            from_path=path,
            to_path=new_plate_folder + f"/child-vial-{child_file_name}",
        )
        parents = df["Parents"].to_list()
        for parent in parents:
            parent_path = (
                search_keyword(parent, "/Parent vials")[0]
                .metadata.get_metadata()
                .path_display
            )
            parent_file_name = parent_path.split("/")[-1]
            dbx.files_copy_v2(
                from_path=parent_path,
                to_path=new_plate_folder + f"/parent-vial-{parent_file_name}",
            )

    # otherwise, the precursor should be a parent vial
    # find the parent vial information and copy to the plate directory
    elif len(child_matches) == 0:
        try:
            parent_path = (
                search_keyword(precursor, "/Parent vials")[0]
                .metadata.get_metadata()
                .path_display
            )
            parent_file_name = parent_path.split("/")[-1]
            dbx.files_copy_v2(
                from_path=parent_path,
                to_path=new_plate_folder + f"/parent-vial-{parent_file_name}",
            )
        except:
            return {"detail": "Precursor barcode is not found"}
    else:
        return {"detail": "Multiple precursors found with the same barcode"}

    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=PLATE_FIELDNAMES)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    # Create the folders in the new folders
    for folder_name in ("General", "Hyperspectral", "SEM/EDS", "XRD"):
        folder_path = new_plate_folder + "/" + folder_name
        dbx.files_create_folder_v2(folder_path)

    try:
        upload_csv_buffer(
            csv_buffer, f'/Sample plates/{data[0]["Date"]}_{plate.barcode}.csv'
        )
        upload_csv_buffer_to_path(
            csv_buffer,
            new_plate_folder + f'/sample-{data[0]["Date"]}_{plate.barcode}.csv',
        )
        return {"detail": "Uploaded successfully"}
    except Exception as e:
        return {"detail": "Upload failed", "error": e}


@app.get("/search/plate")
def search_plate(request: Request):
    """
    Returns the page which allows to search the plate barcode
    """
    return templates.TemplateResponse("search_plate.html", {"request": request})


@app.get("/plate")
def get_plate(request: Request, barcode):
    """
    Downloads the information related to a sample plate
    """
    df, path = download(barcode, "/Sample plates")
    out = {}
    out["props"] = {}
    for attribute, fieldname in PLATE_PROPERTIES_TO_FIELDNAMES["general"].items():
        out[attribute] = df.loc[0, fieldname] if not pd.isna(df.loc[0, fieldname]) else ''
    for attribute, fieldname in PLATE_PROPERTIES_TO_FIELDNAMES["props"].items():
        out["props"][attribute] = df.iloc[0][fieldname]
    precursor = out["precursor"]
    is_child = check_if_exists(precursor, "/Child vials")
    out["is_child"] = is_child
    return templates.TemplateResponse("view_plate.html", {"request": request} | out)


### Profiles ####
#################
@app.get("/profiles", response_class=HTMLResponse)
async def list_profiles(request: Request):
    """
    Renders the page which lists all the saved profiles
    """
    profiles = list_all_profiles()
    return templates.TemplateResponse(
        "profiles.html", {"request": request, "profiles": profiles}
    )


@app.get("/create-profile", response_class=HTMLResponse)
async def create_profile(request: Request):
    """
    Renders the page that allows user to create profile
    """
    return templates.TemplateResponse("create_profile.html", {"request": request})


@app.post("/profile")
def save_profile(profile: Profile):
    """
    Uploads the given profile information to dropbox
    """
    data = [{}]
    data[0]["Name"] = profile.name
    for i, directory in enumerate(profile.parent):
        if i > len(data) - 1:
            data.append({})
        fieldname = PROFILE_PROPERTIES_TO_FIELDNAMES["parent"]
        data[i][fieldname] = directory

    for i, directory in enumerate(profile.child):
        if i > len(data) - 1:
            data.append({})
        fieldname = PROFILE_PROPERTIES_TO_FIELDNAMES["child"]
        data[i][fieldname] = directory

    for i, directory in enumerate(profile.sample):
        if i > len(data) - 1:
            data.append({})
        fieldname = PROFILE_PROPERTIES_TO_FIELDNAMES["sample"]
        data[i][fieldname] = directory

    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=PROFILE_FIELDNAMES)
    writer.writeheader()
    writer.writerows(data)
    csv_buffer.seek(0)

    try:
        upload_csv_buffer(csv_buffer, f"/Profiles/{profile.name}.csv")
        return {"detail": "Uploaded successfully"}
    except Exception as e:
        return {"detail": "Upload failed", "error": e}


def list_all_profiles():
    """
    Returns all user profiles
    """
    return all_file_names("/Profiles")


def download_directories(profile_name):
    """
    Returns all directories found under the given profile name
    """
    path = PARENT_PATH + "/Profiles/" + profile_name + ".csv"
    metadata, response = dbx.files_download(path)
    csv_data = response.content.decode("utf-8")
    df = pd.read_csv(StringIO(csv_data), dtype=str)
    output = {}
    output["name"] = df.iloc[0]["Name"]
    sections = ["parent", "child", "sample"]
    for section in sections:
        fieldname = PROFILE_PROPERTIES_TO_FIELDNAMES[section]
        output[section] = []
        count = df[fieldname].count()
        for i in range(count):
            output[section].append(df.iloc[i][fieldname])
    return output


@app.get("/profile/{profile_name}", response_class=HTMLResponse)
async def edit_profile(request: Request, profile_name: str):
    """
    Renders the page which allows the user to edit their profile
    """
    output = download_directories(profile_name)
    return templates.TemplateResponse(
        "edit_profile.html",
        {
            "request": request,
        }
        | output,
    )


@app.get("/directories")
def get_directories(profile: str, input_type: str):
    """
    Returns all directories for the given profile for the given type
    type: either parent, child, or plate
    """
    return {"directories": download_directories(profile)[input_type]}
