#!/bin/bash

###############################################
###     SLURM script for primecam_sims     ####
###      ARRAY JOB runs all schedules      ####
###					   ####
###     Tested on Uni Bonn Marvin Cluster  ####
###             v2.0 , 18.10.2024          ####
###############################################

### This script runs through all the schedule files
### launching SLURM ARRAY jobs for each schedule independently
### NOTE: ndets parameter must be set in Section 4

### section 1 - SLURM params

#SBATCH --partition=intelsr_short
### cluster specific / intelsr_short, lm_short, lm_devel
### https://wiki.hpc.uni-bonn.de/en/running_jobs

### #SBATCH --ntasks 8      # number of procs to start
### or
#SBATCH --ntasks-per-node 24 # tasks per node ; num of processes per node
#SBATCH --cpus-per-task 4 # number of cores per task ; threads per process

#SBATCH --nodes 1  # number of nodes
#SBATCH --array=0 # Define the array size (= Num. sch. files) 

#SBATCH --job-name=det100_n24c4_sim 
### Job name, det#ndets_#ntaskstotal_#corespertask_sim
### ntasks = 8, cpus=4, d200 seems best ~ 90min

### #ntasks = #nodes x #ntasks-per-node
### #ncores_total = #ntasks x #cpus-per-task
### #ncores_total_pernode = #ntasks-per-node x #cpus-per-task

### #SBATCH --mem-per-cpu=10G # mem per proc, baseline 8G
#SBATCH --mem=400G                # max mem requested, per node [min 400G for 1000 dets]
### Maximum requested time (days-hrs:min:sec)
#SBATCH --time 0-02:00:00 #estimated runtime max 0-04:00:00

### #SBATCH --mail-type=ALL   # notifications for job done & fail
### #SBATCH --mail-user=adev@astro.uni-bonn.de #user email for updates
### #SBATCH --output ./logs/%j.%x.out   # stdout file (overwrite)
### #SBATCH --error ./logs/%j.%x.err     # stdout file (overwrite)
#SBATCH --output ./logs_sim/%A_%a_%x.out 
#SBATCH --error ./logs_sim/%A_%a_%x.err 


### section 2 - Runtime env set-up
module purge
### load all modules needed for Job
module load mpi4py
### initiate conda
### source /opt/software/easybuild-INTEL/software/Anaconda3/2022.05/etc/profile.d/conda.sh
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
### Set number of detectors
ndets=100

### section 5 - Job Run
echo "***** EXEC SCRIPT *****"
echo `date '+%F %H:%M:%S'`
echo "***********************"
echo ""

### Collect all schedule files from input dir
schedule_files_list=($(basename -a input_files/schedules/*.txt))
### Select schedule based on array index
schedule_file=${schedule_files_list[$SLURM_ARRAY_TASK_ID]}
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

echo ""
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Running schedule file: $schedule_file"
echo "Number of dets: $ndets"
echo ""

### Making detector files
## Check if the current array task ID is not 1
if [ "$SLURM_ARRAY_TASK_ID" -ne 0 ]; then
    sleep 5
fi
## Run the fp_trim script with the specified number of detectors (ndets)
python -m scripts.fp_scripts.fp_trim $ndets
## Check if the fp_trim script executed successfully
if [ $? -ne 0 ]; then
    # If there was an error, print an error message and exit the script
    echo "Error occurred in FP file generation script. Exiting."
    exit 1
fi

### Simulating timestream data from schedules
mpirun -np $SLURM_NTASKS python3 sim_data_primecam_mpi.py -s $schedule_file -d $ndets

echo ""
echo "******** DONE *********"
echo `date '+%F %H:%M:%S'`
echo "***********************"


