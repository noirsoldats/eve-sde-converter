# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Bloodlines")
    chrBloodlines = Table('chrBloodlines',metadata)
    
    targetPath = os.path.join(sourcePath, 'bloodlines.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'bloodlines.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'bloodlines.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        bloodlines=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(bloodlines)} bloodlines")

        # Build bulk insert list
        bloodline_rows = []

        for bloodlineid in bloodlines:
            bloodline_rows.append({
                'bloodlineID': bloodlineid,
                'bloodlineName': bloodlines[bloodlineid].get('name',{}).get(language,''),
                'description': bloodlines[bloodlineid].get('description',{}).get(language,''),
                'iconID': bloodlines[bloodlineid].get('iconID'),
                'corporationID': bloodlines[bloodlineid].get('corporationID'),
                'charisma': bloodlines[bloodlineid].get('charisma'),
                'intelligence': bloodlines[bloodlineid].get('intelligence'),
                'memory': bloodlines[bloodlineid].get('memory'),
                'perception': bloodlines[bloodlineid].get('perception'),
                'willpower': bloodlines[bloodlineid].get('willpower'),
                'raceID': bloodlines[bloodlineid].get('raceID'),
                'shipTypeID': bloodlines[bloodlineid].get('shipTypeID')
            })

        # BULK INSERT
        if bloodline_rows:
            connection.execute(chrBloodlines.insert(), bloodline_rows)
            print(f"  Inserted {len(bloodline_rows)} bloodlines")

    trans.commit()
    print("  Done")
