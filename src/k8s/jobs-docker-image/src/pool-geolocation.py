# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import geopandas as gpd
import json
import logging
import math
import os
import glob
import rasterio as rio
import shapely as shp
import argparse, sys
import xml.etree.ElementTree as ET
from pyspark.sql import SparkSession

from numpy import asarray
from pathlib import Path
from pyproj import Transformer
from rasterio.crs import CRS
import logging.config
from jsonschema import validate
from typing import Union

sys.path.append(os.getcwd())

DEFAULT_CONFIG = {"probability_cutoff": 0.5, "width": 512.1, "height": 512, "tag_name": "pool"}

PKG_PATH = Path(__file__).parent
PKG_NAME = PKG_PATH.name

dst_folder_name = 'pool-geolocation'

# collect args
parser = argparse.ArgumentParser(description='Arguments required to run pool geolocation function')

parser.add_argument('--mount_path', type=str, required=True, help='Path where storage account has been mounted')
parser.add_argument('--processing_dir', type=str, required=True, help='Path where intermediate processing files will be stored')
parser.add_argument('--src_folder_name', default=None, required=True, help='Folder containing the source file for cropping')
parser.add_argument('--config_file_name', required=False, help='Config file name')

# parse Args
args = parser.parse_args()
logger = logging.getLogger(__name__)

schema_str = '{'\
    '"title": "config",' \
    '"type": "object",' \
    '"properties": {' \
        '"probability_cutoff": {' \
            '"type": "number"' \
        '},' \
        '"height": {' \
            '"type": "number"' \
        '},' \
        '"width": {' \
            '"type": "number"' \
        '},' \
        '"geometry": {' \
            '"$ref": "#/$defs/geometry"' \
        '}' \
    '},' \
    '"required": [' \
        '"width",' \
        '"height"' \
    ']' \
'}'

def parse_config(config_path: Path, default_config: dict):
    config = default_config

    logger.debug(f"default config options are {config}")

    logger.debug(f"reading config file {config_path}")
    schema = json.loads(schema_str)

    # load config file from path
    with open(config_path, "r") as f:
        config_file = json.load(f)

    logger.debug(f"provided configuration is {config_file}")
    logger.debug(f"validating provided config")

    # validate the config file with the schema
    validate(config_file, schema)

    config.update(config_file)
    logger.info(f"using configuration {config}")

    return config


##########################################################################################
# logging
##########################################################################################


def init_logger(
    name: str,
    level: Union[int, str],
    format: str = "%(asctime)s:[%(levelname)s]:%(name)s:%(message)s",
):
    # enable and configure logging
    logger = logging.getLogger(name)
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(format))
    logger.addHandler(ch)

    return logger
    
