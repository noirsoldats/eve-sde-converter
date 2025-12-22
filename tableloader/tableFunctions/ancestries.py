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
        for ancestryid in characterancestries:
            connection.execute(chrAncestries.insert().values(
                            ancestryID=ancestryid,
                            ancestryName=characterancestries[ancestryid].get('name',{}).get(language,''),
                            description=characterancestries[ancestryid].get('description',{}).get(language,''),
                            iconID=characterancestries[ancestryid].get('iconID'),
                            bloodlineID=characterancestries[ancestryid].get('bloodlineID'),
                            charisma=characterancestries[ancestryid].get('charisma'),
                            intelligence=characterancestries[ancestryid].get('intelligence'),
                            memory=characterancestries[ancestryid].get('memory'),
                            perception=characterancestries[ancestryid].get('perception'),
                            willpower=characterancestries[ancestryid].get('willpower'),
                            shortDescription=characterancestries[ancestryid].get('shortDescription'),
                              ))
    trans.commit()
    print("  Done")
