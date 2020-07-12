"""Fix dependencies in repodata.json in a conda repository ``name``.

For driver see https://github.com/ContinuumIO/anaconda-issues/issues/11920

This depends on files {name}/repodata_{arch}.json that have been generated
with ``upload_packages.py``. These include the dependencies as defined
by the original upstream (e.g. pkgs/main) repodata.json. These may be more
liberal than those within the package itself for reasons I don't understand.
"""

import argparse
import bz2
import json
from pathlib import Path
import collections


def get_opt():
    parser = argparse.ArgumentParser(description="Fix repodata.json dependencies")

    parser.add_argument("repo_dir",
                        type=str,
                        help="Root dir for conda package repository")
    parser.add_argument("--debug",
                        action="store_true",
                        help="Print debug info")

    args = parser.parse_args()
    return args


def main():
    args = get_opt()

    # Collect package repodata supplied by upload_packages which includes the
    # desired dependencies. For each arch there will typically be packages for
    # that arch along with noarch.
    print('*** Reading package dependency info from upload_packages.py ***')
    pkgs_by_subdir = collections.defaultdict(dict)
    for arch in ('win-64', 'linux-64', 'osx-64'):
        repo_file = Path(args.repo_dir, f'repodata_{arch}.json')
        if repo_file.exists():
            print(f'Reading {repo_file}')
            repodata = json.load(open(repo_file))
            for name, pkg in repodata.items():
                pkgs_by_subdir[pkg['subdir']][name] = pkg
        else:
            print(f'Skipping {repo_file}, file not found')

    if args.debug:
        print('Contents of repodata_{arch} files')
        for arch, pkgs in pkgs_by_subdir.items():
            print(f'*** {arch} ***')
            for name in pkgs:
                print(name)

    # Now go through the repodata.json files generated by `conda index`, match
    # packages by the file name, and substitute in the dependencies provided in
    # the file above (from upload_packages.py, based on original upstream
    # dependencies).
    for subdir, pkgs_fix in pkgs_by_subdir.items():
        # subdir is one of {linux,osx,win}-64 or noarch, pkgs_fix is a dict
        # of packages keyed by package file name
        repo_file = Path(args.repo_dir, subdir, f'repodata.json')
        if not repo_file.exists():
            print(f'WARNING: skipping {repo_file}, does not exist')
            continue

        print()
        print(f'*** Fixing {subdir} ***')
        print(f'Reading {repo_file}')
        with open(repo_file) as fh:
            repodata = json.load(fh)

        # Conda index repodata.json has package info in 'packages' (for .bz2)
        # and 'packages.conda' (for .conda). Do in-place update of dependencies.
        for pkg_key in ('packages', 'packages.conda'):
            packages = repodata[pkg_key]
            for name, package in packages.items():
                if package['depends'] != pkgs_fix[name]['depends']:
                    print(f'Fixing: {subdir} {name}')
                    package['depends'] = pkgs_fix[name]['depends']
                else:
                    print(f'OK: {subdir} {name}')

        # Write back repodata.json and repodata.json.bz2
        with open(repo_file, 'w') as fh:
            print(f'Writing {repo_file}')
            json.dump(repodata, fh)
        with open(repo_file, 'rb') as fh_in, bz2.open(str(repo_file) + '.bz2', 'wb') as fh_out:
            print(f'Writing {repo_file}.bz2')
            fh_out.writelines(fh_in)


if __name__ == '__main__':
    main()
