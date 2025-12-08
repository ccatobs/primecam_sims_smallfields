#!/bin/bash

###############################################
###       SLURM script for FB Mapmaking    ####
###                                        ####
###     Tested on Uni Bonn Marvin Cluster  ####
###             v1.0 , 08.12.2025          ####
###  Author: Ankur Dev (adev@uni-bonn.de)  ####
###############################################

### This script run the FB-pipeline for a given set of detector TODs
### NOTE: CONFIG parameter must be set in Section 4

### section 1 - SLURM params

#SBATCH --partition=intelsr_short # cluster specific / intelsr_short, lm_short
### https://wiki.hpc.uni-bonn.de/en/running_jobs

### #SBATCH --ntasks 8      # number of procs to start
### or
#SBATCH --ntasks-per-node 48 # tasks per node ; num of processes per node
#SBATCH --cpus-per-task 2 # number of cores per task ; threads per process

#SBATCH --nodes 1  # number of nodes

#SBATCH --job-name=det100_n48c2nd1_fbmap # Job name, #ntaskstotal#corespertask#n_nodes

### #ntasks = #nodes x #ntasks-per-node
### #ncores_total = #ntasks x #cpus-per-task
### #ncores_total_pernode = #ntasks-per-node x #cpus-per-task

### #SBATCH --mem-per-cpu=4G # mem per proc
#SBATCH --mem=400G           # max mem requested, per node, baseline 400G
### Maximum requested time (days-hrs:min:sec)
#SBATCH --time 0-01:00:00 #estimated runtime max, baseline 0-15:00:00 

### #SBATCH --mail-type=ALL   # notifications for job done & fail
### #SBATCH --mail-user=adev@astro.uni-bonn.de #user email for updates
#SBATCH --output ./logs_map/%j.%x.out   # stdout file (overwrite)
#SBATCH --error ./logs_map/%j.%x.err     # stdout file (overwrite)


### section 2 - Runtime env set-up
module purge
### load all modules needed for Job
module load mpi4py
### initiate conda
### source /opt/software/easybuild-INTEL/software/Anaconda3/2022.05/etc/profile.d/conda.shi
source /opt/software/easybuild-INTEL/software/Miniforge3/24.1.2-0/etc/profile.d/conda.sh
conda deactivate
conda activate toast3

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
echo "Using GCC lib: $(which gcc)"
echo ""

### section 4 - Set Job parameters
### Set TOD data dir
###PARENT_DIR="deep56_data_d1000"
###DATA_DIR="ccat_datacenter_mock/data_testmpi/"
###FULL_DATA_PATH="${DATA_DIR}${PARENT_DIR}"

###################
####  CONFIG   ####
###################
### TODO: Fix INDIR to DATA_DIR
INDIR='orionA_ATMdata_d100'
OUTDIR='fb_dump1'
GRP_SIZE=24
NOTES=''
###################

### section 5 - Job Run
echo "***** EXEC SCRIPT *****"
echo `date '+%F %H:%M:%S'`
echo "***********************"
echo ""

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

### Begin Pipeline 
echo ""
echo "Begin: Map-making pipeline ..."
echo ""

mpirun -np $SLURM_NTASKS python write_toast_maps.py -in $INDIR -out $OUTDIR -g $GRP_SIZE -n "$NOTES"

echo ""
echo "******** DONE *********"
echo `date '+%F %H:%M:%S'`
echo "***********************"
