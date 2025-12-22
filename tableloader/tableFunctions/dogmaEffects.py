# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load, dump
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


distribution={'twosome':1,'bubble':2}
effectcategory={}


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Dogma Effects")
    dgmEffects = Table('dgmEffects',metadata)
    
    targetPath = os.path.join(sourcePath, 'dogmaEffects.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'dogmaEffects.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'dogmaEffects.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        dogmaEffects=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(dogmaEffects)} effects")
        for dogmaEffectsid in dogmaEffects:
            effect=dogmaEffects[dogmaEffectsid]
            connection.execute(dgmEffects.insert().values(
                                effectID=dogmaEffectsid,
                                effectName=effect.get('name'),  # Changed from 'effectName' to 'name'
                                effectCategory=effect.get('effectCategoryID'),  # Changed from effectCategory lookup
                                description=effect.get('description',{}).get(language,'') if isinstance(effect.get('description'), dict) else 'None',
                                guid=effect.get('guid'),
                                iconID=effect.get('iconID'),
                                isOffensive=effect.get('isOffensive', False),
                                isAssistance=effect.get('isAssistance', False),
                                durationAttributeID=effect.get('durationAttributeID'),
                                trackingSpeedAttributeID=effect.get('trackingSpeedAttributeID'),
                                dischargeAttributeID=effect.get('dischargeAttributeID'),
                                rangeAttributeID=effect.get('rangeAttributeID'),
                                falloffAttributeID=effect.get('falloffAttributeID'),
                                disallowAutoRepeat=effect.get('disallowAutoRepeat'),
                                published=effect.get('published'),
                                displayName=effect.get('displayName',{}).get(language,'') if isinstance(effect.get('displayName'), dict) else effect.get('name', 'None'),
                                isWarpSafe=effect.get('isWarpSafe'),
                                rangeChance=effect.get('rangeChance'),
                                electronicChance=effect.get('electronicChance'),
                                propulsionChance=effect.get('propulsionChance'),
                                distribution=distribution.get(effect.get('distribution')),
                                sfxName=effect.get('sfxName'),
                                npcUsageChanceAttributeID=effect.get('npcUsageChanceAttributeID'),
                                npcActivationChanceAttributeID=effect.get('npcActivationChanceAttributeID'),
                                fittingUsageChanceAttributeID=effect.get('fittingUsageChanceAttributeID'),
                                modifierInfo=dump(effect.get('modifierInfo'))

            ))
    trans.commit()
    print("  Done")
