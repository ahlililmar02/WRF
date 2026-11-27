# Load the toolchain WRF/WPS were built with. Usage:  source ~/WRF/wrf_env.sh
source /etc/profile.d/modules.sh
module purge
module load openmpi/5.0.2-gcc hdf5-parallel/1.14.3/gcc11.4.1 netcdf-parallel/4.9.2/gcc11.4.1
export NETCDF=$NETCDF_DIR
export HDF5=$HDF5_PARALLEL_DIR
export WRFIO_NCD_LARGE_FILE_SUPPORT=1
export WRF_DIR=$HOME/WRF/WRFV4.8.0
# JasPer (built locally) for WPS GRIB2 support
export JASPERLIB=$HOME/WRF/libs/lib
export JASPERINC=$HOME/WRF/libs/include
