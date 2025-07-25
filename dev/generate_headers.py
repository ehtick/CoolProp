"""
In this module, we do some of the preparatory work that is needed to get
CoolProp ready to build.  This includes setting the correct versions in the
headers, generating the fluid files, etc.
"""
from __future__ import division, print_function, unicode_literals
from datetime import datetime
import subprocess
import os
import sys
import json
import hashlib
import struct
import glob
from pathlib import Path
import pickle 
import zlib

json_options = {'indent': 2, 'sort_keys': True}


def get_hash(data):
    try:
        return hashlib.sha224(data).hexdigest()
    except TypeError:
        return hashlib.sha224(data.encode('ascii')).hexdigest()


# unicode
repo_root_path = os.path.normpath(os.path.join(os.path.abspath(__file__), '..', '..'))

# Load up the hashes of the data that will be written to each file
hashes_fname = os.path.join(repo_root_path, 'dev', 'hashes.json')
if os.path.exists(hashes_fname):
    try:
        hashes = json.load(open(hashes_fname, 'r'))
    except json.decoder.JSONDecodeError as e:
        print(f'decoding error: {e}')
        contents = open(hashes_fname, 'r').read()
        print(f'hashes.json: {contents}')
        hashes = {}
else:
    hashes = dict()

# 0: Input file path relative to dev folder
# 1: Output file path relative to include folder
# 2: Name of variable
values = [
    ('all_fluids.json', 'all_fluids_JSON.h', 'all_fluids_JSON'),
    ('all_incompressibles.json', 'all_incompressibles_JSON.h', 'all_incompressibles_JSON'),
    ('mixtures/mixture_departure_functions.json', 'mixture_departure_functions_JSON.h', 'mixture_departure_functions_JSON'),
    ('mixtures/mixture_binary_pairs.json', 'mixture_binary_pairs_JSON.h', 'mixture_binary_pairs_JSON'),
    ('mixtures/predefined_mixtures.json', 'predefined_mixtures_JSON.h', 'predefined_mixtures_JSON'),
    ('cubics/all_cubic_fluids.json', 'all_cubics_JSON.h', 'all_cubics_JSON'),
    ('cubics/cubic_fluids_schema.json', 'cubic_fluids_schema_JSON.h', 'cubic_fluids_schema_JSON'),
    ('pcsaft/pcsaft_fluids_schema.json', 'pcsaft_fluids_schema_JSON.h', 'pcsaft_fluids_schema_JSON'),
    ('pcsaft/all_pcsaft_fluids.json', 'all_pcsaft_JSON.h', 'all_pcsaft_JSON'),
    ('pcsaft/mixture_binary_pairs_pcsaft.json', 'mixture_binary_pairs_pcsaft_JSON.h', 'mixture_binary_pairs_pcsaft_JSON')
]
zvalues = [
    ('all_fluids.json.z', 'all_fluids_JSON_z.h', 'all_fluids_JSON_z'),
]

incbin_template = r"""/* File generated for use with incbin */

#ifdef __cplusplus
extern "C" {
#endif

/* INCBIN(%SYMBOL%, "all_fluids.json.z"); */
INCBIN_CONST INCBIN_ALIGN unsigned char g%SYMBOL%Data[] = {
%DATA%
};
INCBIN_CONST INCBIN_ALIGN unsigned char *const g%SYMBOL%End = g%SYMBOL%Data + sizeof(g%SYMBOL%Data);
INCBIN_CONST unsigned int g%SYMBOL%Size = sizeof(g%SYMBOL%Data);

#ifdef __cplusplus
}
#endif
"""


