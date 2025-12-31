# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath,language='en'):
    invTypes = Table('invTypes',metadata)
    trnTranslations = Table('trnTranslations',metadata)
    certMasteries = Table('certMasteries',metadata)
    invTraits = Table('invTraits',metadata)
    invMetaTypes = Table('invMetaTypes',metadata)
    print("Importing Types")

    targetPath = os.path.join(sourcePath, 'types.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'types.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'types.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        typeids=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(typeids)} types")

        # Build bulk insert lists
        type_rows = []
        translation_rows = []
        meta_type_rows = []

        for typeid in typeids:
            type_rows.append({
                'typeID': typeid,
                'groupID': typeids[typeid].get('groupID',0),
                'typeName': typeids[typeid].get('name',{}).get(language,''),
                'description': typeids[typeid].get('description',{}).get(language,''),
                'mass': typeids[typeid].get('mass',0),
                'volume': typeids[typeid].get('volume',0),
                'capacity': typeids[typeid].get('capacity',0),
                'portionSize': typeids[typeid].get('portionSize'),
                'raceID': typeids[typeid].get('raceID'),
                'basePrice': typeids[typeid].get('basePrice'),
                'published': typeids[typeid].get('published',0),
                'marketGroupID': typeids[typeid].get('marketGroupID'),
                'graphicID': typeids[typeid].get('graphicID',0),
                'iconID': typeids[typeid].get('iconID'),
                'soundID': typeids[typeid].get('soundID')
            })

            # @TODO: Fix 'masteries' fetch from certificates.yaml(?)
            # if  "masteries" in typeids[typeid]:
            #     for level in typeids[typeid]["masteries"]:
            #         for cert in typeids[typeid]["masteries"][level]:
            #             connection.execute(certMasteries.insert().values(
            #                                 typeID=typeid,
            #                                 masteryLevel=level,
            #                                 certID=cert))

            if ('name' in typeids[typeid]):
                for lang in typeids[typeid]['name']:
                    translation_rows.append({
                        'tcID': 8,
                        'keyID': typeid,
                        'languageID': lang,
                        'text': typeids[typeid]['name'][lang]
                    })

            if ('description' in typeids[typeid]):
                for lang in typeids[typeid]['description']:
                    translation_rows.append({
                        'tcID': 33,
                        'keyID': typeid,
                        'languageID': lang,
                        'text': typeids[typeid]['description'][lang]
                    })

            # @TODO: Fix 'traits' and figure out what they are and where they went..?
            # Traits moved to the TypeBonus.yaml file and are now handled in the typeBonus.py.
            # if ('traits' in typeids[typeid]):
            #     if 'types' in typeids[typeid]['traits']:
            #         for skill in typeids[typeid]['traits']['types']:
            #             for trait in typeids[typeid]['traits']['types'][skill]:
            #                 result=connection.execute(invTraits.insert().values(
            #                                     typeID=typeid,
            #                                     skillID=skill,
            #                                     bonus=trait.get('bonus'),
            #                                     bonusText=trait.get('bonusText',{}).get(language,''),
            #                                     unitID=trait.get('unitID')))
            #                 traitid=result.inserted_primary_key
            #                 for languageid in trait.get('bonusText',{}):
            #                     connection.execute(trnTranslations.insert().values(tcID=1002,keyID=traitid[0],languageID=languageid,text=trait['bonusText'][languageid]))
            #     if 'roleBonuses' in typeids[typeid]['traits']:
            #         for trait in typeids[typeid]['traits']['roleBonuses']:
            #             result=connection.execute(invTraits.insert().values(
            #                     typeID=typeid,
            #                     skillID=-1,
            #                     bonus=trait.get('bonus'),
            #                     bonusText=trait.get('bonusText',{}).get(language,''),
            #                     unitID=trait.get('unitID')))
            #             traitid=result.inserted_primary_key
            #             for languageid in trait.get('bonusText',{}):
            #                 connection.execute(trnTranslations.insert().values(tcID=1002,keyID=traitid[0],languageID=languageid,text=trait['bonusText'][languageid]))
            #     if 'miscBonuses' in typeids[typeid]['traits']:
            #         for trait in typeids[typeid]['traits']['miscBonuses']:
            #             result=connection.execute(invTraits.insert().values(
            #                     typeID=typeid,
            #                     skillID=-2,
            #                     bonus=trait.get('bonus'),
            #                     bonusText=trait.get('bonusText',{}).get(language,''),
            #                     unitID=trait.get('unitID')))
            #             traitid=result.inserted_primary_key
            #             for languageid in trait.get('bonusText',{}):
            #                 connection.execute(trnTranslations.insert().values(tcID=1002,keyID=traitid[0],languageID=languageid,text=trait['bonusText'][languageid]))

            if 'metaGroupID' in typeids[typeid] or 'variationParentTypeID' in typeids[typeid]:
                meta_type_rows.append({
                    'typeID': typeid,
                    'metaGroupID': typeids[typeid].get('metaGroupID'),
                    'parentTypeID': typeids[typeid].get('variationParentTypeID')
                })

        # BULK INSERTS - 3 calls instead of 30,000+
        if type_rows:
            connection.execute(invTypes.insert(), type_rows)
            print(f"  Inserted {len(type_rows)} types")

        if translation_rows:
            connection.execute(trnTranslations.insert(), translation_rows)
            print(f"  Inserted {len(translation_rows)} translations")

        if meta_type_rows:
            connection.execute(invMetaTypes.insert(), meta_type_rows)
            print(f"  Inserted {len(meta_type_rows)} meta types")

    trans.commit()
    print("  Done")