def get_pool_gelocations(input_path: str,
    output_path: str,
    config_path: str):
  
    if config_path is not None:
        config = parse_config(config_path, DEFAULT_CONFIG)
    else:
        config = DEFAULT_CONFIG

    height = int(config["height"])
    width = int(config["width"])
    prob_cutoff = min(max(config["probability_cutoff"], 0), 1)
    dst_crs = CRS.from_epsg(4326)

    logger.debug(f"looking for PAM file using `{input_path}/*.aux.xml`")

    # find all files that contain the geocoordinate references    
    for pam_file in glob.glob(f'{input_path}/*.aux.xml'):
        pam_base_filename = os.path.basename(pam_file)
        logger.info(f"found PAM file {str(pam_base_filename)}")

        img_name = pam_base_filename.replace(".png.aux.xml", "")
        logger.info(f"using image name {img_name}")

        pam_tree = ET.parse(pam_file)
        pam_root = pam_tree.getroot()

        srs = pam_root.find("SRS")
        wkt = pam_root.find("WKT")

        if not srs is None:
            crs = CRS.from_string(srs.text)
        elif not wkt is None:
            crs = CRS.from_string(wkt.text)
        else:
            crs = CRS.from_epsg(4326)
            logger.warning(
                f"neither node 'SRS' or 'WKT' found in file {pam_file}, using epsg:4326"
            )
        logger.info(f"parsed crs {crs}")

        tfmr = Transformer.from_crs(crs, dst_crs, always_xy=True)

        tfm_xml = pam_root.find("GeoTransform")
        if tfm_xml is None:
            logger.error(f"could not find node 'GeoTransform' in file {pam_file} - quiting")
            exit(1)

        tfm_raw = [float(x) for x in tfm_xml.text.split(",")]
        
        if rio.transform.tastes_like_gdal(tfm_raw):
            tfm = rio.transform.Affine.from_gdal(*tfm_raw)
        else:
            tfm = rio.transform.Affine(*tfm_raw)
        logger.info(f"parsed transform {tfm.to_gdal()}")

        logger.info(f"using width: {width}, height: {height}, probability cut-off: {prob_cutoff}")
        logger.debug(f"looking for custom vision JSON files using `{input_path}/{img_name}*.json`")

        # find all json files to process
        all_predictions = []
        for json_path in glob.glob(f'{input_path}/{img_name}*.json'):
            
            logger.debug(f"reading {json_path}")
            logger.debug(f"file name is {json_path}")
            predictions = json.load(Path(json_path).open())
            col, row = json_path.split(".")[-3:-1]
            col, row = int(col), int(row)

            tag_name = config["tag_name"]

            logger.debug(f"found {len(predictions)} predictions total")
            predictions = [pred for pred in predictions["predictions"] if pred["probability"] >= prob_cutoff and pred["tagName"] == tag_name]
            logger.debug(f"only {len(predictions)} preditions meet criteria")

            # iterate through all predictions and process
            for pred in predictions:
                box = pred["boundingBox"]

                left = (col + box["left"]) * width
                right = (col + box["left"] + box["width"]) * width
                top = (row + box["top"]) * height
                bottom = (row + box["top"] + box["height"]) * height

                img_bbox = shp.geometry.box(left, bottom, right, top)
                bbox = shp.geometry.Polygon(zip(*tfmr.transform(*rio.transform.xy(tfm, *reversed(img_bbox.boundary.xy), offset="ul"))))
                pred["boundingBox"] = bbox
                pred["tile"] = os.path.basename(json_path)

            all_predictions.extend(predictions)

        logger.info(f"found {len(all_predictions)} total predictions")
        if len(all_predictions) > 0:
            pools_geo = gpd.GeoDataFrame(all_predictions, geometry="boundingBox", crs=dst_crs)
            pools_geo["center"] = pools_geo.apply(lambda r: str(asarray(r["boundingBox"].centroid).tolist()), axis=1)
            output_file = f"{output_path}/{img_name}.geojson"
            pools_geo.to_file(output_file, driver='GeoJSON')
            logger.info(f"saved locations to {output_file}")


if __name__ == "__main__":

    # enable logging
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(name)s:%(message)s"
    )

    logger = logging.getLogger("pool_geolocation")

    logger.info("starting pool geolocation, running ...")

    # deriving the input, output and config path
    input_path = f'{args.mount_path}/{args.processing_dir}/{args.src_folder_name}'
    if args.config_file_name != None:
        config_path = f'{args.mount_path}/config/{args.config_file_name}'
        logger.debug(f"config file path {config_path}")
    else:
        config_path = None
        
    output_path = f'{args.mount_path}/{args.processing_dir}/{dst_folder_name}'

    # debug purposes only
    logger.debug(f"input data directory {input_path}")
    logger.debug(f"output data directory {output_path}")

    os.mkdir(output_path)
    try:
        # invoke the main logic
        logger.info('tiling started...')
        get_pool_gelocations(input_path, output_path, config_path)
    except:
        # remove the placefolder file upon failed run
        logger.error('tiling errored out')
        raise
    # final logging for this transform
    logger.info("finished running pool geolocation")