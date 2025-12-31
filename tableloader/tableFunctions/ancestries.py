# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Ancestries")
    chrAncestries = Table('chrAncestries',metadata)

    targetPath = os.path.join(sourcePath, 'ancestries.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'ancestries.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'ancestries.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        characterancestries=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(characterancestries)} ancestries")

        # Build bulk insert list
        ancestry_rows = []

        for ancestryid in characterancestries:
            ancestry_rows.append({
                'ancestryID': ancestryid,
                'ancestryName': characterancestries[ancestryid].get('name',{}).get(language,''),
                'description': characterancestries[ancestryid].get('description',{}).get(language,''),
                'iconID': characterancestries[ancestryid].get('iconID'),
                'bloodlineID': characterancestries[ancestryid].get('bloodlineID'),
                'charisma': characterancestries[ancestryid].get('charisma'),
                'intelligence': characterancestries[ancestryid].get('intelligence'),
                'memory': characterancestries[ancestryid].get('memory'),
                'perception': characterancestries[ancestryid].get('perception'),
                'willpower': characterancestries[ancestryid].get('willpower'),
                'shortDescription': characterancestries[ancestryid].get('shortDescription')
            })

        # BULK INSERT
        if ancestry_rows:
            connection.execute(chrAncestries.insert(), ancestry_rows)
            print(f"  Inserted {len(ancestry_rows)} ancestries")

    trans.commit()
    print("  Done")
