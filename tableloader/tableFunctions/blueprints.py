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
        for blueprint in blueprints:
            connection.execute(industryBlueprints.insert().values(typeID=blueprint,maxProductionLimit=blueprints[blueprint]["maxProductionLimit"]))
            for activity in blueprints[blueprint]['activities']:
                connection.execute(industryActivity.insert().values(
                                    typeID=blueprint,
                                    activityID=activityIDs[activity],
                                    time=blueprints[blueprint]['activities'][activity]['time']))
                if 'materials' in blueprints[blueprint]['activities'][activity]:
                    for material in blueprints[blueprint]['activities'][activity]['materials']:
                        connection.execute(industryActivityMaterials.insert().values(
                                            typeID=blueprint,
                                            activityID=activityIDs[activity],
                                            materialTypeID=material['typeID'],
                                            quantity=material['quantity']))
                if 'products' in blueprints[blueprint]['activities'][activity]:
                    for product in blueprints[blueprint]['activities'][activity]['products']:
                        connection.execute(industryActivityProducts.insert().values(
                                            typeID=blueprint,
                                            activityID=activityIDs[activity],
                                            productTypeID=product['typeID'],
                                            quantity=product['quantity']))
                        if 'probability' in product:
                            connection.execute(industryActivityProbabilities.insert().values(
                                                typeID=blueprint,
                                                activityID=activityIDs[activity],
                                                productTypeID=product['typeID'],
                                                probability=product['probability']))
                try:
                    if 'skills' in blueprints[blueprint]['activities'][activity]:
                        for skill in blueprints[blueprint]['activities'][activity]['skills']:
                            connection.execute(industryActivitySkills.insert().values(
                                                typeID=blueprint,
                                                activityID=activityIDs[activity],
                                                skillID=skill['typeID'],
                                                level=skill['level']))
                except:
                    print(f"  Warning: Blueprint {blueprint} has invalid skill data")
    trans.commit()
    print("  Done")
