# -*- coding: utf-8 -*-
from sqlalchemy import Table, text

def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Inventory Names")

    # Aggregate names from various tables via SQL
    print("  Inserting from invTypes")
    connection.execute(text("INSERT INTO invNames (itemID, itemName) SELECT typeID, typeName FROM invTypes"))

    print("  Inserting from chrFactions")
    connection.execute(text("INSERT INTO invNames (itemID, itemName) SELECT factionID, factionName FROM chrFactions"))

    print("  Inserting from crpNPCCorporations")
    connection.execute(text("INSERT INTO invNames (itemID, itemName) SELECT corporationID, corporationName FROM crpNPCCorporations"))

    print("  Inserting from mapRegions")
    connection.execute(text("INSERT INTO invNames (itemID, itemName) SELECT regionID, regionName FROM mapRegions"))

    print("  Inserting from mapConstellations")
    connection.execute(text("INSERT INTO invNames (itemID, itemName) SELECT constellationID, constellationName FROM mapConstellations"))

    print("  Inserting from mapSolarSystems")
    connection.execute(text("INSERT INTO invNames (itemID, itemName) SELECT solarSystemID, solarSystemName FROM mapSolarSystems"))

    print("  Inserting from staStations")
    connection.execute(text("INSERT INTO invNames (itemID, itemName) SELECT stationID, stationName FROM staStations"))

    print("  Inserting from mapDenormalize (celestials)")
    connection.execute(text("""
        INSERT INTO invNames (itemID, itemName)
        SELECT d.itemID, t.typeName || ' ' || d.itemID
        FROM mapDenormalize d
        JOIN invTypes t ON d.typeID = t.typeID
        LEFT JOIN invNames n ON d.itemID = n.itemID
        WHERE n.itemID IS NULL
    """))

    print("  Done")
