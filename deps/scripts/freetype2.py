
# python 2.7.9

import subprocess, os.path, os, shutil

DEBUG = False
BUILD_CONFIGURATION = "RelWithDebInfo"
PATCH_FILE = os.path.realpath(os.path.join(".", "freetype2.patch"))
BUILD_DIR = os.path.realpath(os.path.join(".", "temp_build"))
PATH_FILE = "paths.txt"
OUTPUT_DIR = os.path.realpath(os.path.join("..", "prebuilt"))
HEADER_DIR = os.path.realpath(os.path.join(OUTPUT_DIR, "include", "freetype"))
MSBUILD_PATH = None
CMAKE_PATH = None
ARCH_TO_DIR_NAME = {"Win32": "x86",
                    "Win64": "x64",
                    "ARM" : "ARM"}
PLATFORM_TO_DIR_NAME = {"Windows8.1": "Windows 8.1",
                        "WindowsPhone8.1": "Windows Phone 8.1",
                        "Windows10.0": "Windows Universal"}

class Configuration:

    def __init__(self, generator, platform, arch, system_name, system_version):
        self.generator = generator
        self.platform = platform
        self.arch = arch
        self.system_name = system_name
        self.system_version = system_version

    def generate_cmake_args(self):
        '''returns list of configuration specific args to pass to cmake'''
        args = []
        # generator
        args.append("-G")
        if self.arch == "Win32":
            args.append(self.generator)
        else:
            args.append("%s %s" % (self.generator, self.arch))
        # system name
        args.append('-DCMAKE_SYSTEM_NAME=%s' % self.system_name)
        # system version
        args.append('-DCMAKE_SYSTEM_VERSION=%s' % self.system_version)
        return args

    def output_directory(self, prefix):
        return os.path.join(prefix,
                            PLATFORM_TO_DIR_NAME[self.platform],
                            ARCH_TO_DIR_NAME[self.arch])

    def __repr__(self):
        return "Configuration(%s, %s, %s, %s, %s)" % (self.generator, self.platform, self.arch,
                                                      self.system_name, self.system_version)
        
def create_configurations():
    '''returns list of predefined Configuration objects for builds'''
    configs = [
        Configuration("Visual Studio 12 2013", "WindowsPhone8.1", "Win32", "WindowsPhone", "8.1"),
        Configuration("Visual Studio 12 2013", "WindowsPhone8.1", "ARM", "WindowsPhone", "8.1"),
        Configuration("Visual Studio 12 2013", "Windows8.1", "Win32", "WindowsStore", "8.1"),
        Configuration("Visual Studio 12 2013", "Windows8.1", "Win64", "WindowsStore", "8.1"),
        Configuration("Visual Studio 12 2013", "Windows8.1", "ARM", "WindowsStore", "8.1"),
        Configuration("Visual Studio 14 2015", "Windows10.0", "Win32", "WindowsStore", "10.0"),
        Configuration("Visual Studio 14 2015", "Windows10.0", "Win64", "WindowsStore", "10.0"),
        Configuration("Visual Studio 14 2015", "Windows10.0", "ARM", "WindowsStore", "10.0"),
    ]
    return configs

def check_path_file():
    '''returns True if path file meets requirements, False otherwise'''
    if not os.path.exists(PATH_FILE):
        return False
    fp = open(PATH_FILE, 'r')
    lines = fp.readlines()
    fp.close()
    if len(lines) < 2:
        return False
    return True

def import_paths():
    '''reads PATH_FILE if it exists, otherwise queries user for paths'''
    while not check_path_file():
        query_paths()
    fp = open(PATH_FILE, 'r')
    lines = fp.readlines()
    fp.close()
    if len(lines) >= 2:
        global MSBUILD_PATH
        global CMAKE_PATH
        MSBUILD_PATH = ' '.join(lines[0].split(' ')[2:]).rstrip()
        CMAKE_PATH = ' '.join(lines[1].split(' ')[2:]).rstrip()
        if DEBUG:
            print "MSBUILD_PATH: %s" % MSBUILD_PATH
            print "CMAKE_PATH: %s" % CMAKE_PATH

def query_paths():
    '''queries user for paths and writes them to PATH_FILE'''
    msbuild_path = raw_input("msbuild path: ")
    while not os.path.exists(msbuild_path):
        msbuild_path = raw_input("msbuild path: ")
    cmake_path = raw_input("cmake path: ")
    while not os.path.exists(msbuild_path):
        cmake_path = raw_input("cmake path: ")
    fp = open(PATH_FILE, 'w')
    fp.write("MSBUILD_PATH = %s\n" % msbuild_path)
    fp.write("CMAKE_PATH = %s\n" % cmake_path)
    fp.close()

