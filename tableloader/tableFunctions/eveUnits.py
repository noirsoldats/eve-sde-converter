# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table

def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Units")

    eveUnits = Table('eveUnits', metadata)

    # Check for dogmaUnits.yaml (modern SDE) or eveUnits.yaml (legacy)
    target_file = None
    for filename in ['dogmaUnits.yaml', 'eveUnits.yaml']:
        for subpath in ['', 'fsd', os.path.join('sde', 'fsd')]:
            candidate = os.path.join(sourcePath, subpath, filename) if subpath else os.path.join(sourcePath, filename)
            if os.path.exists(candidate):
                target_file = candidate
                break
        if target_file:
            break

    if not target_file:
        print("  Warning: Could not find dogmaUnits.yaml or eveUnits.yaml")
        return

    print(f"  Opening {target_file}")

    with open(target_file, 'r', encoding='utf-8') as yamlstream:
        units = load(yamlstream, Loader=SafeLoader)

    print(f"  Processing {len(units)} units")

    def get_lang_text(data, key, lang='en'):
        val = data.get(key, '')
        if isinstance(val, dict):
            return val.get(lang, val.get('en', ''))
        return val

    trans = connection.begin()
    for unitID, unit_data in units.items():
        connection.execute(eveUnits.insert().values(
            unitID=unitID,
            unitName=get_lang_text(unit_data, 'name', language),
            displayName=get_lang_text(unit_data, 'displayName', language),
            description=get_lang_text(unit_data, 'description', language)
        ))
    trans.commit()
    print("  Done")
