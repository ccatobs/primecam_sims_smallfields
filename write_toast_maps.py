import toast
import toast.io as io
import toast.ops
from toast.mpi import MPI

import numpy as np
import os

import astropy.units as u

import h5py
import re
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Write TOAST F&B maps for a given dir")
    parser.add_argument('-in', '--input_dir',
                        type=str,
                        default="orionA_ATMdata_d10",
                        help="Input parent directory with Obs. h5 files")
    parser.add_argument('-out', '--output_dir',
                        type=str,
                        default="outmaps_fb_default",
                        help="Output `directory for maps")
    parser.add_argument('-g', '--grp_size',
                        type=int,
                        default=4,
                        help="Group size for MPI (optional)")
    parser.add_argument('-n', '--note_msg',
                        type=str,
                        default=None,
                        help="Optional message to include in the output dir")
    parsed_args = parser.parse_args()
    
    input_dir = parsed_args.input_dir
    output_dir = parsed_args.output_dir
    grp_size = parsed_args.grp_size
    note_msg = parsed_args.note_msg
    
    ccat_data_dir = f"ccat_datacenter_mock/data_testmpi"
    
    #=============================#
    ### Setup
    #=============================#

    comm, procs, rank = toast.get_world() 
    toast_comm = toast.Comm(world=comm, groupsize=grp_size)
    # performance improves with groupsize increasing
    # max we can do is like 8 groupsize
    # set process_rows=None
    
    # Set up logger and timer
    log_global = toast.utils.Logger.get()
    timer = toast.timing.Timer()
    timer_global = toast.timing.Timer()
    timer_global.start()
    
    log_global.info_rank(f"Parallel HDF5 enabled: {h5py.get_config().mpi}", comm)
    log_global.info_rank(f"Procs, Rank: {procs, rank}", comm)
    log_global.info_rank(f"Group info: GSize GRank: {toast_comm.group_size, toast_comm.group_rank}", comm)
    log_global.info_rank(f"Number of process groups: {toast_comm.ngroups}", comm)
    
    if "OMP_NUM_THREADS" in os.environ:
        nthread = os.environ["OMP_NUM_THREADS"]
    else:
        nthread = "unknown number of"
    log_global.info_rank(
        f"Executing Filter and Bin workflow with {procs} MPI tasks, each with "
        f"{nthread} OpenMP threads",
        comm,
    )
    log_global.info_rank(f"Job group size: {toast_comm.group_size}", comm)
    log_global.info_rank(f"Group rank: {toast_comm.group_rank}", comm)
    
    #--------------------------------------------------#

    # Input Data Dir
    parent_dir = os.path.join(ccat_data_dir, input_dir)
    
    # Maps Output Directory
    maps_outdir = os.path.join(f"ccat_datacenter_mock", f"outmaps")
    savemaps_dir = os.path.join(maps_outdir, output_dir) 
    mapname_prefix = f"orionA"
    os.makedirs(savemaps_dir, exist_ok=True)    
    
    log_global.info_rank(f"Loading data for: {parent_dir}", comm)
    
    if rank == 0 and (len(note_msg.strip()) > 0):
        # Write notes
        notes_file = os.path.join(savemaps_dir, f'notes.txt')
        with open(notes_file, 'w') as f:
            f.write(f"{note_msg} \n")
    
    if rank == 0:
        data_input_path = parent_dir
    else:
        data_input_path = None
        
    comm.barrier()
    data_input_path = comm.bcast(data_input_path, root=0)
    
    #=============================#
    ### Data Loading
    #=============================#
    
    # Create the (empty) data
    data = toast.Data(comm=toast_comm)
    sim_ground = toast.ops.SimGround()              
    
    log_global.info_rank(f"Load data...", comm)
    
    # Metadata fields to load
    meta_list = ["name", "uid", "telescope", "session", 
                "el_noise_model", "noise_model", "scan_el", 
                "scan_max_az", "scan_max_el", "scan_min_az", "scan_min_el"]

    # Shared data fields to load
    shared_list = ["azimuth", "elevation", "times",
                "flags","boresight_azel","boresight_radec",
                "position","velocity"]

    # Detector data fields to load
    detdata_list = ["signal", "flags"]

    # Interval types to load
    intervals_list = ['elnod', 'scan_leftright', 'scan_rightleft', 
                    'scanning', 'sun_close', 'sun_up', 'throw', 
                    'throw_leftright', 'throw_rightleft', 'turn_leftright', 
                    'turn_rightleft', 'turnaround']



    # Instantiate the LoadHDF5 operator
    loader = toast.ops.LoadHDF5(
        volume=data_input_path,  # Directory with observation files
        pattern=r"obs_.*_.*\.h5",                  # Match files like '"obs_.*_.*\.h5"'
        # files=[],                               # Use volume + pattern to find files
        meta=meta_list,     
        shared=shared_list, 
        detdata=detdata_list,                       
        intervals=intervals_list,  
        sort_by_size=False,                       # Sort observations by size
        process_rows=grp_size,                        # Default "None" detector-major layout
        #process_rows=1 Ensures all detectors are available on all ranks
        force_serial=False                        # Use parallel I/O if available
    )

    # Execute the operator
    loader.apply(data)
    
    log_global.info_rank(f"Number of Observations Loaded: {len(data.obs)} in", comm, timer = timer_global)
    # for i,obs in enumerate(data.obs):
    #     log_global.info_rank(f"Shape of Signal in Obs{i}: {np.asarray(obs.detdata['signal']).shape}", comm) 
    #-------------------------------------#
    # exit(1)
    
    #=============================#
    ### Filtering
    #=============================#
    timer.start()

    ### Data Level 3: Common Mode Removal
    log_global.info_rank(f"Common Mode Removal...", comm)
    commonmode_filter = toast.ops.CommonModeFilter()
    commonmode_filter.enabled = True # Toggle to False to disable
    commonmode_filter.apply(data)
    log_global.info_rank(f"Common Mode done in", comm, timer = timer) 
    
    ### Data Level 3a: Regress out 2D polynomials
    log_global.info_rank(f"Regress out 2D polynomials...", comm)
    poly2d_filter = toast.ops.PolyFilter2D()
    poly2d_filter.order = 3 #3
    poly2d_filter.enabled = True  # Toggle to False to disable
    poly2d_filter.apply(data)
    log_global.info_rank(f"2D polynomial filtering done in", comm, timer = timer)  
    
    log_global.info_rank(f"Filtering done in", comm, timer = timer_global)
    
    #=============================#
    ### Binning
    #=============================#
    mode = "I"

    log_global.info_rank(f"Generate Pointing...", comm)
    #center = RA, DEC in DEG
    #bounds = RA_MAX, RA_MIN, DEC_MIN, DEC_MAX
  
    pixels_wcs_radec = toast.ops.PixelsWCS(
                                name="pixels_wcs_radec",
                                projection="CAR",
                                auto_bounds=True,
                            )
    
    pixels_wcs_radec.enabled = True

    det_pointing_radec = toast.ops.PointingDetectorSimple(name="det_pointing_radec", 
                                                          quats="quats_radec")
    det_pointing_radec.enabled = True
    det_pointing_radec.boresight = sim_ground.boresight_radec

    #===================#
    ### Set det pointing
    pixels_wcs_radec.detector_pointing = det_pointing_radec
    #=============================#
    ### Pointing Weights
    weights_radec = toast.ops.StokesWeights(name="weights_radec", mode=mode)
    weights_radec.enabled = True

    weights_radec.detector_pointing = det_pointing_radec

    log_global.info_rank(f"Binning into Maps...", comm)

    #Set up the pointing used in the binning operator
    binner_final = toast.ops.BinMap(name="binner_final", pixel_dist="pix_dist_final")
    binner_final.enabled = True
    # Default: shared_mask_nonscience is flagged
    # binner_final.shared_flag_mask = 0 #No flags masked; include all data and turnarounds
    binner_final.pixel_pointing = pixels_wcs_radec
    binner_final.stokes_weights = weights_radec


    mapmaker = toast.ops.MapMaker(name=mapname_prefix)
    mapmaker.weather = "vacuum"
    mapmaker.write_hdf5 = False
    mapmaker.binning = binner_final
    mapmaker.map_binning = binner_final
    # mapmaker.iter_max = 10
    mapmaker.report_memory = False

    # map product options
    mapmaker.write_hits = True
    mapmaker.write_binmap = True
    mapmaker.write_cov = False
    mapmaker.write_invcov = True
    mapmaker.write_map = True
    mapmaker.write_noiseweighted_map = True
    mapmaker.write_rcond = False
    mapmaker.write_solver_products = False


    # No templates for now (will just do the binning)
    mapmaker.template_matrix = toast.ops.TemplateMatrix(templates=[])

    #if solving templates:
    # mapmaker.template_matrix = toast.ops.TemplateMatrix(templates=[toast.templates.Offset(step_time=0.5*u.second)])
    ##0.5sec is too slow

    mapmaker.output_dir = savemaps_dir
    log_global.info_rank(f"Writing maps in {savemaps_dir}", comm)
    mapmaker.enabled = True
    mapmaker.apply(data)
    log_global.info_rank(f"Binning done in", comm, timer = timer_global)  
    
    
    
if __name__ == "__main__":
    world, procs, rank = toast.mpi.get_world()
    with toast.mpi.exception_guard(comm=world):
        main()
