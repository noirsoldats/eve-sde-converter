# -*- coding: utf-8 -*-
import sys
import os
import requests
from sqlalchemy import Table

def importVolumes(connection,metadata,sourcePath):

    print("Importing Volumes from hoboleaks.space")
    invVolumes = Table('invVolumes',metadata)
    trans = connection.begin()

    try:
        # Fetch packaged volume data from hoboleaks.space
        url = 'https://sde.hoboleaks.space/tq/repackagedvolumes.json'
        print(f"  Fetching data from {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        volume_data = response.json()

        print(f"  Processing {len(volume_data)} volume entries...")

        # Insert typeID-volume pairs
        # JSON keys are strings, values can be int or float
        for type_id_str, volume in volume_data.items():
            type_id = int(type_id_str)
            volume_int = int(volume)
            connection.execute(
                invVolumes.insert().values(typeID=type_id, volume=volume_int)
            )

        trans.commit()
        print(f"  Imported {len(volume_data)} volume entries")
        print("  Done")

    except requests.RequestException as e:
        trans.rollback()
        print(f"Error fetching volume data from hoboleaks.space: {e}")
        print("Volume import failed - please check your internet connection")
        raise
    except Exception as e:
        trans.rollback()
        print(f"Error importing volumes: {e}")
        raise
