from fastapi.testclient import TestClient
import backend.main as main
from backend.main import app, Parent_vial
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd

client = TestClient(app)

def test_get_salt_1():
    response = client.get('/get_salt/01-334088')
    assert response.status_code == 200
    assert response.json() == {'name': '2-Cyanoethyltriethoxysilane',
                               'chem_form': 'C9H19NO3Si', 'molar_mass': '217.34'}

def test_get_salt_2():
    response = client.get('/get_salt/24343212')
    assert response.status_code == 400
    assert response.json() == {'detail': 'Salt barcode not found'}

def test_get_solvent_1():
    response = client.get('/get_solvent/01-334087')
    assert response.status_code == 200
    assert response.json() == {
        'name': '2-Propanol',
        'concentration': 99.9,
    }

def test_save_parent_empty():
    barcode = 6865017
    parent = Parent_vial(date='2025-06-18', executer='Salvi',
                         barcode=str(barcode), salts=[], solvents=[])
    assert main.save_parent(parent) == {'detail': 'Uploaded successfully'}
    time.sleep(2)
    df, path = main.download(str(barcode))
    main.delete_file(path)
    df_2 = pd.read_csv('backend/test_files/2025-06-18_6865017.csv', dtype=str)
    pd.testing.assert_frame_equal(df, df_2)


def test_create_empty():
    driver = webdriver.Chrome()
    driver.get("http://localhost:8000/create")
    executer =driver.find_element(By.ID, 'executer')
    barcode_input = driver.find_element(By.ID, "parent_barcode")
    barcode = random.randint(0, 10000000)
    executer.send_keys('Salvi')
    barcode_input.send_keys(str(barcode))
    save_button = driver.find_element(By.ID, 'save')
    save_button.click()
    time.sleep(2)
    assert "Uploaded successfully" in driver.page_source
    driver.quit()

def test_create_salt():
    driver = webdriver.Chrome()
    driver.get("http://localhost:8000/create")
    executer =driver.find_element(By.ID, 'executer')
    barcode_input = driver.find_element(By.ID, "parent_barcode")
    barcode = random.randint(0, 10000000)
    executer.send_keys('Salvi')
    barcode_input.send_keys(str(barcode))
    add_salt_button = driver.find_element(By.ID, 'add_salt')
    add_salt_button.click()

    time.sleep(0.1)
    salts = driver.find_elements(By.CLASS_NAME, 'salt')
    assert len(salts) == 1
    salt = salts[0]
    salt_barcode = salt.find_element(By.CLASS_NAME, 'salt_barcode')
    salt_barcode.send_keys('01-314117')
    salt_barcode.send_keys(Keys.ENTER)
    time.sleep(0.1)
    salt_name = salt.find_element(By.CLASS_NAME, 'salt_name')
    salt_chem_form = salt.find_element(By.CLASS_NAME, 'salt_chem_form')
    assert salt_name.get_attribute('value') == f"100% ETHANOL"
    assert salt_chem_form.get_attribute('value') == 'C2H6O'
    salt_molar_mass = salt.find_element(By.CLASS_NAME, 'salt_molar_mass')
    salt_molar_mass.send_keys(46)
    salt_mass = salt.find_element(By.CLASS_NAME, 'salt_mass')
    salt_mass.send_keys(10)
    salt_ambient_temp = salt.find_element(By.CLASS_NAME, 'salt_ambient_temp')
    salt_ambient_temp.send_keys(101)
    salt_ambient_humidity = salt.find_element(By.CLASS_NAME, 'salt_ambient_humidity')
    salt_ambient_humidity.send_keys(43)

    # save to dropbox
    save_button = driver.find_element(By.ID, 'save')
    save_button.click()
    time.sleep(2)
    assert "Uploaded successfully" in driver.page_source
    driver.quit()
