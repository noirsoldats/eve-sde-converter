# -*- coding: utf-8 -*-
import sys
import os
from sqlalchemy import Table

from yaml import load, dump
try:
    from yaml import CSafeLoader as SafeLoader
    print("Using CSafeLoader")
except ImportError:
    from yaml import SafeLoader
    print("Using Python SafeLoader")


def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Type Bonuses (Traits)")
    invTraits = Table('invTraits', metadata)

    targetPath = os.path.join(sourcePath, 'typeBonus.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'typeBonus.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'typeBonus.yaml')

    print(f"Opening {targetPath}")
    with open(targetPath, 'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        typeBonuses = load(yamlstream, Loader=SafeLoader)
        print(f"Populating Type Bonuses Table with {len(typeBonuses)} entries")

        for typeID in typeBonuses:
            typeData = typeBonuses[typeID]

            # Process role bonuses (skillID = -1)
            if 'roleBonuses' in typeData:
                for bonus in typeData['roleBonuses']:
                    # Extract bonus text based on language
                    bonusText_data = bonus.get('bonusText', {})
                    if isinstance(bonusText_data, dict):
                        bonusText = bonusText_data.get(language, '')
                    else:
                        bonusText = str(bonusText_data) if bonusText_data else ''

                    connection.execute(invTraits.insert().values(
                        typeID=typeID,
                        skillID=-1,  # Role bonuses use -1 as skillID
                        bonus=bonus.get('bonus'),
                        bonusText=bonusText,
                        unitID=bonus.get('unitID')
                    ))

            # Process type-specific bonuses (skillID from key)
            if 'types' in typeData:
                for skillID, skillBonuses in typeData['types'].items():
                    for bonus in skillBonuses:
                        # Extract bonus text based on language
                        bonusText_data = bonus.get('bonusText', {})
                        if isinstance(bonusText_data, dict):
                            bonusText = bonusText_data.get(language, '')
                        else:
                            bonusText = str(bonusText_data) if bonusText_data else ''

                        connection.execute(invTraits.insert().values(
                            typeID=typeID,
                            skillID=skillID,
                            bonus=bonus.get('bonus'),
                            bonusText=bonusText,
                            unitID=bonus.get('unitID')
                        ))

    trans.commit()
