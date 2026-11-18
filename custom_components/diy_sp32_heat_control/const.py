"""Constants for the DIY Valve Control integration."""

DOMAIN = "diy_heat_control"

# GATT-UUIDs (müssen zur ESPHome-YAML passen)
SERVICE_UUID = "DEF7BD2B-A6AD-45BD-A766-33D314169F9D"
WRITE_UUID = "E9E76F0C-E3E7-40A7-9976-2C921750DEEC"
NOTIFY_UUID = "D50D1277-8781-47ED-91D5-5D9F2FF91FF0"
CIRCUIT_NOTIFY_UUID = "D605EF2A-74E9-4DD9-A62E-BB0B28851D7E"

# Heizkreis-Fühler: 5 Kreise x (Vorlauf, Rücklauf) = 10 Slots
CIRCUIT_COUNT = 5
CIRCUIT_INVALID = -32768  # 0x8000 = kein Wert

# Status-Bits im Notify-Paket (Byte 4)
STATUS_MOVING = 0x01         # Antrieb fährt gerade
STATUS_OVERTEMP = 0x02       # Übertemperatur-Abschaltung aktiv
STATUS_SENSOR_FAULT = 0x04   # Vorlauffühler ausgefallen
STATUS_HOMED = 0x08          # Referenzfahrt erledigt

# Sollwertgrenzen (gleich wie target_min / target_max in der ESPHome-YAML)
MIN_TARGET_TEMP = 20.0
MAX_TARGET_TEMP = 38.0
