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
            connection.execute(skins_table.insert().values(
                            skinID=skinid,
                            internalName=skins[skinid].get('internalName',''),
                            skinMaterialID=skins[skinid].get('skinMaterialID','')))
            for ship in skins[skinid]['types']:
                connection.execute(skinShip.insert().values(
                                skinID=skinid,
                                typeID=ship))


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
            connection.execute(skinLicense.insert().values(
                                licenseTypeID=licenseid,
                                duration=skinlicenses[licenseid]['duration'],
                                skinID=skinlicenses[licenseid]['skinID']))

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
            connection.execute(skinMaterials.insert().values(
                                skinMaterialID=materialid,
                                displayName=skinmaterials[materialid].get('displayName', {}).get(language, ''),
                                materialSetID=skinmaterials[materialid].get('materialSetID')
                                ))

    trans.commit()
    print("  Done")
