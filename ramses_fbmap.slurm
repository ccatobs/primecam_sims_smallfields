#!/bin/bash

###############################################
###             SLURM script for           ####
###          Filter and Bin Mapmaking      ####
###                                        ####
###    Tested on Uni Koeln Ramses Cluster  ####
###             v1.0 , 08.05.2026          ####
###############################################

### This script run the Filter and Bin (FB)-pipeline for
### a given set of detector TODs
### NOTE: PARENT_DIR parameter must be set in Section 4

### section 1 - SLURM params

#SBATCH --partition=smp
#SBATCH --account=ag-riechers # For Ramses/ CCAT

#SBATCH --ntasks-per-node 4 #48 # tasks per node ; num of processes per node
#SBATCH --cpus-per-task 2 #4 # number of cores per task ; threads per process

#SBATCH --nodes 1  # number of nodes

#SBATCH --job-name=det100_n4c2nd1_fb # Job name, #ntaskstotal#corespertask#n_nodes

#SBATCH --mem=100G           # max mem requested, per node, baseline 400G
### Maximum requested time (days-hrs:min:sec)
#SBATCH --time 0-00:30:00

#SBATCH --output ./logs_map/%j.%x.out   # stdout file (overwrite)
#SBATCH --error ./logs_map/%j.%x.err     # stdout file (overwrite)
### To handle dir ownership issues
umask 0002
mkdir -p logs_map
chmod g+rws logs_map

### section 2 - Runtime env set-up
echo ""
echo "*************"
echo "Loading Modules and Env..."
module purge
### load all modules needed for Job
module load lang/Miniconda3/23.9.0-0
module load lib/mpi4py/3.1.5-gompi-2023b
### initiate conda
conda deactivate
conda activate toast3
echo "*************"

### section 3 - Job Logging
echo ""
echo "*************"
echo "Running Job..."
echo "Starting at `date`"
echo "Hostname $HOSTNAME"
echo "Job Name: $SLURM_JOB_NAME"
echo "Job ID: $SLURM_JOB_ID"
echo "Node List: $SLURM_NODELIST"
echo "Running on $SLURM_NNODES nodes."
echo "Running on $SLURM_NPROCS processors."
echo "Slurm Ntasks: $SLURM_NTASKS"
echo "Number of Tasks per Node: $SLURM_NTASKS_PER_NODE"
echo "Number of CPUs per Task: $SLURM_CPUS_PER_TASK"
echo "Cores per Node: $SLURM_CPUS_ON_NODE"
echo "Total Number of Nodes: $SLURM_JOB_NUM_NODES"
echo "Current working directory is `pwd`"
echo "Python path: $(which python)"
echo "Using MPI lib: $(which mpirun)"
echo "mpi4py import version: $(python -c 'import mpi4py; print(mpi4py.__version__)')"
echo "Using GCC lib: $(which gcc)"
echo ""

### section 4 - Set Job parameters
### Set TOD data dir
INDIR='orionA_ATMdata_d100'
OUTDIR='fb_dump1'

PARENT_DIR="ccat_datacenter_mock"
DATA_DIR="mockdata"
FULL_DATA_PATH="${PARENT_DIR}/${DATA_DIR}"

FULL_INDIR="${FULL_DATA_PATH}/${INDIR}"
FULL_OUTDIR="${PARENT_DIR}/${OUTDIR}"
GRP_SIZE=2 #24
NOTES=''
###################

### section 5 - Job Run
echo "***** EXEC SCRIPT *****"
echo `date '+%F %H:%M:%S'`
echo "***********************"
echo ""

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

### Build Map
echo ""
echo "Processing Filter and Bin Pipeline..."
echo ""
mpirun -np $SLURM_NTASKS python write_toast_maps.py -in $FULL_INDIR -out $FULL_OUTDIR -g $GRP_SIZE -n "$NOTES"

echo ""
echo "******** DONE *********"
echo `date '+%F %H:%M:%S'`
echo "***********************"

