FROM ubuntu:22.04

RUN apt update
RUN apt install -y software-properties-common \
                    python3-dev \
                    python3-pip \
                    python3-pyproj \
                    gdal-bin \
                    libgdal-dev 

RUN pip install numpy \
                rasterio \
                geopandas \
                jsonschema \
                PySpark \
                Pillow \
                psycopg2

RUN pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==3.3.0
COPY src/ ./