#!/bin/sh

usage() {
  echo "$@"
  exit 1
}

[ -z "$1" ] && usage "Mount Point not supplied"
[ -z "$2" ] && usage "Processing directory not supplied"
[ -z "$3" ] && usage "AI-Model output directory not supplied"
[ -z "$4" ] && usage "Geolocations input directory not supplied"

set -ex

MOUNT_POINT=$1
PROCESSING_DIR=$2
AIMODEL_OUTPUT_DIR=$3
GEOLOCATION_INPUT_DIR=$4

# Create directories for geolocation processing
mkdir ${MOUNT_POINT}/${PROCESSING_DIR}/${GEOLOCATION_INPUT_DIR}

# copy input files for geolocation processing
cp ${MOUNT_POINT}/${PROCESSING_DIR}/${AIMODEL_OUTPUT_DIR}/json/* ${MOUNT_POINT}/${PROCESSING_DIR}/${GEOLOCATION_INPUT_DIR}/
cp ${MOUNT_POINT}/${PROCESSING_DIR}/${AIMODEL_OUTPUT_DIR}/other/output.png.aux.xml ${MOUNT_POINT}/${PROCESSING_DIR}/${GEOLOCATION_INPUT_DIR}/