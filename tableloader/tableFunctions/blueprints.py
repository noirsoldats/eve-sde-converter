# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath):

    activityIDs={"copying":5,"manufacturing":1,"research_material":4,"research_time":3,"invention":8,"reaction":11};

    industryBlueprints=Table('industryBlueprints',metadata)
    industryActivity = Table('industryActivity',metadata)
    industryActivityMaterials = Table('industryActivityMaterials',metadata)
    industryActivityProducts = Table('industryActivityProducts',metadata)
    industryActivitySkills = Table('industryActivitySkills',metadata)
    industryActivityProbabilities = Table('industryActivityProbabilities',metadata)
    
    
    

    print("Importing Blueprints")

    targetPath = os.path.join(sourcePath, 'blueprints.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'blueprints.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'blueprints.yaml')

    print(f"  Opening {targetPath}")
    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        blueprints=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(blueprints)} blueprints")

        # Build bulk insert lists
        blueprint_rows = []
        activity_rows = []
        material_rows = []
        product_rows = []
        probability_rows = []
        skill_rows = []

        for blueprint in blueprints:
            blueprint_rows.append({
                'typeID': blueprint,
                'maxProductionLimit': blueprints[blueprint]["maxProductionLimit"]
            })

            for activity in blueprints[blueprint]['activities']:
                activity_rows.append({
                    'typeID': blueprint,
                    'activityID': activityIDs[activity],
                    'time': blueprints[blueprint]['activities'][activity]['time']
                })

                if 'materials' in blueprints[blueprint]['activities'][activity]:
                    for material in blueprints[blueprint]['activities'][activity]['materials']:
                        material_rows.append({
                            'typeID': blueprint,
                            'activityID': activityIDs[activity],
                            'materialTypeID': material['typeID'],
                            'quantity': material['quantity']
                        })

                if 'products' in blueprints[blueprint]['activities'][activity]:
                    for product in blueprints[blueprint]['activities'][activity]['products']:
                        product_rows.append({
                            'typeID': blueprint,
                            'activityID': activityIDs[activity],
                            'productTypeID': product['typeID'],
                            'quantity': product['quantity']
                        })

                        if 'probability' in product:
                            probability_rows.append({
                                'typeID': blueprint,
                                'activityID': activityIDs[activity],
                                'productTypeID': product['typeID'],
                                'probability': product['probability']
                            })

                try:
                    if 'skills' in blueprints[blueprint]['activities'][activity]:
                        for skill in blueprints[blueprint]['activities'][activity]['skills']:
                            skill_rows.append({
                                'typeID': blueprint,
                                'activityID': activityIDs[activity],
                                'skillID': skill['typeID'],
                                'level': skill['level']
                            })
                except:
                    print(f"  Warning: Blueprint {blueprint} has invalid skill data")

        # BULK INSERTS - 6 calls instead of 25,000+
        if blueprint_rows:
            connection.execute(industryBlueprints.insert(), blueprint_rows)
            print(f"  Inserted {len(blueprint_rows)} blueprints")

        if activity_rows:
            connection.execute(industryActivity.insert(), activity_rows)
            print(f"  Inserted {len(activity_rows)} activities")

        if material_rows:
            connection.execute(industryActivityMaterials.insert(), material_rows)
            print(f"  Inserted {len(material_rows)} materials")

        if product_rows:
            connection.execute(industryActivityProducts.insert(), product_rows)
            print(f"  Inserted {len(product_rows)} products")

        if probability_rows:
            connection.execute(industryActivityProbabilities.insert(), probability_rows)
            print(f"  Inserted {len(probability_rows)} probabilities")

        if skill_rows:
            connection.execute(industryActivitySkills.insert(), skill_rows)
            print(f"  Inserted {len(skill_rows)} skills")

    trans.commit()
    print("  Done")
