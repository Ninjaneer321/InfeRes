# IMPORTING LIBRARY
import os
import csv
import utm
import numpy as np
from osgeo import gdal, gdal_array
#import matplotlib.pyplot as plt
#from sklearn.cluster import KMeans

# ======================================================  HELPER FUNCTIONS

def pick(c, r, mask): # (column, row, an array of 1 amd 0) 
    filled = set()
    fill = set()
    fill.add((c, r))
    width = mask.shape[1]-1
    height = mask.shape[0]-1
    picked = np.zeros_like(mask, dtype=np.int8)
    while fill:
        x, y = fill.pop()
        if y == height or x == width or x < 0 or y < 0:
            continue
        if mask[y][x] == 1:
            picked[y][x] = 1
            filled.add((x, y))
            west = (x-1, y)
            east = (x+1, y)
            north = (x, y-1)
            south = (x, y+1)
            if west not in filled:
                fill.add(west)
            if east not in filled:
                fill.add(east)
            if north not in filled:
                fill.add(north)
            if south not in filled:
                fill.add(south)
    return picked

def expand(array, n): # (an array of 1 and 0, number of additional pixels)
    expand = array - array
    for i in range(len(array)):
        for j in range(len(array[i])):
            if array[i][j] == 1:
                for k in range(max(0, i-n), min(i+n, len(array)-1)):
                    for l in range(max(0, j-n), min(j+n, len(array[i])-1)):
                        expand[k][l] = 1
                continue
            else:
                continue
    return expand


