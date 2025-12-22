# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath):
    eveIcons = Table('eveIcons',metadata)
    print("Importing Icons")
    
    targetPath = os.path.join(sourcePath, 'iconIDs.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'iconIDs.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'iconIDs.yaml')

    # Also check for icons.yaml (modern SDE name)
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'icons.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'icons.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'icons.yaml')
    
    if not os.path.exists(targetPath):
        print(f"  ERROR: Could not find iconIDs.yaml or icons.yaml")
        return

    print(f"  Opening {targetPath}")
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        icons=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(icons)} icons")
        for icon in icons:
            connection.execute(eveIcons.insert().values(
                            iconID=icon,
                            iconFile=icons[icon].get('iconFile',''),
                            description=''))
    trans.commit()
    print("  Done")