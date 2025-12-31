# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Dogma Types")
    dgmEffects = Table('dgmTypeEffects',metadata)
    dgmAttributes = Table('dgmTypeAttributes',metadata)
    
    targetPath = os.path.join(sourcePath, 'typeDogma.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'typeDogma.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'typeDogma.yaml')
    
    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        dogmaEffects=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(dogmaEffects)} type dogma entries")

        # Build bulk insert lists
        effect_rows = []
        attribute_rows = []

        for typeid in dogmaEffects:
            # Check if this type has dogmaEffects defined
            if 'dogmaEffects' in dogmaEffects[typeid]:
                for effect in dogmaEffects[typeid]['dogmaEffects']:
                    effect_rows.append({
                        'typeID': typeid,
                        'effectID': effect['effectID'],
                        'isDefault': effect.get('isDefault')
                    })

            # Check if this type has dogmaAttributes defined
            if 'dogmaAttributes' in dogmaEffects[typeid]:
                for attribute in dogmaEffects[typeid]['dogmaAttributes']:
                    attribute_rows.append({
                        'typeID': typeid,
                        'attributeID': attribute.get('attributeID'),
                        'valueFloat': attribute.get('value')
                    })

        # BULK INSERTS
        if effect_rows:
            connection.execute(dgmEffects.insert(), effect_rows)
            print(f"  Inserted {len(effect_rows)} dogma effects")

        if attribute_rows:
            connection.execute(dgmAttributes.insert(), attribute_rows)
            print(f"  Inserted {len(attribute_rows)} dogma attributes")

    trans.commit()
    print("  Done")
