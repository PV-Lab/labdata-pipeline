document.addEventListener('DOMContentLoaded', function () {
    try {
        const washed_radios = document.querySelectorAll('input[name="washed"]');
        washed_radios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    if (radio.value === 'Yes') {
                        document.querySelector('#washed').innerHTML = `In what: <input type="text" id="washed_in">`;
                        document.querySelector('#washed_in').focus();
                    } else {
                        document.querySelector('#washed').innerHTML = '';
                    }
                }
            });
        });
        const ozone_radios = document.querySelectorAll('input[name="ozone"]');
        ozone_radios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    if (radio.value === 'Yes') {
                        document.querySelector('#ozone').innerHTML = `Time treated (min): <input type="text" id="ozone_time">`;
                        document.querySelector('#ozone_time').focus();
                    } else {
                        document.querySelector('#ozone').innerHTML = '';
                    }
                }
            });
        });
        const sample_type_radios = document.querySelectorAll('input[name="sample_type"]')
        sample_type_radios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    if (radio.value === 'Dropcast') {
                        document.querySelector('#sample_type').innerHTML = `<div>
                        <div>
                        Droplet volume (μl): <input type="number" id="dropcast_droplet_volume">
                        </div>
                        <div>
                        Dropcasting temperature (C): <input type="number" id="dropcast_temp">
                        </div>
                        <div>
                        Ambient temperature (C): <input type="number" id="dropcast_ambient_temp">
                        </div>
                        <div>
                        Ambient humidity (%): <input type="number" id="dropcast_ambient_humidity">
                        </div>
                        <div>
                        Drying temperature (C): <input type="number" id="dropcast_drying_temp">
                        </div>
                        <div>
                        Drying time (min): <input type="number" id="dropcast_drying_time">
                        </div>
                        </div>`;
                        document.querySelector('#dropcast_volume').focus();
                    } else {
                        document.querySelector('#sample_type').innerHTML = `
                        <div>
                        <div>Droplet volume (μl): <input type="number" id="spuncoat_droplet_volume"></div>
                        <div>Spin speed (RPM): <input type="number" id="spuncoat_spin_speed"></div>
                        <div>Spin acceleration: <input type="number" id="spuncoat_spin_acceleration"></div>
                        <div>Spin time (min): <input type="number" id="spuncoat_spin_time"></div>
                        <div>Ambient temperature (C): <input type="number" id="spuncoat_ambient_temp"></div>
                        <div>Ambient humidity (%): <input type="number" id="spuncoat_ambient_humidity"></div>
                        </div>
                        `;
                        document.querySelector('#spuncoat_volume').focus();
                    }
                }
            });
        });
    } catch (e) {
        console.error("Error:", e.message);
    }
})

// Salts and solvents divd
// Creates a new form to add an extra salt
function add_salt(event) {
    const element = event.target;
    const parent_div = element.parentElement;
    const salt_content_div = parent_div.querySelector('#salt_content');
    const new_salt_div = document.createElement('div');
    new_salt_div.className = "salt";
    new_salt_div.innerHTML = `
    <form>
        <div>
            Salt barcode: <input class="salt_barcode" type="text" onkeypress="search_salt_barcode(event)"> <span class="spinner"></span>
        </div>
        <div>
            Salt name: <input class="salt_name" type="text">
        </div>
        <div>
            Chemical formula: <input class="salt_chem_form" type="text">
        </div>
        <div>
            Molar mass (g/mol): <input class="salt_molar_mass" type="number">
        </div>
         <div>
            Stoichiometric ratio: <input class="salt_ratio" type="number" value="1"> <button onclick="calculate_mass(event)">Calculate mass</button> <span class="spinner"></span>
        </div>
        <div>
            Mass (g): <input class="salt_mass" type="number">
        </div>
        <div>
            Ambient temperature in GB (C): <input class="salt_ambient_temp" type="number">
        </div>
        <div>
            Ambient humidity in GB (%): <input class="salt_ambient_humidity" type="number">
        </div>
        <div>
            Salt receipt date: <input class="salt_receipt_date" type="text">
        </div>
    </form>
    <hr>
    `;
    salt_content_div.appendChild(new_salt_div);
}

