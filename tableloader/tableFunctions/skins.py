# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath,language='en'):
    skinLicense = Table('skinLicense',metadata)
    skinMaterials = Table('skinMaterials',metadata)
    skins_table = Table('skins',metadata)
    skinShip = Table('skinShip',metadata)            
    
    print("Importing Skins")

    trans = connection.begin()

    # Build bulk insert lists
    skin_rows = []
    ship_rows = []
    license_rows = []
    material_rows = []

    targetPath = os.path.join(sourcePath, 'skins.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'skins.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'skins.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        skins=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(skins)} skins")
        for skinid in skins:
            skin_rows.append({
                'skinID': skinid,
                'internalName': skins[skinid].get('internalName',''),
                'skinMaterialID': skins[skinid].get('skinMaterialID','')
            })
            for ship in skins[skinid]['types']:
                ship_rows.append({
                    'skinID': skinid,
                    'typeID': ship
                })

    # BULK INSERTS for skins
    if skin_rows:
        connection.execute(skins_table.insert(), skin_rows)
        print(f"  Inserted {len(skin_rows)} skins")

    if ship_rows:
        connection.execute(skinShip.insert(), ship_rows)
        print(f"  Inserted {len(ship_rows)} skin-ship mappings")

    targetPath = os.path.join(sourcePath, 'skinLicenses.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'skinLicenses.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'skinLicenses.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        skinlicenses=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(skinlicenses)} skin licenses")
        for licenseid in skinlicenses:
            license_rows.append({
                'licenseTypeID': licenseid,
                'duration': skinlicenses[licenseid]['duration'],
                'skinID': skinlicenses[licenseid]['skinID']
            })

    # BULK INSERT for licenses
    if license_rows:
        connection.execute(skinLicense.insert(), license_rows)
        print(f"  Inserted {len(license_rows)} skin licenses")

    targetPath = os.path.join(sourcePath, 'skinMaterials.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'skinMaterials.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'skinMaterials.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        skinmaterials=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(skinmaterials)} skin materials")
        for materialid in skinmaterials:
            material_rows.append({
                'skinMaterialID': materialid,
                'displayName': skinmaterials[materialid].get('displayName', {}).get(language, ''),
                'materialSetID': skinmaterials[materialid].get('materialSetID')
            })

    # BULK INSERT for materials
    if material_rows:
        connection.execute(skinMaterials.insert(), material_rows)
        print(f"  Inserted {len(material_rows)} skin materials")

    trans.commit()
    print("  Done")
