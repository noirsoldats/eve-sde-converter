# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Type Materials")
    invTypeMaterials = Table('invTypeMaterials',metadata)
    
    targetPath = os.path.join(sourcePath, 'typeMaterials.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'typeMaterials.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'typeMaterials.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        materials=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(materials)} type materials")

        # Build bulk insert list
        material_rows = []

        for typeid in materials:
            # Check if this type has materials defined
            if 'materials' in materials[typeid]:
                for material in materials[typeid]['materials']:
                    material_rows.append({
                        'typeID': typeid,
                        'materialTypeID': material['materialTypeID'],
                        'quantity': material['quantity']
                    })

        # BULK INSERT
        if material_rows:
            connection.execute(invTypeMaterials.insert(), material_rows)
            print(f"  Inserted {len(material_rows)} type materials")

    trans.commit()
    print("  Done")
