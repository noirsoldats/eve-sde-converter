# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table

def importyaml(connection,metadata,sourcePath):
    eveGraphics = Table('eveGraphics',metadata)
    print("Importing Graphics")
    
    targetPath = os.path.join(sourcePath, 'graphics.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'graphics.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'graphics.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        graphics=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(graphics)} graphics")

        # Build bulk insert list
        graphic_rows = []

        for graphic in graphics:
            graphic_rows.append({
                'graphicID': graphic,
                'sofFactionName': graphics[graphic].get('sofFactionName',''),
                'graphicFile': graphics[graphic].get('graphicFile',''),
                'sofHullName': graphics[graphic].get('sofHullName',''),
                'sofRaceName': graphics[graphic].get('sofRaceName',''),
                'description': ''
            })

        # BULK INSERT
        if graphic_rows:
            connection.execute(eveGraphics.insert(), graphic_rows)
            print(f"  Inserted {len(graphic_rows)} graphics")

    trans.commit()
    print("  Done")
