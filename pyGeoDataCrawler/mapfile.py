# creates a mapfile from index

from importlib.resources import path
import mappyfile, click, yaml
import os, time, sys
import pprint
import urllib.request
from utils import indexSpatialFile
from yaml.loader import SafeLoader

GRID_FILE_TYPES = ['tif','grib2','nc']
VECTOR_FILE_TYPES = ['shp','mvt','dxf','dwg','fgdb','gml','kml','geojson','vrt','gpkg','xls']

@click.command()
@click.option('-dir',nargs=1,type = click.Path(exists=True),required = True, help = "Directory as source for mapfile")
@click.option('-dir-out',nargs=1,type = click.Path(exists=True),required = False, help = "Directory as target for the generated mapfiles")

def mapForDir(dir,dir_out):

    if not dir_out:
        dir_out = dir 

    print ('Creating a mapfile for dir ' + dir)
    
    try: 
        # Open the file and load the file
        with open(os.path.join(dir,'index.yml')) as f:
            cnf = yaml.load(f, Loader=SafeLoader)
            print(cnf)
    except FileNotFoundError:
        cnf = {
            "name": os.path.basename(os.path.normpath(dir)),
            "abstract": "",
            "mode": "dir",
            "contact": {
                "name": "",
                "organisation": "",
                "email": ""},
            "keywords": [""],
            "license": "",
            "mode": "index"
        }
        try: 
            with open(os.path.join(dir,'index.yml'), 'w') as f:
                yaml.dump(cnf, f)
        except Exception  as e:
            print(e)
    except Exception as e:
        print(e)

    # initalise default mapfile
    mf = mappyfile.open(os.path.join('templates','default.map'))
    lyrs = mf['layers']

    # set up header
    mf["name"] = cnf.get("name","default")
    mf["web"]["metadata"]["ows_title"] = cnf.get("name","default")
    mf["web"]["metadata"]["ows_abstract"] = cnf.get("abstract","default")
    if ("abstract" in cnf):
        mf["web"]["metadata"]["ows_abstract"] = cnf.get("abstract")

    # if mode=tree/dir, build the index 
    # todo

    # loop over index
    for ly in cnf['index']:
        # fetch layer details
        sf = ly.get("path",'')
        base,ext = sf.rsplit('.',1)
        if not sf.startswith("/"):
            sf = os.path.join(dir,sf)
        cnt = indexSpatialFile (sf,ext)

        if cnt:
            cnt['name'] = ly.get('name',cnt.get('name', 'unknown'))
            print("Processing layer {0}".format(cnt['name']))
            cnt['title'] = ly.get('title',cnt.get('title', cnt['name']))
            cnt['crs'] = ly.get('crs', cnt.get('crs',''))
            if (cnt['crs'] == ''):
                cnt['crs'] = cnf.get("crs", 'epsg:4326')

            print("Original type is '{0}'".format(cnt['type']))
            
            if (cnt['type'].lower() == "raster"):
                cnt['type'] = 'raster'
            elif (cnt['type'].lower() in ["linestring","line","multiline","polyline","wkblinestring"]):
                cnt['type'] = 'polygon'
            elif (cnt['type'].lower() in ["point","multipoint","wkbpoint","table"]): # table is suggested for CSV, which is usually point (or none)
                cnt['type'] = 'point'
            else:
                cnt['type'] = 'polygon'

            try:
                cnt['extent'] = "{0} {1} {2} {3}".format(cnt['bounds'][0],
                                                        cnt['bounds'][1],
                                                        cnt['bounds'][2],
                                                        cnt['bounds'][3]) 
            except:
                cnt['extent'] = "-180 -90 180 90"

            cf = ly.get("style",'')
            if not cf.startswith("/"):
                cf = os.path.join(dir,sf)
            try: 
                with open(cf) as f1:
                    new_class_string = f1.read()
                    print ("Failed opening '{0}', use default style for '{1}'".format(ly.get("style",''),cnt['type']))
            except: 
                with open(os.path.join('templates','class-' + cnt['type'] + '.tpl')) as f2:
                    new_class_string2 = f2.read()

            if (cnt['type']=='raster'): #fetch nodata from meta in file properties
                new_class_string2 = 'PROCESSING "NODATA='+ str(cnt.get('meta',{}).get('nodata',-32768)) + '"\n' + new_class_string2

            # prepare layer
            with open(os.path.join('templates','layer.tpl')) as f3:
                new_layer_string = f3.read()

            strLr = new_layer_string.format(name=cnt['name'], 
                                            title=cnt['name'],
                                            abstract=ly.get('abstract',''), 
                                            type=cnt['type'], 
                                            path=ly["path"],
                                            template=ly.get('template','info.html'), 
                                            projection=cnt['crs'], 
                                            projections=ly.get('projections','epsg:4326 epsg:3857'), 
                                            extent=cnt['extent'], 
                                            mdurl=cnf.get('mdUrlPattern','').format(ly.get('uuid','')),  
                                            classes=new_class_string2)

            try:        
                mslr = mappyfile.loads(strLr)
            
                lyrs.insert(len(lyrs)+1, mslr) 
            except Exception as e:
                print("Failed creation of layer {0}; {1}".format(cnt['name'],e))

    # map should have initial layer, remove it
    lyrs.pop(0)

    # print(mappyfile.dumps(mf))

    mappyfile.save(mf, os.path.join(dir_out,cnf['name']+".map"), indent=4, spacer=' ', quote='"', newlinechar='\n', end_comment=False, align_values=False)

if __name__ == "__main__": 
    mapForDir()
