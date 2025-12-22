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
    print("Importing Control Tower Resources")
    invControlTowerResources = Table('invControlTowerResources',metadata)
    
    targetPath = os.path.join(sourcePath, 'controlTowerResources.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'controlTowerResources.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'controlTowerResources.yaml')

    print(f"Opening {targetPath}")
        
    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        controlTowerResources=load(yamlstream,Loader=SafeLoader)
        print(f"Populating Control Tower Resources Table with {len(controlTowerResources)} entries")
        for controlTowerResourcesid in controlTowerResources:
            for purpose in controlTowerResources[controlTowerResourcesid]['resources']:
                connection.execute(invControlTowerResources.insert().values(
                                controlTowerTypeID=controlTowerResourcesid,
                                resourceTypeID=purpose['resourceTypeID'],
                                purpose=purpose['purpose'],
                                quantity=purpose.get('quantity',0),
                                minSecurityLevel=purpose.get('minSecurityLevel',None),
                                factionID=purpose.get('factionID',None)
                ))
    trans.commit()