def make_prebuilt_dirs(configs):
    '''creates output directory for each config'''
    if not os.path.exists(HEADER_DIR):
        os.makedirs(HEADER_DIR)
    for config in configs:
        if not os.path.exists(config.output_directory(OUTPUT_DIR)):
            os.makedirs(config.output_directory(OUTPUT_DIR))

def cmake_generate_project_files(config, source_code_dir):
    '''calls CMAKE_PATH to generates vcxproj files for the given config. returns 
       True if cmake exited with a result of 0, False otherwise'''
    cmake_command = [CMAKE_PATH] + config.generate_cmake_args() + [source_code_dir]
    if DEBUG:
        print cmake_command
        wait = raw_input()
    result = subprocess.call(cmake_command)
    return result == 0
    
def compile_project(config, project_filename):        
    '''calls MSBUILD_PATH to compile the existing vcxproj. returns True if the 
       process exited with a result of 0, False otherwise'''
    msbuild_command = [MSBUILD_PATH, project_filename, "/p:configuration=%s" % BUILD_CONFIGURATION]
    if DEBUG:
        print msbuild_command
        wait = raw_input()
    result = subprocess.call(msbuild_command)
    return result == 0

def add_to_prebuilt(output_dir, filename, output_filename=None):
    '''copies filename to output_dir. can optionally change copied file name'''
    source_file = os.path.join(BUILD_CONFIGURATION, filename)
    if output_filename == None:
        output_filename = filename
    shutil.copyfile(source_file, os.path.join(output_dir, output_filename))

def clean_build(build_dir):
    '''cleans generated files'''
    shutil.rmtree(build_dir, ignore_errors=True)

def add_header(input_directory, filename):
    '''copies file in input_directory to HEADER_DIR'''
    source_file = os.path.join(input_directory, filename)
    shutil.copyfile(source_file, os.path.join(HEADER_DIR, filename))

def apply_patch(patch_file, git_dir):
    '''uses git to apply patch_file to git_dir'''
    cwd = os.getcwd()
    os.chdir(git_dir)
    result = subprocess.call(["git", "apply", patch_file, "--ignore-whitespace"])
    os.chdir(cwd)
    return result == 0

def need_to_apply_patch(git_dir):
    '''returns True if patch needs to be applied (which means no changes have 
    happened to git_dir)'''
    cwd = os.getcwd()
    os.chdir(git_dir)
    result = subprocess.call(["git", "diff", "--exit-code"])
    os.chdir(cwd)
    return result == 0
    
def copy_dir_contents(input_dir, target_dir):
    '''copies input_dir contents into target_dir. will create new subdirectories 
    as needed but target_dir must already exist. Will not check before 
    overwriting files'''
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)
        target_path = os.path.join(target_dir, item)
        if not os.path.exists(target_path):
            if os.path.isdir(item_path):
                os.makedirs(target_path)
                copy_dir_contents(item_path, target_path)
            else:
                shutil.copy2(item_path, target_path)

def run():
    '''runs builds on all configurations, places binaries in prebuilt dir'''
    original_dir = os.path.realpath(".")
    import_paths()
    configs = create_configurations()
    # make sure prebuilt dir tree exists
    make_prebuilt_dirs(configs)
    src_dir = os.path.realpath(os.path.join("..", "3rdParty", "freetype2"))
    # make sure patch is applied
    if need_to_apply_patch(src_dir):
        result = apply_patch(os.path.realpath(PATCH_FILE), src_dir)
        if not result:
            print "Patch failed to apply, won't be able to generate correct builds"
            exit(1)
    # remove old build dir if it exists
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.mkdir(BUILD_DIR)
    os.chdir(BUILD_DIR)
    build_dir = os.path.realpath(".")
    failed_builds = []
    for config in configs:
        os.chdir(build_dir)
        os.makedirs(config.output_directory("."))
        os.chdir(config.output_directory("."))
        result = cmake_generate_project_files(config, src_dir)
        if result:
            result = compile_project(config, "freetype.vcxproj")
            if result:
                output_dir = config.output_directory(OUTPUT_DIR)
                add_to_prebuilt(output_dir, "freetype.dll")
                add_to_prebuilt(output_dir, "freetype.lib")
                if BUILD_CONFIGURATION in ["Debug", "RelWithDebInfo"]:
                    add_to_prebuilt(output_dir, "freetype.pdb")
                continue
        # cmake or build failed
        failed_builds.append(config)
        if DEBUG:
            print "FAILED: %s" % config
            wait = raw_input()
    os.chdir(original_dir)
    # copy relevant header files to right directory
    copy_dir_contents(os.path.join(src_dir, "include"), HEADER_DIR)
    clean_build(build_dir)
    if len(failed_builds) == 0:
        print "Successful"
        exit()
    else:
        print "%d failed builds!" % len(failed_builds)
        for config in failed_builds:
            print config
        exit(1)


if __name__ == "__main__":
    run()