// Creates a new form to add an extra solvent
function add_solvent(event) {
    const element = event.target;
    const parent_div = element.parentElement;
    const solvent_content_div = parent_div.querySelector('#solvent_content');
    const new_solvent_div = document.createElement('div');
    new_solvent_div.className = "solvent";
    new_solvent_div.innerHTML = `
            <form>
                <div>
                    Solvent barcode: <input class="solvent_barcode" type="text" onkeypress="search_solvent(event)"> <span class="spinner"></span>
                </div>
                <div>
                    Solvent name: <input class="solvent_name" type="text">
                </div>
                <div>
                    Concentration: <input class="solvent_concentration" type="text">
                </div>
                <div>
                    Volume added (ml): <input class="solvent_vol" type="number">
                </div>
                <div>
                    Ambient temperature (C): <input class="solvent_temp" type="number">
                </div>
                <div>
                    Ambient humidity (%): <input class="solvent_humidity" type="number">
                </div>
                <div>
                    Stir time (min): <input class="solvent_stir_time" type="number">
                </div>
                <div>
                    Solvent receipt date: <input class="solvent_receipt_date" type="text">
                </div>
            </form>
            <hr>
        `;
    solvent_content_div.appendChild(new_solvent_div);
}

// Creating and sending Parent vial JSON

function create_parent_object() {
    const salts_div = document.querySelector('#salt_content');
    const solvents_div = document.querySelector('#solvent_content');
    const executer = document.querySelector('#executer').value;
    const barcode = document.querySelector('#parent_barcode').value;
    const date = document.querySelector('#date').innerHTML;
    const total_volume = document.querySelector('#volume').value;
    const directory = document.querySelector('#directory').value;
    const notes = document.querySelector('#notes').value;
    const molarity = document.querySelector('#molarity').value;
    let salts = [];
    let solvents = [];
    salts_div.querySelectorAll('.salt').forEach(function(div) {
        if (div.querySelector('.salt_barcode').value === '') {
            return;
        }

        salts.push({
            barcode: div.querySelector('.salt_barcode').value,
            name: div.querySelector('.salt_name').value,
            chemical_formula: div.querySelector('.salt_chem_form').value,
            molar_mass: div.querySelector('.salt_molar_mass').value,
            ratio: div.querySelector('.salt_ratio').value,
            mass: div.querySelector('.salt_mass').value,
            ambient_temp: div.querySelector('.salt_ambient_temp').value,
            ambient_humidity: div.querySelector('.salt_ambient_humidity').value,
            receipt_date: div.querySelector('.salt_receipt_date').value,
        });
    });
    solvents_div.querySelectorAll('.solvent').forEach(function(div) {
        if (div.querySelector('.solvent_barcode').value === '') {
            return;
        }

        solvents.push({
            barcode: div.querySelector('.solvent_barcode').value,
            name: div.querySelector('.solvent_name').value,
            concentration: div.querySelector('.solvent_concentration').value,
            vol_added: div.querySelector('.solvent_vol').value,
            ambient_temp: div.querySelector('.solvent_temp').value,
            ambient_humidity: div.querySelector('.solvent_humidity').value,
            stir_time: div.querySelector('.solvent_stir_time').value,
            receipt_date: div.querySelector('.solvent_receipt_date').value,
        });
    });
    return {
            date: date,
            executer: executer,
            barcode: barcode,
            molarity: molarity,
            total_volume: total_volume,
            salts: salts,
            solvents: solvents,
            directory: directory,
            notes: notes,
        };
}

// Checks if the created Parent vial object is valid
function check_object(object) {
    for (const key in object) {
        if ((key !== 'salts') && (key !== 'solvents')) {
            if (object[key] === '' & key != 'notes') {
                return {
                    'status': false,
                    'empty': key
                }
            }
        } else {
            for (let i = 0; i < object[key].length; i++) {
                const item = object[key][i];
                for (const attribute in item) {
                    if (item[attribute] === '') {
                        return {
                            'status': false,
                            'empty': `${key.slice(0, -1)} #${i+1} ${attribute}`,
                        }
                    }
                }
            }
        }
    }
    return {
        'status': true,
    }
}

function save_to_dropbox() {
    parent_object = create_parent_object();
    check = check_object(parent_object);
    const message_div = document.querySelector('#message');
    const spinner = message_div.parentElement.querySelector('.spinner');
    if (check['status']) {
        spinner.style.display = 'inline-block';
        fetch('/create/parent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(parent_object)
        })
        .then((response) => response.json())
        .then((data) => {
            console.log(data);
            if (data.detail === 'Uploaded successfully') {
                message_div.innerHTML = `<blockquote>${data.detail}</blockquote>`;
            } else {
                message_div.innerHTML = `<blockquote class="error">${data.detail}</blockquote>`;
            }
            spinner.style.display = 'none';
        })
        .catch((error) => {
            console.log('Error', error)
        })
    } else {
        message_div.innerHTML = `<blockquote class="error">${check['empty']} is empty</blockquote>`;
    }

}

