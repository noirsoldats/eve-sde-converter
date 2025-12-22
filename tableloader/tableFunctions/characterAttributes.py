# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Character Attributes")
    chrAttributes = Table('chrAttributes',metadata)
    
    targetPath = os.path.join(sourcePath, 'characterAttributes.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'characterAttributes.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'characterAttributes.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        characterattributes=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(characterattributes)} attributes")
        for attributeid in characterattributes:
            connection.execute(chrAttributes.insert().values(
                            attributeID=attributeid,
                            attributeName=characterattributes[attributeid].get('name',{}).get(language,''),
                            description=characterattributes[attributeid].get('description',''),
                            iconID=characterattributes[attributeid].get('iconID',None),
                            notes=characterattributes[attributeid].get('notes',''),
                            shortDescription=characterattributes[attributeid].get('shortDescription',''),
                              ))
    trans.commit()
    print("  Done")
