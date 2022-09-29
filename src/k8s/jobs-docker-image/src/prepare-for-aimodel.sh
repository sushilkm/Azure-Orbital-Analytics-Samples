#!/bin/sh

usage() {
  echo "$@"
  exit 1
}

[ -z "$1" ] && usage "Mount Point not supplied"
[ -z "$2" ] && usage "Processing directory not supplied"
[ -z "$3" ] && usage "AI-Model input directory not supplied"
[ -z "$4" ] && usage "AI-Model output directory not supplied"
[ -z "$5" ] && usage "AI-Model logs directory not supplied"

set -ex

MOUNT_POINT=$1
PROCESSING_DIR=$2
AIMODEL_INPUT_DIR=$3
AIMODEL_OUTPUT_DIR=$4
AIMODEL_LOG_DIR=$5

# Create directories for AI-Model processing
mkdir ${MOUNT_POINT}/${PROCESSING_DIR}/${AIMODEL_INPUT_DIR}
mkdir ${MOUNT_POINT}/${PROCESSING_DIR}/${AIMODEL_OUTPUT_DIR}
mkdir ${MOUNT_POINT}/${PROCESSING_DIR}/${AIMODEL_LOG_DIR}

# copy input files for AI-Model processing
cp ${MOUNT_POINT}/${PROCESSING_DIR}/tiles/*.png ${MOUNT_POINT}/${PROCESSING_DIR}/${AIMODEL_INPUT_DIR}/
cp ${MOUNT_POINT}/${PROCESSING_DIR}/convert/output.png.aux.xml ${MOUNT_POINT}/${PROCESSING_DIR}/${AIMODEL_INPUT_DIR}/