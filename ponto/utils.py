import math

CRFPB_LAT = -7.125649096473905 
CRFPB_LON = -34.87200801571919

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371000  # Metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))