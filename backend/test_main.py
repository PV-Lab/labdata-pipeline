from fastapi.testclient import TestClient
import backend.main as main
from backend.main import app, Parent_vial
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

client = TestClient(app)

def test_get_salt_1():
    response = client.get('/get_salt/01-334088')
    assert response.status_code == 200
    assert response.json() == {'name': '2-Cyanoethyltriethoxysilane',
                               'chem_form': 'C9H19NO3Si'}

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
    barcode = random.randint(0, 10000000)
    parent = Parent_vial(date='2025-06-17', executer='Salvi',
                         barcode=str(barcode), salts=[], solvents=[])
    assert main.save_parent(parent) == {'detail': 'Uploaded successfully'}

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
    add_test
    save_button = driver.find_element(By.ID, 'save')
    save_button.click()
    time.sleep(2)
    assert "Uploaded successfully" in driver.page_source
    driver.quit()
