# IMPORTING LIBRARY
import os
import csv
import utm
import numpy as np
from osgeo import gdal, gdal_array
import matplotlib.pyplot as plt
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


def mask(res_name, yearOFcommission, max_wl, point, boundary, dem_file_path, res_directory):
    # [0] =======================================  INPUT PARAMETERS
    bc = boundary
    pc = point
    coords = bc + pc
    utm_coords = np.array([utm.from_latlon(coords[i + 1], coords[i]) for i in range(0, len(coords), 2)])
    # Bounding box of the reservoir [ulx, uly, lrx, lry]
    bbox = np.array([utm_coords[0,0], utm_coords[0,1], utm_coords[1,0], utm_coords[1,1]], dtype=np.float32) 
    res_point = np.array([utm_coords[2,0], utm_coords[2,1]], dtype=np.float32)
    xp = round(abs(res_point[0]-bbox[0])/30)
    yp = round(abs(res_point[1]-bbox[1])/30)                              
    
    
    
    
    # [1] =============================  CLIP LANDSAT IMAGES BY THE UTM BOUNDING BOX 
    print('============ [1] CLIP LANDSAT IMAGES BY THE UTM BOUNDING BOX ===============')
    print("Clipping Landsat images by the bounding box ...")
    clip_count = 0 
    os.chdir(res_directory + "/LandsatData")
    directory = os.getcwd()
    for filename in os.listdir(directory):
        try:
            if 'BQA' in filename: year= int(filename[9:13])
            if 'NDWI' in filename: year= int(filename[10:14])
            if (filename.startswith("L") and year>= yearOFcommission-2):                  
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
        except:
            continue
       
        
       
        
    # [2] =============================== DELETE >80% cloudy (over the reservoir) images
    print('============ [2] DELETE >80% cloudy (over the reservoir) images ===============')
    print("Estimating cloud fraction...")
    class_count = 0 
    cloud_threshold = 80
    #L8band_quality_threshold= 22280     # See supplemental folder (Landsat documentation) for more information
    #L7band_quality_threshold= 5896
    #L5band_quality_threshold= 5896
    os.chdir(res_directory + "/Outputs") 
    res_iso = gdal_array.LoadFile('res_iso.tif').astype(np.float32)
    os.chdir(res_directory + "/LandsatData_Clip")
    directory = os.getcwd()
    for filename in os.listdir(directory):
        try:
            if filename.startswith("Clipped_LC08_BQA"):   
                bqa = gdal_array.LoadFile(filename).astype(np.float32)
                water_index = "Clipped_LC08_NDWI" + filename[16:]
                ndwi = gdal_array.LoadFile(water_index).astype(np.float32)
                bqa[np.where(bqa < 22280)] = 0
                bqa[np.where(bqa >= 22280)] = 1
                bqa[np.where(res_iso == 0)] = 0
                cloud_percentage = round(np.sum(bqa)/np.sum(res_iso)*100,2)
                print(filename + " has " + str(cloud_percentage) + "% cloud coverage")
                if cloud_percentage > cloud_threshold:
                    print('File is removed')
                    os.remove(filename)
                    os.remove(water_index)
                    class_count += 1
                    continue
                else:
                    continue
        except:
            continue
        
        try:
            if filename.startswith("Clipped_LE07_BQA"):   
                bqa = gdal_array.LoadFile(filename).astype(np.float32)
                water_index = "Clipped_LE07_NDWI"+filename[16:]
                ndwi = gdal_array.LoadFile(water_index).astype(np.float32)
                bqa[np.where(bqa < 5896)] = 0
                bqa[np.where(bqa >= 5896)] = 1
                bqa[np.where(res_iso == 0)] = 0
                cloud_percentage = round(np.sum(bqa)/np.sum(res_iso)*100,2)
                print(filename + " has " + str(cloud_percentage) + "% cloud coverage")
                if cloud_percentage > cloud_threshold-20:
                    print('File is removed')
                    os.remove(filename)
                    os.remove(water_index)
                    class_count += 1
                    continue
                else:
                    continue
        except:
            continue
        
        try:
            if filename.startswith("Clipped_LT05_BQA"):   
                bqa = gdal_array.LoadFile(filename).astype(np.float32)
                water_index = "Clipped_LT05_NDWI"+filename[16:]
                ndwi = gdal_array.LoadFile(water_index).astype(np.float32)
                bqa[np.where(bqa < 5896)] = 0
                bqa[np.where(bqa >= 5896)] = 1
                bqa[np.where(res_iso == 0)] = 0
                cloud_percentage = round(np.sum(bqa)/np.sum(res_iso)*100,2)
                print(filename + " has " + str(cloud_percentage) + "% cloud coverage")
                if cloud_percentage > cloud_threshold:
                    print('File is removed')
                    os.remove(filename)
                    os.remove(water_index)
                    class_count += 1
                    continue
                else:
                    continue
        except:
            continue
    print('Total files removed= ' + str(class_count))
    print('Cloud filtering completed')
    
    
    
    
    # [3] ===================================  NDWI CALCULATION (adding cloud mask)
    print('============ [3] NDWI CALCULATION (adding cloud mask) ===============')
    print("Adding cloud mask to NDWI images...")
    count = 0 
    os.chdir(res_directory + "/LandsatData_Clip")
    directory = os.getcwd()
    filtered_files = [file for file in os.listdir(directory) if "NDWI" in file]
    for filename in filtered_files:
        try:
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
        except:
            continue
    print("Cloud mask added to the NDWI images...")
                        
      
            
      
    # [4] ==============================  CREATE DEM-BASED MAX WATER EXTENT MASK    
    # DEM is preprocessed to have the same cell size and alignment with Landsat images 
    print('============ [4] CREATE DEM-BASED MAX WATER EXTENT MASK ===============')
    print("Creating DEM-based max water extent mask ...") 
    os.chdir(res_directory +  "/Outputs") 
    res_dem_file = res_name + "DEM.tif"
    dem_clip = gdal_array.LoadFile(res_dem_file).astype(np.float32)
    water_px = dem_clip
    water_px[np.where(dem_clip <= max_wl+10)] = 1
    water_px[np.where(dem_clip > max_wl+10)] = 0
    picked_wp = pick(xp, yp, water_px)
    dem_mask = expand(picked_wp, 3)
    #dm_sum = np.nansum(dem_mask)     
    output = gdal_array.SaveArray(dem_mask.astype(gdal_array.numpy.float32), 
                                  "DEM_Mask.tif", format="GTiff", 
                                  prototype = res_dem_file)
    output = None
    print("Created DEM-based max water extent mask",'green')
    print(" ")
    #------------------ Visualization <Start>
    plt.figure()
    plt.imshow(dem_mask, cmap='jet')
    plt.colorbar()
    plt.title('DEM_Mask.tif')
    #------------------ Visualization <End>
    
    
    
    
    # [5] ============================  CREATE LANDSAT-BASED MAX WATER EXTENT MASK
    print('============ [5] CREATE LANDSAT-BASED MAX WATER EXTENT MASK ===============')
    print("Creating Landsat-based max water extent mask ...")
    os.chdir(res_directory +  "/Outputs") 
    res_dem_file = res_name + "DEM.tif"
    dem_clip = gdal_array.LoadFile(res_dem_file).astype(np.float32)
    res_iso = gdal_array.LoadFile('res_iso.tif').astype(np.float32)
    count = dem_clip - dem_clip
    img_used = 0
    img_list = [["Landsat", "Type", "Date"]] 
    os.chdir(res_directory + "/LandsatData_Clip")
    directory = os.getcwd() 
    filtered_files = [file for file in os.listdir(directory) if "NDWI" in file]      
    for filename in filtered_files:
        try:
            if (filename.startswith("Clipped_LC08") or filename.startswith("Clipped_LT05")):
                print(filename)
                ndwi = gdal_array.LoadFile(filename).astype(np.float32) 
                ndwi[np.where(res_iso == 0)] = 0
                ndwi[np.where(ndwi == -0.5)] = 1
                ndwi[np.where(ndwi != 1)] = 0
                # plt.imshow(ndwi, cmap='jet')
                # plt.colorbar()                                
                cloud_percentage = round(np.nansum(ndwi)/np.nansum(res_iso)*100,2)
                print(str(cloud_percentage) + '% cloud')
                if cloud_percentage < 20:
                    print('-------------------------------------------------')
                    ndwi = gdal_array.LoadFile(filename).astype(np.float32)
                    water = ndwi
                    water[np.where(ndwi >= 0)] = 1
                    water[np.where(ndwi <0)] = 0
                    count += water
                    img_used += 1
                    img_list = np.append(img_list, [[filename[8], filename[10:12], filename[18:28]]], axis=0)
                else:
                    continue
        except:
            continue
    print('Number of cloud-free images used to create Landsat-based mask=', img_used)
    
    os.chdir(res_directory +  "/Outputs")        
    output = gdal_array.SaveArray(count.astype(gdal_array.numpy.float32), "Count.tif", 
                                  format="GTiff", prototype = res_dem_file)
    output = None
    count = gdal_array.LoadFile('Count.tif').astype(np.float32)
    #------------------ Visualization <Start>
    plt.figure()
    plt.imshow(count, cmap='jet')
    plt.colorbar()
    plt.title('Count.tif')
    #------------------ Visualization <End>
    max_we = count
    max_we[np.where(count < 1)] = 0
    max_we[np.where(count >= 1)] = 1
    ls_mask = pick(xp, yp, max_we)
    output = gdal_array.SaveArray(ls_mask.astype(gdal_array.numpy.float32), 
                                  "Landsat_Mask.tif", 
                                  format="GTiff", prototype = res_dem_file)
    output = None
    #------------------ Visualization <Start>
    plt.figure()
    plt.imshow(ls_mask, cmap='jet')
    plt.colorbar()
    plt.title('Landsat_Mask.tif')
    #------------------ Visualization <End>
    with open("Landsat_Mask.csv","w", newline='') as my_csv:
        csvWriter = csv.writer(my_csv)
        csvWriter.writerows(img_list)
    print("Created Landsat-based max water extent mask from "+str(img_used)+" images")
    print(" ")
    
    
    
    # [6] ======================  CREATE EXPANDED MASK (by 3 pixels surrounding each of water pixels)
    print('============ [6] CREATE EXPANDED MASK ===============')
    print("Creating expanded mask ...")
    os.chdir(res_directory +  "/Outputs")
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
    #------------------ Visualization <Start>
    plt.figure()
    plt.imshow(exp_mask, cmap='jet')
    plt.colorbar()
    plt.title('Expanded_Mask.tif')
    #------------------ Visualization <End>
    
    
    
    
    # [7] =================================  CREATE 50-ZONE MAP (FREQUENCE MAP)
    print('============ [7] CREATE 50-ZONE MAP (FREQUENCE MAP) ===============')
    print("Creating 50-zone map (frequence map) ...")
    os.chdir(res_directory +  "/Outputs")
    count = gdal_array.LoadFile("Count.tif").astype(np.float32)
    freq = count*100/np.nanmax(count)
    zone = mask*np.ceil(freq/2)                          # can be user input
    output = gdal_array.SaveArray(zone.astype(gdal_array.numpy.float32), "Zone_Mask.tif", 
                                  format="GTiff", prototype = res_dem_file)
    output = None
    print("Created 50-zone map")
    print(" ")
    #------------------ Visualization <Start>
    plt.figure()
    plt.imshow(zone, cmap='jet')
    plt.colorbar()
    plt.title('Zone_Mask.tif')
    #------------------ Visualization <End>
    print("DONE!!")
                