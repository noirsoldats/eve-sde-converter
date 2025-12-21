# -*- coding: utf-8 -*-
from yaml import load, dump
try:
	from yaml import CSafeLoader as SafeLoader
	print("Using CSafeLoader")
except ImportError:
	from yaml import SafeLoader
	print("Using Python SafeLoader")

import os
import sys
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath,language='en'):
    skinLicense = Table('skinLicense',metadata)
    skinMaterials = Table('skinMaterials',metadata)
    skins_table = Table('skins',metadata)
    skinShip = Table('skinShip',metadata)            
                
    trans = connection.begin()
    print("Importing Skins")
    print("opening Yaml1")
    with open(os.path.join(sourcePath,'skins.yaml'),'r', encoding='utf-8') as yamlstream:
        skins=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for skinid in skins:
            connection.execute(skins_table.insert().values(
                            skinID=skinid,
                            internalName=skins[skinid].get('internalName',''),
                            skinMaterialID=skins[skinid].get('skinMaterialID','')))
            for ship in skins[skinid]['types']:
                connection.execute(skinShip.insert().values(
                                skinID=skinid,
                                typeID=ship))


    print("opening Yaml2")
    with open(os.path.join(sourcePath,'skinLicenses.yaml'),'r', encoding='utf-8') as yamlstream:
        skinlicenses=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for licenseid in skinlicenses:
            connection.execute(skinLicense.insert().values(
                                licenseTypeID=licenseid,
                                duration=skinlicenses[licenseid]['duration'],
                                skinID=skinlicenses[licenseid]['skinID']))
    print("opening Yaml3")
    with open(os.path.join(sourcePath,'skinMaterials.yaml'),'r', encoding='utf-8') as yamlstream:
        skinmaterials=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for materialid in skinmaterials:
            # Setting to None/NULL since we don't have an ID reference
            connection.execute(skinMaterials.insert().values(
                                skinMaterialID=materialid,
                                displayName=skinmaterials[materialid].get('displayName', {}).get(language, ''),
                                materialSetID=skinmaterials[materialid].get('materialSetID')
                                ))

    trans.commit()