function save_edit() {
    parent_object = create_parent_object();
    check = check_object(parent_object);
    const message_div = document.querySelector('#message');
    const spinner = message_div.parentElement.querySelector('.spinner');
    if (check['status']) {
        spinner.style.display = 'inline-block';
        fetch('/edit/parent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(parent_object)
        })
        .then((response) => response.json())
        .then((data) => {
            console.log(data);
            if (data.detail === 'Uploaded successfully') {
                message_div.innerHTML = `<blockquote>${data.detail}</blockquote>`;
            } else {
                message_div.innerHTML = `<blockquote class="error">${data.detail}</blockquote>`;
            }
            spinner.style.display = 'none';
        })
        .catch((error) => {
            console.log('Error', error)
        })
    } else {
        message_div.innerHTML = `<blockquote class="error">${check['empty']} is empty</blockquote>`;
    }
}

function search_salt_barcode(event) {
    event.preventDefault();
    target = event.target;
    barcode_input = target.parentElement.querySelector('.salt_barcode')
    barcode = barcode_input.value;
    parent_div = target.parentElement.parentElement
    const spinner = target.parentElement.querySelector('.spinner')
    if (event.key === "Enter") {
        spinner.style.display = 'inline-block';
        fetch(`/salt/${barcode}`)
        .then((response) => response.json())
        .then((data) => {
            parent_div.querySelector('.salt_name').value = data['name'];
            parent_div.querySelector('.salt_chem_form').value = data['chem_form'];
            parent_div.querySelector('.salt_molar_mass').value = data['molar_mass'];
            parent_div.querySelector('.salt_receipt_date').value = data['receipt_date'];
            spinner.style.display = 'none';
            parent_div.querySelector('.salt_ratio').focus();
        })
        .catch((error) => {
            console.log('Error', error)
        })
    } else {
        barcode_input.value = barcode + event.key;
    };
}

function calculate_mass(event) {
    event.preventDefault();
    const target = event.target;
    const molarity = document.querySelector('#molarity').value;
    const parent_div = target.parentElement.parentElement;
    const spinner = target.parentElement.querySelector('.spinner');
    const ratio = parent_div.querySelector('.salt_ratio').value;
    spinner.style.display = 'inline-block';
    const molar_mass = parent_div.querySelector('.salt_molar_mass').value;
    const volume = document.querySelector('#volume').value;
    parent_div.querySelector('.salt_mass').value = molarity * ratio * volume * molar_mass/ 1000;
    parent_div.querySelector('.salt_ambient_temp').focus();
    spinner.style.display = 'none';
}

function search_solvent(event) {
    event.preventDefault();
    target = event.target;
    barcode_input = target.parentElement.querySelector('.solvent_barcode')
    barcode = barcode_input.value;
    parent_div = target.parentElement.parentElement
    const spinner = target.parentElement.querySelector('.spinner')
    if (event.key === "Enter") {
        spinner.style.display = 'inline-block';
        fetch(`/solvent/${barcode}`)
        .then((response) => response.json())
        .then((data) => {
            parent_div.querySelector('.solvent_name').value = data['name'];
            parent_div.querySelector('.solvent_concentration').value = data['concentration'];
            parent_div.querySelector('.solvent_receipt_date').value = data['receipt_date'];
            spinner.style.display = 'none';
            parent_div.querySelector('.solvent_vol').focus();
        })
        .catch((error) => {
            console.log('Error', error)
        })
    } else {
        barcode_input.value = barcode + event.key;
    }
}

function create_child() {
    let child = {};
    child.parents = [];
    child.executer = document.querySelector('#executer').value;
    child.date = document.querySelector('#date').innerHTML;
    child.directory = document.querySelector('#directory').value;
    child.notes = document.querySelector('#notes').value;
    const inputs = document.querySelectorAll('input');
    inputs.forEach(input => {
        if (input.className === 'parent') {
            if (input.value != '') {
                child['parents'].push(input.value);
            }
        } else {
            child[input.id] = input.value;
        }
    });
    return child;
}

function check_child(object) {
    for (const key in object) {
        if (key != 'parents') {
            if (object[key] === '' & key != 'notes') {
                return {
                    'status': false,
                    'empty': key,
                };
            };
        };
    };
    if (object.parents.length === 0) {
        return {
            'status': false,
            'empty': 'parent barcode'
        };
    };
    return {'status': true}
}

function save_child() {
    const message_div = document.querySelector('#message');
    const spinner = message_div.parentElement.querySelector('.spinner');
    const child = create_child();
    check = check_child(child);
    console.log(check);
    if (check['status']) {
        spinner.style.display = 'inline-block';
        fetch('/create/child', {
            'method': 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(child)
        })
        .then((response) => response.json())
        .then((data) => {
            console.log(data);
            if (data.detail === 'Uploaded successfully') {
                message_div.innerHTML = `<blockquote>${data.detail}</blockquote>`;
            } else {
                message_div.innerHTML = `<blockquote class="error">${data.detail}</blockquote>`;
            }
            spinner.style.display = 'none';
        })
        .catch((error) => {
            console.log('Error', error)
        })
    } else {
        message_div.innerHTML = `<blockquote class="error">${check['empty']} is empty</blockquote>`;
    }

}

