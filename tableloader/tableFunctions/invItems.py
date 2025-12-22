# -*- coding: utf-8 -*-
from sqlalchemy import Table, text

def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Inventory Items")

    print("  Inserting from mapDenormalize (celestials)")
    connection.execute(text("""
        INSERT INTO invItems (itemID, typeID, ownerID, locationID, flagID, quantity)
        SELECT itemID, typeID, 1, solarSystemID, 0, 1
        FROM mapDenormalize
        WHERE solarSystemID IS NOT NULL
    """))

    print("  Inserting from staStations")
    connection.execute(text("""
        INSERT INTO invItems (itemID, typeID, ownerID, locationID, flagID, quantity)
        SELECT stationID, stationTypeID, corporationID, solarSystemID, 0, 1
        FROM staStations
    """))

    print("  Done")