def TO_CPP(root_dir, hashes):
    def to_chunks(l, n):
        if n < 1:
            n = 1
        return [l[i:i + n] for i in range(0, len(l), n)]

    # Normalise path name
    root_dir = os.path.normpath(root_dir)

    # First we package up the JSON files
    combine_json(root_dir)
    
    def needs_build(inpath: Path, outpath: Path):
        if not outpath.exists():
            return True
        if not inpath.exists():
            raise ValueError(f"{inpath} cannot be found")
        return os.path.getmtime(inpath) > os.path.getmtime(outpath)
    
    for infile, outfile, variable in zvalues:
        inpath = Path(root_dir) / 'dev' / infile
        outpath = Path(root_dir) / 'include' / outfile
        if not needs_build(inpath=inpath, outpath=outpath):
            print(f'{outpath} is up to date based on file times')
            continue

        json_ = inpath.open('rb').read()

        # convert each character to hex and add a terminating NULL character to end the
        # string, join into a comma separated string

        try:
            h = ["0x{:02x}".format(ord(b)) for b in json_] + ['0x00']
        except TypeError:
            h = ["0x{:02x}".format(int(b)) for b in json_] + ['0x00']

        # Break up the file into lines of 16 hex characters
        chunks = to_chunks(h, 16)

        # Put the lines back together again
        # The chunks are joined together with commas, and then EOL are used to join the rest
        hex_string = ',\n'.join([', '.join(chunk) for chunk in chunks])

        # Check if hash is up to date based on using variable as key
        if not os.path.isfile(os.path.join(root_dir, 'include', outfile)) or variable not in hashes or (variable in hashes and hashes[variable] != get_hash(hex_string.encode('ascii'))):
        
            with (Path(root_dir) / 'include' / outfile).open('w') as fp:
                fp.write(incbin_template.replace('%SYMBOL%', variable).replace('%DATA%', hex_string))        

            # Store the hash of the data that was written to file (not including the header)
            hashes[variable] = get_hash(hex_string.encode('ascii'))

            print(os.path.join(root_dir, 'include', outfile) + ' written to file')
        else:
            print(outfile + ' is up to date')

    for infile, outfile, variable in values:
        inpath = Path(root_dir) / 'dev' / infile
        outpath = Path(root_dir) / 'include' / outfile
        if not needs_build(inpath=inpath, outpath=outpath):
            print(f'{outpath} is up to date based on file times')
            continue

        # Confirm that the JSON file can be loaded and doesn't have any formatting problems
        with open(os.path.join(root_dir, 'dev', infile), 'r') as fp:
            try:
                jj = json.load(fp)
            except ValueError:
                file = os.path.join(root_dir, 'dev', infile)
                print('"python -mjson.tool ' + file + '" returns ->', end='')
                subprocess.call('python -mjson.tool ' + file, shell=True)
                raise ValueError('unable to decode file %s' % file)

        json_ = open(os.path.join(root_dir, 'dev', infile), 'r').read().encode('ascii')

        # convert each character to hex and add a terminating NULL character to end the
        # string, join into a comma separated string

        try:
            h = ["0x{:02x}".format(ord(b)) for b in json_] + ['0x00']
        except TypeError:
            h = ["0x{:02x}".format(int(b)) for b in json_] + ['0x00']

        # Break up the file into lines of 16 hex characters
        chunks = to_chunks(h, 16)

        # Put the lines back together again
        # The chunks are joined together with commas, and then EOL are used to join the rest
        hex_string = ',\n'.join([', '.join(chunk) for chunk in chunks])

        # Check if hash is up to date based on using variable as key
        if not os.path.isfile(os.path.join(root_dir, 'include', outfile)) or variable not in hashes or (variable in hashes and hashes[variable] != get_hash(hex_string.encode('ascii'))):

            # Generate the output string
            output = '// File generated by the script dev/generate_headers.py on ' + str(datetime.now()) + '\n\n'
            output += '// JSON file encoded in binary form\n'
            output += 'const unsigned char ' + variable + '_binary[] = {\n' + hex_string + '\n};' + '\n\n'
            output += '// Combined into a single std::string \n'
            output += 'std::string {v:s}({v:s}_binary, {v:s}_binary + sizeof({v:s}_binary)/sizeof({v:s}_binary[0]));'.format(v=variable)

            # Write it to file
            f = open(os.path.join(root_dir, 'include', outfile), 'w')
            f.write(output)
            f.close()

            # Store the hash of the data that was written to file (not including the header)
            hashes[variable] = get_hash(hex_string.encode('ascii'))

            print(os.path.join(root_dir, 'include', outfile) + ' written to file')
        else:
            print(outfile + ' is up to date')
            
def get_version(root_dir):
    lines = open(os.path.join(root_dir, 'CMakeLists.txt'), 'r').readlines()
    # Find the necessary lines
    MAJOR_line = [line for line in lines if ('VERSION_MAJOR' in line and 'MINOR' not in line)]
    MINOR_line = [line for line in lines if ('VERSION_MINOR' in line and 'MAJOR' not in line)]
    PATCH_line = [line for line in lines if ('VERSION_PATCH' in line and 'MINOR' not in line)]
    REVISION_line = [line for line in lines if ('VERSION_REVISION' in line and 'MINOR' not in line)]
    # String processing
    MAJOR = MAJOR_line[0].strip().split('VERSION_MAJOR')[1].split(')')[0].strip()
    MINOR = MINOR_line[0].strip().split('VERSION_MINOR')[1].split(')')[0].strip()
    PATCH = PATCH_line[0].strip().split('VERSION_PATCH')[1].split(')')[0].strip()
    REVISION = REVISION_line[0].strip().split('VERSION_REVISION')[1].split(')')[0].strip()
    # Generate the strings
    version = '.'.join([MAJOR, MINOR, PATCH]) + REVISION
    return version