def mask(res_name, max_wl, point_coordinates, boundary_coordinates, dem_file_path, res_directory):
    # =====================================================  INPUT PARAMETERS
    bc = boundary_coordinates
    pc = point_coordinates
    coords = bc + pc
    utm_coords = np.array([utm.from_latlon(coords[i + 1], coords[i]) for i in range(0, len(coords), 2)])
    # Bounding box of the reservoir [ulx, uly, lrx, lry]
    bbox = np.array([utm_coords[0,0], utm_coords[0,1], utm_coords[1,0], utm_coords[1,1]], dtype=np.float32) 
    res_point = np.array([utm_coords[2,0], utm_coords[2,1]], dtype=np.float32)
    xp = round(abs(res_point[0]-bbox[0])/30)
    yp = round(abs(res_point[1]-bbox[1])/30)                              
    
    
    # ===========================================  CLIP LANDSAT IMAGES BY THE BOUNDING BOX 
    print("Clipping Landsat images by the bounding box ...")
    clip_count = 0 
    os.chdir(res_directory + "/LandsatData")
    directory = os.getcwd()
    for filename in os.listdir(directory):
        if filename.startswith("L"):                  
            ls_img = gdal.Open(filename)
            print(ls_img.GetDescription())
            
            
            output_folder = res_directory + "/LandsatData_Clip"
            if 'BQA' in filename:
                output_file = "Clipped_" + filename[:19] + '_' + res_name + filename[19:] # Output file name
            if 'NDWI' in filename:
                output_file = "Clipped_" + filename[:20] + '_' + res_name + filename[20:] # Output file name
            
            # Create the full path for the output file
            output_path = os.path.join(output_folder, output_file)
    
            ls_img = gdal.Translate(output_path, ls_img, projWin=bbox)
            ls_img = None
            clip_count += 1
            print(clip_count)
            continue
        else:
            continue  
       
    
    
    # ======================================================  NDWI CALCULATION (adding cloud mask)
    print("Calculating NDWI ...")
    count = 0 
    os.chdir(res_directory + "/LandsatData_Clip")
    directory = os.getcwd()
    for filename in os.listdir(directory):
        if filename.startswith("Clipped_LC08_NDWI"):  
            count += 1
            print(count)
            print(filename)
            B12 = "Clipped_LC08_BQA" + filename[17:]
            ndwi_raw = gdal_array.LoadFile(filename).astype(np.float32)
            bqa = gdal_array.LoadFile(B12).astype(np.float32)
            ndwi = ndwi_raw
            ndwi[np.where(bqa >= 22280)] = -0.5              # See user guide for more information
            output = gdal_array.SaveArray(ndwi.astype(gdal_array.numpy.float32), 
                                          filename, format="GTiff", 
                                          prototype=filename)
            output = None
        
        if filename.startswith("Clipped_LE07_NDWI"):  
            count += 1
            print(count)
            print(filename)
            B12 = "Clipped_LE07_BQA" + filename[17:]
            ndwi_raw = gdal_array.LoadFile(filename).astype(np.float32)
            bqa = gdal_array.LoadFile(B12).astype(np.float32)
            ndwi = ndwi_raw
            ndwi[np.where(bqa >= 5896)] = -0.5               # See user guide for more information
            output = gdal_array.SaveArray(ndwi.astype(gdal_array.numpy.float32), 
                                          filename, format="GTiff", 
                                          prototype=filename)
            output = None
        
        if filename.startswith("Clipped_LT05_NDWI"):  
            count += 1
            print(count)
            print(filename)
            B12 = "Clipped_LT05_BQA" + filename[17:]
            ndwi_raw = gdal_array.LoadFile(filename).astype(np.float32)
            bqa = gdal_array.LoadFile(B12).astype(np.float32)
            ndwi = ndwi_raw
            ndwi[np.where(bqa >= 5896)] = -0.5               # See user guide for more information
            output = gdal_array.SaveArray(ndwi.astype(gdal_array.numpy.float32), 
                                          filename, format="GTiff", 
                                          prototype=filename)
            output = None
        else:
            continue
         
               
            
    # ======================================================  CREATE DEM-BASED MAX WATER EXTENT MASK    
    # DEM is preprocessed to have the same cell size and alignment with Landsat images 
    print("Creating DEM-based max water extent mask ...") 
    os.chdir(res_directory +  "/Outputs") 
    res_dem_file = res_name + "DEM.tif"
    dem_clip = gdal_array.LoadFile(res_dem_file).astype(np.float32)
    water_px = dem_clip
    water_px[np.where(dem_clip <= max_wl)] = 1
    water_px[np.where(dem_clip > max_wl)] = 0
    picked_wp = pick(xp, yp, water_px)
    dem_mask = expand(picked_wp, 3)
    dm_sum = np.nansum(dem_mask)     
    output = gdal_array.SaveArray(dem_mask.astype(gdal_array.numpy.float32), 
                                  "DEM_Mask.tif", format="GTiff", 
                                  prototype = res_dem_file)
    output = None
    print("Created DEM-based max water extent mask")
    print(" ")
    
    
    # ==============================================  CREATE LANDSAT-BASED MAX WATER EXTENT MASK
    print("Creating Landsat-based max water extent mask ...")
    count = dem_clip - dem_clip
    img_used = 0
    img_list = [["Landsat", "Type", "Date"]] 
    os.chdir(res_directory + "/LandsatData_Clip")
    directory = os.getcwd() 
    filtered_files = [file for file in os.listdir(directory) if "NDWI" in file]      
    for filename in filtered_files:
        if filename.startswith("Clipped_"):  
            if filename[8:12]=='LC08':
                cl_thres = 22280
                B12 = "Clipped_" + filename[8:12] + "_BQA" + filename[17:]
            if filename[8:12]=='LE07':
                cl_thres = 5896
                B12 = "Clipped_" + filename[8:12] + "_BQA" + filename[17:]
            if filename[8:12]=='LT05':
                cl_thres = 5896
                B12 = "Clipped_" + filename[8:12] + "_BQA" + filename[17:]
                
            bqa = gdal_array.LoadFile(B12).astype(np.float32)
            cl_px = bqa
            cl_px[np.where(bqa < cl_thres)] = 0
            cl_px[np.where(bqa >= cl_thres)] = 1
            cl_px[np.where(dem_mask != 1)] = 0
            cl_ratio = np.nansum(cl_px)/dm_sum           
            if cl_ratio < 0.2:
                print(filename)
                #print(cl_ratio)
                ndwi = gdal_array.LoadFile(filename).astype(np.float32)
                water = ndwi        
                water[np.where(ndwi >= 0)] = 1      # 0 = suggested threshold for Landsat
                water[np.where(ndwi < 0)] = 0
                count += water
                img_used += 1
                img_list = np.append(img_list, [[filename[8], filename[9], filename[16:26]]], axis=0)            
                continue
            else:
                continue
            continue
        else:
            continue
    print('Number of cloud-free images used to create Landsat-based mask=', img_used)
    
    os.chdir(res_directory +  "/Outputs")        
    output = gdal_array.SaveArray(count.astype(gdal_array.numpy.float32), "Count.tif", 
                                  format="GTiff", prototype = res_dem_file)
    output = None
    count = gdal_array.LoadFile('Count.tif').astype(np.float32)
    max_we = count
    max_we[np.where(count < 1)] = 0
    max_we[np.where(count >= 1)] = 1
    ls_mask = pick(xp, yp, max_we)
    output = gdal_array.SaveArray(ls_mask.astype(gdal_array.numpy.float32), 
                                  "Landsat_Mask.tif", 
                                  format="GTiff", prototype = res_dem_file)
    output = None
    with open("Landsat_Mask.csv","w", newline='') as my_csv:
        csvWriter = csv.writer(my_csv)
        csvWriter.writerows(img_list)
    print("Created Landsat-based max water extent mask from "+str(img_used)+" images")
    print(" ")
    
    # ===================================  CREATE EXPANDED MASK (by 3 pixels surrounding each of water pixels)
    print("Creating expanded mask ...")
    mask_1 = gdal_array.LoadFile("Landsat_Mask.tif").astype(np.float32)
    mask_2 = gdal_array.LoadFile("DEM_Mask.tif").astype(np.float32)
    sum_mask = mask_1 + mask_2
    mask = sum_mask
    mask[np.where(sum_mask <= 1)] = 0
    mask[np.where(sum_mask > 1)] = 1
    exp_mask = expand(mask, 3) 
    output = gdal_array.SaveArray(exp_mask.astype(gdal_array.numpy.float32), 
                                  "Expanded_Mask.tif", 
                                  format="GTiff", prototype = res_dem_file)
    output = None
    print("Created expanded mask")
    print(" ")
    
    # ===============================================  CREATE 50-ZONE MAP (FREQUENCE MAP)
    print("Creating 50-zone map (frequence map) ...")
    count = gdal_array.LoadFile("Count.tif").astype(np.float32)
    freq = count*100/np.nanmax(count)
    zone = mask*np.ceil(freq/2)                          # can be user input
    output = gdal_array.SaveArray(zone.astype(gdal_array.numpy.float32), "Zone_Mask.tif", 
                                  format="GTiff", prototype = res_dem_file)
    output = None
    print("Created 50-zone map")
    print(" ")
    print("Done")
                