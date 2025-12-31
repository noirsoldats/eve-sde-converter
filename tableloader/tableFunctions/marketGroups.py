# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Market Groups")
    invMarketGroups = Table('invMarketGroups',metadata)
    trnTranslations = Table('trnTranslations',metadata)
    
    targetPath = os.path.join(sourcePath, 'marketGroups.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'marketGroups.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'marketGroups.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        marketgroups=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(marketgroups)} market groups")

        # Build bulk insert lists
        group_rows = []
        translation_rows = []

        for marketgroupid in marketgroups:
            group_rows.append({
                'marketGroupID': marketgroupid,
                'parentGroupID': marketgroups[marketgroupid].get('parentGroupID',None),
                'marketGroupName': marketgroups[marketgroupid].get('name',{}).get(language,''),
                'description': marketgroups[marketgroupid].get('description',{}).get(language,''),
                'iconID': marketgroups[marketgroupid].get('iconID'),
                'hasTypes': marketgroups[marketgroupid].get('hasTypes',False)
            })

            if ('name' in marketgroups[marketgroupid]):
                for lang in marketgroups[marketgroupid]['name']:
                    try:
                        translation_rows.append({
                            'tcID': 36,
                            'keyID': marketgroupid,
                            'languageID': lang,
                            'text': marketgroups[marketgroupid]['name'][lang]
                        })
                    except:
                        print(f"  Warning: Market group {marketgroupid} ({lang}) has translation issue")

            if ('description' in marketgroups[marketgroupid]):
                for lang in marketgroups[marketgroupid]['description']:
                    try:
                        translation_rows.append({
                            'tcID': 37,
                            'keyID': marketgroupid,
                            'languageID': lang,
                            'text': marketgroups[marketgroupid]['description'][lang]
                        })
                    except:
                        print(f"  Warning: Market group {marketgroupid} ({lang}) has description issue")

        # BULK INSERTS
        if group_rows:
            connection.execute(invMarketGroups.insert(), group_rows)
            print(f"  Inserted {len(group_rows)} market groups")

        if translation_rows:
            connection.execute(trnTranslations.insert(), translation_rows)
            print(f"  Inserted {len(translation_rows)} market group translations")

    trans.commit()
    print("  Done")
