# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Categories")
    invCategories = Table('invCategories',metadata)
    trnTranslations = Table('trnTranslations',metadata)
    
    targetPath = os.path.join(sourcePath, 'categoryIDs.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'categoryIDs.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'categoryIDs.yaml')

    # Also check for categories.yaml (modern SDE name)
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'categories.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'categories.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'categories.yaml')
    
    if not os.path.exists(targetPath):
        print(f"  ERROR: Could not find categoryIDs.yaml or categories.yaml")
        return

    print(f"  Opening {targetPath}")
        
    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        categoryids=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(categoryids)} categories")

        # Build bulk insert lists
        category_rows = []
        translation_rows = []

        for categoryid in categoryids:
            category_rows.append({
                'categoryID': categoryid,
                'categoryName': categoryids[categoryid].get('name',{}).get(language,''),
                'iconID': categoryids[categoryid].get('iconID'),
                'published': categoryids[categoryid].get('published',0)
            })

            if ('name' in categoryids[categoryid]):
                for lang in categoryids[categoryid]['name']:
                    try:
                        translation_rows.append({
                            'tcID': 6,
                            'keyID': categoryid,
                            'languageID': lang,
                            'text': categoryids[categoryid]['name'][lang]
                        })
                    except:
                        print(f"  Warning: Category {categoryid} ({lang}) has translation issue")

        # BULK INSERTS
        if category_rows:
            connection.execute(invCategories.insert(), category_rows)
            print(f"  Inserted {len(category_rows)} categories")

        if translation_rows:
            connection.execute(trnTranslations.insert(), translation_rows)
            print(f"  Inserted {len(translation_rows)} category translations")

    trans.commit()
    print("  Done")
