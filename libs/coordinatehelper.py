# coding: utf-8
import numpy as np

EARTH_MEAN_RADIUS_KM=6371
EARTH_MEAN_DIAMETER_KM=2*np.pi*EARTH_MEAN_RADIUS_KM
EARTH_ONE_MEAN_DEG_KM=EARTH_MEAN_DIAMETER_KM/360.0

def length_of_one_mean_degree_at_latitude_km(latitude):
    return EARTH_ONE_MEAN_DEG_KM*np.cos(np.deg2rad(latitude))

def lons_2_km(longitudes, latitude):
    return longitudes * length_of_one_mean_degree_at_latitude_km(latitude)

def lats_2_km(latitudes):
    return latitudes * EARTH_ONE_MEAN_DEG_KM

def km_2_lons(distance_km, latitude):
    return distance_km/length_of_one_mean_degree_at_latitude_km(latitude)

def km_2_lats(distance_km):
    return distance_km/EARTH_ONE_MEAN_DEG_KM
