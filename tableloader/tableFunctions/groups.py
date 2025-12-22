# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath,language='en'):
    invGroups = Table('invGroups',metadata)
    trnTranslations = Table('trnTranslations',metadata)
    print("Importing Groups")
    
    targetPath = os.path.join(sourcePath, 'groupIDs.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'groupIDs.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'groupIDs.yaml')

    # Also check for groups.yaml (modern SDE name)
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'groups.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'groups.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'groups.yaml')
    
    if not os.path.exists(targetPath):
        print(f"  ERROR: Could not find groupIDs.yaml or groups.yaml")
        return

    print(f"  Opening {targetPath}")
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        groupids=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(groupids)} groups")
        for groupid in groupids:
            connection.execute(invGroups.insert().values(
                            groupID=groupid,
                            categoryID=groupids[groupid].get('categoryID',0),
                            groupName=groupids[groupid].get('name',{}).get(language,''),
                            iconID=groupids[groupid].get('iconID'),
                            useBasePrice=groupids[groupid].get('useBasePrice'),
                            anchored=groupids[groupid].get('anchored',0),
                            anchorable=groupids[groupid].get('anchorable',0),
                            fittableNonSingleton=groupids[groupid].get('fittableNonSingleton',0),
                            published=groupids[groupid].get('published',0)))
            if ('name' in groupids[groupid]):
                for lang in groupids[groupid]['name']:
                    connection.execute(trnTranslations.insert().values(tcID=7,keyID=groupid,languageID=lang,text=groupids[groupid]['name'][lang]));
    trans.commit()
    print("  Done")
