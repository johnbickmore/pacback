#! /usr/bin/env python3
# A utility for marking and restoring stable arch packages
import argparse
import re
import signal
from functools import partial
import create
import restore
import pac_utils as pu
import usr_utils as uu
import python_scripts as PS

# Config
version = '2.0.0'
log_file = '/var/log/pacback.log'
rp_paths = '/var/lib/pacback/restore-points'
hook_cooldown = 1
max_snapshots = 25


#<#><#><#><#><#><#>#<#>#<#
#<># CLI Args
#<#><#><#><#><#><#>#<#>#<#
parser = argparse.ArgumentParser(description="A reliable rollback utility for marking and restoring custom save points in Arch Linux.")

# Base RP Functions
parser.add_argument("-ss", "--snapshot", metavar=('SnapShot #'),
                    help="Select an snapshot to rollback to..")
parser.add_argument("-rp", "--restore_point", metavar=('Restore Point #'),
                    help="Rollback to a previously generated restore point.")
parser.add_argument("-dt", "--date", metavar=('YYYY/MM/DD'),
                    help="Rollback to a date in the Arch Archive.")
parser.add_argument("-c", "--create_rp", metavar=('RP#'),
                    help="Generate a pacback restore point. Takes a restore point # as an argument.")
parser.add_argument("-pkg", "--rollback_pkgs", nargs='*', default=[], metavar=('PACKAGE_NAME'),
                    help="Rollback a list of packages looking for old versions on the system.")

# Utils
parser.add_argument("--hook", action='store_true',
                    help="Used exclusivly by the Pacback Hook to create SnapShots.")
parser.add_argument("-ih", "--install_hook", action='store_true',
                    help="Install a pacman hook that creates SnapShots.")
parser.add_argument("-rh", "--remove_hook", action='store_true',
                    help="Remove the pacman hook that creates SnapShots.")
parser.add_argument("--clean", metavar=('# Versions to Keep'),
                    help="Clean old and orphaned pacakages/restore points. ")
parser.add_argument("-rm", "--remove", metavar=('RP#'),
                    help="Remove Selected Restore Point.")

# Optional
parser.add_argument("-f", "--full_rp", action='store_true',
                    help="Generate the rp as a full restore point.")
parser.add_argument("-d", "--add_dir", nargs='*', default=[], metavar=('/PATH'),
                    help="Add custom directories to your restore point when using `--create_rp AND --full_rp`.")
parser.add_argument("-nc", "--no_confirm", action='store_true',
                    help="Skip asking user questions during RP creation. Will answer yes to all.")
parser.add_argument("-l", "--label", metavar=('Label Name'),
                    help="Tag your restore point with a label.")

# Show Info
parser.add_argument("-v", "--version", action='store_true',
                    help="Display Pacback version and config.")
parser.add_argument("-i", "--info", metavar=('RP#'),
                    help="Print information about a retore point.")
parser.add_argument("-df", "--diff", metavar=('RP#1 RP#2'),
                    help="Compare two restore points or snapshots.")
parser.add_argument("-ls", "--list", action='store_true',
                    help="List information about existing restore points and snapshots")
parser.add_argument("-tl", "--timeline", action='store_true',
                    help="Calculate a timeline of changes of changes between snapshots.")


#<#><#><#><#><#><#>#<#>#<#
#<># Args Flow Control
#<#><#><#><#><#><#>#<#>#<#


args = parser.parse_args()

# Display Info
if args.version:
    print('Pacback Version: ' + version)

if args.info:
    if re.findall(r'^([0-9]|0[1-9]|[1-9][0-9])$', args.info):
        uu.print_rp_info(str(args.info).zfill(2), rp_paths)
    else:
        PS.prError('Info Args Must Be in INT Format!')

if args.list:
    uu.list_all_rps(rp_paths)

# MAIN
if args.rollback_pkgs or args.hook or args.snapshot or args.restore_point or args.date \
        or args.create_rp or args.remove or args.clean or args.install_hook or args.remove_hook:

    # Start Up
    signal.signal(signal.SIGINT, partial(pu.sig_catcher, log_file))
    pu.require_root(log_file)
    pu.check_lock('session', log_file)
    pu.fork_session_lock(log_file)

    # Create RPs
    if args.create_rp:
        if re.findall(r'^([0-9]|0[1-9]|[0-9][0-9])$', args.create_rp):
            create.restore_point(version, args.create_rp, args.full_rp,
                    args.add_dir, args.no_confirm, args.label, rp_paths, log_file)
        else:
            PS.prError('Create RP Arg Must Be Int!')

    elif args.hook:
        create.snapshot(version, max_snapshots, hook_cooldown, rp_paths, log_file)

    # Rollback RPs
    if args.rollback_pkgs:
        restore.packages(args.rollback_pkgs, log_file)

    elif args.snapshot:
        if re.findall(r'^([0-9]|0[1-9]|[0-9][0-9])$', args.create_rp):
            restore.snapshot(version, args.snapshot, rp_paths, log_file)
        else:
            PS.prError('SnapShot ' + str(args.snapshot).zfill(2) + ' NOT Found!')

    elif args.restore_point:
        if re.findall(r'^([0-9]|0[1-9]|[0-9][0-9])$', args.restore_point):
            restore.restore_point(version, args.restore_point, rp_paths, log_file)
        else:
            PS.prError('Restore Point Arg Must Be Int!')

    elif args.date:
        if re.findall(r'^(?:[0-9]{2})?[0-9]{2}/[0-3]?[0-9]/(?:[0-9]{2})?[0-9]{2}$', args.restore_point):
            restore.archive_date(args.date, log_file)
        else:
            PS.prError('Rollback to Date Arg Must Be Date in YYYY/MM/DD Format!')

    # Utils
    if args.remove:
        if re.findall(r'^([0-9]|0[1-9]|[0-9][0-9])$', args.remove):
            uu.remove_rp(str(args.remove).zfill(2), rp_paths, args.no_confirm, log_file)
        else:
            PS.prError('Remove RP Arg Must Be INT!')

    if args.clean:
        uu.clean_cache(args.clean, rp_paths, log_file)

    if args.install_hook:
        pu.pacman_hook(True, log_file)

    elif args.remove_hook:
        pu.pacman_hook(False, log_file)

    PS.End_Log('PacbackMain', log_file)
