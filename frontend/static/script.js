document.addEventListener('DOMContentLoaded', function() {
  document.querySelector('#save').addEventListener('click', save_to_dropbox);
});

// Creates a new form to add an extra salt
function add_salt(event) {
    const element = event.target;
    const parent_div = element.parentElement;
    const salt_content_div = parent_div.querySelector('#salt_content');
    const initial_content = salt_content_div.querySelector('.salt').innerHTML;
    const new_salt_div = document.createElement('div');
    new_salt_div.className = "salt";
    new_salt_div.innerHTML = initial_content;
    salt_content_div.appendChild(new_salt_div);
}

// Creates a new form to add an extra solvent
function add_solvent(event) {
    const element = event.target;
    const parent_div = element.parentElement;
    const solvent_content_div = parent_div.querySelector('#solvent_content');
    const initial_content = solvent_content_div.querySelector('.solvent').innerHTML;
    const new_solvent_div = document.createElement('div');
    new_solvent_div.className = "solvent";
    new_solvent_div.innerHTML = initial_content;
    solvent_content_div.appendChild(new_solvent_div);
}

function save_to_dropbox() {
    console.log('Hello');
    const salts_div = document.querySelector('#salt_content');
    const solvents_div = document.querySelector('#solvent_content');
    const executer = document.querySelector('#executer').value;
    const barcode = document.querySelector('#parent_barcode').value;
    let salt_index = 1;
    let solvent_index = 1;
    let salts = {};
    let solvents = {};
    salts_div.querySelectorAll('.salt').forEach(function(div) {
        salts[salt_index] = {
            barcode: div.querySelector('.salt_barcode').value,
            name: div.querySelector('.salt_name').value,
            chemical_formula: div.querySelector('.salt_chem_form').value,
            molar_mass: div.querySelector('.salt_molar_mass').value,
            mass: div.querySelector('.salt_mass').value
        }
        salt_index += 1;
    });
    solvents_div.querySelectorAll('.solvent').forEach(function(div) {
        solvents[solvent_index] = {
            barcode: div.querySelector('.solvent_barcode').value,
            name: div.querySelector('.solvent_name').value,
            concentration: div.querySelector('.solvent_concentration').value,
            vol_added: div.querySelector('.solvent_vol').value,
            desired_molarity: div.querySelector('.solvent_molarity').value,
            ambient_temp: div.querySelector('.solvent_temp').value,
            ambient_humidity: div.querySelector('.solvent_humidity').value,
            stir_time: div.querySelector('.solvent_stir_time').value
        }
        solvent_index += 1;
    });
    console.log(salts);
    console.log(solvents);
    fetch('/create/parent', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            executer: executer,
            barcode: barcode,
            no_salts: salt_index -1,
            salts: salts,
            solvents: solvents,
        })
    })
    .then((response) => response.json())
    .then((data) => {
        console.log(data['message'])
    })
}

function search_salt_barcode(event) {
    event.preventDefault();
    target = event.target;
    barcode = target.parentElement.querySelector('.salt_barcode').value;
    parent_div = target.parentElement.parentElement
    fetch(`/get_salt/${barcode}`)
    .then((response) => response.json())
    .then((data) => {
        parent_div.querySelector('.salt_name').value = data['name'];
        parent_div.querySelector('.salt_chem_form').value = data['chem_form'];
    })
    .catch((error) => {
        console.log('Error', error)
    })
}

function search_solvent(event) {
    event.preventDefault();
    target = event.target;
    barcode = target.parentElement.querySelector('.solvent_barcode').value;
    parent_div = target.parentElement.parentElement
    fetch(`/get_solvent/${barcode}`)
    .then((response) => response.json())
    .then((data) => {
        parent_div.querySelector('.solvent_name').value = data['name'];
        parent_div.querySelector('.solvent_concentration').value = data['concentration'];
    })
    .catch((error) => {
        console.log('Error', error)
    })
}
