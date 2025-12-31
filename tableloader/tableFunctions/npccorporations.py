# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing NPC Corporations")
    crpNPCCorporations = Table('crpNPCCorporations',metadata)
    invNames =  Table('invNames', metadata) 
    
    targetPath = os.path.join(sourcePath, 'npcCorporations.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'npcCorporations.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'npcCorporations.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        npccorps=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(npccorps)} corporations")

        # Build bulk insert list
        corp_rows = []

        for corpid in npccorps:
            corp_rows.append({
                'corporationID': corpid,
                'corporationName': npccorps[corpid].get('name', {}).get(language, ''),
                'description': npccorps[corpid].get('description',{}).get(language,''),
                'iconID': npccorps[corpid].get('iconID'),
                'enemyID': npccorps[corpid].get('enemyID'),
                'factionID': npccorps[corpid].get('factionID'),
                'friendID': npccorps[corpid].get('friendID'),
                'initialPrice': npccorps[corpid].get('initialPrice'),
                'minSecurity': npccorps[corpid].get('minSecurity'),
                'publicShares': npccorps[corpid].get('shares'),
                'size': npccorps[corpid].get('size'),
                'solarSystemID': npccorps[corpid].get('solarSystemID'),
                'extent': npccorps[corpid].get('extent')
            })

        # BULK INSERT
        if corp_rows:
            connection.execute(crpNPCCorporations.insert(), corp_rows)
            print(f"  Inserted {len(corp_rows)} NPC corporations")

    trans.commit()
    print("  Done")
