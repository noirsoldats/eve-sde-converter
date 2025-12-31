# -*- coding: utf-8 -*-
import sys
import os
from sqlalchemy import Table

from yaml import load
try:
	from yaml import CSafeLoader as SafeLoader
	print("Using CSafeLoader")
except ImportError:
	from yaml import SafeLoader
	print("Using Python SafeLoader")


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Planetary Schematics")
    planetSchematics = Table('planetSchematics',metadata)
    planetSchematicsPinMap = Table('planetSchematicsPinMap',metadata)
    planetSchematicsTypeMap = Table('planetSchematicsTypeMap',metadata)
    
    targetPath = os.path.join(sourcePath, 'planetSchematics.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'planetSchematics.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'planetSchematics.yaml')

    print(f"  Opening {targetPath}")
        
    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        schematics=load(yamlstream,Loader=SafeLoader)
        print(f"  Populating Planetary Schematics Tables with {len(schematics)} entries")

        # Build bulk insert lists
        schematic_rows = []
        pin_rows = []
        type_rows = []

        for schematicid in schematics:
            schematic_rows.append({
                'schematicID': schematicid,
                'schematicName': schematics[schematicid].get('name',{}).get(language,''),
                'cycleTime': schematics[schematicid].get('cycleTime')
            })

            for pin in schematics[schematicid].get('pins',{}):
                pin_rows.append({
                    'schematicID': schematicid,
                    'pinTypeID': pin
                })

            for typeid in schematics[schematicid].get('types',{}):
                type_rows.append({
                    'schematicID': schematicid,
                    'typeID': typeid,
                    'quantity': schematics[schematicid]['types'][typeid].get('quantity',0),
                    'isInput': schematics[schematicid]['types'][typeid].get('isInput',False)
                })

        # BULK INSERTS
        if schematic_rows:
            connection.execute(planetSchematics.insert(), schematic_rows)
            print(f"  Inserted {len(schematic_rows)} planetary schematics")

        if pin_rows:
            connection.execute(planetSchematicsPinMap.insert(), pin_rows)
            print(f"  Inserted {len(pin_rows)} schematic-pin mappings")

        if type_rows:
            connection.execute(planetSchematicsTypeMap.insert(), type_rows)
            print(f"  Inserted {len(type_rows)} schematic-type mappings")

    trans.commit()
    print("  Done")