def version_to_file(root_dir):

    # Parse the CMakeLists.txt file to generate the version
    """
    Should have lines like
    "
    set (CoolProp_VERSION_MAJOR 5)
    set (CoolProp_VERSION_MINOR 0)
    set (CoolProp_VERSION_PATCH 0)
    "
    """

    version = get_version(root_dir)

    # Get the hash of the version
    if 'version' not in hashes or ('version' in hashes and hashes['version'] != get_hash(version.encode('ascii'))):
        hashes['version'] = get_hash(version)

        # Format the string to be written
        string_for_file = '//Generated by the generate_headers.py script on {t:s}\n\nstatic char version [] ="{v:s}";'.format(t=str(datetime.now()), v=version)

        # Include path relative to the root
        include_dir = os.path.join(root_dir, 'include')

        # The name of the file to be written into
        file_name = os.path.join(include_dir, 'cpversion.h')

        # Write to file
        f = open(file_name, 'w')
        f.write(string_for_file)
        f.close()

        print('version written to file: ' + file_name)

    else:
        print('cpversion.h is up to date')

    hidden_file_name = os.path.join(root_dir, '.version')

    # Write to file
    f = open(hidden_file_name, 'w')
    f.write(version)
    f.close()

    print('version written to hidden file: ' + hidden_file_name + " for use in builders that don't use git repo")


def gitrev_to_file(root_dir):
    """
    If a git repo, use git to update the gitrevision.  If not a git repo, read
    the gitrevision from the gitrevision.txt file.  Otherwise, fail.
    """

    try:
        try:
            subprocess.check_call('git --version', shell=True)
            print('git is accessible at the command line')

            # Try to get the git revision
            p = subprocess.Popen('git rev-parse HEAD',
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True,
                             cwd=os.path.abspath(os.path.dirname(__file__)))
            stdout, stderr = p.communicate()
            stdout = stdout.decode('utf-8')
            stderr = stderr.decode('utf-8')

            if p.returncode != 0:
                print('tried to get git revision from git, but could not (building from zip file?)')
                print(f'return code: {p.returncode}; stderr: {stderr};  stdout: {stdout}')
                gitrevision_path = os.path.join(root_dir, 'dev', 'gitrevision.txt')
                if os.path.exists(gitrevision_path):
                    gitrev = open(gitrevision_path, 'r').read().strip()
                else:
                    print(f'tried to get git revision from {gitrevision_path}, but could not; root_dir is: {root_dir}')
                    gitrev = '???'
            else:
                gitrev = stdout.strip()

                is_hash = not ' ' in gitrev

                if not is_hash:
                    raise ValueError('No hash returned from call to git, got ' + rev + ' instead')

        except subprocess.CalledProcessError:
            print('git was not found')
            gitrev = '???'

        # Include path relative to the root
        include_dir = os.path.join(root_dir, 'include')

        print('git revision is', str(gitrev))

        if 'gitrevision' not in hashes or ('gitrevision' in hashes and hashes['gitrevision'] != get_hash(gitrev)):
            print('*** Generating gitrevision.h ***')
            gitstring = '//Generated by the generate_headers.py script on {t:s}\n\nstd::string gitrevision = \"{rev:s}\";'.format(t=str(datetime.now()), rev=gitrev)

            f = open(os.path.join(include_dir, 'gitrevision.h'), 'w')
            f.write(gitstring)
            f.close()

            hashes['gitrevision'] = get_hash(gitrev)
            print(os.path.join(include_dir, 'gitrevision.h') + ' written to file')
        else:
            print('gitrevision.h is up to date')

    except (subprocess.CalledProcessError, OSError) as err:
        print('err:', err)