function add_parent(event) {
    target = event.target;
    new_div = document.createElement('div');
    new_div.className = 'parent';
    new_div.innerHTML = `Parent barcode: <input class="parent" type="text">`;
    target.parentElement.querySelector('#parents').appendChild(new_div);
}

function create_plate_object() {
    plate = {};
    plate['props'] = {};
    general = document.querySelector('#general');
    const general_inputs = general.querySelectorAll('input');
    const props = document.querySelector('#props').querySelectorAll('input');
    general_inputs.forEach(input => {
        plate[input.id] = input.value;
    });
    plate.executer = document.querySelector('#executer').value;
    plate.date = general.querySelector('#date').innerHTML;
    plate.directory = document.querySelector('#directory').value;
    plate.notes = document.querySelector('#notes').value;
    plate.other_treatment = document.querySelector('#other_treatment').value;
    props.forEach(input => {
        if (input.type === 'radio' ) {
            if (input.checked) {
                plate['props'][input.name] = input.value;
            }
        } else {
            plate['props'][input.id] = input.value;
        }
    });
    return plate;
}

function check_plate(object) {
    let optional_props = ['notes', 'other_treatment']
    for (const key in object) {
        if (key != 'props' & !(optional_props.includes(key))) {
            if (object[key] === '') {
                return {
                    'status': false,
                    'empty': key,
                };
            };
        };
    };
    for (const key in object.props) {
        if (!(optional_props.includes(key))) {
            if (object['props'][key] === '') {
                return {
                    'status': false,
                    'empty': key,
                };
            };
        };
    };
    let radios = ['sample_type', 'ozone', 'washed']
    for (let key of radios) {
        if (!(key in object.props)) {
            return {
                'status': false,
                'empty': key,
            };
        };
    }
    return {'status': true};
}

// Create a plate
function save_plate() {
    const plate = create_plate_object();
    const check = check_plate(plate);
    const message_div = document.querySelector('#message');
    const spinner = message_div.parentElement.querySelector('.spinner');
    if (check['status']) {
        spinner.style.display = 'inline-block';
        fetch('/plate', {
            'method': 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(plate),
        })
        .then((response) => response.json())
        .then((data) => {
            console.log(data);
            if (data.detail === 'Uploaded successfully') {
                message_div.innerHTML = `<blockquote>${data.detail}</blockquote>`;
            } else {
                message_div.innerHTML = `<blockquote class="error">${data.detail}</blockquote>`;
            }
            spinner.style.display = 'none';
        });
    } else {
        message_div.innerHTML = `<blockquote class="error">${check['empty']} is empty</blockquote>`;
    }
}

// Profiles
function add_directory(event) {
    directories_div = event.target.parentElement.parentElement.querySelector('.directories');
    new_div = document.createElement('div')
    new_div.innerHTML = '<input type="text" class="long-input"> <span class="close-btn" onclick="remove_directory(event)">&times;</span>'
    directories_div.appendChild(new_div)
    new_div.querySelector('input').focus();
}

function remove_directory(event) {
    event.target.parentElement.remove();
}

function save_profile() {
    const name = document.querySelector('#name').value;
    let profile = {'name': name};
    sections = ['parent', 'child', 'sample']
    sections.forEach((section) => {
        profile[section] = [];
        section_div = document.querySelector(`#${section}`)
        inputs = section_div.querySelector('.directories').querySelectorAll('input');
        inputs.forEach((input) => {
            if (input.value != '') {
                profile[section].push(input.value)
            }
        });
    });
    const message_div = document.querySelector('#message');
    const spinner = message_div.parentElement.querySelector('.spinner');
    spinner.style.display = 'inline-block';
    fetch('/profile', {
        'method': 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(profile),
    })
    .then((response) => response.json())
    .then((data) => {
        console.log(data);
        if (data.detail === 'Uploaded successfully') {
            message_div.innerHTML = `<blockquote>${data.detail}</blockquote>`;
        } else {
            message_div.innerHTML = `<blockquote class="error">${data.detail}</blockquote>`;
        }
        spinner.style.display = 'none';
    });
}

function handleprofile(profile, type) {
    if (profile != '') {
        const params = new URLSearchParams({
            profile: profile,
            type: type
        });
        fetch(`/directories?${params}`)
        .then(response => response.json())
        .then((data) => {
            const dropdown = document.querySelector('#directory');
            let options = '<option value="">Select directory</option>';
            data['directories'].forEach((directory) => {
                options += `<option value="${directory}">${directory}</option>`
            });
            dropdown.innerHTML = options;
        })
        .catch(error => console.error("Error", error))
    }
}
