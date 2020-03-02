#! /usr/bin/env python3
# A utility for marking and restoring stable arch packages
import argparse
import re
import os
import signal
from functools import partial
import create_rp as cp
import rollback_rp as rb
import pac_utils as pu
import python_scripts as PS
from version_control import migration_check


#<#><#><#><#><#><#>#<#>#<#
#<># CLI Args
#<#><#><#><#><#><#>#<#>#<#


parser = argparse.ArgumentParser(description="A reliable rollback utility for marking and restoring custom save points in Arch Linux.")
parser.add_argument("-sb", "--snapback", action='store_true',
                    help="Rollback packages to the version state stored before that last pacback upgrade.")
parser.add_argument("--hook", action='store_true',
                    help="Used Exclusivly by the Pacback Hook.")
# Base RP Functions
parser.add_argument("-rb", "--rollback", metavar=('RP# or YYYY/MM/DD'),
                    help="Rollback to a previously generated restore point or to an archive date.")
parser.add_argument("-pkg", "--rollback_pkgs", nargs='*', default=[], metavar=('PACKAGE_NAME'),
                    help="Rollback a list of packages looking for old versions on the system.")
parser.add_argument("-c", "--create_rp", metavar=('RP#'),
                    help="Generate a pacback restore point. Takes a restore point # as an argument.")
parser.add_argument("-f", "--full_rp", action='store_true',
                    help="Generate a pacback full restore point.")
parser.add_argument("-d", "--add_dir", nargs='*', default=[], metavar=('/PATH'),
                    help="Add any custom directories to your restore point during a `--create_rp AND --full_rp`.")
# Utils
parser.add_argument("-ih", "--install_hook", action='store_true',
                    help="Install a Pacman hook that creates a snapback restore point during each Pacman Upgrade.")
parser.add_argument("-rh", "--remove_hook", action='store_true',
                    help="Remove the Pacman hook that creates a snapback restore point during each Pacman Upgrade.")
parser.add_argument("-nc", "--no_confirm", action='store_true',
                    help="Skip asking user questions during RP creation. Will answer yes to all.")
parser.add_argument("--clean", metavar=('# Versions to Keep'),
                    help="Clean Old and Orphaned Pacakages. Provide the number of package you want keep.")
parser.add_argument("-rm", "--remove", metavar=('RP#'),
                    help="Remove Selected Restore Point.")
parser.add_argument("-n", "--notes", metavar=('SOME NOTES HERE'),
                    help="Add Custom Notes to Your Metadata File.")
parser.add_argument("-v", "--version", action='store_true',
                    help="Display Pacback Version.")
parser.add_argument("-i", "--info", metavar=('RP#'),
                    help="Print information about a retore point.")
parser.add_argument("-l", "--list", action='store_true',
                    help="List all Created Restore Points")


#<#><#><#><#><#><#>#<#>#<#
#<># Args Flow Control
#<#><#><#><#><#><#>#<#>#<#


version = '1.7.0'
log_file = '/var/log/pacback.log'
rp_paths = '/var/lib/pacback/restore-points'

signal.signal(signal.SIGINT, partial(pu.sig_catcher, log_file))
PS.Start_Log('PacbackMain', log_file)
args = parser.parse_args()
migration_check(log_file)

# Display Info
if args.version:
    print('Pacback Version: ' + version)

if args.info:
    if re.findall(r'^([0-9]|0[1-9]|[1-9][0-9])$', args.info):
        num = str(args.info).zfill(2)
        pu.print_rp_info(num, rp_paths)
    else:
        PS.prError('Info Args Must Be in INT Format!')

if args.list:
    pu.list_all_rps(rp_paths)

# MAIN
if args.rollback_pkgs or args.hook or args.snapback or args.rollback or args.create_rp or args.remove or args.clean or args.install_hook or args.remove_hook:

    pu.require_root(log_file)
    pu.check_lock('session', log_file)
    pu.spawn_session_lock(log_file)

    # Create RPs
    if args.create_rp:
        if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.create_rp):
            cp.create_restore_point(version, args.create_rp, args.full_rp, args.add_dir, args.no_confirm, args.notes, rp_paths, log_file)
        else:
            PS.prError('Create RP Args Must Be INT or Date! Refer to Documentation for Help.')

    elif args.hook:
        pu.check_lock('hook', log_file)
        args.no_confirm = True
        #  pu.shift_snapbacks()
        cp.create_restore_point(version, '00', args.full_rp, args.add_dir, args.no_confirm, args.notes, rp_paths, log_file)
        pu.spawn_hook_lock(180, log_file)

    # Rollback RPs
    if args.rollback_pkgs:
        pu.rollback_packages(args.rollback_pkgs, log_file)

    elif args.snapback:
        if os.path.exists('/var/lib/pacback/restore-points/rp00.meta'):
            rb.rollback_to_rp(version, '00', rp_paths, log_file)
        else:
            PS.prError('No Snapbacks Found!')

    elif args.rollback:
        if re.findall(r'^([1-9]|0[1-9]|[1-9][0-9])$', args.rollback):
            rb.rollback_to_rp(version, args.rollback, rp_paths, log_file)
        elif re.findall(r'^(?:[0-9]{2})?[0-9]{2}/[0-3]?[0-9]/(?:[0-9]{2})?[0-9]{2}$', args.rollback):
            rb.rollback_to_date(args.rollback, log_file)
        else:
            PS.prError('No Usable Argument! Rollback Arg Must be a Restore Point # or a Date.')

    # Utils
    if args.remove:
        if re.findall(r'^([0-9]|0[1-9]|[1-9][0-9])$', args.remove):
            num = str(args.remove).zfill(2)
            pu.remove_rp(num, rp_paths, args.no_confirm, log_file)
        else:
            PS.prError('Info Args Must Be in INT Format!')

    if args.clean:
        pu.clean_cache(args.clean, rp_paths, log_file)

    if args.install_hook:
        pu.pacman_hook(True, log_file)

    elif args.remove_hook:
        pu.pacman_hook(False, log_file)

PS.End_Log('PacbackMain', log_file)