class DependencyManager:
    def __init__(self, sources: list[Path], destination: Path, cachefile: Path):
        self.sources = sources
        self.destination = Path(destination)
        self.cachefile = cachefile
        
    def needs_build(self):
        if not self.destination.exists():
            return True, "destination does not exist" 
        if not self.cachefile.exists():
            return True, "cache file does not exist"
        # Last modified time of destination (which must exist)
        dest_mtime = os.path.getmtime(self.destination)
        # Build if any source is newer than destination
        for source in self.sources:
            if os.path.getmtime(source) >= dest_mtime:
                return True, f"source file {source} is newer than destination"
        # Check source list if cachefile exists
        if self.cachefile.exists():
            previous_sources = pickle.load(self.cachefile.open('rb'))['sorted_sources']
            if sorted(self.sources) != previous_sources:
                return True, "source list has changed"
        return False, ""
            
    def write_cache(self):
        with self.cachefile.open('wb') as fp:
            pickle.dump(dict(sorted_sources=sorted(self.sources)), fp)
        
def combine_json(root_dir):

    depfluids = DependencyManager(destination=os.path.join(root_dir, 'dev', 'all_fluids.json.z'),
                                  sources=(Path(root_dir) / 'dev' / 'fluids').glob('*.json'),
                                  cachefile=Path(__file__).parent / '.fluiddepcache')
    
    needs, reason = depfluids.needs_build()
    if needs:
        print(f'fluids JSON need packaging because {reason}')
        
        master = []

        for file in glob.glob(os.path.join(root_dir, 'dev', 'fluids', '*.json')):

            path, file_name = os.path.split(file)
            fluid_name = file_name.split('.')[0]

            try:
                # Load the fluid file
                fluid = json.load(open(file, 'r'))
                master += [fluid]
            except ValueError:
                print('"python -mjson.tool ' + file + '" returns ->', end='')
                subprocess.call('python -mjson.tool ' + file, shell=True)
                raise ValueError('unable to decode file %s' % file)

            
            
        with (Path(root_dir) / 'dev' / 'all_fluids.json.z').open('wb') as fp:
            fp.write(zlib.compress(json.dumps(master).encode('utf-8')))
        # with (Path(root_dir) / 'include' / 'all_fluids_JSON_timestamp.h').open('w') as fp:
        #     fp.write("// File generated by the script dev/generate_headers.py on " + str(datetime.now()) + "\n\n//This file is solely used to force a rebuild if the z-compressed files have changed.")

        fp = open(os.path.join(root_dir, 'dev', 'all_fluids_verbose.json'), 'w')
        fp.write(json.dumps(master, **json_options))
        fp.close()

        fp = open(os.path.join(root_dir, 'dev', 'all_fluids.json'), 'w')
        fp.write(json.dumps(master))
        fp.close()
        
        depfluids.write_cache()

    depincomp = DependencyManager(destination=os.path.join(root_dir, 'dev', 'all_incompressibles.json'),
                                  sources=(Path(root_dir) / 'dev' / 'incompressible_liquids' / 'json').glob('*.json'),
                                  cachefile=Path(__file__).parent / '.incompdepcache')
    if depincomp.needs_build():
        print('incomp JSON need packaging')
        master = []

        for file in glob.glob(os.path.join(root_dir, 'dev', 'incompressible_liquids', 'json', '*.json')):

            path, file_name = os.path.split(file)
            fluid_name = file_name.split('.')[0]

            try:
                # Load the fluid file
                fluid = json.load(open(file, 'r'))
            except ValueError:
                print('"python -mjson.tool ' + file + '" returns ->', end='')
                subprocess.call('python -mjson.tool ' + file, shell=True)
                raise ValueError('unable to decode file %s' % file)

            master += [fluid]

        fp = open(os.path.join(root_dir, 'dev', 'all_incompressibles_verbose.json'), 'w')
        fp.write(json.dumps(master, **json_options))
        fp.close()

        fp = open(os.path.join(root_dir, 'dev', 'all_incompressibles.json'), 'w')
        fp.write(json.dumps(master))
        fp.close()
        depincomp.write_cache()


def generate():

    # import shutil
    # shutil.copy2(
    #    os.path.join(repo_root_path, 'externals', 'REFPROP-headers', 'REFPROP_lib.h'),
    #    os.path.join(repo_root_path, 'include', 'REFPROP_lib.h'))

    version_to_file(root_dir=repo_root_path)
    gitrev_to_file(root_dir=repo_root_path)

    TO_CPP(root_dir=repo_root_path, hashes=hashes)

    # Write the hashes to a hashes JSON file
    if hashes:
        fp = open(hashes_fname, 'w')
        fp.write(json.dumps(hashes))
        fp.close()


if __name__ == '__main__':
    generate()
